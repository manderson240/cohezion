"""Daily researcher cron entry.

The 04:00 cron runs this. Acquires the fleet_lock:modelload, runs
the four lanes in order, writes a morning digest to the Obsidian vault.
Refuses to start if preflight fails.

CLI:
  uv run python scripts/daily_researcher.py                # live run
  uv run python scripts/daily_researcher.py --dry-run      # all 4 lanes dry
  uv run python scripts/daily_researcher.py --lane model_scout  # one lane
  uv run python scripts/daily_researcher.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path


# Add the repo root to sys.path so `cohezion` is importable when this
# script is run as `python scripts/daily_researcher.py` from a fresh
# shell (uv run does this for us, but a bare `python` call may not).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


from cohezion.researcher.daily_researcher import (  # noqa: E402
    DailyResearcher,
    DryRunReport,
    FleetLock,
    PreflightFleetCheck,
)


logger = logging.getLogger("daily_researcher")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Daily researcher cron entry")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all four lanes without making real model loads or writes.",
    )
    parser.add_argument(
        "--lane",
        choices=["model_scout", "harness_paper", "datamesh_synthesis", "verify_evolve"],
        help="Run only one lane (default: all four in order).",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip the preflight check. NOT recommended for cron use.",
    )
    args = parser.parse_args()

    if not args.skip_preflight:
        ok, reasons = PreflightFleetCheck.run()
        if not ok:
            logger.error("preflight failed: %s", "; ".join(reasons))
            return 2

    researcher = DailyResearcher()

    if args.dry_run:
        reports = await researcher.run_dry_run()
        for lane_name, report in reports.items():
            logger.info("lane %s: %s", lane_name, report.to_dict())
        await write_morning_digest(reports, dry_run=True)
        return 0

    if args.lane:
        # Single-lane run (still acquires the lock for safety)
        async with FleetLock().acquire(f"fleet_lock:modelload:{args.lane}", timeout=300):
            lane_obj = getattr(researcher, args.lane)
            report = await lane_obj.run(dry_run=False)
            await write_morning_digest({args.lane: report})
        return 0

    # All four lanes in order
    async with FleetLock().acquire("fleet_lock:modelload", timeout=300):
        reports = await researcher.run(lane=None)
        await write_morning_digest(reports)
    return 0


async def write_morning_digest(
    reports: dict[str, DryRunReport], *, dry_run: bool = False
) -> Path | None:
    """Write a morning digest of the four lanes' reports to the vault.

    Returns the file path (or None for dry-run, which doesn't write).
    """
    if dry_run:
        logger.info("dry-run: skipping morning digest write")
        return None
    import os
    vault_root = Path(
        os.environ.get(
            "COHEZION_VAULT_ROOT",
            str(Path.home() / "vaults" / "cohezion-vault" / "01-Learnings"),
        )
    )
    vault_root.mkdir(parents=True, exist_ok=True)
    out = vault_root / f"DAILY-DIGEST-{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
    lines = [
        f"# Daily Researcher — {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Lane summaries",
        "",
    ]
    for lane_name, report in reports.items():
        lines.append(f"### {lane_name}")
        lines.append("")
        if report.notes:
            for n in report.notes:
                lines.append(f"- {n}")
        if report.candidates:
            lines.append("")
            lines.append(f"Candidates: {', '.join(report.candidates)}")
        if report.verifications:
            lines.append("")
            lines.append(f"Verifications: {len(report.verifications)}")
        lines.append("")

    # asyncio.to_thread to keep disk I/O off the event loop
    def _write(path: Path, body: str) -> None:
        path.write_text(body)
    body = "\n".join(lines)
    import asyncio
    await asyncio.to_thread(_write, out, body)
    logger.info("morning digest written to %s", out)
    return out


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
