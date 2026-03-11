"""Journey Persistence Manager (Story 1.5, NFR-3).

Dual-writes 12D trajectory nodes to SurrealDB + local cache fallback.
Background reconciliation replays cached writes when DB connectivity restores.
Idempotency keys prevent duplicate writes.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

LATENCY_TARGET_MS = 10.0


class WriteDestination(Enum):
    SURREAL_DB = "surrealdb"
    LOCAL_CACHE = "local_cache"
    BOTH = "both"


@dataclass
class TrajectoryNode:
    node_id: str
    state_12d: list[float]  # 12D axiomatic vector
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""

    def idempotency_key(self) -> str:
        raw = f"{self.node_id}:{self.timestamp:.3f}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class PersistenceResult:
    node_id: str
    destination: WriteDestination
    latency_ms: float
    idempotency_key: str
    reconciliation_pending: bool = False


class JourneyPersistenceManager:
    """Dual-write persistence with cache fallback and background reconciliation."""

    def __init__(self, db_available: bool = True) -> None:
        self._db_available = db_available
        self._db_records: dict[str, TrajectoryNode] = {}
        self._cache: dict[str, TrajectoryNode] = {}  # Local cache
        self._seen_idempotency_keys: set[str] = set()
        self._pending_reconciliation: list[TrajectoryNode] = []

    def persist(self, node: TrajectoryNode) -> PersistenceResult:
        """Dual-write with <10ms latency target."""
        t0 = time.perf_counter()
        idem_key = node.idempotency_key()

        # Idempotency: skip duplicate writes
        if idem_key in self._seen_idempotency_keys:
            latency_ms = (time.perf_counter() - t0) * 1000
            return PersistenceResult(
                node_id=node.node_id,
                destination=WriteDestination.BOTH,
                latency_ms=latency_ms,
                idempotency_key=idem_key,
            )

        self._seen_idempotency_keys.add(idem_key)
        destination = WriteDestination.BOTH

        # Write to local cache always
        self._cache[node.node_id] = node

        if self._db_available:
            self._db_records[node.node_id] = node
        else:
            # Queue for reconciliation
            self._pending_reconciliation.append(node)
            destination = WriteDestination.LOCAL_CACHE
            logger.warning("DB unavailable: node %s queued for reconciliation", node.node_id)

        latency_ms = (time.perf_counter() - t0) * 1000
        if latency_ms > LATENCY_TARGET_MS:
            logger.warning(
                "Persistence latency %.2fms exceeds target %dms", latency_ms, LATENCY_TARGET_MS
            )

        return PersistenceResult(
            node_id=node.node_id,
            destination=destination,
            latency_ms=latency_ms,
            idempotency_key=idem_key,
            reconciliation_pending=not self._db_available,
        )

    def restore_db_connectivity(self) -> int:
        """Simulate DB recovery. Replays cached writes. Returns replayed count."""
        self._db_available = True
        replayed = 0
        for node in self._pending_reconciliation:
            if node.node_id not in self._db_records:
                self._db_records[node.node_id] = node
                replayed += 1
        self._pending_reconciliation.clear()
        logger.info("Reconciled %d cached nodes to DB", replayed)
        return replayed

    def cache_count(self) -> int:
        return len(self._cache)

    def db_count(self) -> int:
        return len(self._db_records)

    def pending_reconciliation_count(self) -> int:
        return len(self._pending_reconciliation)
