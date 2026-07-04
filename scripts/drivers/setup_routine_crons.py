#!/usr/bin/env python3
"""Print the CronCreate commands to schedule Cohezion compound engineering routine runs.

CronCreate is a deferred tool available only in interactive Claude Code sessions
(available since Claude Code v2.1.136). This script cannot call it directly — instead
it prints the exact calls to paste into an interactive session.

Run this script to see the schedule:
    uv run python scripts/drivers/setup_routine_crons.py

Then paste the printed CronCreate calls into an interactive Claude Code session.

Budget:
    15 routine runs/day total
      3 × routine_skill_geometry  (every 8 hours — fast, ~5s)
      2 × routine_flume_variate   (every 12 hours — slower, ~5-10 min)
     10   reserved for ad-hoc research tasks
"""

from __future__ import annotations

REPO_ROOT_NOTE = "# Run from the cohezion repo root (/home/mike-anderson/dev/cohezion)"

# ── Schedule: geometry sweep (3×/day, every 8 hours) ────────────────────────
GEOMETRY_CRONS = [
    {
        "name": "cohezion-skill-geometry-0600",
        "schedule": "0 6 * * *",
        "label": "06:00 UTC",
        "prompt": (
            "cd /home/mike-anderson/dev/cohezion && "
            "uv run python scripts/drivers/routine_skill_geometry.py"
        ),
    },
    {
        "name": "cohezion-skill-geometry-1400",
        "schedule": "0 14 * * *",
        "label": "14:00 UTC",
        "prompt": (
            "cd /home/mike-anderson/dev/cohezion && "
            "uv run python scripts/drivers/routine_skill_geometry.py"
        ),
    },
    {
        "name": "cohezion-skill-geometry-2200",
        "schedule": "0 22 * * *",
        "label": "22:00 UTC",
        "prompt": (
            "cd /home/mike-anderson/dev/cohezion && "
            "uv run python scripts/drivers/routine_skill_geometry.py"
        ),
    },
]

# ── Schedule: FLUME VAE hyperparameter sweep (2×/day, every 12 hours) ────────
VAE_CRONS = [
    {
        "name": "cohezion-flume-variate-0800",
        "schedule": "0 8 * * *",
        "label": "08:00 UTC",
        "prompt": (
            "cd /home/mike-anderson/dev/cohezion && "
            "uv run python scripts/drivers/routine_flume_variate.py"
        ),
    },
    {
        "name": "cohezion-flume-variate-2000",
        "schedule": "0 20 * * *",
        "label": "20:00 UTC",
        "prompt": (
            "cd /home/mike-anderson/dev/cohezion && "
            "uv run python scripts/drivers/routine_flume_variate.py"
        ),
    },
]

ALL_CRONS = GEOMETRY_CRONS + VAE_CRONS


def _cron_create_call(cron: dict) -> str:
    """Format a CronCreate tool call as a code block for copy-paste."""
    return (
        f"# {cron['label']} — {cron['name']}\n"
        f"CronCreate(\n"
        f'    name="{cron["name"]}",\n'
        f'    schedule="{cron["schedule"]}",\n'
        f'    prompt="{cron["prompt"]}"\n'
        f")"
    )


def print_setup_instructions() -> None:
    banner = "=" * 72

    print(banner)
    print("  COHEZION COMPOUND ENGINEERING — ROUTINE RUN CRON SETUP")
    print(banner)
    print()
    print("Paste each block below into an INTERACTIVE Claude Code session.")
    print("CronCreate is a session-bound tool; this script cannot call it.")
    print()
    print(f"Quota: 15 routine runs/day  |  Using 5  |  10 reserved for ad-hoc")
    print()

    # ── Geometry sweeps ──────────────────────────────────────────────────────
    print("─" * 72)
    print("  1. SkillStateEncoder Geometry Sweep  (3×/day, ~5s each)")
    print("     Script: scripts/drivers/routine_skill_geometry.py")
    print("     Output: data/skill_geometry_autoresearch.jsonl")
    print("─" * 72)
    print()
    for cron in GEOMETRY_CRONS:
        print(_cron_create_call(cron))
        print()

    # ── FLUME VAE sweeps ─────────────────────────────────────────────────────
    print("─" * 72)
    print("  2. FLUME VAE Hyperparameter Sweep  (2×/day, ~5-10 min each)")
    print("     Script: scripts/drivers/routine_flume_variate.py")
    print("     Output: data/flume_variate_autoresearch.jsonl")
    print("─" * 72)
    print()
    for cron in VAE_CRONS:
        print(_cron_create_call(cron))
        print()

    # ── Management commands ──────────────────────────────────────────────────
    print("─" * 72)
    print("  MANAGEMENT COMMANDS  (also run interactively in Claude Code)")
    print("─" * 72)
    print()
    print("# List all scheduled crons:")
    print("CronList()")
    print()
    print("# Delete a specific cron (use the name you gave CronCreate):")
    print('CronDelete(name="cohezion-skill-geometry-0600")')
    print('CronDelete(name="cohezion-skill-geometry-1400")')
    print('CronDelete(name="cohezion-skill-geometry-2200")')
    print('CronDelete(name="cohezion-flume-variate-0800")')
    print('CronDelete(name="cohezion-flume-variate-2000")')
    print()

    # ── State / results ──────────────────────────────────────────────────────
    print("─" * 72)
    print("  STATE PERSISTENCE & RESULT INSPECTION")
    print("─" * 72)
    print()
    print("Each script appends one JSON record per invocation to its JSONL file.")
    print("The next invocation reads the file to pick the next experiment ID,")
    print("so state accumulates across runs without any external database.")
    print()
    print("Inspect the 20 most recent geometry results (pretty-printed):")
    print()
    print(
        '  tail -20 data/skill_geometry_autoresearch.jsonl | '
        'python3 -c "import sys,json; '
        "[print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin]\""
    )
    print()
    print("Inspect the 20 most recent FLUME VAE results:")
    print()
    print(
        '  tail -20 data/flume_variate_autoresearch.jsonl | '
        'python3 -c "import sys,json; '
        "[print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin]\""
    )
    print()
    print("Count WINs vs MISSes in geometry results:")
    print()
    print(
        "  python3 -c \""
        "import json, pathlib; "
        "lines = pathlib.Path('data/skill_geometry_autoresearch.jsonl').read_text().splitlines(); "
        "recs = [json.loads(l) for l in lines if l.strip()]; "
        "wins = sum(1 for r in recs if r.get('status') == 'WIN'); "
        "print(f'WIN={wins} MISS={len(recs)-wins} TOTAL={len(recs)}')"
        '"'
    )
    print()

    # ── Schedule summary ─────────────────────────────────────────────────────
    print("─" * 72)
    print("  SCHEDULE SUMMARY (all times UTC, avoids 00:00)")
    print("─" * 72)
    print()
    print("  Time   Script                         Runs/day  Quota used")
    print("  ─────  ─────────────────────────────  ────────  ──────────")
    for cron in ALL_CRONS:
        h = int(cron["schedule"].split()[1])
        script = "routine_skill_geometry.py" if "geometry" in cron["name"] else "routine_flume_variate.py"
        print(f"  {h:02d}:00   {script:<29}  1         +1")
    print()
    print("  Total routine runs/day consumed: 5  (10 reserved for ad-hoc)")
    print()
    print(banner)


if __name__ == "__main__":
    print_setup_instructions()
