#!/usr/bin/env python3
"""Seed the Cohezion Portfolio Tracker with the current competition slate.

Run from the worktree root:
    uv run python scripts/portfolio_init.py

Idempotent — safe to run multiple times; existing projects are overwritten
only if you pass --force.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

# Ensure cohezion is importable from the worktree
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.portfolio.models import PortfolioProject


PROJECTS = [
    PortfolioProject(
        id="nemotron",
        name="Nemotron Reasoning",
        competition="nvidia-nemotron-model-reasoning-challenge",
        deadline=datetime(2026, 6, 15, tzinfo=UTC),
        prize=106_000,
        status="running",
        score=0.84,
        score_label="0.84 public (v9 banked)",
        kernel="manderson240/nemotron-v7-20260608-1032",
        worktree=".worktrees/nemotron-june",
        notes=[
            "[2026-06-02] v10 smoke COMPLETE — winner corpus + masking pipeline validated",
            "[2026-06-08] v10 re-push submitted as nemotron-v7-20260608-1032 (1 epoch, SMOKE=0)",
        ],
    ),
    PortfolioProject(
        id="orbit-wars",
        name="orbit-wars",
        competition="orbit-wars",
        deadline=datetime(2026, 6, 23, tzinfo=UTC),
        prize=50_000,
        status="active",
        score_label="not yet entered",
        notes=[
            "[2026-06-08] RTS space game, 4034 teams. Strong RL/Gymnasium fit. Not entered yet.",
        ],
    ),
    PortfolioProject(
        id="kaggriculture",
        name="Kaggriculture (Vibe Coding)",
        competition="5-day-ai-agents-intensive-vibecoding-course-with-google",
        deadline=datetime(2026, 6, 30, tzinfo=UTC),
        prize=0,
        status="active",
        score_label="non-cash (cert + badge)",
        worktree="cohezion-labs/google-ai-agents-vibecoding-2026",
        notes=[
            "[2026-06-08] Course Jun 15–19, capstone opens ~Jun 19. kaggle_environments installed.",
        ],
    ),
    PortfolioProject(
        id="qwen-track4",
        name="Qwen Track 4 Autopilot",
        competition="qwen-hackathon-track4",
        deadline=datetime(2026, 7, 9, tzinfo=UTC),
        prize=70_000,
        status="active",
        score_label="not entered",
        notes=[
            "[2026-06-08] Autopilot Agent — requires Alibaba Cloud deploy proof.",
            "[2026-06-08] Portfolio tracker IS the Track 4 artifact + QwenProvider bridge.",
        ],
    ),
    PortfolioProject(
        id="agi-golf",
        name="AGI-Golf / NeuroGolf",
        competition="neurogolf-2026",
        deadline=datetime(2026, 7, 15, tzinfo=UTC),
        prize=50_000,
        status="active",
        score=187.4,
        score_label="187.4 pts (baseline, not submitted)",
        worktree=".worktrees/agi-golf",
        notes=[
            "[2026-06-08] TinyConv solver, 11/400 tasks. ZIP ready at /tmp. No kernel yet.",
        ],
    ),
    PortfolioProject(
        id="xprize-gemini",
        name="XPRIZE Build with Gemini",
        competition="xprize-build-with-gemini",
        deadline=datetime(2026, 8, 17, tzinfo=UTC),
        prize=2_000_000,
        status="active",
        score_label="pitch phase",
        notes=[
            "[2026-06-08] Real business + real customers + revenue in 90 days required.",
            "[2026-06-08] Portfolio tracker + local inference story = the pitch.",
        ],
    ),
    PortfolioProject(
        id="arc-code",
        name="ARC-AGI Code Track",
        competition="arc-prize-2026-arc-agi-2",
        deadline=datetime(2026, 11, 2, tzinfo=UTC),
        prize=1_550_000,
        status="deferred",
        score_label="deferred until post-Nemotron",
        notes=[
            "[2026-06-08] ARC-AGI-2 + ARC-AGI-3. Worktree not yet created.",
        ],
    ),
    PortfolioProject(
        id="arc-paper",
        name="ARC-AGI Paper Track",
        competition="arc-prize-2026-paper-track",
        deadline=datetime(2026, 11, 9, tzinfo=UTC),
        prize=450_000,
        status="deferred",
        score_label="only 26 teams — sleeper",
        notes=[
            "[2026-06-08] Paper track — sleeper. 26 teams only. Defer until post-Jun 15.",
        ],
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Cohezion Portfolio Tracker")
    parser.add_argument("--force", action="store_true", help="Overwrite existing projects")
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="Path to JSON store (default: ~/.cohezion/portfolio.json)",
    )
    args = parser.parse_args()

    from cohezion.portfolio.tracker import PortfolioTracker

    tracker = PortfolioTracker(store_path=args.store)

    inserted = 0
    skipped = 0
    for project in PROJECTS:
        existing = tracker.get(project.id)
        if existing and not args.force:
            print(f"  skip  {project.id} (already exists — use --force to overwrite)")
            skipped += 1
            continue
        tracker.upsert(project)
        print(f"  upsert {project.id:20s}  {project.status:10s}  {project.name}")
        inserted += 1

    total = len(tracker.list_all())
    print(f"\n✓ Done: {inserted} upserted, {skipped} skipped, {total} total in tracker.")
    print(f"  Store: {tracker._store}")


if __name__ == "__main__":
    main()
