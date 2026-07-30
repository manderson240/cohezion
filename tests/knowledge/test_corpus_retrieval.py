"""V-model tests for KnowledgeCorpus and its wiring into KnowledgeMCP.search_knowledge.

Structural tests run offline. The discriminating behavioural test needs the live embedding
endpoint and is marked `integration`, because the property under test -- that semantic
retrieval finds passages substring matching CANNOT -- is meaningless without real embeddings.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from cohezion.knowledge.corpus import Chunk, KnowledgeCorpus, available_corpora


def _write_corpus(root, name, texts, vectors):
    root.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(vectors, dtype=np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
    np.save(root / f"{name}_vectors.npy", arr)
    (root / f"{name}_meta.json").write_text(
        json.dumps([{"text": t, "page": i} for i, t in enumerate(texts)])
    )


class TestStructural:
    def test_available_corpora_requires_both_files(self, tmp_path):
        """A vectors file with no meta is unusable and must not be advertised."""
        np.save(tmp_path / "orphan_vectors.npy", np.zeros((2, 4), dtype=np.float32))
        assert available_corpora(tmp_path) == []
        (tmp_path / "orphan_meta.json").write_text(json.dumps([{"text": "a"}, {"text": "b"}]))
        assert available_corpora(tmp_path) == ["orphan"]

    def test_length_mismatch_is_refused_not_truncated(self, tmp_path):
        """DISCRIMINATING: truncating to the shorter length would return text attributed to
        the WRONG vector -- silently wrong answers, worse than no answer."""
        np.save(tmp_path / "bad_vectors.npy", np.eye(3, dtype=np.float32))
        (tmp_path / "bad_meta.json").write_text(json.dumps([{"text": "only-one"}]))
        kc = KnowledgeCorpus(root=tmp_path)
        assert kc.load("bad") is False
        assert kc.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), corpora=["bad"]) == []

    def test_missing_corpus_returns_empty_not_raises(self, tmp_path):
        kc = KnowledgeCorpus(root=tmp_path / "nope")
        assert kc.load_all() == []
        assert kc.search(np.array([1.0, 0.0], dtype=np.float32)) == []

    def test_zero_query_vector_returns_empty(self, tmp_path):
        _write_corpus(tmp_path, "c", ["x", "y"], [[1, 0], [0, 1]])
        kc = KnowledgeCorpus(root=tmp_path)
        assert kc.search(np.zeros(2, dtype=np.float32)) == []

    def test_ranks_by_similarity_and_respects_threshold(self, tmp_path):
        """Nearest vector first; anything under min_similarity is dropped entirely."""
        _write_corpus(tmp_path, "c", ["east", "north"], [[1, 0], [0, 1]])
        kc = KnowledgeCorpus(root=tmp_path, min_similarity=0.5)
        hits = kc.search(np.array([0.99, 0.14], dtype=np.float32), limit=5)
        assert [h.text for h in hits] == ["east"], "orthogonal vector should fall below threshold"
        assert isinstance(hits[0], Chunk) and hits[0].meta.get("page") == 0

    def test_dimension_mismatch_is_skipped(self, tmp_path):
        _write_corpus(tmp_path, "c", ["x"], [[1, 0, 0]])
        kc = KnowledgeCorpus(root=tmp_path)
        assert kc.search(np.array([1.0, 0.0], dtype=np.float32)) == []

    def test_search_knowledge_calls_corpus_pass(self):
        """CONSUMPTION: the MCP tool must actually invoke the corpus search, not merely be
        able to. A producer with no reader is what this whole module exists to fix."""
        import inspect

        from cohezion.mcp.knowledge_server import KnowledgeMCP

        assert "_search_corpora" in inspect.getsource(KnowledgeMCP.search_knowledge)


@pytest.mark.integration
class TestSemanticBeatsSubstring:
    """The claim that justifies this module: retrieval that substring matching cannot do."""

    QUERY = "what bounds the distortion when projecting to lower dimensions"

    def test_finds_passage_sharing_no_query_words(self):
        from cohezion.mcp.knowledge_server import KnowledgeMCP

        hits = [
            r
            for r in KnowledgeMCP().search_knowledge(self.QUERY, limit=5)
            if r.get("type") == "corpus"
        ]
        if not hits:
            pytest.skip("no corpora on disk or :13305 offline")

        # DISCRIMINATING: the retrieved passage must NOT contain the query as a substring,
        # and must miss most of its content words -- otherwise substring search would have
        # found it too and the semantic pass earned nothing.
        top = hits[0]["snippet"].lower()
        assert self.QUERY.lower() not in top
        content_words = {"distortion", "projecting", "lower", "dimensions", "bounds"}
        overlap = sum(1 for w in content_words if w in top)
        assert overlap < len(content_words), (
            f"top hit shares {overlap}/{len(content_words)} query words — substring search "
            f"could plausibly have found this, so semantic retrieval is unproven here"
        )
