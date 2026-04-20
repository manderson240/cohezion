"""Tests for SymmetryHardwareBridge — the spinor-coherence → turboquant_axis translator.

Phase 0 goal: stop the silent ``ImportError`` in ``fleet._inject_symmetry_axis``.
These tests verify that (1) the bridge module exists and is importable, (2) it
adds a well-typed ``turboquant_axis`` dict to an outgoing inference payload,
(3) strict mode raises rather than swallowing when the bridge is unavailable.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.fast


def test_symmetry_hardware_bridge_module_is_importable() -> None:
    from cohezion.core import symmetry_hardware_bridge

    assert hasattr(symmetry_hardware_bridge, "get_symmetry_bridge")
    assert hasattr(symmetry_hardware_bridge, "SymmetryHardwareBridge")


def test_get_symmetry_bridge_returns_singleton() -> None:
    from cohezion.core.symmetry_hardware_bridge import get_symmetry_bridge

    a = get_symmetry_bridge()
    b = get_symmetry_bridge()
    assert a is b


def test_apply_to_payload_adds_turboquant_axis_dict() -> None:
    from cohezion.core.symmetry_hardware_bridge import get_symmetry_bridge

    bridge = get_symmetry_bridge()
    payload = {"model": "Gemma-4-E4B", "messages": [{"role": "user", "content": "hi"}]}
    result = bridge.apply_to_payload(payload, coherence=0.5)

    assert "turboquant_axis" in result
    axis = result["turboquant_axis"]
    assert set(axis.keys()) >= {"coherence", "hadamard_seed", "bits"}
    assert axis["coherence"] == 0.5
    assert isinstance(axis["hadamard_seed"], int)
    assert isinstance(axis["bits"], (int, float))


def test_apply_to_payload_preserves_existing_keys() -> None:
    from cohezion.core.symmetry_hardware_bridge import get_symmetry_bridge

    bridge = get_symmetry_bridge()
    payload = {"model": "x", "messages": [], "max_tokens": 64, "stream": True}
    result = bridge.apply_to_payload(payload, coherence=0.3)

    assert result["model"] == "x"
    assert result["max_tokens"] == 64
    assert result["stream"] is True


def test_apply_to_payload_is_deterministic_for_same_coherence() -> None:
    """Same coherence → same hadamard_seed so calls are reproducible."""
    from cohezion.core.symmetry_hardware_bridge import get_symmetry_bridge

    bridge = get_symmetry_bridge()
    a = bridge.apply_to_payload({"model": "x"}, coherence=0.5)
    b = bridge.apply_to_payload({"model": "x"}, coherence=0.5)
    assert a["turboquant_axis"]["hadamard_seed"] == b["turboquant_axis"]["hadamard_seed"]


def test_apply_to_payload_different_coherence_different_seed() -> None:
    from cohezion.core.symmetry_hardware_bridge import get_symmetry_bridge

    bridge = get_symmetry_bridge()
    a = bridge.apply_to_payload({"model": "x"}, coherence=0.2)
    b = bridge.apply_to_payload({"model": "x"}, coherence=0.8)
    assert a["turboquant_axis"]["hadamard_seed"] != b["turboquant_axis"]["hadamard_seed"]


def test_apply_to_payload_clamps_coherence_to_unit_interval() -> None:
    from cohezion.core.symmetry_hardware_bridge import get_symmetry_bridge

    bridge = get_symmetry_bridge()
    low = bridge.apply_to_payload({}, coherence=-5.0)
    high = bridge.apply_to_payload({}, coherence=17.0)
    assert 0.0 <= low["turboquant_axis"]["coherence"] <= 1.0
    assert 0.0 <= high["turboquant_axis"]["coherence"] <= 1.0


# --- fleet._inject_symmetry_axis integration ---


def test_inject_symmetry_axis_adds_axis_when_bridge_present() -> None:
    from cohezion.inference.fleet import _inject_symmetry_axis

    payload = {"model": "x", "messages": []}
    result = _inject_symmetry_axis(payload, coherence=0.5)
    assert "turboquant_axis" in result
    assert result["turboquant_axis"]["coherence"] == 0.5


def test_inject_symmetry_axis_still_short_circuits_on_none_coherence() -> None:
    """Pre-existing contract from tests/inference/test_fleet.py must hold."""
    from cohezion.inference.fleet import _inject_symmetry_axis

    payload = {"model": "x", "messages": []}
    result = _inject_symmetry_axis(payload, None)
    assert result is payload


def test_inject_symmetry_axis_strict_mode_raises_when_bridge_missing() -> None:
    """COHEZION_STRICT_AXIS=1 must surface regressions rather than swallow."""
    from cohezion.inference.fleet import _inject_symmetry_axis

    with (
        patch.dict(os.environ, {"COHEZION_STRICT_AXIS": "1"}),
        patch(
            "cohezion.core.symmetry_hardware_bridge.get_symmetry_bridge",
            side_effect=ImportError("bridge unavailable"),
        ),
        pytest.raises(RuntimeError, match="strict"),
    ):
        _inject_symmetry_axis({"model": "x"}, coherence=0.5)


def test_inject_symmetry_axis_non_strict_mode_swallows_and_returns_payload() -> None:
    from cohezion.inference.fleet import _inject_symmetry_axis

    # Default (no env var) = non-strict
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("COHEZION_STRICT_AXIS", None)
        with patch(
            "cohezion.core.symmetry_hardware_bridge.get_symmetry_bridge",
            side_effect=ImportError("bridge unavailable"),
        ):
            payload = {"model": "x"}
            result = _inject_symmetry_axis(payload, coherence=0.5)
            assert result is payload
