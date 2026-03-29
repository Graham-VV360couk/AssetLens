"""
Email Alert Service (Task #19)
Sends daily digest of high-investment-score properties.
"""
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from jinja2 import Template

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; }
  .container { max-width: 680px; margin: 0 auto; padding: 24px; }
  .header { background: #1e293b; border-radius: 16px; padding: 24px; margin-bottom: 24px; border: 1px solid #334155; }
  .header h1 { color: #10b981; margin: 0 0 4px 0; font-size: 24px; }
  .header p { color: #94a3b8; margin: 0; font-size: 14px; }
  .stats-row { display: flex; gap: 12px; margin-bottom: 24px; }
  .stat-box { flex: 1; background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; }
  .stat-box .value { font-size: 28px; font-weight: 800; color: #10b981; }
  .stat-box .label { font-size: 12px; color: #64748b; margin-top: 4px; }
  .section-title { color: #94a3b8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; }
  .property-card { background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 20px; margin-bottom: 12px; }
  .property-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
  .address { font-size: 15px; font-weight: 600; color: #f1f5f9; }
  .postcode { font-size: 12px; color: #64748b; margin-top: 2px; }
  .price { font-size: 20px; font-weight: 800; color: #10b981; }
  .est { font-size: 12px; color: #64748b; }
  .metrics { display: flex; gap: 16px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #334155; }
  .metric { text-align: center; }
  .metric .mval { font-size: 18px; font-weight: 700; }
  .metric .mlbl { font-size: 11px; color: #64748b; margin-top: 2px; }
  .score-high { color: #10b981; }
  .score-med { color: #f59e0b; }
  .band-brilliant { background: #064e3b; color: #34d399; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .band-good { background: #14532d; color: #4ade80; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .band-fair { background: #451a03; color: #fbbf24; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .cta { display: inline-block; background: #10b981; color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 10px; font-weight: 600; font-size: 14px; margin-top: 20px; }
  .footer { text-align: center; color: #475569; font-size: 11px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #1e293b; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>AssetLens Daily Digest</h1>
    <p>{{ date }} — {{ total_high_value }} high-value opportunities identified today</p>
  </div>

  <div class="stats-row">
    <div class="stat-box">
      <div class="value">{{ total_high_value }}</div>
      <div class="label">Score ≥ 70</div>
    </div>
    <div class="stat-box">
      <div class="value">{{ brilliant_count }}</div>
      <div class="label">Brilliant Deals</div>
    </div>
    <div class="stat-box">
      <div class="value">{{ avg_score }}</div>
      <div class="label">Avg Score</div>
    </div>
  </div>

  <div class="section-title">Top Investment Opportunities</div>

  {% for prop in properties %}
  <div class="property-card">
    <div class="property-header">
      <div>
        {% if prop.score and prop.score.price_band %}
        <span class="band-{{ prop.score.price_band }}">{{ prop.score.price_band | capitalize }}</span>
        {% endif %}
        <div class="address" style="margin-top: 8px;">{{ prop.address }}</div>
        <div class="postcode">{{ prop.postcode }}{% if prop.town %} · {{ prop.town }}{% endif %}</div>
      </div>
      <div style="text-align: right;">
        <div class="price">£{{ "{:,}".format(prop.asking_price) if prop.asking_price else "—" }}</div>
        {% if prop.score and prop.score.estimated_value %}
        <div class="est">Est. £{{ "{:,}".format(prop.score.estimated_value | int) }}</div>
        {% endif %}
      </div>
    </div>
    <div class="metrics">
      <div class="metric">
        <div class="mval {% if prop.score and prop.score.investment_score >= 70 %}score-high{% else %}score-med{% endif %}">
          {{ (prop.score.investment_score | int) if prop.score and prop.score.investment_score else "—" }}
        </div>
        <div class="mlbl">Score</div>
      </div>
      <div class="metric">
        <div class="mval" style="color: #22c55e;">
          {{ "%.1f%%" | format(prop.score.gross_yield_pct) if prop.score and prop.score.gross_yield_pct else "—" }}
        </div>
        <div class="mlbl">Yield</div>
      </div>
      <div class="metric">
        <div class="mval" style="color: {% if prop.score and prop.score.price_deviation_pct < 0 %}#10b981{% else %}#ef4444{% endif %};">
          {% if prop.score and prop.score.price_deviation_pct is not none %}
            {{ "%.1f%%" | format(prop.score.price_deviation_pct * 100) }}
          {% else %}—{% endif %}
        </div>
        <div class="mlbl">vs Market</div>
      </div>
      <div class="metric">
        <div class="mval" style="color: #94a3b8;">
          {{ prop.bedrooms if prop.bedrooms else "—" }}
        </div>
        <div class="mlbl">Bedrooms</div>
      </div>
    </div>
  </div>
  {% endfor %}

  <a href="{{ dashboard_url }}" class="cta">View Full Dashboard →</a>

  <div class="footer">
    <p>AssetLens Property Intelligence Dashboard</p>
    <p>Contains Land Registry data © Crown copyright and database right 2026. Open Government Licence v3.0.</p>
    <p>Property data licensed from Searchland/PropertyData.</p>
  </div>
</div>
</body>
</html>
"""


class EmailAlertService:
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.sendgrid.net')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER', 'apikey')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', 'alerts@assetlens.co.uk')
        self.to_email = os.environ.get('ALERT_EMAIL', '')
        self.dashboard_url = os.environ.get('DASHBOARD_URL', 'http://localhost:3000')

    def send_daily_digest(self, properties: list, stats: dict) -> bool:
        if not self.to_email:
            logger.warning("ALERT_EMAIL not configured - skipping email")
            return False

        if not self.smtp_password:
            logger.warning("SMTP_PASSWORD not configured - skipping email")
            return False

        subject = f"AssetLens Daily Digest — {stats.get('total_high_value', 0)} high-value opportunities ({datetime.utcnow().strftime('%d %b %Y')})"

        template = Template(EMAIL_TEMPLATE)
        html = template.render(
            date=datetime.utcnow().strftime('%d %B %Y'),
            total_high_value=stats.get('total_high_value', 0),
            brilliant_count=stats.get('brilliant_count', 0),
            avg_score=stats.get('avg_score', '—'),
            properties=properties[:20],  # Top 20
            dashboard_url=self.dashboard_url,
        )

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [self.to_email], msg.as_string())

            logger.info("Daily digest sent to %s", self.to_email)
            return True

        except Exception as e:
            logger.error("Failed to send email: %s", e)
            return False

    def send_notification(self, subject: str, body: str) -> bool:
        """Send a plain-text email. Used for internal notifications."""
        if not self.to_email or not self.smtp_password:
            logger.warning("Email not configured — skipping notification")
            return False
        try:
            msg = MIMEText(body, 'plain')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [self.to_email], msg.as_string())
            logger.info("Notification email sent: %s", subject)
            return True
        except Exception as e:
            logger.error("Failed to send notification email: %s", e)
            return False
