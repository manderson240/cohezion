"""Tests for local-inference engine feedback — multi-engine GIC compounding (2026-06-29).

make_local_execute_fn now reports tier_used (the ENGINE that ran), closing the loop:
cascade outcome → tier_used → ExecutionMetrics (CB16) → DifficultyEstimator.record → predict_tier
→ O9 cascade-entry binding. The DifficultyEstimator can finally LEARN per-skill engine allocation.
"""

from __future__ import annotations

from cohezion.compound.local_inference import _OMNI_TIERS, _engine_for


class TestEngineFor:
    def test_omni_tier_order(self):
        assert _OMNI_TIERS == ("npu", "igpu", "cpu")

    def test_no_escalation_is_npu(self):
        assert _engine_for(0, 0, is_cloud=False) == "npu"

    def test_escalation_count_drives_engine(self):
        """Discriminating: escalation_count maps to the engine that ran. A wrong impl that ignores
        it (always reports the entry/'npu') fails the iGPU/CPU cases."""
        assert _engine_for(0, 1, is_cloud=False) == "igpu"
        assert _engine_for(0, 2, is_cloud=False) == "cpu"

    def test_entry_plus_escalation(self):
        assert _engine_for(1, 1, is_cloud=False) == "cpu"  # iGPU entry + 1 escalation → CPU

    def test_clamped_to_cpu(self):
        assert _engine_for(0, 9, is_cloud=False) == "cpu"

    def test_cloud_short_circuits(self):
        assert _engine_for(0, 0, is_cloud=True) == "cloud"
        assert _engine_for(2, 5, is_cloud=True) == "cloud"


def test_exhausted_cascade_is_reported_as_gate_miss_not_empty_success() -> None:
    """Measured 2026-09-19: three 503 admission refusals came back as ("", {cost_usd: 0.0,
    tokens_output: 1}) with NO error key. A caller could not tell 'model answered nothing'
    from 'no model ran'. The execute_fn must surface cascade exhaustion as a failure."""
    from unittest.mock import AsyncMock, MagicMock, patch

    import cohezion.compound.local_inference as li
    from cohezion.inference.orchestrator import OrchestrationResult

    exhausted = OrchestrationResult(
        text="",
        primary_model="llama3.2-1b-FLM",
        final_model="Gemma-4-E4B-it-GGUF",
        escalation_count=3,
        cost_usd=0.0,
        error="503 admission_refused: below hard floor",
    )
    orch = MagicMock()
    orch.run = AsyncMock(return_value=exhausted)
    with patch.object(li, "_get_orchestrator", return_value=orch):
        out, metrics = li.make_local_execute_fn("probe")("say ok")
    assert out == ""
    assert metrics["gate_miss"] is True
    assert "503" in metrics["error"]
    assert metrics["tokens_output"] == 0
    assert metrics["escalation_count"] == 3


def test_empty_text_without_error_is_also_a_gate_miss() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    import cohezion.compound.local_inference as li
    from cohezion.inference.orchestrator import OrchestrationResult

    orch = MagicMock()
    orch.run = AsyncMock(
        return_value=OrchestrationResult(
            text="   ", primary_model="m", final_model="m", escalation_count=0
        )
    )
    with patch.object(li, "_get_orchestrator", return_value=orch):
        out, metrics = li.make_local_execute_fn("probe")("say ok")
    assert out == "" and metrics["gate_miss"] is True and "error" in metrics
