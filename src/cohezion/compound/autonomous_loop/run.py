#!/usr/bin/env python3
"""CLI entry point for the autonomous compound engineering loop.

Usage:
    uv run python -m cohezion.compound.autonomous_loop.run
    uv run python -m cohezion.compound.autonomous_loop.run --hours 2 --resume
    uv run python -m cohezion.compound.autonomous_loop.run --generate-only
    uv run python -m cohezion.compound.autonomous_loop.run --status
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .coordinator import LoopConfig, LoopCoordinator, LoopReport
from .executor import ImprovementExecutor
from .first_sprint import TestStabilizationSprint
from .task_generator import TaskGenerator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("autonomous_loop")


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full autonomous loop."""
    config = LoopConfig(
        max_wall_clock_hours=args.hours,
        checkpoint_interval_seconds=args.checkpoint_interval,
        resume_from_checkpoint=args.resume,
    )

    # Initialize components
    coordinator = LoopCoordinator(config)
    executor = ImprovementExecutor(config)

    # Load or generate backlog
    backlog_path = config.backlog_path
    if Path(backlog_path).exists() and args.resume:
        logger.info("Loading existing backlog from %s", backlog_path)
        _raw_tasks = json.loads(Path(backlog_path).read_text())
    else:
        logger.info("Generating new backlog")
        # First sprint: test stabilization
        sprint = TestStabilizationSprint(config.worktree_path)
        sprint_tasks = sprint.generate_tasks()

        # Additional tasks from codebase scanning
        generator = TaskGenerator(config.worktree_path)
        additional_tasks = generator.generate_all()

        # Combine: sprint tasks first (highest priority), then additional
        all_tasks = sprint_tasks + additional_tasks

        # Save backlog
        Path(backlog_path).parent.mkdir(parents=True, exist_ok=True)
        Path(backlog_path).write_text(json.dumps(all_tasks, indent=2))
        logger.info("Generated %d tasks", len(all_tasks))

    # Run the loop
    logger.info("Starting autonomous loop (%.1fh budget)", config.max_wall_clock_hours)
    report: LoopReport = coordinator.run(executor)

    # Print report
    print("\n" + report.summary())

    # Save results
    results_path = Path(config.results_path)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        json.dumps(
            {
                "report": {
                    "started_at": report.started_at,
                    "elapsed_hours": report.elapsed_hours,
                    "tasks_completed": report.tasks_completed,
                    "tasks_failed": report.tasks_failed,
                    "tasks_total": report.tasks_total,
                    "success_rate": report.success_rate,
                    "tokens_used": report.tokens_used,
                },
                "results": report.results,
            },
            indent=2,
        )
    )
    logger.info("Results saved to %s", results_path)


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate tasks without running the loop."""
    repo_root = args.repo or "/home/mike-anderson/dev/cohezion"

    # Test stabilization sprint
    sprint = TestStabilizationSprint(repo_root)
    sprint_tasks = sprint.generate_tasks()

    # Additional tasks
    generator = TaskGenerator(repo_root)
    additional_tasks = generator.generate_all()

    all_tasks = sprint_tasks + additional_tasks
    all_tasks.sort(key=lambda t: t.get("priority", 99))

    print(json.dumps(all_tasks, indent=2))
    logger.info("Generated %d tasks", len(all_tasks))


def cmd_status(args: argparse.Namespace) -> None:
    """Show current loop status from checkpoint."""
    checkpoint_path = args.checkpoint or "/tmp/cohezion-autonomous-loop/checkpoint.json"
    path = Path(checkpoint_path)

    if not path.exists():
        print("No checkpoint found. Loop has not started or was cleaned up.")
        return

    data = json.loads(path.read_text())
    print("### Autonomous Loop Status")
    print("")
    print(f"**Started:** {data.get('started_at', 'unknown')}")
    print(f"**Last updated:** {data.get('last_updated', 'unknown')}")
    print(
        f"**Wall clock:** {data.get('wall_clock_seconds', 0):.0f}s ({data.get('wall_clock_seconds', 0) / 3600:.1f}h)"
    )
    print("")
    print("| Metric | Value |")
    print("|--------|-------|")
    print(f"| Tasks completed | {data.get('tasks_completed', 0)} |")
    print(f"| Tasks failed | {data.get('tasks_failed', 0)} |")
    print(f"| Tasks total | {data.get('tasks_total', 0)} |")
    print(f"| Tokens used | {data.get('tokens_used', 0):,} |")
    print(f"| Sprint count | {data.get('total_sprints', 0)} |")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous compound engineering loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python -m cohezion.compound.autonomous_loop.run
  uv run python -m cohezion.compound.autonomous_loop.run --hours 2 --resume
  uv run python -m cohezion.compound.autonomous_loop.run --generate-only
  uv run python -m cohezion.compound.autonomous_loop.run --status
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    run_parser = subparsers.add_parser("run", help="Run the autonomous loop")
    run_parser.add_argument("--hours", type=float, default=3.0, help="Max wall-clock hours")
    run_parser.add_argument(
        "--checkpoint-interval", type=int, default=900, help="Checkpoint interval (seconds)"
    )
    run_parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    run_parser.add_argument(
        "--repo", default="/home/mike-anderson/dev/cohezion", help="Repository root"
    )

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate tasks without running")
    gen_parser.add_argument(
        "--repo", default="/home/mike-anderson/dev/cohezion", help="Repository root"
    )

    # status
    status_parser = subparsers.add_parser("status", help="Show loop status")
    status_parser.add_argument("--checkpoint", help="Checkpoint file path")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        # Default: run
        cmd_run(args)


if __name__ == "__main__":
    main()
