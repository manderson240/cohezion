"""World Model layer — JEPA predictor, SurpriseExplorer, SIGReg."""

import contextlib


# Wiring-sweep 2026-06-06: surprise_explorer was a genuine production orphan (SurpriseExplorer /
# SurpriseRegion had 0 src importers; world_model/__init__ re-exported nothing). Guarded re-export
# puts the documented World Model components on the package surface + makes them statically
# reachable (cycle-safe — no swarm/compound module-scope import; fail-soft).
with contextlib.suppress(Exception):
    from cohezion.world_model.surprise_explorer import (
        SurpriseExplorer as SurpriseExplorer,
    )
    from cohezion.world_model.surprise_explorer import (
        SurpriseRegion as SurpriseRegion,
    )

# Wiring-sweep 2026-06-06: sigreg was a genuine production orphan (SIGReg, an nn.Module, had 0 src
# importers). Separate guarded block so a torch-absent environment can't take down the
# surprise_explorer re-export above.
with contextlib.suppress(Exception):
    from cohezion.world_model.sigreg import (
        SIGReg as SIGReg,
    )
