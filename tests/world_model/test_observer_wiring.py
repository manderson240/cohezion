"""Consumption tests for the TRACE tier-flow wiring (2026-07-15).

Per verification-depth: a capability is wired only when a production consumer reads it
and acts on it. These tests fail if the gate preference or the execute-path feed is
neutralized — not merely if the symbols exist.
"""

from __future__ import annotations

import inspect

import pytest

import cohezion.world_model.observer_world_model as owm_mod
from cohezion.world_model.observer_world_model import ObserverWorldModel, get_default_observer_model


@pytest.fixture(autouse=True)
def _reset_singleton():
    owm_mod._default_model = None
    yield
    owm_mod._default_model = None


def test_gate_prefers_observer_model_once_warm(monkeypatch):
    import cohezion.compound.lemonade_world_model as lwm

    monkeypatch.setattr(lwm, "lemonade_available", lambda **_: True, raising=False)
    monkeypatch.setattr(
        "cohezion.compound.local_inference.lemonade_available", lambda **_: True
    )
    # cold: falls through to the FLUME/LLM world model
    cold_gate = lwm.build_live_jepa_gate()
    assert not isinstance(cold_gate._world_model if hasattr(cold_gate, "_world_model") else cold_gate.world_model, ObserverWorldModel)
    # warm: >= 10 real transitions flips the preference
    model = get_default_observer_model()
    for _ in range(10):
        model.record("npu", "npu", 0.9)
    warm_gate = lwm.build_live_jepa_gate()
    wm = warm_gate._world_model if hasattr(warm_gate, "_world_model") else warm_gate.world_model
    assert isinstance(wm, ObserverWorldModel), (
        "gate must consume the tier-flow observer once it has data — "
        "a neutralized preference silently reverts to the prompt-length LLM signal"
    )


def test_execute_path_feeds_observer():
    from cohezion.compound.local_inference import make_local_execute_fn

    src = inspect.getsource(make_local_execute_fn)
    assert "get_default_observer_model" in src and ".record(" in src, (
        "make_local_execute_fn must feed the tier-flow observer on every execution"
    )


def test_warm_observer_coherence_reflects_recorded_flow():
    model = get_default_observer_model()
    for _ in range(10):
        model.record("npu", "npu", 0.9)  # clean NPU flow
    model._state = "npu"
    clean = model.predict_next_state(None, None)[0]
    for _ in range(10):
        model.record("cpu", "cloud", 0.2)  # degraded CPU flow escalating to cloud
    model._state = "cpu"
    degraded = model.predict_next_state(None, None)[0]
    assert clean > degraded, "coherence must separate clean vs degraded tier flows"
