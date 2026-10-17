"""
send_email.py — Actually sends an email via Gmail's SMTP server.

SAFETY DESIGN, read this before using:
- TEST_MODE (default: True) sends every email to YOUR OWN inbox instead
  of the real contact, with "[TEST]" in the subject and the real intended
  recipient shown in the body. This lets you see exactly what a real send
  looks like, safely, before anything reaches an actual business.
- Setting TEST_MODE to False in .env enables real sending, but
  agent3_send_outreach.py still asks for an explicit y/n confirmation
  before EVERY individual email, even in live mode. There is no
  "send all, no questions asked" path in this codebase, by design.
"""

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() != "false"


def send_email(to_email: str, subject: str, body: str) -> dict:
    """Sends one email. In TEST_MODE, redirects to your own inbox instead
    of the real recipient, and clearly marks it as a test."""
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        return {"sent": False, "error": "Set SENDER_EMAIL and SENDER_APP_PASSWORD in .env first."}

    actual_recipient = to_email
    actual_subject = subject
    actual_body = body

    if TEST_MODE:
        actual_recipient = SENDER_EMAIL
        actual_subject = f"[TEST - would go to {to_email}] {subject}"
        actual_body = f"--- TEST MODE: this would have been sent to {to_email} ---\n\n{body}"

    msg = MIMEText(actual_body)
    msg["Subject"] = actual_subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = actual_recipient

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.send_message(msg)
        return {"sent": True, "mode": "TEST" if TEST_MODE else "LIVE", "actual_recipient": actual_recipient}
    except Exception as e:
        return {"sent": False, "error": str(e)}


if __name__ == "__main__":
    result = send_email(
        to_email="someone@example.com",
        subject="Test subject",
        body="This is a test email body.",
    )
    print(result)
