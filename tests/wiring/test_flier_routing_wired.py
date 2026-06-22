"""Discriminating test for the wiring-sweep edge: physics → flier_routing (2026-06-06).

Genuine Class-A orphan in physics/ (cycle-safe). Re-exported through `cohezion.physics`.
Fails if the static edge is removed: asserts the name resolves FROM the package AND is the
source module's own object.
"""

from __future__ import annotations

import cohezion.physics as physics
import cohezion.physics.flier_routing as src


def test_flier_router_reexported_from_physics() -> None:
    assert hasattr(physics, "FLIERRouter"), "unreachable — wiring edge missing"
    assert physics.FLIERRouter is src.FLIERRouter


def test_reexport_is_a_class() -> None:
    assert isinstance(physics.FLIERRouter, type)
