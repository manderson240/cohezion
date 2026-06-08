#!/usr/bin/env python3
"""dorahacks_feed_summary.py — parse DORAHACKS_FEED.md into scored tiers.

Item 272 (Thread D: Hackathon Intel, 2026-06-08).

Usage:
    .venv/bin/python3 scripts/dorahacks_feed_summary.py
    .venv/bin/python3 scripts/dorahacks_feed_summary.py --feed docs/feeds/DORAHACKS_FEED.md

Returns a dict (also prints a table) grouping hackathon entries by score tier:
  top      — score ≥ 9
  good     — 7 ≤ score ≤ 8
  marginal — score < 7

Pure parser: no network, no LLM, no I/O beyond reading the feed file.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO = Path(__file__).parent.parent
DEFAULT_FEED = REPO / "docs" / "feeds" / "DORAHACKS_FEED.md"


def dorahacks_feed_summary(feed_path: Path | None = None) -> dict[str, object]:
    """Parse DORAHACKS_FEED.md and return entries grouped by score tier.

    Returns::

        {
            "total": int,
            "top": list[dict],     # score >= 9
            "good": list[dict],    # 7 <= score <= 8
            "marginal": list[dict] # score < 7
        }

    Each entry dict has keys: title, url, score, prize, deadline, tags, added.
    Empty or missing feed → all-empty lists.  Pure; no I/O beyond the read.
    """
    if feed_path is None:
        feed_path = DEFAULT_FEED

    if not feed_path.exists():
        return {"total": 0, "top": [], "good": [], "marginal": []}

    content = feed_path.read_text(encoding="utf-8")

    # Split on section headers (## Title lines) — each h2 is one hackathon entry
    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    # sections[0] is the preamble (before first ##); skip it

    entries: list[dict] = []
    for section in sections[1:]:
        lines = section.strip().splitlines()
        if not lines:
            continue

        title = lines[0].strip()
        url = ""
        score = 0
        prize = ""
        deadline = ""
        tags = ""
        added = ""

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("- **URL:**"):
                url = line.removeprefix("- **URL:**").strip()
            elif line.startswith("- **AI-relevance score:**"):
                raw = line.removeprefix("- **AI-relevance score:**").strip()
                m = re.search(r"\d+", raw)
                if m:
                    score = int(m.group())
            elif line.startswith("- **Prize:**"):
                prize = line.removeprefix("- **Prize:**").strip()
            elif line.startswith("- **Deadline:**"):
                deadline = line.removeprefix("- **Deadline:**").strip()
            elif line.startswith("- **Tags:**"):
                tags = line.removeprefix("- **Tags:**").strip()
            elif line.startswith("- **Added:**"):
                added = line.removeprefix("- **Added:**").strip()

        if not url:
            continue  # skip malformed entries without a URL

        entries.append({
            "title": title,
            "url": url,
            "score": score,
            "prize": prize,
            "deadline": deadline,
            "tags": tags,
            "added": added,
        })

    top = [e for e in entries if e["score"] >= 9]
    good = [e for e in entries if 7 <= e["score"] <= 8]
    marginal = [e for e in entries if e["score"] < 7]

    return {
        "total": len(entries),
        "top": top,
        "good": good,
        "marginal": marginal,
    }


def _print_table(summary: dict) -> None:
    """Pretty-print the summary as a tiered table."""
    total = summary["total"]
    print(f"[feed-summary] {total} hackathon(s) in feed\n")
    for tier, label in [("top", "TOP (≥9)"), ("good", "GOOD (7-8)"), ("marginal", "MARGINAL (<7)")]:
        entries = summary[tier]
        print(f"  {label}: {len(entries)}")
        for e in sorted(entries, key=lambda x: -x["score"]):
            print(f"    [{e['score']:2d}/10] {e['title']}")
            print(f"           {e['url']}")
        if not entries:
            print("    (none)")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarise DoraHacks hackathon feed by score tier")
    parser.add_argument("--feed", type=Path, default=DEFAULT_FEED, help="Path to DORAHACKS_FEED.md")
    args = parser.parse_args()

    summary = dorahacks_feed_summary(args.feed)
    _print_table(summary)

    if summary["total"] == 0:
        print(f"[feed-summary] Feed is empty or not yet populated: {args.feed}")
        print("[feed-summary] Run scripts/dorahacks_monitor.py (with DORAHACKS_COOKIE set) to populate.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
