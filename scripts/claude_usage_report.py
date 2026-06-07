#!/usr/bin/env python3
"""Claude usage readout — token burn across session / day / week (task #15, 2026-06-07).

The production consumer of ``cohezion.observability.claude_usage``: reads the live Claude Code
transcripts and prints token spend + burn rate so you can see how fast you're approaching a cap.

    python scripts/claude_usage_report.py                 # default windows
    python scripts/claude_usage_report.py --week-budget 2_000_000_000   # show % of a budget

HONEST: this is LOCAL token spend (a proxy). The Max-plan session/weekly % shown in the Claude
UI are server-side rate-limit buckets this tool cannot reproduce exactly — use the burn rate and
trend, not as the authoritative server %.
"""

from __future__ import annotations

import argparse
import time

from cohezion.observability.claude_usage import load_usage_records, summarize_usage


_WINDOWS = {"session(5h)": 5 * 3600.0, "day": 86400.0, "week": 7 * 86400.0}


def _fmt(n: int) -> str:
    return f"{n:,}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--projects-dir", default="~/.claude/projects")
    ap.add_argument("--week-budget", type=int, default=0, help="weekly token budget for a % readout")
    args = ap.parse_args()

    records = load_usage_records(args.projects_dir)
    if not records:
        print(f"No usage records under {args.projects_dir}")
        return 0

    now = time.time()
    summary = summarize_usage(records, now_ts=now, windows=_WINDOWS)

    print(f"Claude local token spend (proxy for plan usage) — {len(records):,} usage records")
    print(f"{'window':12} {'records':>8} {'output':>14} {'cache_read':>16} {'total':>16} {'burn/hr':>14}")
    print("-" * 84)
    for name in _WINDOWS:
        w = summary[name]
        print(
            f"{name:12} {w.records:>8} {_fmt(w.output):>14} {_fmt(w.cache_read):>16} "
            f"{_fmt(w.total):>16} {_fmt(int(w.burn_per_hour)):>14}"
        )
    if args.week_budget > 0:
        pct = summary["week"].projected_pct(args.week_budget)
        print(f"\nweek: {pct:.1f}% of {_fmt(args.week_budget)} token budget")
    print("\nNote: cache_read dominates token counts but is cheap on the plan; watch 'output' burn.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
