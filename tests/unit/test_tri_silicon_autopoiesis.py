"""Unit tests for TriSiliconAutopoiesisEngine on AMD Strix Halo."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from cohezion.autopoiesis import (
    TriSiliconAutopoiesisEngine,
    TriSiliconCycleResult,
    tri_silicon_engine,
)
from cohezion.config.defaults import tier0_model


# Hermetic: execute_npu_phase POSTs the tier-0 model id to :13305, which makes the live
# router auto-load it. Every connect is refused and recorded; a recorded attempt fails.
pytestmark = pytest.mark.usefixtures("no_network")


@pytest.fixture(autouse=True)
def fake_urlopen(monkeypatch, tmp_path):
    """Mock every HTTP boundary the engine reaches, at source.

    The engine, TripartiteGoalLoop and the SurrealDB ``_sql`` helper all call
    ``urllib.request.urlopen`` through the module attribute, so one patch covers them.
    Chat requests get a canned completion; SurrealDB ``/sql`` gets an empty OK result.
    Also keeps the vault retro file and VaultNeuronWriter off the real stores.
    """
    requests: list[tuple[str, dict | str]] = []

    def _urlopen(req, timeout=None):
        url = req.full_url
        body = req.data.decode() if req.data else ""
        if url.endswith("/sql"):
            requests.append((url, body))
            payload: object = [{"status": "OK", "result": []}]
        else:
            requests.append((url, json.loads(body) if body else {}))
            payload = {"choices": [{"message": {"content": "Focus on ARC invariants."}}]}
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)
    monkeypatch.setattr(tri_silicon_engine, "VAULT_LEARNINGS_DIR", tmp_path / "learnings")
    monkeypatch.setattr(
        "cohezion.learning.vault_neuron_reader.VaultNeuronWriter.get_instance",
        lambda *a, **k: MagicMock(),
    )
    return requests


@pytest.fixture
def engine() -> TriSiliconAutopoiesisEngine:
    return TriSiliconAutopoiesisEngine(cpu_threads=4)


def test_tri_silicon_engine_initialization(engine: TriSiliconAutopoiesisEngine):
    assert engine.cpu_threads == 4
    assert engine.npu_model == "Gemma-4-E2B-it-GGUF"  # tier 0 default (2026-10-23 sweep)
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


def test_tri_silicon_execute_cycle_end_to_end(engine: TriSiliconAutopoiesisEngine, fake_urlopen):
    result = engine.execute_cycle(cycle=2)
    npu_calls = [b for u, b in fake_urlopen if u == tri_silicon_engine.LEMONADE_URL]
    assert npu_calls and npu_calls[0]["model"] == tier0_model()
    assert isinstance(result, TriSiliconCycleResult)
    assert result.cycle == 2
    assert isinstance(result.npu_guidance, str)
    assert result.delta_entropy <= 0.0  # Negentropy invariant
    assert result.autoharness_verified is True
    assert result.total_latency_ms > 0.0
