"""AI-powered property investment analysis using Claude."""
import json
import logging
import os
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.property import Property, PropertyScore
from backend.models.property_ai_insight import PropertyAIInsight

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
MODEL = 'claude-sonnet-4-6'
# Minimum seconds between API calls — prevents rate-limit (429) errors.
# Increase this if you hit throttling. At Anthropic Tier 1 (5 RPM) set to 13.
# At Tier 2 (50 RPM) set to 1.5. At Tier 3+ (1000 RPM) set to 0.
AI_CALL_DELAY = float(os.getenv('AI_CALL_DELAY', '2.0'))

VERDICT_OPTIONS = ['STRONG_BUY', 'BUY', 'HOLD', 'AVOID']

# Module-level client — created once, reused across all calls.
# max_retries=4 with exponential backoff handles transient 429s automatically.
_client = None

def _get_client():
    global _client
    if _client is None:
        try:
            import anthropic
            _client = anthropic.Anthropic(
                api_key=ANTHROPIC_API_KEY,
                max_retries=4,
            )
        except ImportError:
            raise ValueError("anthropic SDK not installed — run: pip install anthropic")
    return _client


def _build_prompt(prop: Property) -> str:
    score = prop.score
    price_str = f"£{prop.asking_price:,.0f}" if prop.asking_price else "unknown"
    est_str = f"£{score.estimated_value:,.0f}" if (score and score.estimated_value) else "no estimate"
    yield_str = f"{score.gross_yield_pct:.1f}%" if (score and score.gross_yield_pct) else "unknown"
    inv_score = f"{score.investment_score:.0f}/100" if (score and score.investment_score) else "not scored"
    price_band = score.price_band if score else "unknown"
    beds = f"{prop.bedrooms} bed" if prop.bedrooms else ""
    prop_type = f"{beds} {prop.property_type}".strip()

    return f"""You are a UK property investment analyst with deep knowledge of UK regional markets, auction dynamics, and buy-to-let fundamentals.

Analyse this property for investment potential and respond ONLY with a JSON object in this exact format:
{{
  "verdict": "<STRONG_BUY|BUY|HOLD|AVOID>",
  "confidence": <0.0-1.0>,
  "summary": "<2-3 sentence overview of the investment case>",
  "location_notes": "<what you know about this area: typical prices, rental demand, regeneration, commuter links, local economy>",
  "positives": ["<point 1>", "<point 2>", "<point 3>"],
  "risks": ["<risk 1>", "<risk 2>"]
}}

Property details:
- Address: {prop.address}
- Postcode: {prop.postcode}
- Type: {prop_type or "unknown"}
- Asking price: {price_str}
- Estimated market value: {est_str}
- Price band: {price_band}
- Estimated gross yield: {yield_str}
- Investment score: {inv_score}
- Source: {prop.status} ({getattr(prop, 'description', '')[:200] if prop.description else 'no description'})

Base your verdict on:
1. Price relative to estimated value (is it below market?)
2. Yield attractiveness for UK buy-to-let (>6% = strong, 4-6% = good, <4% = weak)
3. Your knowledge of this specific postcode/area (demand, growth prospects, risks)
4. Property type suitability for investment

Respond with JSON only, no other text."""


def analyse_property(property_id: int, db: Session, _rate_limit_delay: bool = True) -> dict:
    """Run Claude analysis on one property and store the result. Returns the insight dict.

    _rate_limit_delay: set False only when caller is already managing pacing (e.g. batch loop).
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set — add it to the backend environment variables")

    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise ValueError(f"Property {property_id} not found")

    prompt = _build_prompt(prop)

    # Enforce minimum inter-call delay before hitting the API
    if _rate_limit_delay and AI_CALL_DELAY > 0:
        time.sleep(AI_CALL_DELAY)

    try:
        import anthropic as _anthropic
        client = _get_client()
        response = client.messages.create(
            model=MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        # Surface the error clearly so callers can decide whether to retry
        logger.error("Claude API error for property %d: %s", property_id, exc)
        raise

    raw = response.content[0].text.strip()
    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    # Parse JSON response
    try:
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        data = json.loads(raw)
    except Exception as e:
        logger.error("Failed to parse Claude response: %s\nRaw: %s", e, raw[:500])
        raise ValueError(f"Claude returned unparseable response: {e}")

    verdict = data.get('verdict', 'HOLD')
    if verdict not in VERDICT_OPTIONS:
        verdict = 'HOLD'

    # Upsert insight
    insight = db.query(PropertyAIInsight).filter(PropertyAIInsight.property_id == property_id).first()
    if not insight:
        insight = PropertyAIInsight(property_id=property_id)
        db.add(insight)

    insight.verdict = verdict
    insight.confidence = float(data.get('confidence', 0.7))
    insight.summary = data.get('summary', '')[:2000]
    insight.location_notes = data.get('location_notes', '')[:2000]
    insight.positives = json.dumps(data.get('positives', []))
    insight.risks = json.dumps(data.get('risks', []))
    insight.model_used = MODEL
    insight.tokens_used = tokens_used
    insight.generated_at = datetime.utcnow()

    db.commit()
    db.refresh(insight)
    logger.info("AI analysis complete for property %d: %s (%.0f tokens)", property_id, verdict, tokens_used)

    return {
        'property_id': property_id,
        'verdict': verdict,
        'confidence': insight.confidence,
        'summary': insight.summary,
        'location_notes': insight.location_notes,
        'positives': data.get('positives', []),
        'risks': data.get('risks', []),
        'tokens_used': tokens_used,
    }


import re as _re
_POSTCODE_RE = _re.compile(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', _re.IGNORECASE)


def ai_guess_postcode(address: str) -> Optional[str]:
    """Ask Claude Haiku to infer a UK postcode from a property address.

    Returns a validated postcode string or None if uncertain.
    Uses the cheapest model and minimal tokens — ~50 tokens per call.
    """
    if not address or not ANTHROPIC_API_KEY:
        return None
    try:
        client = _get_client()
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=20,
            messages=[{
                'role': 'user',
                'content': (
                    f'UK property address: "{address}"\n'
                    'Reply with ONLY the most likely UK postcode (e.g. NG1 5AB), '
                    'or reply UNKNOWN if you cannot determine it.'
                ),
            }],
        )
        reply = (msg.content[0].text or '').strip().upper()
        if reply == 'UNKNOWN' or not reply:
            return None
        m = _POSTCODE_RE.search(reply)
        return m.group(0).upper() if m else None
    except Exception as e:
        logger.warning("ai_guess_postcode failed for %r: %s", address[:60], e)
        return None
