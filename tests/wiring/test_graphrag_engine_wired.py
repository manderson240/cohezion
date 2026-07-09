"""Discriminating test for the wiring-sweep edge: knowledge_graph → graphrag_engine (2026-06-06).

`graphrag_engine` was a genuine Class-A production orphan in knowledge_graph/: its public
surface (GraphRAGEngine / GraphRAGResponse / RetrievalResult) had ZERO literal import edges
anywhere in src/ or scripts/. The lone non-test reference — `"cohezion.knowledge_graph.
graphrag_engine"` in `agents/specialists/surreal_dba.py`'s `canonical_modules` tuple — is a
STRING literal (importlib-on-a-string / metadata), invisible to static import-graph analysis.
Wired non-destructively via a guarded `cohezion.knowledge_graph` __init__ re-export.

Falsifiable: fails if the static edge is removed. Each name must resolve FROM the package,
be the source module's own object (identity, not a lookalike), and appear in __all__. The
both-import-order check guarantees the edge holds regardless of which module loads first.
"""

from __future__ import annotations


_NAMES = ("GraphRAGEngine", "GraphRAGResponse", "RetrievalResult")


def test_graphrag_engine_reexported_from_knowledge_graph() -> None:
    import cohezion.knowledge_graph as kg
    import cohezion.knowledge_graph.graphrag_engine as src

    for name in _NAMES:
        assert hasattr(kg, name), f"knowledge_graph.{name} unreachable — wiring edge missing"
        assert getattr(kg, name) is getattr(src, name), f"{name} is not the source object"
        assert name in kg.__all__, f"{name} missing from knowledge_graph.__all__"


def test_edge_holds_when_submodule_imported_first() -> None:
    # Both-import-order check: the re-export must bind even if the submodule loads first.
    # Order is deliberate (submodule before package) — keep it; do not let isort re-sort.
    import cohezion.knowledge_graph.graphrag_engine as src  # noqa: I001
    import cohezion.knowledge_graph as kg

    assert kg.GraphRAGEngine is src.GraphRAGEngine
