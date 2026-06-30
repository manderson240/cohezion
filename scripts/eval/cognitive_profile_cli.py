#!/usr/bin/env python3
"""CLI entry point for the cognitive-profile harness — the live consumption seam.

Runs `run_profile()` against Cohezion-as-system on the local AMD fleet ($0), prints the honest
per-axis scorecard, and (default) persists to SurrealDB `cognitive_profile` + a vault markdown.

    uv run python scripts/eval/cognitive_profile_cli.py            # live profile, persist
    uv run python scripts/eval/cognitive_profile_cli.py --no-persist --repeats 2
    uv run python scripts/eval/cognitive_profile_cli.py --json     # machine-readable

This is the pinned consumer for the dormancy scan (scripts/ci/dormancy_scan.py): removing the
`run_profile(` call below re-dormants the harness → the scan goes RED.
"""

from __future__ import annotations

import argparse
import json
import sys

from cohezion.eval.cognitive_profile import run_profile


def main() -> int:
    ap = argparse.ArgumentParser(description="Cohezion cognitive-profile harness (DeepMind 10-faculty).")
    ap.add_argument("--repeats", type=int, default=1, help="repeat each axis N times (stochasticity).")
    ap.add_argument("--no-persist", action="store_true", help="do not write SurrealDB / vault scorecard.")
    ap.add_argument("--json", action="store_true", help="emit the profile as JSON only.")
    args = ap.parse_args()

    profile = run_profile(repeats=args.repeats, persist=not args.no_persist)

    if args.json:
        print(json.dumps(profile, indent=2))
        return 0

    s = profile["summary"]
    print(f"\nCohezion Cognitive Profile  —  {profile['timestamp']}  ·  fleet={profile['fleet_model']}")
    print(f"system: {profile['system']}\n")
    print(f"{'AXIS':<22} {'FACULTY':<34} {'SCORE':>6} {'n':>3}  {'STATUS':<13} SUBSTRATE")
    print("-" * 96)
    for aid, ax in profile["axes"].items():
        sub = "BEYOND-REACH" if ax["substrate_beyond_reach"] else ""
        print(
            f"{aid:<22} {ax['faculty'][:34]:<34} {ax['score']:>6.2f} {ax['n']:>3}  {ax['status']:<13} {sub}"
        )
    print("-" * 96)
    print(
        f"summary: {s['MET']} MET · {s['PARTIAL']} PARTIAL · {s['GAP']} GAP · "
        f"{s['BEYOND_REACH']} BEYOND_REACH  |  mean testable score = {s['mean_score_testable']:.3f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
