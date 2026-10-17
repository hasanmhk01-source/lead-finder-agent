"""
agent1_find_leads.py — Agent 1: Lead Qualifier (now with autonomous search)

Two modes:
1. SEARCH MODE (default): searches Google for businesses matching your
   SEARCH_QUERIES list, researches each candidate found, writes a report.
2. MANUAL MODE: if leads_input.txt exists and has real URLs in it, uses
   that list instead of searching - useful for researching specific
   businesses you already have in mind.

Either way, this agent still NEVER contacts anyone. It finds and
researches candidates; a human reviews the report and decides what
happens next. That gate has not moved - only how candidates get FOUND
has changed.

Usage:
    python agent1_find_leads.py
"""

import os
import csv
import time
import random
import google.generativeai as genai
from dotenv import load_dotenv

from detect_chatbot import fetch_page, detect_chatbot, extract_visible_text
from find_contact import find_contact_email
from analyze_lead import analyze_lead
from search_leads import search_multiple

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
INPUT_FILE = "leads_input.txt"
OUTPUT_FILE = "leads_report.csv"
MAX_RETRIES = 2

# Edit these to change what kinds of businesses Agent 1 looks for.
# Keep this list short while testing - each query uses part of your daily
# free search quota (100/day on Google's free tier).
SEARCH_QUERIES = [
    "clinics in Karachi",
    "boutiques in Karachi",
    "restaurants in Karachi",
    "dental clinics in Karachi",
    "real estate agencies in Karachi",
    "salons and spas in Karachi",
    "gyms and fitness centers in Karachi",
    "wedding photographers in Karachi",
]
RESULTS_PER_QUERY = 8


def get_urls_to_research() -> list[str]:
    """Manual list takes priority if it has real (non-comment) URLs in it -
    otherwise falls back to autonomous search."""
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        if urls:
            print(f"Using {len(urls)} URL(s) from {INPUT_FILE} (manual mode).\n")
            return urls

    print(f"No manual URLs found - searching automatically instead.\n")
    urls = search_multiple(SEARCH_QUERIES, RESULTS_PER_QUERY)
    print(f"\nFound {len(urls)} candidate business(es) via search.\n")
    return urls


def research_lead(url: str, model) -> dict:
    try:
        html = fetch_page(url)
        chatbot_info = detect_chatbot(html)
        site_text = extract_visible_text(html)
        analysis = analyze_lead(site_text, chatbot_info["has_chatbot"], model)
        contact_email = find_contact_email(html)

        return {
            "url": url,
            "status": "researched",
            "has_chatbot": chatbot_info["has_chatbot"],
            "detected_providers": ", ".join(chatbot_info["detected_providers"]),
            "business_type": analysis["business_type"],
            "lead_quality": analysis["lead_quality"],
            "reason": analysis["reason"],
            "contact_email": contact_email or "",
        }
    except Exception as e:
        return {
            "url": url,
            "status": "failed",
            "has_chatbot": "",
            "detected_providers": "",
            "business_type": "",
            "lead_quality": "",
            "reason": f"Could not research this URL: {e}",
            "contact_email": "",
        }


def main():
    if not GEMINI_API_KEY:
        print("Set GEMINI_API_KEY in .env first.")
        return

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    urls = get_urls_to_research()
    if not urls:
        print("No URLs to research - check your search queries or leads_input.txt.")
        return

    print(f"Researching {len(urls)} business(es)...\n")
    results = []

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}...")
        result = None
        for attempt in range(1, MAX_RETRIES + 1):
            result = research_lead(url, model)
            if result["status"] == "researched":
                break
            if attempt < MAX_RETRIES:
                wait = 15 * attempt + random.uniform(0, 3)
                print(f"    Rate limited or failed, waiting {wait:.0f}s before retry...")
                time.sleep(wait)
        results.append(result)
        status_label = "OK" if result["status"] == "researched" else "FAILED"
        print(f"    -> {status_label}: {result.get('lead_quality') or result['reason'][:60]}")
        if i < len(urls):
            time.sleep(13)  # stay under Gemini free tier's 5-requests/minute cap

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "url", "status", "has_chatbot", "detected_providers",
            "business_type", "lead_quality", "reason", "contact_email",
        ])
        writer.writeheader()
        writer.writerows(results)

    researched = sum(1 for r in results if r["status"] == "researched")
    print(f"\nDone. {researched}/{len(results)} researched successfully.")
    print(f"Report written to {OUTPUT_FILE} — REVIEW THIS BEFORE CONTACTING ANYONE.")


if __name__ == "__main__":
    main()
