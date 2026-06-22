"""Discriminating test for the wiring-sweep edge: compound → hiho_lm_gate (2026-06-06).

hiho_lm_gate was an import-graph orphan (no production importer). The wiring-sweep loop
re-exported its HIHO-LM quality gate through `cohezion.compound`'s public surface. This
test fails if that static edge is removed (the whole point of the wiring): a plain
"module imports OK" test would still pass without the edge, so instead we assert the
re-exported names are reachable FROM the package AND are the SAME objects as in the source
module (proving it's a real re-export, not an accidental name collision).
"""

from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.hiho_lm_gate as gate


def test_hiho_lm_gate_reexported_from_compound() -> None:
    # The edge: `from cohezion.compound import ppl_score` must resolve. If the __init__
    # re-export is deleted, these attributes vanish and this fails.
    for name in ("check_quality", "check_sycophancy", "ppl_score"):
        assert hasattr(compound, name), f"compound.{name} not reachable — wiring edge missing"
        assert getattr(compound, name) is getattr(gate, name), f"{name} is not the gate's object"


def test_reexported_gate_is_callable() -> None:
    assert callable(compound.ppl_score)
    assert callable(compound.check_quality)
