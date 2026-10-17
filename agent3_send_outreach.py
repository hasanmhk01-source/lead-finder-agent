"""
agent3_send_outreach.py — Agent 3: Outreach Sender.

Reads outreach_drafts.csv (Agent 2's output) and sends each email - but
ALWAYS asks for your explicit y/n confirmation before every single send,
whether you're in TEST_MODE or live mode. There is no "send everything"
shortcut in this file. That's deliberate: even once you trust the drafts,
a human reads and confirms each one before it goes out.

In TEST_MODE (the default - see send_email.py), every email is redirected
to your own inbox so you can see exactly what would have been sent,
safely, with zero risk to a real business's inbox.

SAFETY: real (non-test) sends are capped at DAILY_SEND_LIMIT per calendar
day, tracked in send_log.jsonl across every run of this script - not just
this session. Sending many cold emails in a short burst from a personal
account is a real spam-pattern signal that can get the account itself
flagged or rate-limited, which is worse than slow, steady outreach. There
is also a real delay between each LIVE send, on top of the delay already
built into Agent 2's drafting step.

Usage:
    python agent3_send_outreach.py
"""

import csv
import os
import json
import time
from datetime import datetime, timezone
from send_email import send_email, TEST_MODE

INPUT_FILE = "outreach_drafts.csv"
SEND_LOG_FILE = "send_log.jsonl"
DAILY_SEND_LIMIT = 20          # max REAL sends per calendar day, across all runs
SECONDS_BETWEEN_LIVE_SENDS = 10  # spacing between real sends specifically


def count_real_sends_today() -> int:
    if not os.path.exists(SEND_LOG_FILE):
        return 0
    today = datetime.now(timezone.utc).date().isoformat()
    count = 0
    with open(SEND_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                if record.get("date") == today and record.get("mode") == "LIVE":
                    count += 1
            except json.JSONDecodeError:
                continue
    return count


def log_real_send(to_email: str):
    record = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "LIVE",
        "to": to_email,
    }
    with open(SEND_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} not found - run agent2_draft_outreach.py first.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        drafts = list(csv.DictReader(f))

    real_drafts = [d for d in drafts if not d.get("draft_body", "").startswith("DRAFT FAILED")]

    sent_today_already = count_real_sends_today() if not TEST_MODE else 0

    print(f"{'='*60}")
    print(f"MODE: {'TEST (emails will go to your own inbox)' if TEST_MODE else 'LIVE (emails will go to real recipients)'}")
    print(f"{len(real_drafts)} draft(s) ready to review.")
    if not TEST_MODE:
        print(f"Real sends already logged today: {sent_today_already}/{DAILY_SEND_LIMIT}")
    print(f"{'='*60}\n")

    sent_count = 0
    skipped_count = 0

    for i, draft in enumerate(real_drafts, 1):
        if not TEST_MODE and (sent_today_already + sent_count) >= DAILY_SEND_LIMIT:
            print(f"\nDaily limit of {DAILY_SEND_LIMIT} real sends reached. "
                  f"Stopping here to protect your email account from spam-pattern "
                  f"flagging. Resume tomorrow for the rest.")
            break

        print(f"\n--- [{i}/{len(real_drafts)}] {draft['url']} ---")
        print(f"To: {draft['contact_email']}")
        print(f"Contact name status: {draft.get('contact_name_status', 'n/a')}")
        print(f"Subject: {draft.get('subject', '(no subject)')}")
        print(f"\n{draft['draft_body']}\n")

        if "GUESS" in draft.get("contact_name_status", ""):
            print("⚠️  This draft uses an UNVERIFIED guessed name - confirm it's correct first.")

        answer = input(f"Send this one? (y/n/q to quit): ").strip().lower()
        if answer == "q":
            print("Stopped.")
            break
        if answer != "y":
            print("Skipped.")
            skipped_count += 1
            continue

        result = send_email(draft["contact_email"], draft.get("subject", "Quick note"), draft["draft_body"])
        if result["sent"]:
            print(f"✓ Sent ({result['mode']} mode, actually delivered to {result['actual_recipient']})")
            sent_count += 1
            if not TEST_MODE:
                log_real_send(draft["contact_email"])
                if i < len(real_drafts):
                    print(f"    (waiting {SECONDS_BETWEEN_LIVE_SENDS}s before the next one...)")
                    time.sleep(SECONDS_BETWEEN_LIVE_SENDS)
        else:
            print(f"✗ Failed to send: {result['error']}")

    print(f"\n{'='*60}")
    print(f"Done. {sent_count} sent, {skipped_count} skipped.")
    if TEST_MODE:
        print("Remember: TEST_MODE is on, so nothing went to a real business.")
        print("Check your own inbox to see exactly what was sent.")
    else:
        print(f"Real sends today: {sent_today_already + sent_count}/{DAILY_SEND_LIMIT}")


if __name__ == "__main__":
    main()
