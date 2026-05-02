"""Tests for Journey Persistence Manager (Story 1.5)."""

from __future__ import annotations

from cohezion.core.journey_persistence_manager import (
    JourneyPersistenceManager,
    TrajectoryNode,
    WriteDestination,
)


class TestJourneyPersistenceManager:
    def _node(self, node_id: str = "n1") -> TrajectoryNode:
        return TrajectoryNode(node_id=node_id, state_12d=[0.5] * 12, agent_id="agent-1")

    def test_persist_to_both_when_db_available(self):
        mgr = JourneyPersistenceManager(db_available=True)
        result = mgr.persist(self._node())
        assert result.destination == WriteDestination.BOTH
        assert mgr.db_count() == 1
        assert mgr.cache_count() == 1

    def test_persist_to_cache_when_db_unavailable(self):
        mgr = JourneyPersistenceManager(db_available=False)
        result = mgr.persist(self._node())
        assert result.destination == WriteDestination.LOCAL_CACHE
        assert result.reconciliation_pending is True
        assert mgr.db_count() == 0
        assert mgr.cache_count() == 1

    def test_reconciliation_replays_cached_writes(self):
        mgr = JourneyPersistenceManager(db_available=False)
        mgr.persist(self._node("n1"))
        mgr.persist(self._node("n2"))
        assert mgr.pending_reconciliation_count() == 2
        replayed = mgr.restore_db_connectivity()
        assert replayed == 2
        assert mgr.db_count() == 2
        assert mgr.pending_reconciliation_count() == 0

    def test_idempotency_key_prevents_duplicate_writes(self):
        mgr = JourneyPersistenceManager()
        node = self._node()
        mgr.persist(node)
        mgr.persist(node)  # Same node, same timestamp → same idempotency key
        assert mgr.cache_count() == 1

    def test_latency_is_reasonable(self):
        mgr = JourneyPersistenceManager()
        result = mgr.persist(self._node())
        assert result.latency_ms < 100.0  # Well under 10ms target in test env

    def test_idempotency_key_included_in_result(self):
        mgr = JourneyPersistenceManager()
        result = mgr.persist(self._node())
        assert isinstance(result.idempotency_key, str)
        assert len(result.idempotency_key) == 16
