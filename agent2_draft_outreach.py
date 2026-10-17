"""
agent2_draft_outreach.py — Agent 2: Outreach Drafter.

Reads leads_report.csv (Agent 1's output), and for leads YOU choose to
pursue, drafts a personalized outreach email using the actual research
Agent 1 already did - grounded in the real business_type and reason
fields, not generic template filler.

Now includes: a subject line, your portfolio link inserted automatically,
and a best-effort search for a real contact person's name.

THIS AGENT NEVER SENDS ANYTHING. It writes drafts to outreach_drafts.csv
for you to read, edit, and send yourself from your own email client. That
gate is deliberate: an AI autonomously emailing real people in your name
is a fundamentally different risk than an AI drafting text for you to
review first.

IMPORTANT: the contact name found by this agent is a BEST-EFFORT GUESS
from a web search, not a verified fact - unlike the chatbot-detection or
email-finding logic (which read one deterministic page), a person's name
found via broader search could be outdated, wrong, or belong to someone
who has since left the company. Every draft is labeled with whether the
name is confirmed or a guess. ALWAYS verify a guessed name yourself
before using it in a real email.

Usage:
    python agent2_draft_outreach.py
"""

import os
import csv
import time
import random
import requests
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_URL = "https://api.tavily.com/search"
INPUT_FILE = "leads_report.csv"
OUTPUT_FILE = "outreach_drafts.csv"

# Only draft outreach for leads at or above this quality, AND only ones
# where Agent 1 actually found a contact email. Edit this if you want to
# also include "Medium" quality leads.
MIN_LEAD_QUALITY = ["High"]

YOUR_NAME = "Hasan Khan"
YOUR_SERVICE = "custom AI chatbots trained on your business's own documents and FAQs"
# Put your real Fiverr gig URL or a portfolio/demo link here once it's live.
YOUR_PORTFOLIO_LINK = "https://www.fiverr.com/hasankhanai"

DRAFT_PROMPT = """Write a short, professional cold outreach email introducing
an AI automation service to a business.

Business type: {business_type}
Why they're a good fit: {reason}
Greeting to use: {greeting}

My name: {your_name}
My service: {your_service}
My portfolio/proof link: {portfolio_link}

Rules:
- Start with exactly this greeting: "{greeting}"
- Keep the body under 130 words.
- Reference their SPECIFIC business type and situation (from the info
  above) - do not write a generic template that could apply to anyone.
- Do not invent details about their business beyond what's given above.
- Naturally mention the portfolio/proof link once, as evidence, not as
  a hard sell.
- Professional, warm, no hype/exaggeration. No emojis.
- End with a soft call to action (e.g. offering a quick call or demo),
  not a hard sales push.
- Output in exactly this format, nothing else:
SUBJECT: <a short, specific subject line, under 60 characters>
BODY:
<the email body>
"""


def find_contact_name(business_type: str, url: str) -> dict:
    """Best-effort search for a real contact person's name (owner, CEO,
    founder) for this business. Returns {'name': str or None, 'confidence':
    'guess'} - this is NEVER treated as confirmed fact, since it comes from
    a broader web search rather than the business's own page."""
    if not TAVILY_API_KEY:
        return {"name": None, "confidence": "no_search_configured"}

    domain = url.split("//")[-1].split("/")[0]
    query = f"{domain} {business_type} founder OR CEO OR owner name"

    try:
        payload = {"api_key": TAVILY_API_KEY, "query": query, "max_results": 3, "search_depth": "basic"}
        resp = requests.post(TAVILY_URL, json=payload, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        snippet_text = " ".join(r.get("content", "")[:500] for r in results)
        if not snippet_text.strip():
            return {"name": None, "confidence": "not_found"}

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = (
            f"Based ONLY on this text, is there a specific named person (founder, "
            f"CEO, or owner) mentioned for this business? Text: {snippet_text[:2000]}\n\n"
            f"Reply with ONLY the person's name if clearly stated, or exactly "
            f"'NONE' if no specific name is clearly given. Do not guess or infer "
            f"a name that isn't explicitly written in the text."
        )
        response = model.generate_content(prompt)
        name = response.text.strip()
        if name.upper() == "NONE" or len(name) > 50:
            return {"name": None, "confidence": "not_found"}
        return {"name": name, "confidence": "guess"}
    except Exception:
        return {"name": None, "confidence": "search_failed"}


def draft_email(business_type: str, reason: str, greeting: str, model) -> dict:
    prompt = DRAFT_PROMPT.format(
        business_type=business_type,
        reason=reason,
        greeting=greeting,
        your_name=YOUR_NAME,
        your_service=YOUR_SERVICE,
        portfolio_link=YOUR_PORTFOLIO_LINK,
    )
    response = model.generate_content(prompt)
    text = response.text.strip()

    subject, body = "", text
    if "SUBJECT:" in text and "BODY:" in text:
        subject = text.split("SUBJECT:")[1].split("BODY:")[0].strip()
        body = text.split("BODY:")[1].strip()
    return {"subject": subject, "body": body}


def draft_email_with_retry(business_type: str, reason: str, greeting: str, model, max_retries: int = 3) -> dict:
    """Gemini's free tier caps requests per minute - retry with backoff
    instead of just recording the failure."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return draft_email(business_type, reason, greeting, model)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait = 15 * attempt + random.uniform(0, 3)
                print(f"    Rate limited, waiting {wait:.0f}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait)
    return {"subject": "", "body": f"DRAFT FAILED after {max_retries} attempts: {last_error}"}


def main():
    if not GEMINI_API_KEY:
        print("Set GEMINI_API_KEY in .env first.")
        return
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} not found - run agent1_find_leads.py first.")
        return

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    candidates = [
        lead for lead in leads
        if lead.get("status") == "researched"
        and lead.get("lead_quality") in MIN_LEAD_QUALITY
        and lead.get("contact_email", "").strip()
    ]

    skipped_no_email = [
        lead for lead in leads
        if lead.get("status") == "researched"
        and lead.get("lead_quality") in MIN_LEAD_QUALITY
        and not lead.get("contact_email", "").strip()
    ]

    print(f"Found {len(candidates)} lead(s) with an email to draft for.")
    if skipped_no_email:
        print(f"Skipped {len(skipped_no_email)} good lead(s) with no contact email found - "
              f"you'll need to find these manually:")
        for lead in skipped_no_email:
            print(f"  - {lead['url']}")
    print()

    drafts = []
    for i, lead in enumerate(candidates, 1):
        print(f"[{i}/{len(candidates)}] Researching contact name for {lead['url']}...")
        name_result = find_contact_name(lead["business_type"], lead["url"])

        if name_result["name"]:
            greeting = f"Hi {name_result['name']},"
            name_status = f"GUESS (verify before sending): {name_result['name']}"
        else:
            greeting = "Hi there,"
            name_status = "not found - used generic greeting"

        print(f"    Contact name: {name_status}")
        print(f"    Drafting email...")
        draft = draft_email_with_retry(lead["business_type"], lead["reason"], greeting, model)

        drafts.append({
            "url": lead["url"],
            "contact_email": lead["contact_email"],
            "business_type": lead["business_type"],
            "contact_name_status": name_status,
            "subject": draft["subject"],
            "draft_body": draft["body"],
        })
        if i < len(candidates):
            time.sleep(13)  # stay under the 5-requests/minute free-tier cap

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "url", "contact_email", "business_type",
            "contact_name_status", "subject", "draft_body",
        ])
        writer.writeheader()
        writer.writerows(drafts)

    print(f"\nDone. {len(drafts)} draft(s) written to {OUTPUT_FILE}")
    print("REVIEW AND EDIT EVERY DRAFT YOURSELF BEFORE SENDING.")
    print("Any name marked GUESS must be verified - never send an unverified name.")
    print("Nothing has been sent.")


if __name__ == "__main__":
    main()
