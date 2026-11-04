"""FLUX provider implementations — cache, history, SurrealDB, tools, vault."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.flux.providers.cache_flux import CacheFlux as CacheFlux

with contextlib.suppress(Exception):
    from cohezion.flux.providers.history_flux import HistoryFlux as HistoryFlux

with contextlib.suppress(Exception):
    from cohezion.flux.providers.surreal_flux import SurrealFlux as SurrealFlux

with contextlib.suppress(Exception):
    from cohezion.flux.providers.tool_flux import ToolFlux as ToolFlux

with contextlib.suppress(Exception):
    from cohezion.flux.providers.vault_flux import VaultFlux as VaultFlux

# Restored 2026-11-04: #242 (853084c05) squash-merged the wiring test for this edge but not
# the __init__ change, so the test failed on main from the day it landed.
# Only names whose guarded import succeeded, so `from ... import *` never breaks.
__all__ = [
    _name
    for _name in (
        "CacheFlux",
        "HistoryFlux",
        "SurrealFlux",
        "ToolFlux",
        "VaultFlux",
    )
    if _name in globals()
]
