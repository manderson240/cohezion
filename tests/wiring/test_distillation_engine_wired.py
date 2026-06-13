"""Discriminating test for the wiring-sweep edge: compound → distillation_engine.

Genuine Class-A orphan (no production importer, no test, no registry ref). Re-exported
through `cohezion.compound`. Fails if the static edge is removed: asserts the name resolves
FROM the package AND is the SAME object as the source module.
"""

from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.distillation_engine as src


def test_distillation_engine_reexported_from_compound() -> None:
    assert hasattr(compound, "DistillationEngine"), "unreachable — wiring edge missing"
    assert compound.DistillationEngine is src.DistillationEngine


def test_reexport_is_a_class() -> None:
    assert isinstance(compound.DistillationEngine, type)
