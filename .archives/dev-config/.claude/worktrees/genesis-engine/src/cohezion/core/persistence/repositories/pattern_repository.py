"""
Pattern Repository - Persistence layer for code patterns and anti-patterns.
Supports SurrealDB with a local write-buffer for stability.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.core.persistence.surreal_client import SurrealClient


logger = logging.getLogger(__name__)


@dataclass
class CodePattern:
    name: str
    category: str
    description: str
    file_paths: list[str]
    code_example: str
    id: str | None = None
    frequency: int = 1
    confidence: float = 0.0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    obsidian_synced: bool = False
    sync_status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class CodeAntiPattern:
    name: str
    category: str
    description: str
    file_paths: list[str]
    severity: str  # low, medium, high, critical
    risk_level: int
    remediation: str
    code_example: str
    id: str | None = None
    frequency: int = 1
    confidence: float = 0.0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    obsidian_synced: bool = False
    sync_status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


class PatternRepository:
    """
    Handles persistence of patterns and anti-patterns.
    Uses a local write-buffer (.pattern_buffer.json) for reliability.
    """

    def __init__(
        self, client: SurrealClient, buffer_path: str = ".pattern_buffer.json"
    ) -> None:
        self.client = client
        self.buffer_path = Path(buffer_path)
        self._load_buffer()

    def _load_buffer(self) -> None:
        """Load local buffer from disk."""
        if self.buffer_path.exists():
            try:
                with open(self.buffer_path) as f:
                    self.buffer = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load pattern buffer: {e}")
                self.buffer = {"patterns": [], "anti_patterns": []}
        else:
            self.buffer = {"patterns": [], "anti_patterns": []}

    def _save_buffer(self) -> None:
        """Save local buffer to disk."""
        try:
            with open(self.buffer_path, "w") as f:
                json.dump(self.buffer, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save pattern buffer: {e}")

    async def store_pattern(self, pattern: CodePattern) -> str:
        """Store a pattern in the buffer and attempt SurrealDB sync."""
        pattern_dict = asdict(pattern)

        # Add to buffer
        self.buffer["patterns"].append(pattern_dict)
        self._save_buffer()

        # Attempt SurrealDB sync
        try:
            if await self.client.is_alive():
                res = await self.client.create("code_patterns", pattern_dict)
                if res and isinstance(res, list):
                    pattern_id = res[0].get("id")
                    logger.info(f"Pattern synced to SurrealDB: {pattern_id}")
                    return pattern_id
            else:
                logger.warning("SurrealDB offline. Pattern stored in local buffer.")
        except Exception as e:
            logger.error(f"Failed to sync pattern to SurrealDB: {e}")

        return "buffered"

    async def store_anti_pattern(self, anti_pattern: CodeAntiPattern) -> str:
        """Store an anti-pattern in the buffer and attempt SurrealDB sync."""
        anti_pattern_dict = asdict(anti_pattern)

        # Add to buffer
        self.buffer["anti_patterns"].append(anti_pattern_dict)
        self._save_buffer()

        # Attempt SurrealDB sync
        try:
            if await self.client.is_alive():
                res = await self.client.create("code_anti_patterns", anti_pattern_dict)
                if res and isinstance(res, list):
                    anti_pattern_id = res[0].get("id")
                    logger.info(f"Anti-pattern synced to SurrealDB: {anti_pattern_id}")
                    return anti_pattern_id
            else:
                logger.warning(
                    "SurrealDB offline. Anti-pattern stored in local buffer."
                )
        except Exception as e:
            logger.error(f"Failed to sync anti-pattern to SurrealDB: {e}")

        return "buffered"

    async def find_similar_patterns(
        self, embedding: list[float], limit: int = 5
    ) -> list[dict]:
        """Query SurrealDB for similar patterns."""
        if not await self.client.is_alive():
            return []

        try:
            query = f"""
            SELECT *, vector::similarity::cosine(embedding, $vector) AS score
            FROM code_patterns
            WHERE embedding IS NOT NULL
            ORDER BY score DESC
            LIMIT {limit}
            """
            res = await self.client.query(query, {"vector": embedding})
            return res[0].get("result", []) if res else []
        except Exception as e:
            logger.error(f"Failed to query similar patterns: {e}")
            return []

    async def increment_frequency(self, table: str, record_id: str) -> bool:
        """Increment frequency count for a pattern/anti-pattern."""
        if not await self.client.is_alive():
            return False

        try:
            query = f"UPDATE {record_id} SET frequency += 1, last_seen = time::now()"
            await self.client.query(query)
            return True
        except Exception as e:
            logger.error(f"Failed to increment frequency for {record_id}: {e}")
            return False

    def get_buffered_findings(self) -> dict:
        """Get all findings currently in the local buffer."""
        return self.buffer
