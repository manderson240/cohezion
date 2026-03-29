#!/usr/bin/env python3
"""Compound engineering pipeline: search -> plan -> retrospect.

Usage:
    uv run python scripts/compound_pipeline.py "add error handling to API"
    uv run python scripts/compound_pipeline.py --list-capabilities
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def search_capabilities(intent: str, top_k: int = 5) -> list:
    """Search the capability registry for matching skills."""
    from cohezion.registry.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()
    matches = registry.find(intent, top_k=top_k)
    return matches


def generate_team_plan(intent: str, max_agents: int = 4) -> object:
    """Generate a team plan from an intent."""
    from cohezion.swarm.team_orchestrator import TeamOrchestrator

    orchestrator = TeamOrchestrator()
    plan = orchestrator.plan_team(intent, max_agents=max_agents)
    return plan


def run_retrospection(session_facts: dict) -> str:
    """Run retrospection and generate a session report."""
    from cohezion.core.compound.retrospection import RetrospectionEngine

    engine = RetrospectionEngine()
    report = engine.generate_session_report(session_facts)
    return report


def list_capabilities() -> None:
    """List all registered capabilities grouped by type."""
    from cohezion.registry.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()

    by_type: dict[str, list] = {}
    for cap in registry.capabilities:
        by_type.setdefault(cap.type, []).append(cap)

    total = len(registry.capabilities)
    print(f"\nCapability Registry: {total} total capabilities\n")

    for cap_type, caps in sorted(by_type.items()):
        print(f"  [{cap_type.upper()}] ({len(caps)})")
        for cap in sorted(caps, key=lambda c: c.name)[:10]:
            usage = f" (used {cap.usage_count}x)" if cap.usage_count > 0 else ""
            print(f"    - {cap.name}: {cap.description[:60]}{usage}")
        if len(caps) > 10:
            print(f"    ... and {len(caps) - 10} more")
    print()


def compound_pipeline(intent: str, max_agents: int = 4) -> None:
    """Run the full compound engineering loop.

    1. Search capabilities
    2. Generate team plan
    3. Output plan for Claude Code to execute
    4. Run retrospection
    """
    print(f"\n{'=' * 60}")
    print("  COMPOUND ENGINEERING PIPELINE")
    print(f"  Intent: {intent}")
    print(f"{'=' * 60}\n")

    # Step 1: Search capabilities
    print("Step 1: Searching capability registry...")
    matches = search_capabilities(intent)
    if not matches:
        print("  No matching capabilities found.")
        return

    print(f"  Found {len(matches)} matching capabilities:")
    for m in matches:
        print(f"    - [{m.type}] {m.name} (score: {m.score:.2f})")
    print()

    # Step 2: Generate team plan
    print("Step 2: Generating team plan...")
    plan = generate_team_plan(intent, max_agents=max_agents)
    print(f"\n{plan.summary}\n")

    # Step 3: Model routing
    print("Step 3: Model routing for tasks:")
    from cohezion.swarm.team_orchestrator import TeamOrchestrator

    orchestrator = TeamOrchestrator()
    for task in plan.tasks:
        model = orchestrator.select_model(task)
        print(f"  [{task.id}] {task.subject[:40]} -> {model}")
    print()

    # Step 4: Retrospection
    print("Step 4: Running retrospection...")
    session_facts = {
        "intent": intent,
        "capabilities_used": [m.name for m in matches],
    }
    report = run_retrospection(session_facts)
    print(report)

    # Step 5: Track usage
    print("\nStep 5: Tracking capability usage...")
    from cohezion.registry.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()
    for match in matches:
        registry.increment_usage(match.name)
        print(f"  Incremented usage: {match.name}")

    print(f"\n{'=' * 60}")
    print("  Pipeline complete.")
    print(f"{'=' * 60}\n")


def live_execution(intent: str, model: str | None = None) -> None:
    """Run live compound execution via CompoundExecutor."""
    import asyncio

    from cohezion.compound.executor import CompoundExecutor

    async def _run() -> None:
        executor = CompoundExecutor()
        # Use intent as both skill hint and input
        skill_name = "COMPOUND_ENGINEERING_PRIME"  # default skill
        print(f"\n  Running live execution: {skill_name}")
        print(f"  Input: {intent[:80]}...")
        result = await executor.execute_skill(skill_name, intent, model=model)
        print(f"\n  Steps: {len(result.steps)}")
        print(f"  Tokens: {result.total_tokens}")
        print(f"  Duration: {result.total_duration_ms:.0f}ms")
        print(f"  Models: {result.model_usage}")
        print(f"\n  Output: {result.final_output[:200]}...")

    asyncio.run(_run())


def feedback_cycle(intent: str, cycles: int = 1, model: str | None = None) -> None:
    """Run the compound feedback loop."""
    import asyncio

    from cohezion.compound.feedback_loop import CompoundFeedbackLoop

    async def _run() -> None:
        loop = CompoundFeedbackLoop()
        skill_name = "COMPOUND_ENGINEERING_PRIME"
        if cycles > 1:
            report = await loop.run_multi_cycle(skill_name, intent, cycles=cycles, model=model)
            print(f"\n  Cycles: {report.total_cycles}")
            print(f"  Tokens: {report.total_tokens}")
            print(f"  Refinements: {report.total_refinements}")
            print(f"  Final delta: {report.final_compound_score_delta:.4f}")
        else:
            result = await loop.run_cycle(skill_name, intent, model=model)
            print(f"\n  Delta: {result.compound_score_delta:.4f}")
            print(f"  Tokens: {result.execution_tokens}")
            print(f"  Refinements: {result.refinements_applied}")
            print(f"  Patterns: {result.patterns}")

    asyncio.run(_run())


def show_metrics() -> None:
    """Display compound metrics from the collector."""
    from cohezion.compound.metrics import get_collector

    collector = get_collector()
    health = collector.to_health_dict()
    print("\n  Compound Health Report:")
    print(f"    Executions: {health['total_executions']}")
    print(f"    Refinements: {health['total_refinements']}")
    print(f"    Cycles: {health['total_cycles']}")
    print(f"    Success rate: {health['success_rate']:.1%}")
    print(f"    Total tokens: {health['total_tokens']}")
    if health["model_usage"]:
        print(f"    Model usage: {health['model_usage']}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compound Engineering Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "intent",
        nargs="?",
        help="Natural language intent for the pipeline",
    )
    parser.add_argument(
        "--list-capabilities",
        action="store_true",
        help="List all registered capabilities",
    )
    parser.add_argument(
        "--max-agents",
        type=int,
        default=4,
        help="Maximum number of agents (default: 4)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live compound execution via Ollama",
    )
    parser.add_argument(
        "--feedback",
        action="store_true",
        help="Run compound feedback loop (execute -> analyze -> refine)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of feedback cycles (default: 1)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override Ollama model for live execution",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Display compound metrics",
    )

    args = parser.parse_args()

    if args.list_capabilities:
        list_capabilities()
        return

    if args.metrics:
        show_metrics()
        return

    if not args.intent:
        parser.error("Please provide an intent or use --list-capabilities / --metrics")

    if args.feedback:
        feedback_cycle(args.intent, cycles=args.cycles, model=args.model)
    elif args.live:
        live_execution(args.intent, model=args.model)
    else:
        compound_pipeline(args.intent, max_agents=args.max_agents)


if __name__ == "__main__":
    main()
