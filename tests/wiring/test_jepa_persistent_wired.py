"""Discriminating test: world_model → jepa_world_model_persistent (2026-06-06, world_model 3/3).

`jepa_world_model_persistent` was a genuine production orphan — `JEPAWorldModelPersistent` (a
JEPAWorldModel subclass, documented World Model component) had ZERO src importers. Wired
non-destructively via a guarded `cohezion.world_model` __init__ re-export (torch-guarded, since
it's an nn.Module subclass). Fails if the static edge is removed: JEPAWorldModelPersistent must
resolve FROM the package AND be the source module's own object.
"""

from __future__ import annotations

import pytest


def test_jepa_persistent_reexported_from_world_model() -> None:
    pytest.importorskip("torch")  # JEPAWorldModelPersistent subclasses an nn.Module
    import cohezion.world_model as world_model
    import cohezion.world_model.jepa_world_model_persistent as src

    assert hasattr(world_model, "JEPAWorldModelPersistent"), "unreachable — wiring edge missing"
    assert world_model.JEPAWorldModelPersistent is src.JEPAWorldModelPersistent
