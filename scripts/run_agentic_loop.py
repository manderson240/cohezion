#!/usr/bin/env python3
"""Agentic compound loop — local inference via Lemonade OmniRouter on :13305.

Populates a backlog from PRIME skills and runs LoopCoordinator.
All inference routed through the single OmniRouter; no per-port addresses.

Usage:
    uv run python scripts/run_agentic_loop.py                # 10 skills, 5 min sprints
    uv run python scripts/run_agentic_loop.py --skills 20    # larger backlog
    uv run python scripts/run_agentic_loop.py --dry-run      # verify connectivity only
    uv run python scripts/run_agentic_loop.py --skills 5 --sprint 120  # short sprints
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.compound.autonomous_loop.coordinator import LoopConfig, LoopCoordinator, LoopTask
from cohezion.compound.autonomous_loop.local_executor import get_tier_health, warmup_tiers
from cohezion.config.defaults import LEMONADE_BASE_URL
from cohezion.inference.oom_guard import check_ram, verify_all_bounded


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agentic_loop")


def _check_router(base_url: str) -> bool:
    try:
        req = urllib.request.Request(f"{base_url}/api/v1/models", method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
            d = json.loads(resp.read())
            models = d if isinstance(d, list) else d.get("models", d.get("data", []))
            logger.info("OmniRouter healthy: %d models available", len(models))
            return True
    except Exception as exc:
        logger.error("OmniRouter unreachable at %s: %s", base_url, exc)
        return False


def _warmup_and_show_tiers(base_url: str, skip_warmup: bool = False) -> None:
    """Pre-load all compute tiers and display device placement."""
    if not skip_warmup:
        logger.info("Warming up compute tiers (NPU / iGPU / CPU) …")
        results = warmup_tiers(base_url)
        for tier, ok in results.items():
            logger.info("  tier %-6s warmup: %s", tier, "OK" if ok else "FAILED")

    health = get_tier_health(base_url)
    if health:
        logger.info("Active inference tiers:")
        tier_map = {"npu": "NPU (XDNA2)", "gpu": "iGPU (RDNA3.5)", "cpu": "CPU (x86)"}
        for model, device in sorted(health.items()):
            label = tier_map.get(device, device)
            logger.info("  %-45s → %s", model, label)
    else:
        logger.warning("Could not reach /v1/health to verify tier placement")


def _build_backlog(n: int) -> list[LoopTask]:
    """Build a loop backlog from PRIME skills."""
    from cohezion.core.template_engine import TemplateEngine

    engine = TemplateEngine()
    specs = engine.parse_all()
    with_instructions = [s for s in specs if s.instructions]
    selected = (with_instructions + [s for s in specs if not s.instructions])[:n]

    tasks: list[LoopTask] = []
    for i, spec in enumerate(selected):
        instruction = spec.instructions[0] if spec.instructions else f"Analyze {spec.name}"
        tasks.append(
            LoopTask(
                id=f"skill-{i + 1:03d}-{spec.name[:20].replace(' ', '_')}",
                description=f"[SKILL: {spec.name}] {instruction}",
                category="skill_improvement",
                priority=10 - (i % 10),
                verification=f"Verify {spec.name} improvement is concrete and actionable",
                estimated_tokens=300,
            )
        )

    # Add data mesh quality tasks
    tasks.append(
        LoopTask(
            id="datamesh-quality-001",
            description="Audit the DataMesh EventBridge SurrealDB write-through path for correctness and OOM safety",
            category="data_mesh",
            priority=8,
            verification="Confirm EventBridge handles queue-full gracefully and ctx_size=0 guard is enforced",
            estimated_tokens=400,
        )
    )
    tasks.append(
        LoopTask(
            id="oom-guard-verify-001",
            description="Verify all heavy models in the OmniRouter catalog have ctx_size bounded (N3 invariant)",
            category="infrastructure",
            priority=9,
            verification="All heavy models (>=5GB) show ctx_size <= 16384 in /api/v1/models",
            estimated_tokens=200,
        )
    )
    tasks.append(
        LoopTask(
            id="compound-loop-health-001",
            description="Assess the compound engineering loop health: cache hit rate, token efficiency, routing accuracy",
            category="compound_health",
            priority=7,
            verification="Report cache hit rate, model routing distribution, and any degradation signals",
            estimated_tokens=350,
        )
    )

    logger.info("Backlog built: %d tasks (%d from skills, 3 infrastructure)", len(tasks), len(selected))
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic compound loop with local inference")
    parser.add_argument("--skills", type=int, default=10, help="Number of PRIME skills to include (default: 10)")
    parser.add_argument("--sprint", type=float, default=300.0, help="Sprint duration in seconds (default: 300)")
    parser.add_argument("--max-tokens", type=int, default=50_000, help="Token budget for the loop (default: 50000)")
    parser.add_argument("--dry-run", action="store_true", help="Check connectivity and exit")
    parser.add_argument("--base-url", default=LEMONADE_BASE_URL, help="OmniRouter base URL")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Cohezion Agentic Loop — Lemonade OmniRouter: %s", args.base_url)
    logger.info("=" * 60)

    # Pre-flight checks
    if not _check_router(args.base_url):
        logger.error("Aborting: OmniRouter not reachable. Start with: lemond --port 13305")
        sys.exit(1)

    all_bounded, violations = verify_all_bounded(args.base_url)
    if violations:
        logger.error("N3 VIOLATION: heavy models with ctx_size=0: %s", violations)
        logger.error("Run: oom_guard.scan_and_harden() to fix before continuing")
        sys.exit(1)

    safe, free_gb = check_ram(min_free_gb=8.0)
    if not safe:
        logger.warning("RAM low: %.1f GiB free (8 GiB floor). Proceeding with caution.", free_gb)
    else:
        logger.info("RAM: %.1f GiB free — OK", free_gb)

    # Warmup all three compute tiers (fixes stale NPU FLM context; loads CPU tier)
    _warmup_and_show_tiers(args.base_url, skip_warmup=args.dry_run)

    if args.dry_run:
        logger.info("Dry run complete — all pre-flight checks passed")
        return

    # Build backlog
    tasks = _build_backlog(args.skills)

    # Configure and run loop
    config = LoopConfig(
        use_local_inference=True,
        local_base_url=args.base_url,
        max_tokens=args.max_tokens,
        sprint_duration_seconds=args.sprint,
        cloud_escalation_threshold=3,
        min_free_ram_gb=8.0,
    )

    coordinator = LoopCoordinator(config)
    coordinator._backlog = tasks  # noqa: SLF001

    logger.info("Starting loop: %d tasks, %.0fs sprints, %d token budget",
                len(tasks), config.sprint_duration_seconds, config.max_tokens)
    t0 = time.monotonic()

    try:
        report = coordinator.run()
    except KeyboardInterrupt:
        logger.info("Loop interrupted by user")
        return

    elapsed = time.monotonic() - t0
    local_tokens = sum(s.local_tokens for s in report.sprint_results)
    cloud_tokens = sum(s.cloud_tokens for s in report.sprint_results)

    logger.info("=" * 60)
    logger.info("Loop complete in %.1fs", elapsed)
    logger.info("  Tasks completed : %d", report.tasks_completed)
    logger.info("  Tasks failed    : %d", report.tasks_failed)
    logger.info("  Local tokens    : %d (cost: $0.00)", local_tokens)
    logger.info("  Cloud tokens    : %d", cloud_tokens)
    logger.info("  Sprints         : %d", len(report.sprint_results))
    logger.info("=" * 60)

    # Print per-task summary
    for r in report.results[:20]:
        status = "✓" if r["success"] else "✗"
        model = r.get("model", "?")[:20]
        logger.info("  %s %-40s  %s  %d tok",
                    status, r["task_id"][:40], model, r.get("tokens", 0))


if __name__ == "__main__":
    main()
