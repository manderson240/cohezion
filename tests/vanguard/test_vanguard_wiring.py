"""Wiring test: vanguard/__init__ re-exports each module's primary class (wiring-sweep 2026-06-07).

Before this, the empty `vanguard/__init__.py` left `attribution` and `connectors` reachable ONLY
from the test suite (intra-package orphans). The re-export adds the missing static production edge.

Discriminating: each test asserts the name re-exported from the PACKAGE is the SAME object as the
class in its module — so removing or mis-pointing a re-export edge FAILS, not just "a name exists".
"""

from __future__ import annotations

import cohezion.vanguard as vanguard
from cohezion.vanguard.attribution import AttributionEngine
from cohezion.vanguard.connectors import VanguardScoutReport
from cohezion.vanguard.sandbox_validation import SubstrateSandbox
from cohezion.vanguard.source_connector import SourceConnector


def test_each_vanguard_module_reexported_is_the_real_class() -> None:
    assert vanguard.AttributionEngine is AttributionEngine
    assert vanguard.VanguardScoutReport is VanguardScoutReport
    assert vanguard.SubstrateSandbox is SubstrateSandbox
    assert vanguard.SourceConnector is SourceConnector


def test_all_lists_every_reexport() -> None:
    assert set(vanguard.__all__) == {
        "AttributionEngine",
        "SourceConnector",
        "SubstrateSandbox",
        "VanguardScoutReport",
    }
