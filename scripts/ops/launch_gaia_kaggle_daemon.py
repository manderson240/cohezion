#!/usr/bin/env python3
"""Launch and Manage GAIA SDK Autonomous Kaggle Competition Daemons.

CLI Interface to manage the multi-track GAIA SDK competition swarm:
  --once          Execute a single full-portfolio sweep and exit
  --interval SEC  Run continuously with the specified interval (default 1800s)
  --track SLUG    Run only the specified active competition track
  --tmux          Launch as a detached TMUX session (`gaia-kaggle-swarm`)
  --status        Check running daemon status and print latest portfolio card
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path


# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cohezion.competitions.gaia_kaggle_daemon import (  # noqa: E402
    ACTIVE_KAGGLE_TRACKS,
    GaiaKaggleCompetitionAgent,
    GaiaKaggleSwarmDaemon,
)


TMUX_SESSION = "gaia-kaggle-swarm"
STATUS_CARD_PATH = Path("docs/research/gaia_kaggle_portfolio_status.md")


def is_tmux_running() -> bool:
    """Check if the gaia-kaggle-swarm tmux session is currently active."""
    res = subprocess.run(["tmux", "has-session", "-t", TMUX_SESSION], capture_output=True)
    return res.returncode == 0


def launch_in_tmux(interval: int) -> None:
    """Launch the daemon inside a detached tmux session."""
    if is_tmux_running():
        print(f"⚠ TMUX session '{TMUX_SESSION}' is already running.")
        print(f"Attach using: tmux attach-session -t {TMUX_SESSION}")
        return

    worktree_dir = Path(__file__).resolve().parents[2]
    cmd = (
        f"cd {worktree_dir} && "
        f"PYTHONPATH=src /home/mike-anderson/dev/cohezion/.venv/bin/python "
        f"scripts/ops/launch_gaia_kaggle_daemon.py --interval {interval}"
    )

    subprocess.run(["tmux", "new-session", "-d", "-s", TMUX_SESSION, cmd], check=True)
    print(f"✔ Launched GAIA Kaggle Swarm Daemon in detached TMUX session: '{TMUX_SESSION}'")
    print(f"  • Interval : {interval} seconds")
    print(f"  • Attach   : tmux attach -t {TMUX_SESSION}")
    print("  • Status   : python scripts/ops/launch_gaia_kaggle_daemon.py --status")


def show_status() -> None:
    """Display current status of the daemon and latest portfolio card."""
    running = is_tmux_running()
    print("=" * 80)
    print("🤖 GAIA SDK KAGGLE COMPETITION SWARM STATUS")
    print("=" * 80)
    print(f"  • TMUX Session '{TMUX_SESSION}': {'🟢 RUNNING' if running else '⚪ STOPPED'}")
    print(f"  • Active Tracks Configured    : {len(ACTIVE_KAGGLE_TRACKS)}")

    if STATUS_CARD_PATH.exists():
        print("\n" + STATUS_CARD_PATH.read_text())
    else:
        print("\n  (No portfolio status card found yet. Run with --once to generate one.)")


async def run_single_track(track_slug: str) -> None:
    """Run a single active competition agent."""
    if track_slug not in ACTIVE_KAGGLE_TRACKS:
        print(f"Error: Unknown or inactive track '{track_slug}'.")
        print("Active tracks:")
        for slug in ACTIVE_KAGGLE_TRACKS:
            print(f"  - {slug}")
        sys.exit(1)

    spec = ACTIVE_KAGGLE_TRACKS[track_slug]
    agent = GaiaKaggleCompetitionAgent(spec)
    print(f"▶ Running GAIA Agent for track: {spec.display_name}...")
    report = await agent.run_cycle()
    print("\n--- AGENT CYCLE REPORT ---")
    print(f"  Track        : {report.display_name}")
    print(f"  Model        : {report.assigned_model}")
    print(f"  Hardware     : {report.hardware_target}")
    print(f"  Status       : {report.submission_status}")
    print(f"  SOTA Score   : {report.latest_score}")
    print(f"  AutoHarness  : {'✔ VERIFIED' if report.autoharness_verified else '✗ REJECTED'}")
    print(f"  Recommendation: {report.tactical_recommendation}")
    print(f"  Latency      : {report.execution_latency_ms:.1f} ms\n")


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Launch GAIA SDK Kaggle Daemon")
    parser.add_argument("--once", action="store_true", help="Execute single sweep and exit")
    parser.add_argument("--interval", type=int, default=1800, help="Loop interval in seconds")
    parser.add_argument("--track", type=str, help="Run single track slug")
    parser.add_argument("--tmux", action="store_true", help="Launch in detached TMUX session")
    parser.add_argument("--status", action="store_true", help="Show status and exit")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.tmux:
        launch_in_tmux(args.interval)
        return

    if args.track:
        await run_single_track(args.track)
        return

    daemon = GaiaKaggleSwarmDaemon()

    if args.once:
        print("▶ Executing single GAIA Kaggle Swarm sweep...")
        reports = await daemon.run_swarm_cycle()
        md = daemon.generate_portfolio_markdown(reports)
        STATUS_CARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_CARD_PATH.write_text(md)
        print("\n" + md)
    else:
        await daemon.start_daemon(interval_seconds=args.interval)


if __name__ == "__main__":
    asyncio.run(main_async())
