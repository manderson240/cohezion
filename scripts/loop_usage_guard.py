#!/usr/bin/env python3
"""Loop throttle — decide whether an autonomous loop tick should proceed/throttle/halt.

The production consumer of ``cohezion.observability.claude_usage.usage_guard`` (task #15 / item
134). A loop tick calls this BEFORE spending an agent turn so we never run the Claude Code plan
quota to zero — when burn is high it shifts work to the local fleet and widens the cadence.

    python scripts/loop_usage_guard.py            # prints action + recommended wakeup delay
    python scripts/loop_usage_guard.py --json      # machine-readable for scripted loops

Exit code = action: 0 proceed, 10 throttle, 20 halt (so a shell loop can branch on it).

CALIBRATION (honest): budgets are token counts, NOT the opaque server-side %. Defaults are
extrapolated from the 2026-06-07 observation (weekly total ~9.46e9 tokens ≈ 25% of the Max-20x
weekly cap → ~100% ≈ 3.78e10). Conservative by design ("never run out"): soft ≈ 70%, hard ≈ 88%.
Override with --soft/--hard or COHEZION_CLAUDE_WEEK_SOFT / _HARD.
"""

from __future__ import annotations

import argparse
import json as _json
import os
import time

from cohezion.observability.claude_usage import (
    load_usage_records,
    summarize_usage,
    usage_guard,
)


_WEEK = 7 * 86400.0
# Extrapolated from 25% ≈ 9.46e9 weekly total tokens (2026-06-07). Override per your plan.
_DEFAULT_SOFT = int(os.getenv("COHEZION_CLAUDE_WEEK_SOFT", str(26_000_000_000)))
_DEFAULT_HARD = int(os.getenv("COHEZION_CLAUDE_WEEK_HARD", str(33_000_000_000)))

# What a throttled / halted loop should do (the directive the loop obeys).
_ADVICE = {
    "proceed": ("proceed normally", 1200),
    "throttle": ("widen cadence + shift inference to the local fleet (extend_claude)", 3600),
    "halt": ("STOP scheduling autonomous wakeups; user-driven + local-fleet work only", 0),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--projects-dir", default="~/.claude/projects")
    ap.add_argument("--soft", type=int, default=_DEFAULT_SOFT)
    ap.add_argument("--hard", type=int, default=_DEFAULT_HARD)
    ap.add_argument("--metric", default="total", choices=["total", "output"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    records = load_usage_records(args.projects_dir)
    summary = summarize_usage(records, now_ts=time.time(), windows={"week": _WEEK})
    action = usage_guard(
        summary, window="week", soft_budget=args.soft, hard_budget=args.hard, metric=args.metric
    )
    week = summary["week"]
    value = getattr(week, args.metric)
    advice, delay = _ADVICE[action]
    pct = 100.0 * value / args.hard if args.hard else 0.0

    if args.json:
        print(_json.dumps({
            "action": action, "metric": args.metric, "value": value,
            "soft": args.soft, "hard": args.hard, "pct_of_hard": round(pct, 1),
            "recommended_wakeup_seconds": delay, "advice": advice,
        }))
    else:
        print(f"action: {action.upper()}  ({args.metric}={value:,} = {pct:.1f}% of hard cap)")
        print(f"  soft={args.soft:,}  hard={args.hard:,}")
        print(f"  → {advice}")
        if delay:
            print(f"  → recommended ScheduleWakeup: {delay}s")

    return {"proceed": 0, "throttle": 10, "halt": 20}[action]


if __name__ == "__main__":
    raise SystemExit(main())
