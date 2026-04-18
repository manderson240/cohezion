"""V-Model Phase 6 — Tiered Orchestrator AutoHarness.

Gatekeeps invariants O1–O8 from ``docs/vmodel/PHASE6_ORCHESTRATOR_PLAN.md``.
Pure-structural + pytest — no live fleet calls required.
"""

from __future__ import annotations

import inspect
import subprocess
import sys


def _pass(inv: str, detail: str = "") -> None:
    print(f"✅ {inv}{': ' + detail if detail else ''}")


def _fail(inv: str, reason: str) -> None:
    print(f"❌ FAILED {inv}: {reason}")


def verify_invariants() -> bool:
    print("🛡️  [V-MODEL Phase 6 HARNESS] Verifying orchestrator invariants...")

    try:
        from cohezion.inference import (
            OrchestrationResult,
            QualityGate,
            TierAttempt,
            TieredOrchestrator,
            default_hierarchy,
        )
    except ImportError as exc:
        _fail("import", f"orchestrator not importable: {exc}")
        return False

    # O5: QualityGate.TRUST always passes; min_chars gate is deterministic.
    if not QualityGate.TRUST.check(
        __import__("cohezion.inference", fromlist=["RouteResult"]).RouteResult(
            text="", model="m", lane="l", latency_ms=0.0
        )
    )[0]:
        _fail("O5", "QualityGate.TRUST does not always pass")
        return False
    g10 = QualityGate(min_chars=10)
    from cohezion.inference.fleet import RouteResult

    if g10.check(RouteResult(text="short", model="m", lane="l", latency_ms=0.0))[0]:
        _fail("O5", "min_chars=10 accepted 5-char text")
        return False
    if not g10.check(RouteResult(text="longer than ten", model="m", lane="l", latency_ms=0.0))[0]:
        _fail("O5", "min_chars=10 rejected 15-char text")
        return False
    _pass("O5", "QualityGate semantics deterministic")

    # O6: OrchestrationResult schema
    required = {
        "text",
        "primary_model",
        "final_model",
        "escalation_count",
        "tier_path",
        "cost_usd",
        "latency_ms",
        "ttft_ms",
        "error",
    }
    actual = {f.name for f in OrchestrationResult.__dataclass_fields__.values()}
    missing = required - actual
    if missing:
        _fail("O6", f"OrchestrationResult missing fields: {missing}")
        return False
    _pass("O6", f"OrchestrationResult exposes {len(required)} required fields")

    # O8: Orchestrator.run is async
    if not inspect.iscoroutinefunction(TieredOrchestrator.run):
        _fail("O8", "TieredOrchestrator.run is not async")
        return False
    _pass("O8", "TieredOrchestrator.run is async")

    # O3b: TieredOrchestrator.run accepts a `budget_usd` kwarg so a parent
    # orchestrator can propagate its remaining budget to a nested one and
    # cap composite spend (adversarial review Edge-case #10).
    run_sig = inspect.signature(TieredOrchestrator.run)
    budget_param = run_sig.parameters.get("budget_usd")
    if budget_param is None:
        _fail("O3b", "TieredOrchestrator.run missing `budget_usd` kwarg")
        return False
    if budget_param.kind not in (
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        _fail("O3b", f"`budget_usd` must be passable by keyword, got {budget_param.kind}")
        return False
    _pass("O3b", "TieredOrchestrator.run accepts budget_usd kwarg (nested pass-through)")

    # TierAttempt schema (O2 depends on it)
    required_ta = {
        "tier_index",
        "model_or_sub",
        "passed",
        "reason",
        "cost_usd",
        "latency_ms",
        "ttft_ms",
    }
    actual_ta = {f.name for f in TierAttempt.__dataclass_fields__.values()}
    missing_ta = required_ta - actual_ta
    if missing_ta:
        _fail("O2", f"TierAttempt missing fields: {missing_ta}")
        return False
    _pass("O2", "TierAttempt log schema complete")

    # default_hierarchy factory
    orch = default_hierarchy(include_claude=True)
    if len(orch.tiers) != 4:
        _fail("factory", f"default_hierarchy expected 4 tiers, got {len(orch.tiers)}")
        return False
    _pass("factory", "default_hierarchy builds 4-tier ladder")

    # Empty tiers raise (safety check)
    try:
        TieredOrchestrator(tiers=[])
    except ValueError:
        _pass("safety", "empty tiers raise ValueError as expected")
    else:
        _fail("safety", "empty tiers should raise ValueError")
        return False

    # gaia_adapter surface
    try:
        from cohezion.inference.gaia_adapter import (
            GaiaAgentTier,
            amd_optimized_hierarchy,
            rank_models_by_amd_optimization,
        )
    except ImportError as exc:
        _fail("gaia", f"gaia_adapter not importable: {exc}")
        return False
    ranked = rank_models_by_amd_optimization(["claude-opus-4-7", "Gemma-4-E2B-it-GGUF"])
    if ranked[0] != "Gemma-4-E2B-it-GGUF":
        _fail("gaia-rank", f"NPU should sort ahead of Claude, got {ranked}")
        return False
    _pass("gaia", "gaia_adapter importable; AMD-path ranking correct")

    # O1, O3, O4, O7 behavior is covered by pytest — run the orchestrator suite.
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/inference/test_orchestrator.py", "-q", "--no-cov"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        _fail("O1/O3/O4/O7", f"pytest failed (exit {result.returncode})")
        print(result.stdout[-600:])
        return False
    summary = [ln for ln in result.stdout.splitlines() if "passed" in ln]
    _pass("O1/O3/O4/O7", summary[-1].strip() if summary else "pytest exit 0")

    print()
    print("✨ UNIT VERIFICATION SUCCESSFUL: all orchestrator invariants pass")
    return True


if __name__ == "__main__":
    sys.exit(0 if verify_invariants() else 1)
