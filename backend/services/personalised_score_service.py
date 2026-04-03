"""Personalised deal score — adjusts base score using investor profile."""
from typing import Dict, Any, Optional, List


STRATEGY_LABELS = {
    'btl': 'BTL Score',
    'hmo': 'HMO Score',
    'flip': 'Flip Score',
    'development': 'Development Score',
    'brrr': 'BRRR Score',
}


def personalise(score, profile, asking_price: float, postcode: str) -> Dict[str, Any]:
    """
    Adjust base score using investor profile. Returns personalised score dict.
    Does NOT modify the stored score — all adjustments are request-time only.
    """
    notes: List[str] = []
    adjustment = 0.0
    strategy = getattr(profile, 'strategy', None) or None
    label = STRATEGY_LABELS.get(strategy, 'Deal Score')

    base = score.investment_score or 0

    # Strategy-specific adjustments
    if strategy == 'btl':
        if score.gross_yield_pct and score.gross_yield_pct > 8:
            adjustment += 3
            notes.append("Strong BTL yield above 8%.")
        if not getattr(profile, 'hmo_experience', False):
            notes.append("Note: HMO licence required if 3+ unrelated tenants — you have not indicated HMO experience.")

    elif strategy == 'flip':
        if score.price_score and score.price_score > 25:
            adjustment += 5
            notes.append("Below-market entry price — strong flip potential.")

    # Experience-based notes
    experience = getattr(profile, 'investment_experience', None)
    if experience == 'first_time':
        notes.append("As a first-time investor, consider taking professional advice on this type of property.")

    # Credit history
    credit = getattr(profile, 'credit_history', None)
    if credit == 'adverse':
        notes.append("With adverse credit history, standard mortgage products may be limited — bridging finance is likely the most accessible route.")

    # UK residency — SDLT surcharge
    if getattr(profile, 'uk_resident', True) is False:
        notes.append("Non-UK resident: 2% SDLT surcharge applies to this purchase.")

    # Main residence — additional dwelling surcharge
    if getattr(profile, 'main_residence', True) is False:
        notes.append("Additional dwelling: 3% SDLT surcharge applies.")

    # Deposit check
    max_deposit = getattr(profile, 'max_deposit', None)
    if max_deposit and asking_price and max_deposit < asking_price * 0.25:
        notes.append("Your indicated deposit may be below the minimum required for bridging finance on this property type.")

    # Location mismatch
    target = getattr(profile, 'target_location', None)
    location_mismatch = False
    if target and postcode:
        target_lower = target.lower().strip()
        postcode_lower = postcode.lower().strip()
        if target_lower not in postcode_lower and postcode_lower[:3] not in target_lower:
            location_mismatch = True
            notes.append(f"This property is outside your target area ({target}).")

    # Readiness
    readiness = getattr(profile, 'readiness', None)
    if readiness == 'researching':
        notes.append("Area trend data is shown below — take time to understand the local market before committing.")

    personalised_score = min(100, max(0, base + adjustment))

    return {
        'base_score': base,
        'adjustment': adjustment,
        'personalised_score': round(personalised_score, 1),
        'label': label,
        'notes': notes,
        'location_mismatch': location_mismatch,
    }
