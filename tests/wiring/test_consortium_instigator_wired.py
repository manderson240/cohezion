"""Discriminating test for the wiring-sweep edge: compound → consortium_instigator.

Genuine Class-A orphan (no production importer, no test, no registry ref). Re-exported
through `cohezion.compound`. Fails if the static edge is removed: asserts the name resolves
FROM the package AND is the SAME object as the source module.
"""

from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.consortium_instigator as src


def test_consortium_instigator_reexported_from_compound() -> None:
    assert hasattr(compound, "ConsortiumInstigator"), "unreachable — wiring edge missing"
    assert compound.ConsortiumInstigator is src.ConsortiumInstigator


def test_reexport_is_a_class() -> None:
    assert isinstance(compound.ConsortiumInstigator, type)
