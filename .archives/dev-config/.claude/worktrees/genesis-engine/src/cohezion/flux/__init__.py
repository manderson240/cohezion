"""FLUX Protocol — Federated Lattice of Unified conteXt.

Unified context interface merging vault, SurrealDB, MCP tools, cache,
and execution history into a single query surface for agent nodes.
"""

from cohezion.flux.aggregator import FluxAggregator
from cohezion.flux.provider import FluxProvider
from cohezion.flux.types import FluxBlock, FluxContext, FluxSource


__all__ = [
    "FluxAggregator",
    "FluxBlock",
    "FluxContext",
    "FluxProvider",
    "FluxSource",
]
