"""Coherent matter precipitation — Cosmogony Step 10 as a typed event stream.

Public API:

    from cohezion.precipitation import PrecipitationEvent, PrecipitationKind
    from cohezion.precipitation import get_bus, emit, aemit
    from cohezion.precipitation import register_default_sinks

Example:

    from cohezion.precipitation import PrecipitationEvent, PrecipitationKind, emit

    emit(
        PrecipitationEvent(
            kind=PrecipitationKind.WITNESS_MARK,
            universe_id="universe-001",
            coherence=0.73,
            payload={"artifact": "src/foo.py", "commit_sha": "deadbeef"},
        )
    )
"""

from .bus import PrecipitationBus, aemit, emit, get_bus, set_bus
from .events import (
    FABRIC_DIMS,
    HIHO_BASELINE,
    TWELVE_D_DIMS,
    PrecipitationEvent,
    PrecipitationKind,
    compute_fabric_breakdown,
    zero_twelve_d,
)
from .sinks import (
    DEFAULT_VAULT_DIR,
    GitLedgerSink,
    SurrealSink,
    VaultSink,
    register_default_sinks,
)


__all__ = [
    "DEFAULT_VAULT_DIR",
    "FABRIC_DIMS",
    "HIHO_BASELINE",
    "TWELVE_D_DIMS",
    "GitLedgerSink",
    "PrecipitationBus",
    "PrecipitationEvent",
    "PrecipitationKind",
    "SurrealSink",
    "VaultSink",
    "aemit",
    "compute_fabric_breakdown",
    "emit",
    "get_bus",
    "register_default_sinks",
    "set_bus",
    "zero_twelve_d",
]
