"""Discriminating test for the wiring-sweep edge: world_model → surprise_explorer (2026-06-06).

`surprise_explorer` was a genuine production orphan in world_model/ — `SurpriseExplorer` /
`SurpriseRegion` (documented World Model components, CLAUDE.md) had ZERO src importers and
world_model/__init__ re-exported nothing. Wired non-destructively via a guarded
`cohezion.world_model` __init__ re-export (cycle-safe — imports no swarm/compound at module
scope). This test fails if the static edge is removed: the public surface must resolve FROM the
package AND be the source module's own objects (an identity check a stale shadow would fail).
"""

from __future__ import annotations

import cohezion.world_model as world_model
import cohezion.world_model.surprise_explorer as src


_PUBLIC = ("SurpriseExplorer", "SurpriseRegion")


def test_surprise_explorer_surface_reexported_from_world_model() -> None:
    for name in _PUBLIC:
        assert hasattr(world_model, name), f"world_model.{name} unreachable — wiring edge missing"
        assert getattr(world_model, name) is getattr(src, name), f"{name} is not the source object"
