import logging
import os
from typing import Any, cast

from surrealdb import AsyncSurreal


logger = logging.getLogger(__name__)


class OuroborosMonitor:
    """
    Monitor daemon for ingesting telemetry from SurrealDB trajectories.
    """

    def __init__(
        self,
        url: str = "ws://localhost:8001/rpc",
        namespace: str = "cohezion",
        database: str = "cohezion",
    ):
        self.url = url
        self.namespace = namespace
        self.database = database

    async def fetch_recent_trajectories(self, limit: int = 100) -> list[dict[Any, Any]]:
        """
        Fetches the most recent trajectories from SurrealDB.

        Args:
            limit: Maximum number of trajectory points to fetch.

        Returns:
            List[Dict]: List of trajectory records.
        """
        async with AsyncSurreal(self.url) as db:
            try:
                # NOTE: `async with AsyncSurreal(...) as db` already establishes
                # the WebSocket connection via __aenter__. Calling db.connect()
                # here was a stale paste-from-docs bug (Ω11 Phase 1, 2026-04-23).
                # See sibling cohezion/persistence/surreal_logger.py:58-66 for
                # the canonical pattern (no manual connect()).
                await db.use(self.namespace, self.database)

                user = os.getenv("SURREAL_USER", "root")
                password = os.getenv("SURREAL_PASS", "root")
                await db.signin({"user": user, "pass": password})

                # Query recent trajectories ordered by timestamp
                result = await db.query(
                    f"SELECT * FROM trajectory ORDER BY timestamp DESC LIMIT {limit}"
                )

                # Defensive narrowing: SurrealDB returns list[Value], but for
                # SELECT statements we expect [{"result": [...records...], ...}].
                # Anything else is a driver/server contract violation -> [].
                if not result or not isinstance(result, list):
                    return []
                first = result[0]
                if not isinstance(first, dict):
                    return []
                rows = first.get("result")
                if not isinstance(rows, list):
                    return []
                return cast(list[dict[Any, Any]], rows)

            except Exception as e:
                logger.error(f"Failed to fetch trajectories from SurrealDB: {e}")
                raise
