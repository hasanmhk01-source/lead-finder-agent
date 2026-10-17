"""
search_leads.py — Finds candidate business websites automatically using
the Tavily Search API, built specifically for AI agents (no credit card
required, 1,000 free searches/month).

This is a legitimate, sanctioned search API - the programmatic equivalent
of a human typing a search into a search engine and looking at results,
not scraping any platform's private data.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_URL = "https://api.tavily.com/search"


def search_businesses(query: str, num_results: int = 5) -> list[str]:
    """Runs one search query and returns a list of candidate website URLs."""
    if not TAVILY_API_KEY:
        raise RuntimeError(
            "Set TAVILY_API_KEY in .env first. Sign up free (no card needed) "
            "at https://tavily.com - see README.md for details."
        )

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": min(num_results, 10),
        "search_depth": "basic",
    }
    resp = requests.post(TAVILY_URL, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    urls = []
    for item in data.get("results", []):
        url = item.get("url")
        if url:
            urls.append(url)
    return urls


def search_multiple(queries: list[str], num_results_per_query: int = 5) -> list[str]:
    """Runs several search queries and returns a deduplicated list of URLs,
    preserving order (first-seen wins) so results stay reproducible.
    Filters out domains that are never real single-business leads - social
    media profile pages, document hosts, and large aggregator/directory
    platforms - to avoid wasting research effort on pages that can't
    actually be evaluated as a business."""
    EXCLUDED_DOMAINS = [
        "instagram.com", "facebook.com", "twitter.com", "x.com", "tiktok.com",
        "scribd.com", "substack.com", "tripadvisor.com", "youtube.com",
        "linkedin.com", "pinterest.com",
    ]

    seen = set()
    all_urls = []
    for query in queries:
        print(f"  Searching: \"{query}\"...")
        try:
            urls = search_businesses(query, num_results_per_query)
        except Exception as e:
            print(f"    Search failed for this query: {e}")
            continue
        for url in urls:
            if url in seen:
                continue
            if any(domain in url for domain in EXCLUDED_DOMAINS):
                print(f"    Skipping (excluded domain): {url}")
                continue
            seen.add(url)
            all_urls.append(url)
    return all_urls


if __name__ == "__main__":
    results = search_businesses("clinics in Karachi", num_results=5)
    for url in results:
        print(url)
