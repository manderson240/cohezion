"""Tests for the Vault Knowledge Graph parser and API endpoints."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from cohezion.worldviews.vault_graph import (
    GraphEdge,
    GraphNode,
    VaultGraph,
    _extract_wikilinks,
    _parse_frontmatter,
    parse_cortex,
)


class TestFrontmatterParsing:
    """Test YAML frontmatter extraction."""

    def test_valid_frontmatter(self):
        content = dedent("""\
            ---
            title: "Test Note"
            tags: [concept, test]
            aspect: knower
            neural:
              activation: 0.8
              stage: mature
              synapse_in: 5
              synapse_out: 3
            ---

            # Content here
        """)
        fm = _parse_frontmatter(content)
        assert fm["title"] == "Test Note"
        assert fm["tags"] == ["concept", "test"]
        assert fm["neural"]["activation"] == 0.8

    def test_no_frontmatter(self):
        fm = _parse_frontmatter("# Just a heading\n\nSome content.")
        assert fm == {}

    def test_malformed_frontmatter(self):
        fm = _parse_frontmatter("---\ninvalid: [unclosed\n---\n")
        # Should not raise, returns empty or partial
        assert isinstance(fm, dict)

    def test_empty_content(self):
        fm = _parse_frontmatter("")
        assert fm == {}


class TestWikilinkExtraction:
    """Test [[wikilink]] regex parsing."""

    def test_simple_wikilink(self):
        links = _extract_wikilinks("See [[target-note]] for details.")
        assert links == ["target-note"]

    def test_aliased_wikilink(self):
        links = _extract_wikilinks("See [[target-note|display text]] here.")
        assert links == ["target-note"]

    def test_multiple_wikilinks(self):
        content = "Links to [[note-a]], [[note-b]], and [[note-c|alias]]."
        links = _extract_wikilinks(content)
        assert links == ["note-a", "note-b", "note-c"]

    def test_no_wikilinks(self):
        links = _extract_wikilinks("No links here, just plain text.")
        assert links == []

    def test_nested_brackets_not_matched(self):
        links = _extract_wikilinks("Not a link: [regular](url)")
        assert links == []


class TestGraphNode:
    """Test GraphNode dataclass."""

    def test_to_dict(self):
        node = GraphNode(
            slug="test-node",
            title="Test Node",
            tags=("concept", "test"),
            aspect="knower",
            activation=0.9,
            stage="mature",
            synapse_in=10,
            synapse_out=5,
        )
        d = node.to_dict()
        assert d["slug"] == "test-node"
        assert d["tags"] == ["concept", "test"]
        assert d["activation"] == 0.9


class TestGraphEdge:
    """Test GraphEdge dataclass."""

    def test_to_dict(self):
        edge = GraphEdge(source="note-a", target="note-b")
        d = edge.to_dict()
        assert d == {"source": "note-a", "target": "note-b"}


class TestVaultGraph:
    """Test VaultGraph aggregate methods."""

    def _sample_graph(self) -> VaultGraph:
        nodes = [
            GraphNode("a", "Note A", ("concept", "indigenous-cosmology"), "knower", 0.9, "mature", 5, 3),
            GraphNode("b", "Note B", ("concept", "TOE"), "thinker", 0.7, "growing", 3, 2),
            GraphNode("c", "Note C", ("pattern",), "doer", 0.5, "seed", 1, 1),
            GraphNode("d", "Note D", ("concept", "cross-tradition"), "knower", 0.8, "mature", 4, 2),
        ]
        edges = [
            GraphEdge("a", "b"),
            GraphEdge("b", "d"),
            GraphEdge("a", "c"),
            GraphEdge("c", "a"),
        ]
        return VaultGraph(nodes=nodes, edges=edges)

    def test_node_count(self):
        g = self._sample_graph()
        assert g.node_count == 4

    def test_edge_count(self):
        g = self._sample_graph()
        assert g.edge_count == 4

    def test_clusters(self):
        g = self._sample_graph()
        clusters = g.get_clusters()
        aspects = {c["aspect"] for c in clusters}
        assert "knower" in aspects
        assert "thinker" in aspects
        assert "doer" in aspects

    def test_tradition_subgraph(self):
        g = self._sample_graph()
        sub = g.get_tradition_subgraph()
        # Only a, b, d have tradition-related tags
        assert sub["node_count"] == 3
        # Only a->b and b->d are within the subgraph (a->c excluded, c not in subgraph)
        assert sub["edge_count"] == 2

    def test_to_dict(self):
        g = self._sample_graph()
        d = g.to_dict()
        assert d["node_count"] == 4
        assert d["edge_count"] == 4
        assert "clusters" in d
        assert len(d["nodes"]) == 4

    def test_empty_graph(self):
        g = VaultGraph()
        assert g.node_count == 0
        assert g.edge_count == 0
        assert g.to_dict()["clusters"] == []


class TestParseCortex:
    """Test cortex directory parsing with synthetic test data."""

    def test_parse_synthetic_cortex(self, tmp_path: Path):
        # Create synthetic cortex notes
        note_a = tmp_path / "note-a.md"
        note_a.write_text(
            dedent("""\
            ---
            title: "Note A"
            tags: [concept]
            aspect: knower
            neural:
              activation: 0.8
              stage: mature
              synapse_in: 3
              synapse_out: 2
            ---

            # Note A

            Links to [[note-b]] and [[note-c]].
        """)
        )

        note_b = tmp_path / "note-b.md"
        note_b.write_text(
            dedent("""\
            ---
            title: "Note B"
            tags: [pattern]
            aspect: doer
            ---

            # Note B

            Back-link to [[note-a]].
        """)
        )

        note_c = tmp_path / "note-c.md"
        note_c.write_text(
            dedent("""\
            ---
            title: "Note C"
            tags: [concept, indigenous-cosmology]
            aspect: thinker
            ---

            # Note C

            Standalone note with link to [[nonexistent-note]].
        """)
        )

        graph = parse_cortex(cortex_dir=tmp_path)

        assert graph.node_count == 3
        # note-a -> note-b, note-a -> note-c, note-b -> note-a
        # note-c -> nonexistent-note is excluded (not a known slug)
        assert graph.edge_count == 3

        slugs = {n.slug for n in graph.nodes}
        assert slugs == {"note-a", "note-b", "note-c"}

    def test_parse_empty_directory(self, tmp_path: Path):
        graph = parse_cortex(cortex_dir=tmp_path)
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_parse_nonexistent_directory(self, tmp_path: Path):
        graph = parse_cortex(cortex_dir=tmp_path / "does-not-exist")
        assert graph.node_count == 0

    def test_deduplicates_edges(self, tmp_path: Path):
        note = tmp_path / "note-a.md"
        note.write_text(
            dedent("""\
            ---
            title: "Note A"
            tags: []
            ---

            Links to [[note-b]] twice: [[note-b]] and [[note-b|alias]].
        """)
        )
        note_b = tmp_path / "note-b.md"
        note_b.write_text("---\ntitle: Note B\ntags: []\n---\n# B\n")

        graph = parse_cortex(cortex_dir=tmp_path)
        edges_a_to_b = [e for e in graph.edges if e.source == "note-a" and e.target == "note-b"]
        assert len(edges_a_to_b) == 1

    def test_self_links_excluded(self, tmp_path: Path):
        note = tmp_path / "note-a.md"
        note.write_text("---\ntitle: A\ntags: []\n---\n[[note-a]] self-link\n")

        graph = parse_cortex(cortex_dir=tmp_path)
        assert graph.edge_count == 0


class TestLiveVaultGraph:
    """Test parsing the real vault cortex (if available)."""

    def test_live_cortex_parses(self):
        """Parse the live cortex — should produce a non-trivial graph."""
        cortex_dir = Path.home() / "vaults" / "cohezion-vault" / "cortex"
        if not cortex_dir.is_dir():
            pytest.skip("Vault cortex not available")

        graph = parse_cortex(cortex_dir=cortex_dir)
        assert graph.node_count > 100
        assert graph.edge_count > 50

    def test_live_tradition_subgraph(self):
        """The tradition subgraph should contain the 16 tradition notes."""
        cortex_dir = Path.home() / "vaults" / "cohezion-vault" / "cortex"
        if not cortex_dir.is_dir():
            pytest.skip("Vault cortex not available")

        graph = parse_cortex(cortex_dir=cortex_dir)
        sub = graph.get_tradition_subgraph()
        assert sub["node_count"] >= 15
