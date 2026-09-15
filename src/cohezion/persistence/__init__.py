"""Git-safe persistence and handoff mechanisms."""

import contextlib


# Wiring-sweep 2026-06-22: surreal_logger, obsidian_mcp were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.persistence.surreal_logger import (
        SurrealTrajectoryLogger as SurrealTrajectoryLogger,
    )

with contextlib.suppress(Exception):
    from cohezion.persistence.obsidian_mcp import (
        ObsidianMemoryMCP as ObsidianMemoryMCP,
    )

with contextlib.suppress(Exception):
    from cohezion.persistence.surreal_connection_pool import (
        PoolConfig as PoolConfig,
        SurrealConnectionPool as SurrealConnectionPool,
        get_surreal_connection_pool as get_surreal_connection_pool,
    )
