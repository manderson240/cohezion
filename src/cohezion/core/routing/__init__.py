"""Manifold-based routing and request bridging."""

import contextlib

from cohezion.core.routing.router import LocalExpertRouter


__all__ = ["LocalExpertRouter", "ManifoldBridge"]

# Wiring-sweep 2026-06-22: manifold_bridge was an import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.core.routing.manifold_bridge import ManifoldBridge as ManifoldBridge
