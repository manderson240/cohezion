"""Tests for local-inference engine feedback — multi-engine GIC compounding (2026-06-29).

make_local_execute_fn now reports tier_used (the ENGINE that ran), closing the loop:
cascade outcome → tier_used → ExecutionMetrics (CB16) → DifficultyEstimator.record → predict_tier
→ O9 cascade-entry binding. The DifficultyEstimator can finally LEARN per-skill engine allocation.
"""
from __future__ import annotations

from cohezion.compound.local_inference import _engine_for, _OMNI_TIERS


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
