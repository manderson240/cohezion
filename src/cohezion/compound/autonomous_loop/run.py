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
from .first_sprint import TestStabilizationSprint
from .task_generator import TaskGenerator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("autonomous_loop")


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full autonomous loop — Lemonade local inference by default."""
    use_local = not getattr(args, "no_local", False)
    config = LoopConfig(
        max_wall_clock_hours=args.hours,
        checkpoint_interval_seconds=args.checkpoint_interval,
        resume_from_checkpoint=args.resume,
        use_local_inference=use_local,
        local_model=getattr(args, "local_model", LoopConfig.local_model),
        local_base_url=getattr(args, "local_url", LoopConfig.local_base_url),
    )

    logger.info(
        "Executor: %s (model=%s, url=%s)",
        "local/Lemonade" if use_local else "cloud/Claude-CLI",
        config.local_model if use_local else config.claude_model,
        config.local_base_url if use_local else "subprocess",
    )

    coordinator = LoopCoordinator(config)

    # Load or generate backlog
    backlog_path = config.backlog_path
    if Path(backlog_path).exists() and args.resume:
        logger.info("Loading existing backlog from %s", backlog_path)
        raw = json.loads(Path(backlog_path).read_text())
        from .coordinator import LoopTask

        coordinator._backlog = [LoopTask(**t) for t in raw]
    else:
        logger.info("Generating new backlog")
        sprint = TestStabilizationSprint(config.worktree_path)
        sprint_tasks = sprint.generate_tasks()

        generator = TaskGenerator(config.worktree_path)
        additional_tasks = generator.generate_all()

        from .coordinator import LoopTask

        all_task_dicts = sprint_tasks + additional_tasks
        Path(backlog_path).parent.mkdir(parents=True, exist_ok=True)
        Path(backlog_path).write_text(json.dumps(all_task_dicts, indent=2))
        coordinator._backlog = [
            LoopTask(**{k: v for k, v in t.items() if k in LoopTask.__dataclass_fields__})
            for t in all_task_dicts
        ]
        logger.info("Generated %d tasks", len(coordinator._backlog))

    # Run — coordinator selects LocalImprovementExecutor or ImprovementExecutor per config
    logger.info("Starting autonomous loop (%.1fh budget)", config.max_wall_clock_hours)
    report: LoopReport = coordinator.run()  # no explicit executor — uses config.use_local_inference

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

    # Self-improvement feedback: persist learnings to vault via RetrospectionEngine
    _persist_loop_learnings(report, config)


def _persist_loop_learnings(report: LoopReport, config: LoopConfig) -> None:
    """Feed loop results back into the compound self-improvement infrastructure.

    Writes a structured learning record so the next loop iteration can build on
    what worked and avoid what failed. Uses local Lemonade inference to synthesize
    if available, otherwise writes raw metrics.
    """
    import json
    import urllib.request
    from datetime import datetime, timezone

    learning = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "loop_type": "local" if config.use_local_inference else "cloud",
        "model": config.local_model if config.use_local_inference else config.claude_model,
        "tasks_completed": report.tasks_completed,
        "tasks_failed": report.tasks_failed,
        "success_rate": report.success_rate,
        "elapsed_hours": report.elapsed_hours,
        "tokens_used": report.tokens_used,
        "results": [r for r in report.results[-10:]],  # last 10 tasks
    }

    # Try to synthesize a 1-sentence learning using local Lemonade
    if config.use_local_inference:
        try:
            payload = json.dumps(
                {
                    "model": config.local_fallback_model,  # fast model for synthesis
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"Summarize this autonomous loop run in one sentence, "
                                f"noting what category of tasks succeeded vs failed:\n{json.dumps(learning, indent=2)}"
                            ),
                        }
                    ],
                    "max_tokens": 100,
                    "temperature": 0.0,
                }
            ).encode()
            req = urllib.request.Request(
                f"{config.local_base_url}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                learning["synthesis"] = data["choices"][0]["message"].get("content", "")
        except Exception as exc:
            logger.debug("Synthesis skipped: %s", exc)

    # Write to SurrealDB experiment_runs table if available
    try:
        surreal_payload = (
            f"CREATE experiment_runs SET "
            f"event='autonomous_loop', "
            f"success_rate={learning['success_rate']:.4f}, "
            f"tasks_completed={learning['tasks_completed']}, "
            f"tasks_failed={learning['tasks_failed']}, "
            f"model='{learning['model']}', "
            f"loop_type='{learning['loop_type']}', "
            f"ts=time::now();"
        )
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=surreal_payload.encode(),
            headers={
                "Content-Type": "text/plain",
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Authorization": "Basic cm9vdDpyb290",  # root:root
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as _:
            pass
        logger.info("Loop learnings persisted to SurrealDB experiment_runs")
    except Exception as exc:
        logger.debug("SurrealDB write skipped: %s", exc)

    # Always write to local JSONL for offline inspection
    learning_path = Path(config.results_path).parent / "loop_learnings.jsonl"
    with open(learning_path, "a") as f:
        f.write(json.dumps(learning) + "\n")
    logger.info("Loop learning appended to %s", learning_path)


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
    run_parser.add_argument(
        "--no-local", action="store_true", help="Use Claude CLI instead of Lemonade (cloud mode)"
    )
    run_parser.add_argument(
        "--local-model",
        default=LoopConfig.local_model,
        help=f"Lemonade model name (default: {LoopConfig.local_model})",
    )
    run_parser.add_argument(
        "--local-url",
        default=LoopConfig.local_base_url,
        help=f"Lemonade base URL (default: {LoopConfig.local_base_url})",
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
