"""Unit tests for TriSiliconAutopoiesisEngine on AMD Strix Halo."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.autopoiesis import TriSiliconAutopoiesisEngine, TriSiliconCycleResult


@pytest.fixture
def engine() -> TriSiliconAutopoiesisEngine:
    return TriSiliconAutopoiesisEngine(cpu_threads=4)


def test_tri_silicon_engine_initialization(engine: TriSiliconAutopoiesisEngine):
    assert engine.cpu_threads == 4
    assert engine.npu_model == "llama3.2-1b-FLM"
    assert engine.entropy_engine is not None
    assert engine.arc_dsl_engine is not None


def test_tri_silicon_npu_phase_fallback(engine: TriSiliconAutopoiesisEngine):
    # When Lemonade is unreachable or throws, it safely falls back without raising
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        guidance, latency_ms = engine.execute_npu_phase(cycle=1)
        assert isinstance(guidance, str)
        assert len(guidance) > 0
        assert latency_ms >= 0.0


def test_tri_silicon_cpu_phase(engine: TriSiliconAutopoiesisEngine):
    res = engine.execute_cpu_phase(cycle=1, npu_guidance="test guidance")
    assert "programs_found" in res
    assert "converged" in res
    assert "latency_ms" in res
    assert res["latency_ms"] > 0.0


def test_tri_silicon_igpu_phase_skipped(engine: TriSiliconAutopoiesisEngine):
    # When cycle % 10 != 0, synthesis is skipped
    triggered, content, latency_ms = engine.execute_igpu_phase(
        cycle=1, cpu_results={"programs_found": 1, "final_reward": 0.9}
    )
    assert not triggered
    assert "skipped" in content.lower()
    assert latency_ms == 0.0


def test_tri_silicon_execute_cycle_end_to_end(engine: TriSiliconAutopoiesisEngine):
    result = engine.execute_cycle(cycle=2)
    assert isinstance(result, TriSiliconCycleResult)
    assert result.cycle == 2
    assert isinstance(result.npu_guidance, str)
    # First cycle: no measured previous state, so Delta S is UNKNOWN -- never a
    # constructed negentropy pass (the old test asserted the constructed value).
    assert result.delta_entropy is None
    assert result.autoharness_verified is None
    assert result.total_latency_ms > 0.0
