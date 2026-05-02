#!/usr/bin/env python3
"""Compound engineering driver — runs the full template-directed loop.

Cycle:
  1. Select N PRIME skills
  2. Expand each via InstructionExpander -> ExecutablePlan
  3. Build a TeamPlan and execute via ExecutionOrchestrator
  4. Analyze via RetrospectionEngine.analyze_execution()
  5. Refine skills if compound_score_delta > threshold
  6. Report: token metrics, executions, refinements, compound score

Usage:
  uv run python scripts/compound_driver.py --skills 5 --dry-run
  uv run python scripts/compound_driver.py --skills 10 --model phi3:mini
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path


# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.core.compound.retrospection import RetrospectionEngine
from cohezion.core.compound.skill_refiner import SkillRefiner
from cohezion.core.instruction_expander import InstructionExpander
from cohezion.core.template_engine import SkillSpec, TemplateEngine
from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator
from cohezion.swarm.team_orchestrator import TaskSpec, TeamPlan


logger = logging.getLogger(__name__)


def select_skills(n: int) -> list[SkillSpec]:
    """Parse all PRIME skills and return the first N."""
    engine = TemplateEngine()
    specs = engine.parse_all()
    # Prefer skills with instructions (more interesting to execute)
    with_instructions = [s for s in specs if s.instructions]
    without = [s for s in specs if not s.instructions]
    ordered = with_instructions + without
    return ordered[:n]


def build_team_plan(specs: list[SkillSpec], expander: InstructionExpander) -> TeamPlan:
    """Build a TeamPlan from expanded skill specs."""
    tasks: list[TaskSpec] = []
    for i, spec in enumerate(specs):
        plan = expander.expand(spec)
        tasks.append(
            TaskSpec(
                id=f"skill-{i + 1}",
                subject=f"Execute: {spec.name}",
                description=f"Run {len(plan.steps)} steps for {spec.name}",
                tags=[spec.name],
            )
        )
    return TeamPlan(
        name="compound-cycle",
        intent="Compound engineering cycle across PRIME skills",
        tasks=tasks,
    )


async def run_compound_cycle(
    num_skills: int = 5,
    threshold: float = 0.5,
    dry_run: bool = True,
    model: str = "phi3:mini",
) -> dict:
    """Run one full compound engineering cycle.

    Parameters
    ----------
    num_skills : int
        Number of PRIME skills to process.
    threshold : float
        Compound score delta threshold for triggering refinements.
    dry_run : bool
        If True, use no LLM calls (placeholder execution).
    model : str
        Ollama model for live execution.

    Returns
    -------
    dict
        Cycle report with metrics.
    """
    t0 = time.monotonic()
    report: dict = {
        "mode": "dry-run" if dry_run else f"live ({model})",
        "skills_requested": num_skills,
    }

    # --- Step 1: Select skills ---
    print(f"\n{'=' * 60}")
    print("  COMPOUND ENGINEERING CYCLE")
    print(f"  Mode: {'DRY RUN' if dry_run else f'LIVE ({model})'}")
    print(f"  Skills: {num_skills} | Threshold: {threshold}")
    print(f"{'=' * 60}\n")

    specs = select_skills(num_skills)
    report["skills_selected"] = len(specs)
    print(f"[1/5] Selected {len(specs)} PRIME skills:")
    for s in specs:
        print(f"  - {s.name} ({len(s.instructions)} instructions)")

    # --- Step 2: Expand instructions ---
    expander = InstructionExpander()
    plans = []
    total_steps = 0
    for spec in specs:
        plan = expander.expand(spec)
        plans.append((spec, plan))
        total_steps += len(plan.steps)

    report["total_steps"] = total_steps
    print(f"\n[2/5] Expanded {len(plans)} skills into {total_steps} plan steps")

    # --- Step 3: Execute via orchestrator ---
    token_client = None
    if not dry_run:
        try:
            from cohezion.swarm.compound_client import get_compound_client

            token_client = get_compound_client(model=model)
            print(f"  Using live TokenEfficientClient with {model}")
        except ImportError:
            print("  WARNING: compound_client not available, using dry-run mode")

    team_plan = build_team_plan(specs, expander)
    orchestrator = ExecutionOrchestrator(token_client=token_client)
    exec_report = await orchestrator.execute(team_plan)

    report["tasks_completed"] = sum(1 for tr in exec_report.task_results if tr.status == "completed")
    report["tasks_failed"] = sum(1 for tr in exec_report.task_results if tr.status == "failed")
    report["total_tokens"] = exec_report.total_tokens
    report["execution_duration_ms"] = round(exec_report.total_duration_ms, 1)

    print("\n[3/5] Execution complete:")
    print(f"  Completed: {report['tasks_completed']}/{len(exec_report.task_results)}")
    print(f"  Tokens: {report['total_tokens']}")
    print(f"  Duration: {report['execution_duration_ms']:.0f}ms")

    # --- Step 4: Retrospection ---
    retro = RetrospectionEngine()
    analysis = retro.analyze_execution(exec_report)
    compound_delta = analysis.get("compound_score_delta", 0.0)
    report["compound_score_delta"] = compound_delta
    report["patterns"] = analysis.get("patterns", [])

    print("\n[4/5] Retrospection analysis:")
    print(f"  Compound score delta: {compound_delta:.4f}")
    for pattern in report["patterns"]:
        print(f"  - {pattern}")

    # --- Step 5: Skill refinement ---
    refinements_applied = 0
    if compound_delta >= threshold:
        suggestions = retro.suggest_skill_refinements()
        if suggestions:
            refiner = SkillRefiner()
            results = refiner.refine_from_suggestions(suggestions)
            refinements_applied = sum(1 for r in results if r.additions)
            print(f"\n[5/5] Applied {refinements_applied} skill refinements")
            for r in results:
                if r.additions:
                    print(f"  - {r.skill_name}: v{r.version_before} -> v{r.version_after}")
        else:
            print("\n[5/5] No refinement suggestions (all skills up to date)")
    else:
        print(f"\n[5/5] Skipping refinement (delta {compound_delta:.4f} < threshold {threshold})")

    report["refinements_applied"] = refinements_applied

    # --- Token metrics ---
    if token_client is not None:
        metrics = token_client.get_metrics()
        report["token_metrics"] = metrics
        print("\n  Token Metrics:")
        print(f"    Cache hit rate: {metrics.get('cache_hit_rate', 0):.1%}")
        print(f"    Tokens saved: {metrics.get('tokens_saved', 0)}")
        print(f"    Total calls: {metrics.get('total_calls', 0)}")

    elapsed = time.monotonic() - t0
    report["total_cycle_duration_s"] = round(elapsed, 2)

    print(f"\n{'=' * 60}")
    print(f"  CYCLE COMPLETE in {elapsed:.1f}s")
    print(f"  Skills: {report['skills_selected']} | Steps: {report['total_steps']}")
    print(f"  Compound delta: {compound_delta:.4f} | Refinements: {refinements_applied}")
    print(f"{'=' * 60}\n")

    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run a compound engineering cycle across PRIME skills")
    parser.add_argument("--skills", type=int, default=5, help="Number of skills to process")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Compound score threshold for refinement",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run without LLM calls (placeholder execution)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="phi3:mini",
        help="Ollama model for live execution",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    """Entry point."""
    args = parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    return asyncio.run(
        run_compound_cycle(
            num_skills=args.skills,
            threshold=args.threshold,
            dry_run=args.dry_run,
            model=args.model,
        )
    )


if __name__ == "__main__":
    main()
