"""Lexical (BM25) retrieval and rank fusion — the missing half of hybrid search.

``GraphRAGEngine.hybrid_search`` fuses *vector + graph*. It does not do lexical
matching at all, so a query naming a rare exact token (an identifier, an error
code, a flag) can miss: embeddings smooth rare tokens toward their neighbourhood
and a dense-only ranker has no signal that the literal string was present.

This module supplies the lexical ranker and a fusion primitive so dense and
sparse rankings can be combined.

Okapi BM25 (Robertson & Zaragoza, 2009)::

    score(D, Q) = sum_i IDF(q_i) * (f_i * (k1 + 1))
                               / (f_i + k1 * (1 - b + b * |D| / avgdl))

    IDF(q_i)   = ln( (N - n_i + 0.5) / (n_i + 0.5) + 1 )

The ``+ 1`` inside the log is the standard non-negative variant: without it a
term appearing in more than half the corpus earns a negative IDF and actively
penalises documents that contain it.

Reciprocal Rank Fusion (Cormack et al., 2009) combines rankings by *rank* rather
than score, which avoids having to calibrate a cosine similarity against a BM25
score — they are not on a common scale and any fixed alpha blend silently
depends on corpus statistics.

Pure standard library: no new dependency.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


__all__ = ["BM25Index", "reciprocal_rank_fusion", "tokenize"]

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

# BM25 free parameters. k1 controls term-frequency saturation, b controls how
# strongly document length normalises. These are the standard defaults.
_K1 = 1.5
_B = 0.75

# RRF damping. 60 is the value from the original paper; it flattens the
# contribution of top ranks so one ranker cannot dominate on a single hit.
_RRF_K = 60


def tokenize(text: str) -> list[str]:
    """Lowercase word/underscore tokens.

    ``_`` is kept inside tokens so identifiers such as ``_score_papers_batch``
    survive as a single unit rather than fragmenting into common English words.
    """
    return _TOKEN_RE.findall(text.lower())


@dataclass
class BM25Index:
    """In-memory Okapi BM25 index.

    Parameters
    ----------
    k1 : float
        Term-frequency saturation.
    b : float
        Document-length normalisation strength.

    Notes
    -----
    Documents are held in memory. This is sized for a vault-scale corpus
    (thousands of notes), not a web index.
    """

    k1: float = _K1
    b: float = _B
    _doc_len: dict[str, int] = field(default_factory=dict, repr=False)
    _tf: dict[str, Counter[str]] = field(default_factory=dict, repr=False)
    _df: Counter[str] = field(default_factory=Counter, repr=False)

    def __len__(self) -> int:
        return len(self._doc_len)

    @property
    def avg_doc_len(self) -> float:
        """Mean document length in tokens; 0.0 for an empty index."""
        if not self._doc_len:
            return 0.0
        return sum(self._doc_len.values()) / len(self._doc_len)

    def add(self, doc_id: str, text: str) -> None:
        """Add or replace a document.

        Re-adding an existing ``doc_id`` replaces it, decrementing the previous
        document frequencies first so the index stays consistent.
        """
        if doc_id in self._tf:
            for term in self._tf[doc_id]:
                self._df[term] -= 1
                if self._df[term] <= 0:
                    del self._df[term]

        toks = tokenize(text)
        tf = Counter(toks)
        self._tf[doc_id] = tf
        self._doc_len[doc_id] = len(toks)
        for term in tf:
            self._df[term] += 1

    def add_many(self, docs: dict[str, str]) -> None:
        """Add several documents at once."""
        for doc_id, text in docs.items():
            self.add(doc_id, text)

    def idf(self, term: str) -> float:
        """Non-negative inverse document frequency for ``term``."""
        n = len(self._doc_len)
        if n == 0:
            return 0.0
        df = self._df.get(term, 0)
        return math.log((n - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, query: str, doc_id: str) -> float:
        """BM25 score of one document against ``query``."""
        tf = self._tf.get(doc_id)
        if tf is None:
            return 0.0
        avgdl = self.avg_doc_len
        if avgdl == 0.0:
            return 0.0
        dl = self._doc_len[doc_id]
        total = 0.0
        for term in tokenize(query):
            f = tf.get(term, 0)
            if f == 0:
                continue
            denom = f + self.k1 * (1.0 - self.b + self.b * dl / avgdl)
            total += self.idf(term) * (f * (self.k1 + 1.0)) / denom
        return total

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Rank documents by BM25, descending.

        Only documents sharing at least one query term are considered, so an
        unmatched query returns an empty list rather than an arbitrary ordering
        of zero-scored documents.
        """
        terms = set(tokenize(query))
        if not terms or not self._doc_len:
            return []
        candidates = {d for d, tf in self._tf.items() if terms & tf.keys()}
        scored = [(d, self.score(query, d)) for d in candidates]
        # No score>0 filter: every candidate shares a term, and IDF is
        # non-negative by construction, so a candidate's score is always > 0.
        # Sort by score desc, then doc_id asc so ties are deterministic.
        scored.sort(key=lambda kv: (-kv[1], kv[0]))
        return scored[:top_k]


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    top_k: int = 10,
    k: int = _RRF_K,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """Fuse several ranked ID lists into one.

    Parameters
    ----------
    rankings : list[list[str]]
        One ranked list of document IDs per retriever, best first.
    top_k : int
        Number of fused results to return.
    k : int
        RRF damping constant.
    weights : list[float] | None
        Optional per-ranker weight, same length as ``rankings``. Defaults to
        equal weighting.

    Returns
    -------
    list[tuple[str, float]]
        ``(doc_id, fused_score)`` descending. Ties break on ``doc_id`` so the
        ordering is deterministic.

    Notes
    -----
    Fusion is on *rank*, not score, so a document ranked highly by one retriever
    and missed entirely by another still surfaces. That asymmetry is the point:
    it is what lets a rare exact-token match beat a uniformly mediocre dense
    ranking.
    """
    if not rankings:
        return []
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError(f"weights length {len(weights)} != rankings length {len(rankings)}")

    fused: dict[str, float] = {}
    for ranking, weight in zip(rankings, weights, strict=True):
        for rank, doc_id in enumerate(ranking, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + weight / (k + rank)

    out = sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))
    return out[:top_k]
