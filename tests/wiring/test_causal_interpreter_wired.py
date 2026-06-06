"""Discriminating test for the wiring-sweep edge: rl → causal_interpreter (2026-06-06).

`causal_interpreter` was a genuine production orphan in rl/ — its ActivationPatcher /
CausalInterventionTester / InterventionResult / InterpretabilityReport (causal-intervention
interpretability for RL policies) had ZERO importers anywhere. Wired non-destructively via a
guarded `cohezion.rl` __init__ re-export (torch-guarded — the module imports torch at scope).

Falsifiable: this test fails if the static edge is removed — every name must resolve FROM the
package AND be the source module's own object (identity), and appear in __all__.
"""

from __future__ import annotations

import pytest


def test_causal_interpreter_reexported_from_rl() -> None:
    pytest.importorskip("torch")  # module defines nn.Module-based patchers; skip if torch absent
    import cohezion.rl as rl
    import cohezion.rl.causal_interpreter as src

    for name in (
        "ActivationPatcher",
        "CausalInterventionTester",
        "InterventionResult",
        "InterpretabilityReport",
    ):
        assert hasattr(rl, name), f"rl.{name} unreachable — wiring edge missing"
        assert getattr(rl, name) is getattr(src, name), f"{name} is not the source object"
        assert name in rl.__all__, f"{name} missing from rl.__all__"
