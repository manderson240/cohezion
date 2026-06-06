"""Discriminating test for the wiring-sweep edge: substrate → popcorn (2026-06-06).

`popcorn` was a genuine production orphan in substrate/ — its Popcorn-CLI kernel submission API
(submit / SubmitResult) had ZERO importers anywhere; the lone "Popcorn" grep hit in
scripts/compound_kernel_cycle.py is a LOG STRING, not an import. Wired non-destructively via a
guarded `cohezion.substrate` __init__ re-export.

Falsifiable: this test fails if the static edge is removed — both names must resolve FROM the
package AND be the source module's own objects (identity), and appear in __all__.
"""

from __future__ import annotations

import cohezion.substrate as substrate
import cohezion.substrate.popcorn as src


def test_popcorn_reexported_from_substrate() -> None:
    for name in ("SubmitResult", "submit"):
        assert hasattr(substrate, name), f"substrate.{name} unreachable — wiring edge missing"
        assert getattr(substrate, name) is getattr(src, name), f"{name} is not the source object"
        assert name in substrate.__all__, f"{name} missing from substrate.__all__"
