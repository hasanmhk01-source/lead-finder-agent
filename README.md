# Multi-Agent Business Development System — Agent 1 + Agent 2

A two-agent system for finding and drafting outreach to real automation/
chatbot leads. Every step that could damage a real relationship or
reputation if wrong has a human approval gate right after it.

## What it deliberately does NOT do

- It does not scrape private or authenticated platforms (LinkedIn, etc.) —
  search happens through the Tavily Search API, a legitimate, sanctioned
  service built for exactly this kind of use case.
- It does not send anything. Agent 2 drafts emails; it never sends one.
  You read every draft, edit it, and send it yourself from your own
  email client.
- It does not decide who to contact. Agent 1 produces a report, Agent 2
  drafts for leads YOU choose to pursue — a human is the decision-maker
  at both handoff points.

This is a deliberate architecture choice, not a missing feature:
**Agent 1 researches → human reviews → Agent 2 drafts outreach (human
edits and sends) → human scopes and approves any project → Agent 3
scaffolds a starting solution (human finishes and delivers).**

## How it works

**Agent 1 — Lead Qualifier:**
1. `search_leads.py` — runs your search queries (e.g. "clinics in
   Karachi") through the Tavily Search API, filtering out social media
   profiles and known aggregator/directory domains
2. `detect_chatbot.py` — fetches each business's public homepage and
   checks for known chatbot widget fingerprints
3. `find_contact.py` — looks for a contact email on the same page
   (mailto: links first, then a text scan)
4. `analyze_lead.py` — sends the page's visible text to Gemini, asking it
   to summarize the business and rate lead quality, grounded only in
   what the page actually says
5. `agent1_find_leads.py` — orchestrates all of it with retries and
   per-URL failure isolation, writes `leads_report.csv`

**Agent 2 — Outreach Drafter:**
6. `agent2_draft_outreach.py` — reads `leads_report.csv`, and for leads
   at "High" quality with a found contact email:
   - does a best-effort search for a real contact person's name (clearly
     labeled as a GUESS to verify, never presented as confirmed fact)
   - drafts a personalized email with a real subject line, referencing
     the actual business type and reasoning Agent 1 found, and naturally
     including your portfolio/proof link
   - writes everything to `outreach_drafts.csv`. **Never sends anything.**

**Agent 3 — Outreach Sender:**
7. `agent3_send_outreach.py` — reads `outreach_drafts.csv` and actually
   sends emails via `send_email.py`, but:
   - **TEST_MODE defaults to on.** Every email is redirected to your own
     inbox instead of the real recipient, clearly labeled, so you can see
     exactly what a real send looks like with zero risk.
   - **Every single email, in either mode, requires an explicit y/n
     confirmation before sending.** There is no "send all" shortcut
     anywhere in this codebase - even with TEST_MODE off, you read and
     approve each email individually before it goes out.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

**Gemini API key:** same one you've used for other projects, from
https://aistudio.google.com/apikey

**Tavily API key (free, no credit card required):**
1. Go to https://tavily.com and sign up
2. Your API key is shown on your dashboard
3. Copy it into TAVILY_API_KEY in your .env

Free tier: 1,000 searches/month, no card needed.

**Gmail App Password (for Agent 3, sending emails):**
Gmail blocks regular passwords for this kind of programmatic sending -
you need a separate "App Password":
1. Go to https://myaccount.google.com/security
2. Turn on 2-Step Verification if it isn't already on (required for App
   Passwords to be available at all)
3. Search for "App Passwords" in your Google Account settings (or go to
   https://myaccount.google.com/apppasswords directly)
4. Create a new one, name it something like "lead-finder-agent"
5. Copy the 16-character password it gives you into
   SENDER_APP_PASSWORD in your .env - and put your real Gmail address
   into SENDER_EMAIL

Note: this project originally targeted Google's Custom Search API, but
Google closed that service to new signups as of late 2026. Tavily is
used instead - free without a card, purpose-built for AI agent use.

## Running it

```bash
python agent1_find_leads.py
```

Searches automatically using `SEARCH_QUERIES` in `agent1_find_leads.py`
(edit that list for different business categories/cities), or uses
`leads_input.txt` instead if you've put real URLs there. Writes
`leads_report.csv` — **read this yourself before deciding who to
pursue.**

```bash
python agent2_draft_outreach.py
```

Reads `leads_report.csv`, drafts outreach for "High" quality leads with
a found email (edit `MIN_LEAD_QUALITY` in the file to include "Medium"
too). Set `YOUR_PORTFOLIO_LINK` at the top of the file to your real
Fiverr gig or demo link before running. Writes `outreach_drafts.csv`.

**Check the `contact_name_status` column for every row before sending.**
If it says `GUESS (verify before sending): <name>`, that name came from a
web search, not the business's own page — confirm it's actually correct
(and still current) before using it. If it says "not found," the draft
uses a generic "Hi there," greeting instead — don't invent a name
yourself without checking either. **Read and edit every draft yourself
before sending anything — nothing is sent automatically, ever.**

```bash
python agent3_send_outreach.py
```

Walks through every draft one at a time, shows you the full email, and
asks `y/n/q` before sending each one. With `TEST_MODE=true` (the
default), every send actually lands in your own inbox, clearly labeled
with the real intended recipient — run it this way first, every time, to
see exactly what would go out before ever setting `TEST_MODE=false`.

When you're ready for real sends: set `TEST_MODE=false` in `.env`, but
know that the per-email confirmation prompt is still there — it never
goes away, in any mode, by design.

## Tradeoffs / what I'd improve next

- **Chatbot fingerprint list is not exhaustive** — only checks ~8 common
  providers.
- **Single-page check only** — only looks at the homepage, for both
  chatbot detection and contact email finding. A business's real contact
  email might live on a separate /contact page this tool never visits.
- **Some sites block automated requests entirely** (403 errors) — large
  corporate sites with bot-protection will often fail to fetch even
  though the site is completely live. Confirmed during testing (Foodpanda,
  McDonald's Pakistan, TripAdvisor all blocked this way).
- **Regional DNS reliability varies** — some country-code domains (e.g.
  .pk) did not resolve reliably from every network tested, even though
  confirmed live from elsewhere.
- **JavaScript-rendered content is invisible to this tool** — the agent
  correctly reports "not enough information" rather than guessing when a
  page's real content loads dynamically - confirmed during testing.
- **Search result relevance is only as good as the query** — the domain
  filter catches obvious noise (social media, directories) but can't
  distinguish a genuinely small business from a large, well-funded
  platform that happens to match the search terms (e.g. Foodpanda showing
  up in a "restaurants in Karachi" search). That judgment still needs a
  human reading the report.
- **LLM lead-quality judgments have some run-to-run variance** — the same
  URL was rated "Medium" in one run and "Low" in another during testing.
  Useful as a triage signal, not a precise score.
- **Agent 2's drafts are a starting point, not a final send** — always
  read every draft for tone, accuracy, and anything that needs
  personalizing further before sending.
- **Contact names found by Agent 2 are unverified guesses, not facts** —
  they come from a broader web search, not the business's own page, and
  could be outdated or belong to someone who has left. This is the one
  piece of this system with a real, non-trivial chance of being wrong -
  treat every guessed name as something to double-check, never as
  confirmed.

## What's next (not built yet, on purpose)

Agent 3 (scaffolding a starting solution for a signed client) comes after
Agent 1 and 2 are tested and trusted in real use — with its own
human-approval gate before any code reaches a real client.
