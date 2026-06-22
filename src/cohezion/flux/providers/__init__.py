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
