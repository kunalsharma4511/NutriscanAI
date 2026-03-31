# test_mail.py
# Run this directly: python test_mail.py
# This bypasses Streamlit secrets and tests Gmail SMTP directly.
# Delete this file after debugging.

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Fill these in directly for testing ───────────────────────────────────────
GMAIL_ADDRESS  = "nutriscanai.dev@gmail.com"    # ← the Gmail that sends
GMAIL_APP_PASS = "kozi cuni nfsj uuki"      # ← the 16-char app password
SEND_TO        = "kunalsharmap451@gmail.com"  # ← where to send the test email
# ─────────────────────────────────────────────────────────────────────────────

print(f"Testing Gmail SMTP...")
print(f"  From : {GMAIL_ADDRESS}")
print(f"  To   : {SEND_TO}")
print(f"  Pass : {GMAIL_APP_PASS[:4]}{'*' * 12}")
print()

try:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "NutriScan AI — SMTP test"
    msg["From"]    = f"NutriScan AI <{GMAIL_ADDRESS}>"
    msg["To"]      = SEND_TO
    msg.attach(MIMEText("If you see this, Gmail SMTP is working correctly.", "plain"))

    print("Connecting to smtp.gmail.com:465 ...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        print("Connected. Logging in...")
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
        print("Login successful. Sending...")
        server.sendmail(GMAIL_ADDRESS, SEND_TO, msg.as_string())
        print()
        print("SUCCESS — email sent! Check your inbox (and spam folder).")

except smtplib.SMTPAuthenticationError:
    print()
    print("FAILED — Authentication error.")
    print("Possible causes:")
    print("  1. Wrong App Password — re-generate it at myaccount.google.com/apppasswords")
    print("  2. 2-Step Verification is not enabled on this Gmail account")
    print("  3. You used your real Gmail password instead of the App Password")

except smtplib.SMTPException as e:
    print(f"FAILED — SMTP error: {e}")

except Exception as e:
    print(f"FAILED — Unexpected error: {e}")
    print("Possible cause: firewall or antivirus blocking port 465")