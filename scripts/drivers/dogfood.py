#!/usr/bin/env python3
"""Cohezion builds Cohezion — minimal dogfood runner.

Runs the compound loop on actual compound engineering tasks using real local
inference (:13305 OmniRouter). No mocks. Failures ARE the findings.

Usage:
    uv run python scripts/drivers/dogfood.py
    uv run python scripts/drivers/dogfood.py --task "wire jepa_coherence into check_degradation"
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logging.basicConfig(level=logging.WARNING, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("dogfood")

TASKS = [
    "Describe the wiring gap in H1 (bootstrap_fixtures has no prod caller) and propose the one-line fix in SkillRefiner.refine().",
    "What does jepa_coherence currently produce in execute_task() and what does check_degradation() need to consume it? Name the exact method and file.",
    "Identify the dormant inference_provider field in CompoundExecutor.execute_task() — where is it set and where is it NOT read?",
    "What does DegradationDetector.suggest_routing_tier() return and which callers in production code act on its return value?",
]

# Static codebase context injected at the front of every prompt.
# Gives the CPU-tier 31B model enough domain grounding to answer Cohezion-specific
# questions without needing SurrealDB, vault access, or the full file tree.
COHEZION_CONTEXT = """You are an expert in the Cohezion compound AI codebase. Key facts:

## Module Map (src/cohezion/compound/)
- executor.py       — CompoundExecutor.execute_task() — 11-step pipeline, 1690 lines
- executor_factory.py — ExecutorFactory.create() / make_executor() — preferred constructor
- skill_refiner.py  — SkillRefiner.refine() — PRIME skill updates; durable spine (to_dict/from_dict)
- degradation_detector.py — DegradationDetector — EMA thresholds, suggest_routing_tier(), check_degradation()
- jepa_gate.py      — JepaGate.check() — pre-execution PROCEED/REROUTE/SKIP verdict, .last_coherence
- journey_tracker.py — JourneyTracker.track_execution() — 12D trajectory, FLUME encoder
- local_inference.py — make_local_execute_fn() — bridges sync execute_fn → async TieredOrchestrator
- difficulty_estimator.py — DifficultyEstimator.predict_tier() — GIC tier prediction

## Active Open Wiring Gaps (V-model deferred items)
- H2 (FIXED — wiring complete, calibration is the real gap): jepa_coherence flows from JepaGate →
  degradation_metrics (executor.py:1228) → check_degradation() (degradation_detector.py:241) →
  alert at lines 325-340 → baseline at lines 433-434. Fully wired. But LemonadeWorldModel
  gives coherence=0.010 for all compound questions (1B NPU has no Cohezion knowledge), so the
  alert threshold (chebyshev_lower_bound on a near-zero constant) never fires a useful signal.
- inference_provider (OPEN): CompoundExecutor.__init__ stores inference_provider in self._inference_provider.
  execute_task() never reads self._inference_provider inside the method. Dormant dead-end.
- CR1 (OPEN): _recompute_tier_at_compaction() is defined in CompoundExecutor but has no caller in production.
- JEPA coherence calibration (FIXED 2026-07-02): Beta(2,2) prior in LemonadeWorldModel.predict_next_state():
  coh = (2*0.7 + llm_coh) / 3.0. Raw 0.010 → smoothed 0.470 → REROUTE (not SKIP). SKIP is now
  structurally impossible for any in-range LLM output (min smoothed = 0.467 > SKIP threshold 0.1).

## Key Fixed Items (this session)
- CB5 (FIXED): ExecutorFactory.create() now auto-creates DegradationDetector and wires set_routing_callback.
- DRR-3 (FIXED): executor.py Step 5.85 now resolves real PRIME skill file paths before calling DRRGenerator.
- H1+M1 (FIXED): SkillRefinerFactory.get_singleton() now delegates to create() which wires _regression_run_fn.
- Orchestrator (FIXED): local_inference.py now uses build_reasoning_orchestrator() (deepseek-r1-8B NPU +
  Gemma-4-E4B iGPU + Gemma-4-E4B CPU/TRUST, max_tokens=2048 each) instead of build_triune_omni_orchestrator()
  which had min_chars=500/2000 quality gates guaranteeing 100% escalation to the slow 31B thinking model.
- JEPA calibration (FIXED 2026-07-02): Beta(2,2) prior in LemonadeWorldModel. coherence 0.010→0.470.
  REROUTE still fires (jepa_coherence < 0.6) but no longer collapses to SKIP. All 17 gate tests pass.
"""


def build_minimal_mcp():
    """Minimal MCP client — only vault ops needed for execute_task."""
    mcp = MagicMock()
    mcp.vault_find_relevant_context.return_value = []
    mcp.vault_search.return_value = []
    mcp.vault_write.return_value = "success"
    mcp.vault_read.return_value = "{}"
    mcp.vault_log_experiment.return_value = "experiments/dogfood.md"
    mcp.vault_log_decision.return_value = "decisions/dogfood.md"
    # Sync vault stubs: vault.py:log_execution_result calls vault_read_sync then
    # json.loads() on the result — must return a valid JSON string, not MagicMock.
    _empty_experiment = '{"status": "pending", "metrics": {}, "output_summary": ""}'
    mcp.vault_read_sync.return_value = _empty_experiment
    mcp.vault_write_sync.return_value = "success"
    return mcp


def run(task: str) -> dict:
    from cohezion.compound import make_executor
    from cohezion.compound.local_inference import make_local_execute_fn

    mcp = build_minimal_mcp()
    executor = make_executor(mcp)

    execute_fn = make_local_execute_fn(task_description=task, context_prefix=COHEZION_CONTEXT)

    findings: dict = {
        "task": task,
        "executor_type": type(executor).__name__,
        "inference_provider": type(getattr(executor, "_inference_provider", None)).__name__,
        "degradation_detector": type(getattr(executor, "_degradation_detector", None)).__name__,
        "jepa_gate": type(getattr(executor, "_jepa_gate", None)).__name__,
        "errors": [],
        "output": None,
        "metrics": {},
        "duration_s": 0.0,
    }

    t0 = time.time()
    try:
        result = executor.execute_task(
            task_description=task,
            operation_type="analyze",
            skill_name="compound-engineering",
            execute_fn=execute_fn,
        )
        findings["output"] = result.output[:500] if result.output else "(empty)"
        findings["metrics"] = {
            k: v for k, v in (result.metrics or {}).items()
            if k in ("tier_used", "escalation_count", "quality_score", "tokens_used",
                     "suggested_tier", "predicted_tier", "jepa_coherence")
        }
    except Exception as exc:
        findings["errors"].append(f"{type(exc).__name__}: {exc}")
        logger.warning("execute_task raised: %s", exc, exc_info=True)

    findings["duration_s"] = round(time.time() - t0, 2)
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=None, help="single task to run")
    parser.add_argument("--all", action="store_true", help="run all built-in tasks")
    args = parser.parse_args()

    tasks = [args.task] if args.task else (TASKS if args.all else TASKS[:1])

    print("\n" + "=" * 72)
    print("COHEZION BUILDS COHEZION — dogfood run")
    print("=" * 72)

    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] Task: {task[:80]}...")
        findings = run(task)

        print(f"  executor     : {findings['executor_type']}")
        print(f"  inference    : {findings['inference_provider']}")
        print(f"  degradation  : {findings['degradation_detector']}")
        print(f"  jepa_gate    : {findings['jepa_gate']}")
        print(f"  duration     : {findings['duration_s']}s")

        if findings["errors"]:
            print(f"  ERRORS ({len(findings['errors'])}):")
            for e in findings["errors"]:
                print(f"    ✗ {e}")
        else:
            print(f"  metrics      : {findings['metrics']}")
            out = findings["output"] or "(empty)"
            print(f"  output[:200] : {out[:200]}")


if __name__ == "__main__":
    main()
