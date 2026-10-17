"""
detect_chatbot.py — Fetches a business's public homepage and checks for
known chatbot/live-chat widget fingerprints. This only reads publicly
served page content - the same thing your own browser downloads when you
visit the site - not scraping anything private or authenticated.
"""

import requests
from bs4 import BeautifulSoup

# Known script/domain fingerprints for common chat widget providers.
# If any of these show up in the page's HTML, the business already has
# a chat solution - not a great lead for "you don't have this yet."
CHATBOT_FINGERPRINTS = {
    "Intercom": "widget.intercom.io",
    "Drift": "js.driftt.com",
    "Tidio": "code.tidio.co",
    "Tawk.to": "embed.tawk.to",
    "Crisp": "client.crisp.chat",
    "Zendesk Chat": "static.zdassets.com",
    "HubSpot Chat": "js.hs-scripts.com",
    "LiveChat": "cdn.livechatinc.com",
}


def fetch_page(url: str, timeout: int = 10) -> str:
    """Fetch a page's raw HTML. Uses a normal browser User-Agent since
    some sites block requests that don't look like a real browser."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LeadResearchBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def detect_chatbot(html: str) -> dict:
    """Checks the page HTML for known chatbot fingerprints."""
    found = [name for name, fingerprint in CHATBOT_FINGERPRINTS.items() if fingerprint in html]
    return {
        "has_chatbot": len(found) > 0,
        "detected_providers": found,
    }


def extract_visible_text(html: str, max_chars: int = 3000) -> str:
    """Pulls out the human-readable text from a page, stripping scripts/
    styles/tags - this is what gets sent to the LLM to understand what
    the business actually does, without wasting tokens on raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:max_chars]


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    html = fetch_page(url)
    result = detect_chatbot(html)
    print(f"URL: {url}")
    print(f"Has chatbot: {result['has_chatbot']}")
    if result["detected_providers"]:
        print(f"Detected: {', '.join(result['detected_providers'])}")
    print(f"\nSample visible text:\n{extract_visible_text(html)[:300]}...")
