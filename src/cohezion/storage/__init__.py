"""Storage — SurrealDB client for trajectory persistence."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.storage.surreal_client import SurrealDBClient as SurrealDBClient
    from cohezion.storage.surreal_client import TrajectoryNode as TrajectoryNode
