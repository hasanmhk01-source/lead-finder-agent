"""
run_all.py — Runs Agent 1, Agent 2, and Agent 3 in sequence.

This is a convenience wrapper, not a shortcut around safety: Agent 3's
per-email y/n/q confirmation is completely untouched and still runs
exactly as it does standalone. This file only saves you from typing three
separate commands - it does not remove the human approval step.

Usage:
    python run_all.py
"""

import agent1_find_leads
import agent2_draft_outreach
import agent3_send_outreach


def main():
    print("\n" + "=" * 60)
    print("STEP 1/3: Finding and researching leads (Agent 1)")
    print("=" * 60 + "\n")
    agent1_find_leads.main()

    print("\n" + "=" * 60)
    print("STEP 2/3: Drafting outreach emails (Agent 2)")
    print("=" * 60 + "\n")
    agent2_draft_outreach.main()

    print("\n" + "=" * 60)
    print("STEP 3/3: Sending outreach (Agent 3) - REVIEW EACH ONE")
    print("=" * 60 + "\n")
    agent3_send_outreach.main()


if __name__ == "__main__":
    main()
