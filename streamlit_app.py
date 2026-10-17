"""
streamlit_app.py - Public demo for the lead-finder agents (Agent 1 + Agent 2 only).

DEMO_MODE is hard-wired: this file never imports send_email or agent3, so
nothing can be sent from the public app. Contact emails are masked.

Run locally:   streamlit run streamlit_app.py
Deploy:        Streamlit Community Cloud, add GEMINI_API_KEY and TAVILY_API_KEY
               under App settings -> Secrets.
"""

import os
import json
import time
from datetime import date

import streamlit as st

# Load secrets into env BEFORE importing the agent modules (they read env at import).
for _k in ("GEMINI_API_KEY", "TAVILY_API_KEY", "GEMINI_MODEL"):
    try:
        if _k in st.secrets:
            os.environ[_k] = st.secrets[_k]
    except Exception:
        pass

import google.generativeai as genai
from search_leads import search_multiple
from agent1_find_leads import research_lead
from agent2_draft_outreach import draft_email_with_retry

MAX_LEADS_PER_RUN = 3
MAX_RUNS_PER_SESSION = 3
MAX_RUNS_PER_DAY = 30
USAGE_FILE = "demo_usage.json"
GEMINI_PAUSE = 13  # stay under Gemini free tier's 5 requests/minute


def _daily_runs() -> int:
    try:
        with open(USAGE_FILE, "r") as f:
            data = json.load(f)
        return data["count"] if data.get("date") == date.today().isoformat() else 0
    except Exception:
        return 0


def _bump_daily_runs():
    with open(USAGE_FILE, "w") as f:
        json.dump({"date": date.today().isoformat(), "count": _daily_runs() + 1}, f)


st.set_page_config(page_title="AI Lead Finder", layout="wide")
st.title("AI Lead Finder")
st.caption(
    "Agent 1 finds and qualifies local businesses. Agent 2 drafts a personalized "
    "outreach email. Demo mode: nothing is ever sent, contact emails are hidden."
)

col1, col2 = st.columns(2)
industry = col1.text_input("Business type", placeholder="dental clinics")
city = col2.text_input("City", placeholder="Karachi")

if "runs" not in st.session_state:
    st.session_state.runs = 0

go = st.button("Find leads", type="primary", disabled=not (industry and city))

if go:
    if st.session_state.runs >= MAX_RUNS_PER_SESSION:
        st.warning("Demo limit reached for this session.")
        st.stop()
    if _daily_runs() >= MAX_RUNS_PER_DAY:
        st.warning("Daily demo limit reached. Try again tomorrow.")
        st.stop()
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        st.error("API keys are not configured.")
        st.stop()

    st.session_state.runs += 1
    _bump_daily_runs()

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.6-flash"))

    rows, drafts = [], {}
    with st.status("Running agents (about 1-2 minutes on the free tier)...", expanded=True) as status:
        st.write("Agent 1: searching...")
        urls = search_multiple([f"{industry} {city} official website"], 8)[:MAX_LEADS_PER_RUN]
        if not urls:
            status.update(label="No results found.", state="error")
            st.stop()

        for i, url in enumerate(urls, 1):
            st.write(f"Agent 1: researching {url} ({i}/{len(urls)})")
            lead = research_lead(url, model)
            time.sleep(GEMINI_PAUSE)
            rows.append({
                "url": url,
                "business": lead["business_type"],
                "quality": lead["lead_quality"],
                "has_chatbot": lead["has_chatbot"],
                "email_found": "yes" if lead["contact_email"] else "no",
                "reason": lead["reason"],
            })
            if lead["status"] == "researched" and lead["lead_quality"] in ("High", "Medium"):
                st.write(f"Agent 2: drafting email for {url}")
                drafts[url] = draft_email_with_retry(
                    lead["business_type"], lead["reason"], "Hi there,", model
                )
                time.sleep(GEMINI_PAUSE)
        status.update(label="Done", state="complete", expanded=False)

    st.subheader("Qualified leads")
    st.dataframe(rows, width="stretch")

    st.subheader("Drafted outreach")
    if not drafts:
        st.info("No High/Medium quality leads this run, so no drafts were written.")
    for url, d in drafts.items():
        with st.expander(f"{url} - {d['subject'] or '(no subject)'}"):
            st.text(d["body"])
    st.caption("Demo mode: drafts are for review only and are never sent.")