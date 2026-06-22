"""SurrealDB persistence layer."""

import contextlib

from cohezion.core.persistence.surreal_client import SurrealClient


__all__ = ["DBAdmin", "PhysicsState", "RedisAggregator", "SurrealClient"]

# Wiring-sweep 2026-06-22: admin, redis_aggregator, query_patterns were import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.core.persistence.admin import DBAdmin as DBAdmin

with contextlib.suppress(Exception):
    from cohezion.core.persistence.redis_aggregator import (
        RedisAggregator as RedisAggregator,
    )

with contextlib.suppress(Exception):
    from cohezion.core.persistence.surreal_client import PhysicsState as PhysicsState
