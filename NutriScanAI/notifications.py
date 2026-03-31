# notifications.py
# NutriScan AI — Push Notifications (Email Digest)
#
# Streamlit apps can't send true browser push notifications without a
# service worker + HTTPS setup. This module implements the practical
# alternative: a daily/weekly email digest of the user's scan activity.
#
# Additionally, in-app toast notifications are shown after each scan.
#
# Setup: same Gmail credentials as mailer.py (no extra config needed).

import streamlit as st
from mailer import send_reset_email, is_configured
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import load_scans, get_scan_count


# ─────────────────────────────────────────────────────────────────────────────
#  IN-APP TOAST  (shown immediately after a scan)
# ─────────────────────────────────────────────────────────────────────────────

def show_scan_toast(report_data: dict):
    """
    Show an in-app styled notification after a scan completes.
    Call this right after _add_to_history() in app.py.
    """
    dark    = st.session_state.get("dark_mode", True)
    score   = report_data.get("display_score")
    product = report_data.get("product_name", "Product")
    freq    = report_data.get("consumption_frequency", "")

    if score is None:
        return

    if score >= 8:
        colour, icon, msg = "#27ae60", "✓", "Great choice!"
    elif score >= 6:
        colour, icon, msg = "#2980b9", "ℹ", "Decent option."
    elif score >= 4:
        colour, icon, msg = "#f39c12", "⚠", "Consume in moderation."
    else:
        colour, icon, msg = "#e74c3c", "✕", "Consider a healthier alternative."

    freq_line = f"<br><span style='font-size:11px;opacity:0.8;'>Recommended: {freq.title()}</span>" \
                if freq else ""

    st.markdown(f"""
<div style="
    background:{"#1a1a1a" if dark else "#ffffff"};
    border:1px solid {colour}40;
    border-left:4px solid {colour};
    border-radius:10px;
    padding:12px 16px;
    margin:12px 0;
    display:flex;
    align-items:center;
    gap:12px;
">
  <div style="
      width:36px;height:36px;border-radius:50%;
      background:{colour}20;
      display:flex;align-items:center;justify-content:center;
      font-size:16px;flex-shrink:0;color:{colour}!important;
  ">{icon}</div>
  <div>
    <div style="font-weight:700;font-size:14px;">{product}</div>
    <div style="font-size:13px;color:{colour}!important;">
      {score}/10 — {msg}{freq_line}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  EMAIL DIGEST
# ─────────────────────────────────────────────────────────────────────────────

def _build_digest_html(user_name: str, scans: list, total: int) -> str:
    """Build the HTML body for a digest email."""
    rows = ""
    for s in scans[:10]:
        sc    = s["score"]
        if sc is None: continue
        if sc >= 8:   col = "#27ae60"
        elif sc >= 6: col = "#2980b9"
        elif sc >= 4: col = "#f39c12"
        else:         col = "#e74c3c"
        rows += f"""
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;font-size:14px;">
            {s['product_name']}
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;text-align:center;">
            <span style="font-weight:700;color:{col};">{sc}/10</span>
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;
                     font-size:12px;color:#888;">
            {s.get('scanned_date','')}
          </td>
        </tr>"""

    return f"""
<!DOCTYPE html><html><head><meta charset="utf-8"/></head>
<body style="font-family:Arial,sans-serif;background:#f7f9fc;margin:0;padding:0;">
<div style="max-width:560px;margin:32px auto;background:#fff;
            border-radius:16px;overflow:hidden;border:1px solid #e0e4ea;">
  <div style="background:#0d1f0e;padding:28px 36px;">
    <div style="display:inline-block;background:#27ae60;border-radius:10px;
                padding:8px 16px;font-size:18px;font-weight:700;color:#fff;">
      Nutri<span style="font-weight:400;color:#a8f0c0;">Scan</span> AI
    </div>
  </div>
  <div style="padding:32px 36px;">
    <h2 style="font-size:20px;font-weight:700;color:#1a1a1a;margin:0 0 8px;">
      Your nutrition digest, {user_name.split()[0]}
    </h2>
    <p style="font-size:14px;color:#666;margin:0 0 24px;">
      Here's a summary of your recent scans. You've scanned
      <strong>{total}</strong> products so far.
    </p>
    <table style="width:100%;border-collapse:collapse;
                  border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
      <thead>
        <tr style="background:#f7f9fc;">
          <th style="padding:10px 16px;text-align:left;font-size:12px;
                     color:#888;font-weight:600;letter-spacing:0.5px;">PRODUCT</th>
          <th style="padding:10px 16px;text-align:center;font-size:12px;
                     color:#888;font-weight:600;letter-spacing:0.5px;">SCORE</th>
          <th style="padding:10px 16px;text-align:left;font-size:12px;
                     color:#888;font-weight:600;letter-spacing:0.5px;">DATE</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="font-size:13px;color:#888;margin-top:24px;">
      Keep scanning to build your nutrition intelligence.
      Your personalised health score improves as you log more meals.
    </p>
  </div>
  <div style="background:#f7f9fc;padding:16px 36px;text-align:center;
              font-size:12px;color:#aaa;border-top:1px solid #e0e4ea;">
    NutriScan AI · You're receiving this because you enabled digests
  </div>
</div>
</body></html>"""


def send_digest_email(to_email: str, user_name: str) -> bool:
    """
    Send a scan activity digest to the user.
    Returns True on success.
    """
    if not is_configured():
        return False

    try:
        gmail   = st.secrets["GMAIL_ADDRESS"]
        app_pwd = st.secrets["GMAIL_APP_PASS"]
    except Exception:
        return False

    scans = load_scans(to_email, limit=10)
    total = get_scan_count(to_email)

    if not scans:
        return False

    html  = _build_digest_html(user_name, scans, total)
    plain = f"Your NutriScan AI digest — {total} scans recorded. Open in a browser to view."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your NutriScan AI digest — {total} scans"
        msg["From"]    = f"NutriScan AI <{gmail}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, app_pwd)
            server.sendmail(gmail, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[notifications] Failed to send digest: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  NOTIFICATION SETTINGS WIDGET  (for sidebar or profile page)
# ─────────────────────────────────────────────────────────────────────────────

def render_notification_settings():
    """
    Render a notification preferences widget.
    Embed this inside your sidebar or profile page.
    """
    dark    = st.session_state.get("dark_mode", True)
    subtext = "#888888" if dark else "#666666"
    user    = st.session_state.get("current_user", {})
    email   = user.get("email", "")
    name    = user.get("name", "")

    st.markdown(f"<div style='font-size:11px;font-weight:700;color:{subtext};"
                f"letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;'>"
                f"Notifications</div>", unsafe_allow_html=True)

    configured = is_configured()

    if not configured:
        st.caption("Add GMAIL_ADDRESS and GMAIL_APP_PASS to secrets.toml to enable email notifications.")
        return

    if "notif_digest" not in st.session_state:
        st.session_state.notif_digest = False

    st.session_state.notif_digest = st.toggle(
        "Email digest",
        value=st.session_state.notif_digest,
        key="notif_digest_toggle",
        help="Receive a summary of your recent scans by email"
    )

    if st.session_state.notif_digest:
        st.caption(f"Digests will be sent to {email}")
        if st.button("Send digest now", use_container_width=True, key="send_digest_now"):
            with st.spinner("Sending..."):
                ok = send_digest_email(email, name)
            if ok:
                st.success("Digest sent! Check your inbox.")
            else:
                st.error("Failed to send. Check your Gmail credentials.")