"""Async SurrealDB client for vault_graph module."""

import os
from typing import Any

from surrealdb import AsyncSurreal


class GraphQueryError(Exception):
    """SurrealDB returned an error response."""


class GraphClient:
    def __init__(self) -> None:
        self.url = os.environ.get("SURREALDB_URL", "http://localhost:8001")
        self.username = os.environ.get("SURREALDB_USERNAME", "root")
        self.password = os.environ.get("SURREALDB_PASSWORD", "root")
        self.namespace = os.environ.get("SURREALDB_NAMESPACE", "cohezion")
        self.database = os.environ.get("SURREALDB_DATABASE", "vault")

    def _make_connection(self) -> Any:
        """Return an AsyncSurreal connection (sync factory for testability)."""
        return AsyncSurreal(self.url)

    async def query(self, sql: str) -> list:
        """Execute SurrealQL, unwrap first result set, raise on error."""
        db = self._make_connection()
        async with db:
            await db.signin({"username": self.username, "password": self.password})
            await db.use(self.namespace, self.database)
            data = await db.query(sql)
        if isinstance(data, dict) and "code" in data:
            raise GraphQueryError(data.get("description", str(data)))
        # Unwrap: [{"result": [...]}] → [...]
        # isinstance(data[0], dict) is LOAD-BEARING. Without it, `"result" in data[0]`
        # is a SUBSTRING test when data[0] is a str -- so a string response falls through
        # here, gets returned as-is, and the caller's .get() dies with
        # "'str' object has no attribute 'get'". That is exactly how graph_stats and
        # graph_bridges failed (2026-07-19): both threw instead of returning data, and the
        # two tools for finding non-obvious connections were dead for an unknown period.
        if data and isinstance(data, list) and isinstance(data[0], dict) and "result" in data[0]:
            return data[0]["result"]
        return data or []

    async def execute(self, sql: str) -> None:
        """Execute SurrealQL without returning results (for writes)."""
        await self.query(sql)


_client: GraphClient | None = None


def get_graph_client() -> GraphClient:
    global _client
    if _client is None:
        _client = GraphClient()
    return _client
