"""Discriminating test for the wiring-sweep edge: inference → lynx_gate (2026-06-06).

First genuine Class-A orphan wired in the inference/ package (the only one — the rest are
tests-only). Re-exported through `cohezion.inference`. Fails if the static edge is removed:
asserts the name resolves FROM the package AND is the source module's own object.
"""

from __future__ import annotations

import cohezion.inference as inference
import cohezion.inference.lynx_gate as src


def test_lynx_gate_reexported_from_inference() -> None:
    assert hasattr(inference, "LYNXGate"), "unreachable — wiring edge missing"
    assert inference.LYNXGate is src.LYNXGate


def test_reexport_is_a_class() -> None:
    assert isinstance(inference.LYNXGate, type)
