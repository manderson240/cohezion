import logging
import os
from typing import Any

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
                await db.connect()
                await db.use(self.namespace, self.database)

                user = os.getenv("SURREAL_USER", "root")
                password = os.getenv("SURREAL_PASS", "root")
                await db.signin({"user": user, "pass": password})

                # Query recent trajectories ordered by timestamp
                result = await db.query(
                    f"SELECT * FROM trajectory ORDER BY timestamp DESC LIMIT {limit}"
                )

                # SurrealDB query returns a list of results (one per statement)
                if result and result[0].get("result"):
                    return result[0]["result"]
                return []

            except Exception as e:
                logger.error(f"Failed to fetch trajectories from SurrealDB: {e}")
                raise
