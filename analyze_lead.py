"""
analyze_lead.py — Takes a business's visible website text (already
extracted, already known whether they have a chatbot) and asks an LLM to
summarize what the business does and whether it's a good automation/
chatbot lead - grounded ONLY in what's actually on their page, same
grounding discipline as the RAG agent: no inventing details about a
business beyond what their site actually says.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

ANALYSIS_PROMPT = """You are helping research potential leads for an AI
automation/chatbot service. Below is the visible text from a business's
website, and whether they already have a chat widget installed.

Website text:
{site_text}

Already has a chat widget: {has_chatbot}

Based ONLY on the website text above, answer in this exact format:
BUSINESS TYPE: <one short phrase describing what this business does>
LEAD QUALITY: <High, Medium, or Low>
REASON: <one or two sentences explaining the lead quality rating>

Rules:
- If the website text doesn't give enough information to judge the
  business, say LEAD QUALITY: Low and explain why in REASON.
- If they already have a chat widget, that generally lowers lead quality
  unless there's a specific reason it might still be a good fit (e.g. very
  large business, multiple products, complex support needs).
- Do not invent details about the business that aren't in the text.
- If the site is a directory, listing, marketplace, aggregator, or review platform rather than a single business, set LEAD QUALITY: Low and say so in REASON.
"""


def analyze_lead(site_text: str, has_chatbot: bool, model) -> dict:
    prompt = ANALYSIS_PROMPT.format(
        site_text=site_text if site_text.strip() else "(no readable text found)",
        has_chatbot="Yes" if has_chatbot else "No",
    )
    response = model.generate_content(prompt)
    text = response.text.strip()

    # Parse the structured response - simple line-based parsing since we
    # controlled the exact output format in the prompt.
    result = {"business_type": "", "lead_quality": "", "reason": ""}
    for line in text.split("\n"):
        if line.startswith("BUSINESS TYPE:"):
            result["business_type"] = line.replace("BUSINESS TYPE:", "").strip()
        elif line.startswith("LEAD QUALITY:"):
            result["lead_quality"] = line.replace("LEAD QUALITY:", "").strip()
        elif line.startswith("REASON:"):
            result["reason"] = line.replace("REASON:", "").strip()
    return result


if __name__ == "__main__":
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    sample_text = ("Joe's Plumbing has served the local area for 20 years. "
                    "Call us or fill out our contact form for a quote. We do "
                    "not offer online booking or live chat.")
    result = analyze_lead(sample_text, has_chatbot=False, model=model)
    print(result)
