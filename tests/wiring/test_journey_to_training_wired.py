"""Discriminating test for the wiring-sweep edge: compound → journey_to_training (2026-06-06).

journey_to_training was an import-graph orphan (genuine Class-A: no production importer, no
test, no registry ref). The wiring-sweep loop re-exported its public bridge through
`cohezion.compound`. Fails if the static edge is removed: asserts the names resolve FROM the
package AND are the SAME objects as the source module (a plain import-OK test would pass even
with the wiring deleted, so it would not discriminate).
"""

from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.journey_to_training as src


def test_journey_bridge_reexported_from_compound() -> None:
    for name in ("JourneyToTrainingBridge", "ValidationResult"):
        assert hasattr(compound, name), f"compound.{name} unreachable — wiring edge missing"
        assert getattr(compound, name) is getattr(src, name), f"{name} is not the source object"


def test_journey_bridge_is_a_class() -> None:
    assert isinstance(compound.JourneyToTrainingBridge, type)
