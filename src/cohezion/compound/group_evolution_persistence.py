"""SurrealDB-backed durable persistence for the GEA evolutionary archive.

This is the concrete :class:`ArchivePersister` (see ``group_evolution``) that
gives the in-memory GEA archive a durable stepping-stone pool — including the
``rejected_novel`` entries dropped by size-pruning (the DGM point).

Kept in a SEPARATE module on purpose: the engine's default path
(``GroupEvolutionEngine(persister=None)``) imports nothing here and nothing
from ``surrealdb``, so unit tests stay in-memory (CB4/CB17 isolation). This
persister is injected only by callers that want durability, and every write
is a fail-open side-write — the engine swallows any error it raises.

The engine methods are synchronous while :class:`SurrealClient` is async, so
each call bridges onto a single dedicated background event loop. One loop
(not a fresh ``asyncio.run`` per call) is required because the underlying
websocket binds to the loop it was opened on. Reuses the existing client,
adds no dependency.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from cohezion.core.persistence.surreal_client import SurrealClient, get_surreal_client


TABLE = "gea_archive"


class SurrealArchivePersister:
    """Append-only archive persister backed by :class:`SurrealClient`.

    Each :meth:`persist` writes one row (auto-id); ``agent_id`` and ``status``
    are plain fields, so a just-added-then-pruned entry yields both a
    ``retained`` and a ``rejected_novel`` row (an honest event log).
    """

    def __init__(self, client: SurrealClient | None = None) -> None:
        self._client = client or get_surreal_client()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def _run(self, coro: Any) -> Any:
        """Run an async coroutine on the dedicated background loop."""
        with self._lock:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                threading.Thread(target=self._loop.run_forever, daemon=True).start()
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def persist(self, record: dict[str, Any]) -> None:
        self._run(self._client.create(TABLE, record))

    def load(self, limit: int = 1000) -> list[dict[str, Any]]:
        return self._query(f"SELECT * FROM {TABLE} LIMIT $limit", {"limit": int(limit)})

    def query_rejected_novel(self, limit: int = 1000) -> list[dict[str, Any]]:
        return self._query(
            f"SELECT * FROM {TABLE} WHERE status = $status LIMIT $limit",
            {"status": "rejected_novel", "limit": int(limit)},
        )

    def _query(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        result = self._run(self._client.query(sql, params))
        if not result:
            return []
        first = result[0]
        # SurrealDB wraps rows under "result"; InMemoryStore returns a bare list.
        if isinstance(first, dict) and "result" in first:
            return list(first.get("result") or [])
        return list(result[0]) if isinstance(result[0], list) else list(result)
