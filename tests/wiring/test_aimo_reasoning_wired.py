"""Discriminating test for the wiring-sweep edge: compound → aimo_reasoning.

Genuine Class-A orphan (no production importer, no test, no registry ref). Re-exported
through `cohezion.compound` via its DISTINCTIVE classes (AIMOScaler, ProcessRewardModel) —
NOT `ReasoningModel`, which collides with agi_reasoning.ReasoningModel (a surface-name
duplicate flagged for human review). Fails if the static edge is removed: asserts the names
resolve FROM the package AND are aimo_reasoning's own objects.
"""

from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.aimo_reasoning as src


def test_aimo_reasoning_reexported_from_compound() -> None:
    for name in ("AIMOScaler", "ProcessRewardModel"):
        assert hasattr(compound, name), f"compound.{name} unreachable — wiring edge missing"
        assert getattr(compound, name) is getattr(src, name), f"{name} is not the source object"


def test_reexport_is_a_class() -> None:
    assert isinstance(compound.AIMOScaler, type)
