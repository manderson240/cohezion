"""Greenfield tests for cohezion.knowledge_graph module (Wave 3D).

Covers:
- BidirectionalLink construction and idempotent SHA-256 IDs
- KnowledgeGraph in-memory link storage, traversal, and shortest-path BFS
- KnowledgeGraphQueryEngine: DB path, file fallback, pattern aggregation, search
- Convenience link helpers (link_doc_to_doc) wired to singleton
- Migration metadata dataclasses (UniverseArtifactMigration)
- UniverseGenealogySurvey static phases (pattern extraction)

All external services (SurrealDB, vault filesystem, git subprocess) are mocked.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from cohezion.knowledge_graph.bidirectional_linker import (
    BidirectionalLink,
    KnowledgeGraph,
    LinkType,
    get_knowledge_graph,
    link_doc_to_doc,
)
from cohezion.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from cohezion.knowledge_graph.universe_artifact_migration import (
    ArtifactMetadata,
    MigrationSnapshot,
    TrainingRunMetadata,
    UniverseArtifactMigration,
)
from cohezion.knowledge_graph.universe_genealogy_migration import (
    UniverseEpoch,
    UniverseGenealogySurvey,
    UniversePattern,
)


# ---------------------------------------------------------------------------
# BidirectionalLink + KnowledgeGraph (in-memory mode)
# ---------------------------------------------------------------------------


def test_bidirectional_link_create_assigns_deterministic_id():
    """Same source/target/link_type must produce the same SHA-256 link_id."""
    link_a = BidirectionalLink.create(source="alpha", target="beta", link_type=LinkType.DOC_TO_DOC)
    link_b = BidirectionalLink.create(source="alpha", target="beta", link_type=LinkType.DOC_TO_DOC)
    # Bidirectional: A->B and B->A share the same id
    link_reverse = BidirectionalLink.create(
        source="beta", target="alpha", link_type=LinkType.DOC_TO_DOC
    )

    assert link_a.link_id == link_b.link_id
    assert link_a.link_id == link_reverse.link_id
    assert len(link_a.link_id) == 64  # SHA-256 hex digest length

    # Different link_type should produce a different id
    link_other = BidirectionalLink.create(
        source="alpha", target="beta", link_type=LinkType.DOC_TO_CODE
    )
    assert link_other.link_id != link_a.link_id


def test_bidirectional_link_to_surreal_format():
    """to_surreal must emit a record with id, source, target, link_type, ISO timestamp."""
    link = BidirectionalLink.create(
        source="src",
        target="dst",
        link_type=LinkType.SKILL_TO_CODE,
        metadata={"reason": "demo"},
    )
    record = link.to_surreal()

    assert record["id"].startswith("link:")
    assert record["source"] == "src"
    assert record["target"] == "dst"
    assert record["link_type"] == "skill_to_code"
    assert record["metadata"] == {"reason": "demo"}
    # ISO 8601 timestamp must be parseable
    datetime.fromisoformat(record["created_at"])


@pytest.mark.asyncio
async def test_knowledge_graph_add_and_get_links_in_memory(tmp_path, monkeypatch):
    """add_link should cache in memory; get_links should return both directions."""
    # Stub vault persistence to no-op (avoid touching ~/vaults)
    kg = KnowledgeGraph(vault_root=tmp_path / "vault")
    kg.client = None  # force in-memory fallback

    # Bypass _persist_to_vault to keep tests pure
    async def _noop(_link):
        return None

    monkeypatch.setattr(kg, "_persist_to_vault", _noop)

    link = await kg.add_link(
        source="A.md",
        target="B.md",
        link_type=LinkType.DOC_TO_DOC,
        metadata={"reason": "test"},
    )

    assert link.link_id in kg._links
    by_source = await kg.get_links("A.md")
    by_target = await kg.get_links("B.md")
    assert len(by_source) == 1
    assert len(by_target) == 1
    assert by_source[0].link_id == link.link_id

    # link_type filter
    none_match = await kg.get_links("A.md", link_type=LinkType.SKILL_TO_CODE)
    assert none_match == []


@pytest.mark.asyncio
async def test_knowledge_graph_neighbors_and_shortest_path(tmp_path, monkeypatch):
    """get_neighbors (BFS) and find_path should walk the in-memory graph."""
    kg = KnowledgeGraph(vault_root=tmp_path / "vault")
    kg.client = None

    async def _noop(_link):
        return None

    monkeypatch.setattr(kg, "_persist_to_vault", _noop)

    # Build chain: A -> B -> C
    await kg.add_link("A", "B", LinkType.REFERENCES)
    await kg.add_link("B", "C", LinkType.REFERENCES)

    neighbors_1 = await kg.get_neighbors("A", depth=1)
    neighbors_2 = await kg.get_neighbors("A", depth=2)
    assert neighbors_1 == {"B"}
    assert neighbors_2 == {"B", "C"}

    # Shortest path
    path = await kg.find_path("A", "C")
    assert path == ["A", "B", "C"]

    # Self path
    assert await kg.find_path("A", "A") == ["A"]

    # No path
    assert await kg.find_path("A", "ZZZ_unreachable") is None


@pytest.mark.asyncio
async def test_knowledge_graph_load_from_vault_roundtrip(tmp_path):
    """Persist a link to vault, then reload it into a fresh KnowledgeGraph."""
    import json

    kg = KnowledgeGraph(vault_root=tmp_path / "vault")
    kg.client = None

    link = BidirectionalLink.create(
        source="docX",
        target="codeY",
        link_type=LinkType.DOC_TO_CODE,
        metadata={"section": "intro"},
    )
    await kg._persist_to_vault(link)

    # Verify on-disk format
    vault_file = tmp_path / "vault" / "links" / f"{link.link_id}.json"
    assert vault_file.exists()
    payload = json.loads(vault_file.read_text())
    assert payload["link_type"] == "doc_to_code"

    # Fresh KG loads it back
    kg2 = KnowledgeGraph(vault_root=tmp_path / "vault")
    kg2.client = None
    count = await kg2.load_from_vault()
    assert count == 1
    assert link.link_id in kg2._links


@pytest.mark.asyncio
async def test_link_doc_to_doc_uses_singleton(monkeypatch, tmp_path):
    """Convenience helper should call the singleton's add_link with DOC_TO_DOC."""
    import cohezion.knowledge_graph.bidirectional_linker as linker_mod

    # Reset singleton to ensure clean fixture
    monkeypatch.setattr(linker_mod, "_knowledge_graph", None)

    kg = get_knowledge_graph()
    kg.vault_root = tmp_path / "vault"
    kg.client = None

    # Spy on add_link
    called = {}

    async def _spy(source, target, link_type, metadata=None):
        called["source"] = source
        called["target"] = target
        called["link_type"] = link_type
        called["metadata"] = metadata
        return BidirectionalLink.create(source, target, link_type, metadata)

    monkeypatch.setattr(kg, "add_link", _spy)

    await link_doc_to_doc("a.md", "b.md", reason="cross-ref")

    assert called["source"] == "a.md"
    assert called["target"] == "b.md"
    assert called["link_type"] == LinkType.DOC_TO_DOC
    assert called["metadata"] == {"reason": "cross-ref"}


# ---------------------------------------------------------------------------
# KnowledgeGraphQueryEngine
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_execution_history_db_path_returns_rows():
    """When a DB client is supplied, query_execution_history should return its rows."""
    fake_db = AsyncMock()
    fake_db.query = AsyncMock(
        return_value=[
            {"agent_name": "alpha", "status": "completed", "final_coherence": 0.5},
            {"agent_name": "beta", "status": "failed", "final_coherence": 0.2},
        ]
    )
    engine = KnowledgeGraphQueryEngine(db_client=fake_db)
    rows = await engine.query_execution_history(limit=10)

    fake_db.query.assert_awaited_once()
    assert len(rows) == 2
    assert rows[0]["agent_name"] == "alpha"


@pytest.mark.asyncio
async def test_query_execution_history_falls_back_when_db_raises(tmp_path, monkeypatch):
    """If DB raises and no journey files exist, fallback returns empty list."""
    fake_db = AsyncMock()
    fake_db.query = AsyncMock(side_effect=RuntimeError("connection refused"))
    engine = KnowledgeGraphQueryEngine(db_client=fake_db)

    # Run from a tmp cwd so data/universe doesn't exist
    monkeypatch.chdir(tmp_path)
    result = await engine.query_execution_history(limit=5)
    assert result == []


@pytest.mark.asyncio
async def test_get_pattern_summary_aggregates_counts():
    """get_pattern_summary should aggregate agent_counts, status_counts, avg_coherence."""
    fake_db = AsyncMock()
    fake_db.query = AsyncMock(
        return_value=[
            {"agent_name": "alpha", "status": "completed", "final_coherence": 0.4},
            {"agent_name": "alpha", "status": "completed", "final_coherence": 0.6},
            {"agent_name": "beta", "status": "failed", "final_coherence": None},
        ]
    )
    engine = KnowledgeGraphQueryEngine(db_client=fake_db)
    summary = await engine.get_pattern_summary()

    assert summary["total_executions"] == 3
    assert summary["agent_counts"] == {"alpha": 2, "beta": 1}
    assert summary["status_counts"] == {"completed": 2, "failed": 1}
    # Two coherences (0.4, 0.6) → avg 0.5; None is excluded
    assert summary["avg_coherence"] == pytest.approx(0.5)


def test_search_knowledge_returns_top_k_ranked(tmp_path):
    """search_knowledge should TF-IDF-rank markdown files and return top_k."""
    # Seed two markdown files
    (tmp_path / "lessons.md").write_text(
        "# Lessons\nCohezion uses HIHO stability for coherence checks.\n"
    )
    (tmp_path / "unrelated.md").write_text("# Other\nThis discusses something else entirely.\n")

    engine = KnowledgeGraphQueryEngine(knowledge_dir=tmp_path)
    results = engine.search_knowledge("HIHO coherence", top_k=2)

    assert len(results) >= 1
    assert results[0]["title"] == "Lessons"
    assert results[0]["score"] > 0
    assert "HIHO" in results[0]["snippet"] or "coherence" in results[0]["snippet"].lower()


def test_search_knowledge_empty_query_returns_empty():
    """Whitespace-only or short query should return []."""
    engine = KnowledgeGraphQueryEngine(knowledge_dir=Path("/tmp"))
    assert engine.search_knowledge("   ") == []
    # All terms < 3 chars are filtered out
    assert engine.search_knowledge("a b c") == []


# ---------------------------------------------------------------------------
# Migration dataclasses + survey static phases
# ---------------------------------------------------------------------------


def test_migration_dataclasses_construct_cleanly():
    """ArtifactMetadata, TrainingRunMetadata, MigrationSnapshot should be plain dataclasses."""
    artifact = ArtifactMetadata(
        artifact_id="a1",
        run_id="r1",
        file_path="/tmp/x",
        file_name="x.json",
        artifact_type="log",
        file_size_bytes=1024,
        content_hash="deadbeef",
        language_model_generation=1,
        training_phase="phase_0",
        extraction_timestamp="2026-04-23T00:00:00",
    )
    assert artifact.file_size_bytes == 1024

    run = TrainingRunMetadata(
        run_id="r1",
        timestamp="2026-04-23T00:00:00",
        model_id="m",
        model_version="v1",
        universe_epoch=1,
        coherence_score=0.46,
        total_artifacts=10,
        total_size_bytes=2048,
        training_duration_seconds=120.0,
        language_drift_rate=0.01,
        git_commit="abc123",
    )
    assert run.extraction_status == "pending"

    snap = MigrationSnapshot(
        snapshot_id="s1",
        phase="phase_0",
        timestamp="t",
        artifacts_processed=5,
        artifacts_verified=5,
        total_bytes_migrated=10,
        status="ok",
    )
    assert snap.error_count == 0


def test_universe_artifact_migration_init_creates_output_dir(tmp_path):
    """UniverseArtifactMigration.__init__ should create output_dir and init empty state."""
    out_dir = tmp_path / "export"
    svc = UniverseArtifactMigration(cohezion_root=tmp_path / "repo", output_dir=out_dir)
    assert out_dir.exists()
    assert svc.artifacts == []
    assert svc.training_runs == []
    assert svc.errors == []
    assert svc.surreal_ns == "cohezion"


def test_universe_genealogy_phase_1_extract_patterns(tmp_path):
    """phase_1_extract_patterns is pure (no git) and returns 7 patterns."""
    survey = UniverseGenealogySurvey(cohezion_root=tmp_path / "repo", output_dir=tmp_path / "out")
    summary = survey.phase_1_extract_patterns()

    assert summary["status"] == "extracted"
    assert summary["patterns_identified"] == 7
    pattern_names = [p["name"] for p in summary["patterns"]]
    assert any("Ouroboros" in n for n in pattern_names)
    assert any("HIHO" in n for n in pattern_names)


def test_universe_genealogy_dataclasses_construct():
    """UniverseEpoch and UniversePattern should be plain dataclasses."""
    epoch = UniverseEpoch(
        epoch_id="e1",
        epoch_number=1,
        name="genesis",
        description="initial",
        philosophical_question="why?",
        design_decision="HIHO",
        start_commit="aaa",
        end_commit="bbb",
        start_date="2025-11-01",
        end_date="2025-12-01",
    )
    pattern = UniversePattern(
        pattern_id="p1",
        pattern_number=1,
        name="Ouroboros",
        description="recursive",
        first_appearance_epoch=1,
        evidence_strength="strong",
        appears_in_modules=["compound"],
        appears_in_commits=["aaa"],
    )
    assert epoch.epoch_number == 1
    assert pattern.appears_in_modules == ["compound"]
