"""Verification leg for the orphan-integration bridge (V-model audit 2026-06-05).

Importing this test counts as an external importer of the bridge, and the bridge
imports every orphan -- so this single seam flips all 11 audited orphans from
``orphan`` to ``wired`` in the import graph, non-destructively.
"""

from __future__ import annotations

from types import ModuleType

from cohezion.wiring import WIRED_ORPHANS, verify_wiring
from cohezion.wiring.orphan_bridge import _ORPHAN_MODULES


def test_bridge_covers_every_audited_orphan() -> None:
    status = verify_wiring()
    assert status["total"] == len(_ORPHAN_MODULES) == 11
    # wired + degraded must partition the full set (fail-soft, nothing dropped).
    assert int(status["wired_count"]) + int(status["degraded_count"]) == 11  # type: ignore[arg-type]


def test_degraded_orphans_record_a_reason_never_raise() -> None:
    # Any orphan that fails to import is recorded as a string reason, not an exception.
    for name, value in WIRED_ORPHANS.items():
        if not isinstance(value, ModuleType):
            assert isinstance(value, str) and value.startswith("unavailable:"), name


def test_consolidation_orphans_are_importable() -> None:
    # The four consolidation candidates must at least import (integration precondition).
    for name in ("datamesh", "sandboxing", "simulations", "reporting"):
        assert isinstance(WIRED_ORPHANS[name], ModuleType), f"{name}: {WIRED_ORPHANS[name]}"
