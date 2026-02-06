"""
Cache Replay Protocol - Enables compound engineering for persistence.

When SurrealDB goes offline, writes are cached locally.
When SurrealDB reconnects, cached writes are replayed idempotently.
COHEZION = 0.5 HIHO drives stability.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path("cache")
PENDING_WRITES_FILE = CACHE_DIR / "pending_writes.jsonl"


@dataclass
class CachedWrite:
    """A cached write operation."""

    id: str
    operation: str  # "create", "update", "delete"
    table: str
    data: dict[str, Any]
    timestamp: str
    replayed: bool = False


class CacheReplayManager:
    """
    Manages offline cache and replay for SurrealDB.

    Compound Engineering: This component enables all future persistence
    features by providing reliable offline-first storage.
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pending_file = self.cache_dir / "pending_writes.jsonl"

    def cache_write(self, operation: str, table: str, data: dict[str, Any]) -> str:
        """
        Cache a write operation for later replay.

        Returns:
            Write ID for tracking
        """
        write_id = f"{table}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        cached = CachedWrite(
            id=write_id,
            operation=operation,
            table=table,
            data=data,
            timestamp=datetime.now().isoformat(),
        )

        with open(self.pending_file, "a") as f:
            f.write(json.dumps(asdict(cached)) + "\n")

        logger.info(f"Cached write: {write_id}")
        return write_id

    def get_pending_writes(self) -> list[CachedWrite]:
        """Get all pending (unreplayed) writes."""
        if not self.pending_file.exists():
            return []

        pending = []
        with open(self.pending_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if not data.get("replayed", False):
                        pending.append(CachedWrite(**data))
        return pending

    async def replay_to_surreal(self, client: Any) -> int:
        """
        Replay all pending writes to SurrealDB.

        Args:
            client: SurrealDB client instance

        Returns:
            Number of writes replayed
        """
        pending = self.get_pending_writes()
        if not pending:
            logger.info("No pending writes to replay")
            return 0

        replayed_count = 0
        replayed_ids = set()

        for write in pending:
            try:
                if write.operation == "create":
                    await client.query(
                        f"CREATE {write.table} CONTENT $data", {"data": write.data}
                    )
                elif write.operation == "update":
                    record_id = write.data.get("id", write.id)
                    await client.query(
                        f"UPDATE {record_id} CONTENT $data", {"data": write.data}
                    )
                elif write.operation == "delete":
                    record_id = write.data.get("id", write.id)
                    await client.query(f"DELETE {record_id}")

                replayed_ids.add(write.id)
                replayed_count += 1
                logger.info(f"Replayed: {write.id}")

            except Exception as e:
                logger.error(f"Failed to replay {write.id}: {e}")

        # Mark replayed writes
        self._mark_replayed(replayed_ids)

        logger.info(f"✅ Replayed {replayed_count} writes to SurrealDB")
        return replayed_count

    def _mark_replayed(self, replayed_ids: set[str]):
        """Mark writes as replayed in the cache file."""
        if not self.pending_file.exists():
            return

        lines = []
        with open(self.pending_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if data["id"] in replayed_ids:
                        data["replayed"] = True
                    lines.append(json.dumps(data))

        with open(self.pending_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def clear_replayed(self):
        """Remove all replayed writes from cache (cleanup)."""
        if not self.pending_file.exists():
            return

        pending = []
        with open(self.pending_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if not data.get("replayed", False):
                        pending.append(json.dumps(data))

        with open(self.pending_file, "w") as f:
            if pending:
                f.write("\n".join(pending) + "\n")
            else:
                f.write("")

        logger.info(f"Cleared replayed writes, {len(pending)} pending remain")


# Singleton for easy access
_manager: CacheReplayManager | None = None


def get_cache_manager() -> CacheReplayManager:
    """Get or create the cache replay manager singleton."""
    global _manager
    if _manager is None:
        _manager = CacheReplayManager()
    return _manager


if __name__ == "__main__":
    # Quick test
    manager = CacheReplayManager()

    # Simulate caching
    write_id = manager.cache_write(
        operation="create",
        table="test_nodes",
        data={"content": "Test node", "physics_state": [0.5] * 12},
    )
    print(f"Cached write: {write_id}")

    pending = manager.get_pending_writes()
    print(f"Pending writes: {len(pending)}")
