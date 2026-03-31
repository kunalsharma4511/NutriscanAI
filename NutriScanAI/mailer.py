# mailer.py
# NutriScan AI — Gmail SMTP Email Sender
#
# Setup (one-time):
#   1. Go to myaccount.google.com → Security → 2-Step Verification → ON
#   2. Go to myaccount.google.com → Security → App Passwords
#   3. Create an app password for "Mail" → copy the 16-char password
#   4. Add to .streamlit/secrets.toml:
#
#      GMAIL_ADDRESS  = "yourgmail@gmail.com"
#      GMAIL_APP_PASS = "xxxx xxxx xxxx xxxx"   # 16-char app password
#      APP_BASE_URL   = "http://localhost:8501"  # change for production

import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_config() -> tuple[str, str, str]:
    """Load mail config from Streamlit secrets."""
    try:
        gmail   = st.secrets["GMAIL_ADDRESS"]
        app_pwd = st.secrets["GMAIL_APP_PASS"]
        base    = st.secrets.get("APP_BASE_URL", "http://localhost:8501")
        return gmail, app_pwd, base
    except Exception:
        raise RuntimeError(
            "Email not configured. Add GMAIL_ADDRESS, GMAIL_APP_PASS "
            "and APP_BASE_URL to .streamlit/secrets.toml"
        )


def send_reset_email(to_email: str, token: str) -> bool:
    """
    Send a password reset email with a clickable link.
    Returns True on success, False on failure.
    """
    try:
        gmail, app_pwd, base_url = _get_config()
    except RuntimeError:
        return False

    reset_url = f"{base_url}?reset_token={token}"

    # ── HTML email body ───────────────────────────────────────────────────────
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    body {{ font-family: 'DM Sans', Arial, sans-serif; background: #f7f9fc; margin: 0; padding: 0; }}
    .wrap {{ max-width: 520px; margin: 40px auto; background: #ffffff;
             border-radius: 16px; overflow: hidden;
             border: 1px solid #e0e4ea; }}
    .header {{ background: #0d1f0e; padding: 32px 40px; text-align: center; }}
    .logo-box {{ display: inline-block; background: #27ae60;
                 border-radius: 12px; padding: 10px 18px;
                 font-size: 22px; font-weight: 700; color: #fff;
                 letter-spacing: -0.5px; }}
    .logo-box span {{ font-weight: 400; color: #a8f0c0; }}
    .body {{ padding: 36px 40px; }}
    h2 {{ color: #1a1a1a; font-size: 22px; font-weight: 700;
          margin: 0 0 12px; letter-spacing: -0.3px; }}
    p {{ color: #555; font-size: 15px; line-height: 1.7; margin: 0 0 20px; }}
    .btn {{ display: inline-block; background: #27ae60; color: #ffffff !important;
            text-decoration: none; padding: 14px 32px; border-radius: 10px;
            font-weight: 700; font-size: 15px; letter-spacing: 0.2px; }}
    .expire {{ font-size: 13px; color: #999; margin-top: 24px; }}
    .footer {{ background: #f7f9fc; padding: 20px 40px; text-align: center;
               font-size: 12px; color: #aaa; border-top: 1px solid #e0e4ea; }}
    .url-fallback {{ word-break: break-all; font-size: 12px; color: #888;
                     margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="logo-box">Nutri<span>Scan</span> AI</div>
    </div>
    <div class="body">
      <h2>Reset your password</h2>
      <p>We received a request to reset the password for your NutriScan AI account
         associated with <strong>{to_email}</strong>.</p>
      <p>Click the button below to set a new password:</p>
      <a href="{reset_url}" class="btn">Reset my password</a>
      <p class="expire">⏱ This link expires in <strong>30 minutes</strong>.
         If you didn't request a reset, you can safely ignore this email.</p>
      <p class="url-fallback">Or copy this link into your browser:<br>{reset_url}</p>
    </div>
    <div class="footer">
      NutriScan AI · Nutrition Intelligence · This is an automated message
    </div>
  </div>
</body>
</html>
"""

    plain = (
        f"Reset your NutriScan AI password\n\n"
        f"Click this link to reset your password (expires in 30 minutes):\n"
        f"{reset_url}\n\n"
        f"If you didn't request a reset, ignore this email."
    )

    # ── Build and send ────────────────────────────────────────────────────────
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your NutriScan AI password"
        msg["From"]    = f"NutriScan AI <{gmail}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, app_pwd)
            server.sendmail(gmail, to_email, msg.as_string())

        return True

    except Exception as e:
        print(f"[mailer] Failed to send reset email: {e}")
        return False


def is_configured() -> bool:
    """Return True if email secrets are present in secrets.toml."""
    try:
        _get_config()
        return True
    except Exception:
        return False