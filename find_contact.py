"""
find_contact.py — Looks for a contact email address on a business's
public homepage: checks mailto: links first (most reliable, explicitly
meant to be found), then falls back to scanning visible text for
anything that looks like an email address.

Only reads publicly served page content - same as detect_chatbot.py.
"""

import re
from bs4 import BeautifulSoup

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Generic addresses that technically match the pattern but are almost
# never useful for outreach (image files, placeholder examples, etc.)
IGNORE_PATTERNS = ["example.com", "yourdomain", "sentry.io", ".png", ".jpg", ".gif", ".svg"]


def find_contact_email(html: str) -> str | None:
    """Returns the best-guess contact email found on the page, or None."""
    soup = BeautifulSoup(html, "html.parser")

    # Priority 1: an explicit mailto: link - the site owner deliberately
    # made this address clickable for contact purposes.
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if email and not _should_ignore(email):
                return email

    # Priority 2: scan visible text for anything email-shaped.
    text = soup.get_text(separator=" ")
    matches = EMAIL_PATTERN.findall(text)
    for email in matches:
        if not _should_ignore(email):
            return email

    return None


def _should_ignore(email: str) -> bool:
    email_lower = email.lower()
    return any(pattern in email_lower for pattern in IGNORE_PATTERNS)


if __name__ == "__main__":
    sample_html = '''
    <html><body>
        <p>Contact us at info@example-business.com or visit our office.</p>
        <a href="mailto:sales@example-business.com">Email Sales</a>
    </body></html>
    '''
    print(find_contact_email(sample_html))  # should print the mailto one first
