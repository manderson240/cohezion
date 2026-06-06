"""Pipeline module — connects mass sim, training, and weight transfer."""

import contextlib


# Wiring-sweep 2026-06-06: incremental_trainer was a genuine production orphan — its
# IncrementalResult / IncrementalVAETrainer / IncrementalRLTrainer (online/incremental
# VAE+RL training) had ZERO importers anywhere (src, tests, registry, entry-points).
# Cycle-safe (imports only numpy at module scope). Guarded re-export puts the incremental
# trainers on the package surface and makes them statically reachable (suppress keeps the
# package importable if numpy is ever absent — failure-domain isolation).
__all__: list[str] = []

with contextlib.suppress(Exception):
    from cohezion.pipeline.incremental_trainer import (
        IncrementalResult as IncrementalResult,
    )
    from cohezion.pipeline.incremental_trainer import (
        IncrementalRLTrainer as IncrementalRLTrainer,
    )
    from cohezion.pipeline.incremental_trainer import (
        IncrementalVAETrainer as IncrementalVAETrainer,
    )

    __all__ += ["IncrementalRLTrainer", "IncrementalResult", "IncrementalVAETrainer"]
