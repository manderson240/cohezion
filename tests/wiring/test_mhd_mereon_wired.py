"""Discriminating test for the wiring-sweep edge: physics → mhd_mereon (2026-06-06).

Genuine Class-A orphan in physics/ (cycle-safe). Re-exported through `cohezion.physics`.
Fails if the static edge is removed: asserts the name resolves FROM the package AND is the
source module's own object.
"""

from __future__ import annotations

import cohezion.physics as physics
import cohezion.physics.mhd_mereon as src


def test_mhd_mereon_reexported_from_physics() -> None:
    for name in ("MHDMereonOperator", "MHDState"):
        assert hasattr(physics, name), f"physics.{name} unreachable — wiring edge missing"
        assert getattr(physics, name) is getattr(src, name), f"{name} is not the source object"


def test_reexport_is_a_class() -> None:
    assert isinstance(physics.MHDMereonOperator, type)
