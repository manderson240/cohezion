"""Discriminating test for the wiring-sweep edge: compound → optimized_session_manager.

Genuine Class-A orphan (no production importer, no test, no registry ref). Re-exported
through `cohezion.compound`. Fails if the static edge is removed: asserts the names resolve
FROM the package AND are the SAME objects as the source module (a plain import-OK test would
pass even with the wiring deleted — and `is` identity also catches a name collision with a
differently-sourced SessionManager).
"""
from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.optimized_session_manager as src


def test_session_classes_reexported_from_compound() -> None:
    for name in ("CompoundSessionManager", "OptimizedSessionRuntime"):
        assert hasattr(compound, name), f"compound.{name} unreachable — wiring edge missing"
        assert getattr(compound, name) is getattr(src, name), f"{name} is not the source object"


def test_reexports_are_classes() -> None:
    assert isinstance(compound.CompoundSessionManager, type)
    assert isinstance(compound.OptimizedSessionRuntime, type)
