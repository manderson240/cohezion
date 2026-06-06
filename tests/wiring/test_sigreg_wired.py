"""Discriminating test for the wiring-sweep edge: world_model → sigreg (2026-06-06).

`sigreg` was a genuine production orphan in world_model/ — `SIGReg` (a documented World Model
component, CLAUDE.md) had ZERO src importers. Wired non-destructively via a guarded
`cohezion.world_model` __init__ re-export (cycle-safe; the guard also tolerates torch being
absent since SIGReg is an nn.Module). This test fails if the static edge is removed: SIGReg must
resolve FROM the package AND be the source module's own object.
"""

from __future__ import annotations

import pytest


def test_sigreg_reexported_from_world_model() -> None:
    pytest.importorskip("torch")  # SIGReg is an nn.Module; skip cleanly if torch is unavailable
    import cohezion.world_model as world_model
    import cohezion.world_model.sigreg as src

    assert hasattr(world_model, "SIGReg"), "world_model.SIGReg unreachable — wiring edge missing"
    assert world_model.SIGReg is src.SIGReg, "SIGReg is not the source object"
