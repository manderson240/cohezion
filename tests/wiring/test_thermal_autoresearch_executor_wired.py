"""Discriminating test for the wiring-sweep edge: compound → thermal_autoresearch_executor.

Genuine Class-A orphan (no production importer, no test, no registry ref). Re-exported
through `cohezion.compound`. Fails if the static edge is removed: asserts the name resolves
FROM the package AND is the SAME object as the source module (a plain import-OK test would
pass even with the wiring deleted).
"""
from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.thermal_autoresearch_executor as src


def test_thermal_executor_reexported_from_compound() -> None:
    assert hasattr(compound, "ThermalAutoresearchExecutor"), "unreachable — wiring edge missing"
    assert compound.ThermalAutoresearchExecutor is src.ThermalAutoresearchExecutor


def test_reexport_is_a_class() -> None:
    assert isinstance(compound.ThermalAutoresearchExecutor, type)
