"""FLUX Protocol — Federated Lattice of Unified conteXt.

Unified context interface merging vault, SurrealDB, MCP tools, cache,
and execution history into a single query surface for agent nodes.
"""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.flux.aggregator import FluxAggregator as FluxAggregator

with contextlib.suppress(Exception):
    from cohezion.flux.provider import FluxProvider as FluxProvider

with contextlib.suppress(Exception):
    from cohezion.flux.types import FluxBlock as FluxBlock
    from cohezion.flux.types import FluxContext as FluxContext
    from cohezion.flux.types import FluxSource as FluxSource


__all__ = [
    "FluxAggregator",
    "FluxBlock",
    "FluxContext",
    "FluxProvider",
    "FluxSource",
]
