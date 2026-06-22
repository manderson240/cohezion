"""Discriminating test for the wiring-sweep edge: compound → agi_reasoning.

Genuine Class-A orphan (no production importer, no test, no registry ref). Re-exported
through `cohezion.compound`. Fails if the static edge is removed: asserts the names resolve
FROM the package AND are the SAME objects as the source module.
"""

from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.agi_reasoning as src


def test_agi_reasoning_reexported_from_compound() -> None:
    for name in ("AGIEvaluator", "ReasoningModel"):
        assert hasattr(compound, name), f"compound.{name} unreachable — wiring edge missing"
        assert getattr(compound, name) is getattr(src, name), f"{name} is not the source object"


def test_reexport_is_a_class() -> None:
    assert isinstance(compound.AGIEvaluator, type)
