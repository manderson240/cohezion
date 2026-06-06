"""Reinforcement Learning module for FLUME manifold navigation."""

import contextlib


# Wiring-sweep 2026-06-06: causal_interpreter was a genuine production orphan — its
# ActivationPatcher / CausalInterventionTester / InterventionResult / InterpretabilityReport
# (causal-intervention interpretability for RL policies) had ZERO importers anywhere. Cycle-safe
# (no cohezion module-scope import). Guarded re-export (it imports torch at module scope — the
# suppress tolerates a torch-absent environment) makes it statically reachable.
with contextlib.suppress(Exception):
    from cohezion.rl.causal_interpreter import (
        ActivationPatcher as ActivationPatcher,
    )
    from cohezion.rl.causal_interpreter import (
        CausalInterventionTester as CausalInterventionTester,
    )
    from cohezion.rl.causal_interpreter import (
        InterpretabilityReport as InterpretabilityReport,
    )
    from cohezion.rl.causal_interpreter import (
        InterventionResult as InterventionResult,
    )

    __all__ = [
        "ActivationPatcher",
        "CausalInterventionTester",
        "InterpretabilityReport",
        "InterventionResult",
    ]
