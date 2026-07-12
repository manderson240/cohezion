"""Tests for optional durable persistence of the GEA evolutionary archive.

Covers the additive, fail-open, off-by-default SurrealDB side-write (GAP 1.1):
- persistence OFF by default → behaviour identical to in-memory-only
- with a persister: both retained adds AND pruned (rejected_novel) entries write
- selection/pruning behaviour is UNCHANGED by attaching a persister
- fail-open: a raising persister never breaks the engine
- load/query round-trips over the serialized records

No live SurrealDB: the engine takes a duck-typed persister, stubbed here.
"""

from typing import Any

from cohezion.compound.group_evolution import (
    GroupEvolutionEngine,
    TaskSuccessVector,
)


class StubPersister:
    """In-list persister implementing the ArchivePersister protocol."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def persist(self, record: dict[str, Any]) -> None:
        self.records.append(record)

    def load(self, limit: int = 1000) -> list[dict[str, Any]]:
        return self.records[:limit]

    def query_rejected_novel(self, limit: int = 1000) -> list[dict[str, Any]]:
        return [r for r in self.records if r["status"] == "rejected_novel"][:limit]


class RaisingPersister:
    """Persister whose every method raises — exercises the fail-open path."""

    def persist(self, record: dict[str, Any]) -> None:
        raise RuntimeError("surreal down")

    def load(self, limit: int = 1000) -> list[dict[str, Any]]:
        raise RuntimeError("surreal down")

    def query_rejected_novel(self, limit: int = 1000) -> list[dict[str, Any]]:
        raise RuntimeError("surreal down")


def _vec(agent_id: str, results: list[bool]) -> TaskSuccessVector:
    return TaskSuccessVector.from_execution_history(
        agent_id=agent_id,
        task_ids=[f"t{i}" for i in range(len(results))],
        results=results,
    )


def _add_sequence(engine: GroupEvolutionEngine, n: int) -> None:
    """Add n entries with varied success vectors (drives novelty + pruning)."""
    for i in range(n):
        results = [i % 2 == 0, i % 3 == 0, i % 4 == 0]
        engine.add_to_archive(
            agent_id=f"agent-{i}",
            parent_ids=[f"parent-{i}"],
            success_vector=_vec(f"agent-{i}", results),
        )


# ---------------------------------------------------------------------------
# (a) Off by default
# ---------------------------------------------------------------------------


class TestPersistenceOffByDefault:
    def test_persister_is_none_by_default(self):
        engine = GroupEvolutionEngine()
        assert engine._persister is None

    def test_behaves_as_before_without_persister(self):
        engine = GroupEvolutionEngine()
        _add_sequence(engine, 5)
        assert len(engine.archive) == 5
        assert engine._generation == 5

    def test_load_and_query_empty_without_persister(self):
        engine = GroupEvolutionEngine()
        _add_sequence(engine, 3)
        assert engine.load_archive() == []
        assert engine.query_rejected_novel() == []


# ---------------------------------------------------------------------------
# (b) Persister writes on add and on prune, rejected_novel marked
# ---------------------------------------------------------------------------


class TestPersisterWrites:
    def test_add_writes_retained(self):
        stub = StubPersister()
        engine = GroupEvolutionEngine(persister=stub)
        engine.add_to_archive("a", [], _vec("a", [True, False, True]))
        assert len(stub.records) == 1
        rec = stub.records[0]
        assert rec["status"] == "retained"
        assert rec["agent_id"] == "a"
        # successes must be a plain list (ndarray would break JSON/CBOR).
        assert isinstance(rec["successes"], list)
        assert rec["successes"] == [1.0, 0.0, 1.0]
        assert set(rec) >= {
            "agent_id",
            "generation",
            "parent_ids",
            "performance",
            "novelty",
            "gea_score",
            "skill_patches",
            "ancestor_count",
            "creation_time",
            "task_ids",
            "successes",
            "status",
        }

    def test_prune_writes_rejected_novel(self):
        stub = StubPersister()
        engine = GroupEvolutionEngine(max_archive_size=3, persister=stub)
        _add_sequence(engine, 5)
        # 5 retained adds + 2 pruned rejected_novel = 7 rows.
        retained = [r for r in stub.records if r["status"] == "retained"]
        rejected = [r for r in stub.records if r["status"] == "rejected_novel"]
        assert len(retained) == 5
        assert len(rejected) == 2
        assert len(engine.archive) == 3


# ---------------------------------------------------------------------------
# selection/pruning unchanged by attaching a persister (the real safety claim)
# ---------------------------------------------------------------------------


class TestSelectionUnchanged:
    def test_in_memory_archive_identical_with_and_without_persister(self):
        engine_none = GroupEvolutionEngine(max_archive_size=3)
        engine_persist = GroupEvolutionEngine(max_archive_size=3, persister=StubPersister())
        _add_sequence(engine_none, 6)
        _add_sequence(engine_persist, 6)

        def fingerprint(e: GroupEvolutionEngine):
            return [(x.agent_id, round(x.gea_score, 9)) for x in e.archive]

        assert fingerprint(engine_none) == fingerprint(engine_persist)
        assert engine_none._generation == engine_persist._generation
        assert engine_none.get_archive_stats() == engine_persist.get_archive_stats()


# ---------------------------------------------------------------------------
# (c) Fail-open
# ---------------------------------------------------------------------------


class TestFailOpen:
    def test_raising_persister_does_not_break_add_or_prune(self):
        engine = GroupEvolutionEngine(max_archive_size=3, persister=RaisingPersister())
        _add_sequence(engine, 5)  # exercises both add + prune persist paths
        assert len(engine.archive) == 3
        assert engine._generation == 5

    def test_raising_persister_load_and_query_return_empty(self):
        engine = GroupEvolutionEngine(persister=RaisingPersister())
        engine.add_to_archive("a", [], _vec("a", [True, True]))
        assert engine.load_archive() == []
        assert engine.query_rejected_novel() == []


# ---------------------------------------------------------------------------
# (d) load / query round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_load_returns_all_persisted_records(self):
        stub = StubPersister()
        engine = GroupEvolutionEngine(max_archive_size=3, persister=stub)
        _add_sequence(engine, 5)
        loaded = engine.load_archive()
        assert len(loaded) == 7  # 5 retained + 2 rejected_novel
        assert {r["status"] for r in loaded} == {"retained", "rejected_novel"}

    def test_query_rejected_novel_round_trip(self):
        stub = StubPersister()
        engine = GroupEvolutionEngine(max_archive_size=3, persister=stub)
        _add_sequence(engine, 5)
        rejected = engine.query_rejected_novel()
        assert len(rejected) == 2
        assert all(r["status"] == "rejected_novel" for r in rejected)
        # Serialized shape survives the round-trip.
        assert all(isinstance(r["successes"], list) for r in rejected)
