"""Discriminating test for the wiring-sweep edge: physics → mereon_data (2026-06-06).

Genuine Class-A orphan in physics/ (functions only — the first function re-export in the
sweep). Re-exported through `cohezion.physics`. Fails if the static edge is removed: asserts
the functions resolve FROM the package AND are the source module's own objects.
"""
from __future__ import annotations

import cohezion.physics as physics
import cohezion.physics.mereon_data as src


def test_mereon_data_functions_reexported_from_physics() -> None:
    for name in ("get_m120p_vertices", "get_m144p_vertices"):
        assert hasattr(physics, name), f"physics.{name} unreachable — wiring edge missing"
        assert getattr(physics, name) is getattr(src, name), f"{name} is not the source object"


def test_reexports_are_callable() -> None:
    assert callable(physics.get_m120p_vertices)
