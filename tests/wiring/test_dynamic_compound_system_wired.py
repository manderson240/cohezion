"""Discriminating test for the wiring-sweep edge: compound → dynamic_compound_system.

Genuine Class-A orphan (no production importer, no test, no registry ref). Re-exported
through `cohezion.compound`. Fails if the static edge is removed: asserts the names resolve
FROM the package AND are the SAME objects as the source module.
"""

from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.dynamic_compound_system as src


def test_dynamic_compound_system_reexported_from_compound() -> None:
    for name in ("DynamicCompoundSystem", "DynamicExecutionResult"):
        assert hasattr(compound, name), f"compound.{name} unreachable — wiring edge missing"
        assert getattr(compound, name) is getattr(src, name), f"{name} is not the source object"


def test_reexport_is_a_class() -> None:
    assert isinstance(compound.DynamicCompoundSystem, type)
