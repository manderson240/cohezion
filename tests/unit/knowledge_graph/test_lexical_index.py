"""Tests for BM25 lexical retrieval and reciprocal rank fusion.

The load-bearing test here is ``TestHybridBeatsDenseOnly``: it asserts both that
fusion surfaces a rare exact-token match AND that the same corpus fails when the
lexical ranking is removed. Without that second assertion the test would pass
against an implementation that ignores BM25 entirely, which is the exact
"consumption invariant vs declaration" failure this repo keeps hitting.

Mutation-verified 2026-08-08: 7/7 mutants killed (negative IDF, underscore
tokenisation, stale document frequencies, doc_id ordering, ignored RRF weights,
dropped length normalisation, dropped candidate filter).
"""

from __future__ import annotations

import pytest

from cohezion.knowledge_graph.lexical_index import (
    BM25Index,
    reciprocal_rank_fusion,
    tokenize,
)


pytestmark = pytest.mark.unit


class TestTokenize:
    def test_lowercases(self) -> None:
        assert tokenize("Hello WORLD") == ["hello", "world"]

    def test_keeps_underscores_inside_identifiers(self) -> None:
        # An identifier must survive as ONE token; splitting it into "score",
        # "papers", "batch" would make it indistinguishable from prose.
        assert tokenize("_score_papers_batch") == ["_score_papers_batch"]

    def test_splits_on_punctuation(self) -> None:
        assert tokenize("a.b-c") == ["a", "b", "c"]

    def test_empty_string(self) -> None:
        assert tokenize("") == []


class TestBM25Basics:
    def test_empty_index(self) -> None:
        idx = BM25Index()
        assert len(idx) == 0
        assert idx.avg_doc_len == 0.0
        assert idx.search("anything") == []
        assert idx.score("anything", "missing") == 0.0

    def test_avg_doc_len(self) -> None:
        idx = BM25Index()
        idx.add("a", "one two")  # 2 tokens
        idx.add("b", "one two three four")  # 4 tokens
        assert idx.avg_doc_len == 3.0

    def test_idf_is_non_negative_for_ubiquitous_term(self) -> None:
        # A term in EVERY document must not earn a negative weight; the raw
        # Robertson IDF goes negative above 50% document frequency.
        idx = BM25Index()
        for i in range(5):
            idx.add(f"d{i}", "common term here")
        assert idx.idf("common") >= 0.0

    def test_rare_term_outweighs_common_term(self) -> None:
        idx = BM25Index()
        for i in range(20):
            idx.add(f"d{i}", "the quick brown fox")
        idx.add("rare", "the quick brown fox zzqqxx")
        assert idx.idf("zzqqxx") > idx.idf("quick")

    def test_readd_replaces_and_keeps_df_consistent(self) -> None:
        idx = BM25Index()
        idx.add("a", "alpha beta")
        idx.add("a", "gamma")
        assert len(idx) == 1
        # "alpha" was replaced away, so nothing should match it any more.
        assert idx.search("alpha") == []
        assert [d for d, _ in idx.search("gamma")] == ["a"]

    def test_replace_restores_idf_of_the_removed_term(self) -> None:
        # Membership alone is not enough: dropping a document must also lower
        # that term's document frequency, which RAISES its IDF. A replace that
        # forgets to decrement leaves the weight silently wrong.
        idx = BM25Index()
        idx.add("a", "alpha")
        idx.add("b", "alpha")
        before = idx.idf("alpha")
        idx.add("a", "gamma")  # "alpha" now appears in 1 doc, not 2
        assert idx.idf("alpha") > before

    def test_search_returns_empty_for_unmatched_query(self) -> None:
        idx = BM25Index()
        idx.add("a", "alpha beta")
        assert idx.search("nothingmatcheshere") == []

    def test_ranks_by_relevance_not_by_doc_id(self) -> None:
        # "aaa_low" sorts FIRST alphabetically but is the WEAKER match, so an
        # implementation that orders by doc_id instead of score gets this wrong.
        idx = BM25Index()
        idx.add("aaa_low", "target " + "filler " * 40)
        idx.add("zzz_high", "target target target target target")
        assert next(d for d, _ in idx.search("target")) == "zzz_high"

    def test_shorter_document_wins_at_equal_term_frequency(self) -> None:
        # Same term frequency (1), different lengths. Only length normalisation
        # separates them; without it they tie and the order becomes arbitrary.
        idx = BM25Index()
        idx.add("short", "target")
        idx.add("long", "target " + "padding " * 60)
        assert next(d for d, _ in idx.search("target")) == "short"

    def test_search_respects_top_k(self) -> None:
        idx = BM25Index()
        for i in range(10):
            idx.add(f"d{i}", "shared token")
        assert len(idx.search("shared", top_k=3)) == 3

    def test_ranking_is_deterministic_on_ties(self) -> None:
        idx = BM25Index()
        for i in range(5):
            idx.add(f"d{i}", "identical text")
        first = idx.search("identical")
        for _ in range(5):
            assert idx.search("identical") == first


class TestReciprocalRankFusion:
    def test_empty(self) -> None:
        assert reciprocal_rank_fusion([]) == []

    def test_single_ranking_preserves_order(self) -> None:
        fused = reciprocal_rank_fusion([["a", "b", "c"]])
        assert [d for d, _ in fused] == ["a", "b", "c"]

    def test_agreement_reinforces(self) -> None:
        # "b" is 2nd in both lists; "a" and "c" are 1st in one and absent in
        # the other. Consistent mid-rank should beat inconsistent top-rank.
        fused = reciprocal_rank_fusion([["a", "b"], ["c", "b"]])
        assert fused[0][0] == "b"

    def test_weights_shift_the_winner(self) -> None:
        rankings = [["a", "b"], ["b", "a"]]
        equal = reciprocal_rank_fusion(rankings)
        weighted = reciprocal_rank_fusion(rankings, weights=[0.0, 1.0])
        # With the first ranker zeroed out, the second ranker's top must win.
        assert weighted[0][0] == "b"
        assert equal[0][0] == "a"  # tie broken on doc_id

    def test_mismatched_weights_raise(self) -> None:
        with pytest.raises(ValueError, match="weights length"):
            reciprocal_rank_fusion([["a"], ["b"]], weights=[1.0])

    def test_respects_top_k(self) -> None:
        fused = reciprocal_rank_fusion([["a", "b", "c", "d"]], top_k=2)
        assert len(fused) == 2


# Corpus where a rare exact token is buried in a document that is, on topic,
# about something else entirely. This is the case dense retrieval loses.
_CORPUS = {
    "vec1": "vector similarity search using cosine distance over dense embeddings",
    "vec2": "approximate nearest neighbour indexes such as HNSW for embedding search",
    "vec3": "semantic retrieval with transformer sentence embeddings and reranking",
    "vec4": "chunking strategies for embedding documents before vector indexing",
    # Topically unrelated to retrieval, but holds the literal token.
    "ops1": "runbook for the nightly batch job; on failure the process emits "
    "error code E2140 and the operator must drain the queue",
}

# A dense retriever ranks by topical similarity, so for the query below it
# surfaces the retrieval-flavoured documents and puts the runbook LAST.
_DENSE_RANKING = ["vec1", "vec2", "vec3", "vec4", "ops1"]


class TestHybridBeatsDenseOnly:
    """The reason this module exists."""

    def test_bm25_finds_the_rare_token(self) -> None:
        idx = BM25Index()
        idx.add_many(_CORPUS)
        assert [d for d, _ in idx.search("E2140")] == ["ops1"]

    def test_fusion_surfaces_what_dense_buried(self) -> None:
        idx = BM25Index()
        idx.add_many(_CORPUS)
        lexical = [d for d, _ in idx.search("E2140")]

        fused = reciprocal_rank_fusion([_DENSE_RANKING, lexical])
        assert fused[0][0] == "ops1", (
            "hybrid fusion must promote the exact-token match above the "
            "topically-similar but wrong documents"
        )

    def test_dense_only_FAILS_the_same_query(self) -> None:
        """Discriminator: proves the previous test measures the mechanism.

        If this assertion ever flips, the corpus stopped being a real test of
        hybrid retrieval and ``test_fusion_surfaces_what_dense_buried`` would
        pass even against an implementation that ignores BM25.
        """
        dense_only = reciprocal_rank_fusion([_DENSE_RANKING])
        assert dense_only[0][0] != "ops1"
        assert dense_only[0][0] == "vec1"

    def test_fusion_keeps_dense_wins_when_lexical_is_silent(self) -> None:
        # A purely semantic query has no rare token to latch onto; BM25 returns
        # nothing and fusion must not degrade the dense ordering.
        idx = BM25Index()
        idx.add_many(_CORPUS)
        lexical = [d for d, _ in idx.search("zzzznomatch")]
        assert lexical == []
        fused = reciprocal_rank_fusion([_DENSE_RANKING, lexical])
        assert [d for d, _ in fused] == _DENSE_RANKING
