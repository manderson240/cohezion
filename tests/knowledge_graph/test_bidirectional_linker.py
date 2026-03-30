"""Tests for cohezion.knowledge_graph.bidirectional_linker.

Phase 3c coverage push.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cohezion.knowledge_graph.bidirectional_linker import (
    BidirectionalLink,
    KnowledgeGraph,
    LinkType,
    get_knowledge_graph,
)


class TestLinkType:
    """Tests for LinkType enum."""

    def test_all_types_exist(self):
        """Should define all expected link types."""
        assert LinkType.DOC_TO_DOC.value == "doc_to_doc"
        assert LinkType.DOC_TO_CODE.value == "doc_to_code"
        assert LinkType.SKILL_TO_CODE.value == "skill_to_code"
        assert LinkType.CODE_TO_CODE.value == "code_to_code"
        assert LinkType.CODE_TO_TEST.value == "code_to_test"
        assert LinkType.IMPLEMENTS.value == "implements"
        assert LinkType.REFERENCES.value == "references"
        assert LinkType.EXTENDS.value == "extends"
        assert LinkType.SUPERSEDES.value == "supersedes"


class TestBidirectionalLink:
    """Tests for BidirectionalLink dataclass."""

    def test_create_link(self):
        """Should create a link with deterministic ID."""
        link = BidirectionalLink.create(
            source="fileA.py",
            target="fileB.py",
            link_type=LinkType.CODE_TO_CODE,
        )
        assert link.source == "fileA.py"
        assert link.target == "fileB.py"
        assert link.link_type == LinkType.CODE_TO_CODE
        assert len(link.link_id) == 64  # SHA-256 hex

    def test_create_with_metadata(self):
        """Should store metadata."""
        link = BidirectionalLink.create(
            source="doc.md",
            target="code.py",
            link_type=LinkType.DOC_TO_CODE,
            metadata={"section": "Architecture"},
        )
        assert link.metadata["section"] == "Architecture"

    def test_bidirectional_id_symmetry(self):
        """A->B and B->A should produce same link_id."""
        id_ab = BidirectionalLink._generate_link_id("A", "B", LinkType.REFERENCES)
        id_ba = BidirectionalLink._generate_link_id("B", "A", LinkType.REFERENCES)
        assert id_ab == id_ba

    def test_different_types_different_id(self):
        """Same nodes but different types should have different IDs."""
        id_ref = BidirectionalLink._generate_link_id("A", "B", LinkType.REFERENCES)
        id_ext = BidirectionalLink._generate_link_id("A", "B", LinkType.EXTENDS)
        assert id_ref != id_ext

    def test_to_surreal(self):
        """Should serialize to SurrealDB record format."""
        link = BidirectionalLink.create(
            source="src.py",
            target="test.py",
            link_type=LinkType.CODE_TO_TEST,
        )
        surreal = link.to_surreal()
        assert surreal["id"].startswith("link:")
        assert surreal["source"] == "src.py"
        assert surreal["link_type"] == "code_to_test"
        assert "created_at" in surreal


class TestKnowledgeGraph:
    """Tests for KnowledgeGraph in-memory mode (no SurrealDB)."""

    @pytest.fixture()
    def kg(self, tmp_path):
        """Create KnowledgeGraph with tmp vault root, no SurrealDB client."""
        graph = KnowledgeGraph(vault_root=tmp_path / "vault")
        graph.client = None  # Simulate in-memory-only mode (no connect())
        return graph

    @pytest.mark.asyncio
    async def test_add_link(self, kg):
        """Should add link to in-memory cache."""
        link = await kg.add_link("A.py", "B.py", LinkType.CODE_TO_CODE)
        assert link.source == "A.py"
        assert link.link_id in kg._links

    @pytest.mark.asyncio
    async def test_get_links_by_source(self, kg):
        """Should find links where node is source."""
        await kg.add_link("A.py", "B.py", LinkType.CODE_TO_CODE)
        links = await kg.get_links("A.py")
        assert len(links) == 1
        assert links[0].target == "B.py"

    @pytest.mark.asyncio
    async def test_get_links_by_target(self, kg):
        """Should find links where node is target (bidirectional)."""
        await kg.add_link("A.py", "B.py", LinkType.CODE_TO_CODE)
        links = await kg.get_links("B.py")
        assert len(links) == 1
        assert links[0].source == "A.py"

    @pytest.mark.asyncio
    async def test_get_links_filter_by_type(self, kg):
        """Should filter links by type."""
        await kg.add_link("A.py", "B.py", LinkType.CODE_TO_CODE)
        await kg.add_link("A.py", "test_A.py", LinkType.CODE_TO_TEST)
        links = await kg.get_links("A.py", link_type=LinkType.CODE_TO_TEST)
        assert len(links) == 1
        assert links[0].link_type == LinkType.CODE_TO_TEST

    @pytest.mark.asyncio
    async def test_get_links_empty(self, kg):
        """Should return empty list for unknown node."""
        links = await kg.get_links("nonexistent")
        assert links == []

    @pytest.mark.asyncio
    async def test_get_neighbors_depth1(self, kg):
        """Should return immediate neighbors."""
        await kg.add_link("A", "B", LinkType.REFERENCES)
        await kg.add_link("A", "C", LinkType.REFERENCES)
        neighbors = await kg.get_neighbors("A", depth=1)
        assert neighbors == {"B", "C"}

    @pytest.mark.asyncio
    async def test_get_neighbors_depth2(self, kg):
        """Should return 2-hop neighbors."""
        await kg.add_link("A", "B", LinkType.REFERENCES)
        await kg.add_link("B", "C", LinkType.REFERENCES)
        neighbors = await kg.get_neighbors("A", depth=2)
        assert "B" in neighbors
        assert "C" in neighbors

    @pytest.mark.asyncio
    async def test_get_neighbors_excludes_self(self, kg):
        """Should not include the queried node."""
        await kg.add_link("A", "B", LinkType.REFERENCES)
        neighbors = await kg.get_neighbors("A")
        assert "A" not in neighbors

    @pytest.mark.asyncio
    async def test_find_path_direct(self, kg):
        """Should find direct path."""
        await kg.add_link("A", "B", LinkType.REFERENCES)
        path = await kg.find_path("A", "B")
        assert path == ["A", "B"]

    @pytest.mark.asyncio
    async def test_find_path_multi_hop(self, kg):
        """Should find multi-hop path."""
        await kg.add_link("A", "B", LinkType.REFERENCES)
        await kg.add_link("B", "C", LinkType.REFERENCES)
        path = await kg.find_path("A", "C")
        assert path == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_find_path_same_node(self, kg):
        """Should return single node for self-path."""
        path = await kg.find_path("A", "A")
        assert path == ["A"]

    @pytest.mark.asyncio
    async def test_find_path_no_connection(self, kg):
        """Should return None when no path exists."""
        await kg.add_link("A", "B", LinkType.REFERENCES)
        path = await kg.find_path("A", "Z")
        assert path is None

    @pytest.mark.asyncio
    async def test_persist_and_load_vault(self, kg, tmp_path):
        """Should round-trip links through vault JSON files."""
        await kg.add_link("X.py", "Y.py", LinkType.CODE_TO_CODE, metadata={"reason": "test"})

        # Create a new graph and load from same vault
        kg2 = KnowledgeGraph(vault_root=tmp_path / "vault")
        kg2.client = None
        count = await kg2.load_from_vault()
        assert count == 1
        links = await kg2.get_links("X.py")
        assert len(links) == 1
        assert links[0].metadata["reason"] == "test"

    @pytest.mark.asyncio
    async def test_load_from_empty_vault(self, tmp_path):
        """Should return 0 when vault has no links."""
        kg = KnowledgeGraph(vault_root=tmp_path / "empty_vault")
        kg.client = None
        count = await kg.load_from_vault()
        assert count == 0

    @pytest.mark.asyncio
    async def test_idempotent_links(self, kg):
        """Adding same link twice should produce same link_id (overwrite, not duplicate)."""
        link1 = await kg.add_link("A", "B", LinkType.REFERENCES)
        link2 = await kg.add_link("A", "B", LinkType.REFERENCES)
        assert link1.link_id == link2.link_id
        links = await kg.get_links("A")
        assert len(links) == 1


class TestGetKnowledgeGraph:
    """Tests for singleton accessor."""

    def test_returns_instance(self):
        """Should return a KnowledgeGraph instance."""
        import cohezion.knowledge_graph.bidirectional_linker as mod
        mod._knowledge_graph = None
        kg = get_knowledge_graph()
        assert isinstance(kg, KnowledgeGraph)

    def test_singleton_same_instance(self):
        """Should return the same instance."""
        import cohezion.knowledge_graph.bidirectional_linker as mod
        mod._knowledge_graph = None
        kg1 = get_knowledge_graph()
        kg2 = get_knowledge_graph()
        assert kg1 is kg2
        # Cleanup
        mod._knowledge_graph = None
