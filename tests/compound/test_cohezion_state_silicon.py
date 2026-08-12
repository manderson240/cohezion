"""Fleet capability truth: _silicon_state() must read the verified :13305 oracle.

Background (measured 2026-08-12): `_silicon_state()` probed :13306 (NPU) and :13307
(iGPU) via `# allow-direct-port` overrides. Both ports are documented-dead under
invariant N1 and return no listener, so the function reported
`{npu_up: False, igpu_up: False, npu_models: [], igpu_models: 0}` UNCONDITIONALLY
while the OmniRouter was serving an NPU-resident FLM model and three iGPU models.

These tests are DISCRIMINATING: they fail against the dead-port implementation
precisely because it asks the wrong ports, and they fail again if anyone reverts.
They deliberately do NOT require a live fleet — the oracle is patched — so the
assertion is about WHICH SOURCE the consumer reads, not about local hardware.
"""

from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

import pytest

from cohezion.inference.lemonade_health import LemonadeHealth


def _health_with_devices() -> LemonadeHealth:
    """A snapshot in which the NPU and iGPU are demonstrably occupied."""
    return LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="11.5.2",
        status="ok",
        loaded_count=4,
        devices={
            "npu": ["deepseek-r1-0528-8b-FLM"],
            "gpu": ["Gemma-4-31B-it-GGUF", "Gemma-4-E4B-it-GGUF", "nomic-embed-text-v2-moe-GGUF"],
        },
    )


@pytest.fixture
def _no_direct_ports(monkeypatch):
    """Make ANY direct httpx call fail.

    This is the load-bearing part of the test. If `_silicon_state()` reaches for
    :13306/:13307 itself, it gets an exception and must report the fleet down —
    which is exactly the bug. Only an implementation that reads the oracle passes.
    """

    def _boom(*_a, **_k):  # pragma: no cover - invoked only by a wrong implementation
        raise AssertionError("_silicon_state must not probe ports directly; use the oracle")

    fake_httpx = types.SimpleNamespace(get=_boom, AsyncClient=_boom)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    return fake_httpx


class TestSiliconStateReadsOracle:
    """FT1 — fleet device truth comes from the :13305 oracle, not per-port probes."""

    def test_npu_up_true_when_oracle_reports_npu_resident_model(self, monkeypatch):
        """DISCRIMINATING: dead-port impl returns npu_up=False here; oracle impl returns True."""
        import cohezion.inference.lemonade_health as lh

        async def _fake_probe(*_a, **_k):
            return _health_with_devices()

        monkeypatch.setattr(lh, "probe_lemonade", _fake_probe)

        from cohezion.compound.cohezion_state import _silicon_state

        state = _silicon_state()
        assert state["npu_up"] is True, "NPU is occupied per the oracle but reported down"
        assert state["npu_models"] == ["deepseek-r1-0528-8b-FLM"]

    def test_igpu_up_and_count_from_oracle(self, monkeypatch):
        import cohezion.inference.lemonade_health as lh

        async def _fake_probe(*_a, **_k):
            return _health_with_devices()

        monkeypatch.setattr(lh, "probe_lemonade", _fake_probe)

        from cohezion.compound.cohezion_state import _silicon_state

        state = _silicon_state()
        assert state["igpu_up"] is True
        assert state["igpu_models"] == 3

    def test_does_not_probe_dead_ports_directly(self, monkeypatch, _no_direct_ports):
        """Any direct httpx use raises — only an oracle-backed impl can pass."""
        import cohezion.inference.lemonade_health as lh

        async def _fake_probe(*_a, **_k):
            return _health_with_devices()

        monkeypatch.setattr(lh, "probe_lemonade", _fake_probe)

        from cohezion.compound.cohezion_state import _silicon_state

        state = _silicon_state()
        assert state["npu_up"] is True

    def test_unreachable_oracle_is_not_reported_as_idle_fleet(self, monkeypatch):
        """'I cannot tell' must be distinguishable from 'nothing is running'.

        The old code failed CLOSED to {False, [], 0}, which is indistinguishable from a
        genuinely idle box — so every downstream gate degraded silently.
        """
        import cohezion.inference.lemonade_health as lh

        async def _fake_probe(*_a, **_k):
            return LemonadeHealth(
                checked_at=0.0,
                port=13305,
                version="?",
                status="down",
                loaded_count=0,
                errors=["unreachable: connection refused"],
            )

        monkeypatch.setattr(lh, "probe_lemonade", _fake_probe)

        from cohezion.compound.cohezion_state import _silicon_state

        state = _silicon_state()
        assert state["npu_up"] is False
        assert state.get("probe_ok") is False, "an unreachable oracle must be flagged, not silent"


class TestPortBypassRemoved:
    """FT2 — the dead-port escape hatches must not come back."""

    def test_no_allow_direct_port_overrides_in_cohezion_state(self):
        """Dead-port literals must not appear in EXECUTABLE code.

        Comments may legitimately name :13306/:13307 to explain why they are avoided,
        so strip comments before asserting — a raw substring scan would flag its own
        rationale (a false positive of exactly the kind this suite exists to prevent).
        """
        import cohezion.compound.cohezion_state as mod

        source = Path(mod.__file__).read_text()
        tree = ast.parse(source)

        # AST literals only: comments AND docstrings are excluded by construction, so
        # prose explaining why the dead ports are avoided cannot trip the check.
        dead = {13306, 13307, 13309}
        found = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, int)
        } & dead
        assert not found, f"N1: dead port literal(s) {sorted(found)} in executable code"

        # String literals could smuggle a port into a URL without an int constant.
        # Exclude docstrings: a bare string EXPRESSION statement is documentation, not
        # a value the code uses. (Docstrings are ast.Constant too — the naive check
        # flags the very paragraph explaining why the ports are avoided.)
        docstring_ids = {
            id(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        }
        urls = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
            and any(str(p) in node.value for p in dead)
        ]
        assert not urls, f"N1: dead port embedded in string literal(s): {urls}"

        assert "allow-direct-port" not in source, (
            "the port-bypass override is the hole that let the dead-port probe in"
        )
