"""Item 115: Adaptive retrieval-gating (Thread P).

``should_retrieve(query, *, score_fn, threshold)`` decides whether to invoke
the semantic recall pipeline for a given query, rather than ALWAYS retrieving.

Cohezion's semantic cache checks recall on EVERY call (CA1 invariant).  Nothing
currently asks "is retrieval even useful for THIS query?" — wasting recall on
greetings, arithmetic, and other self-contained queries that a model answers from
parametric knowledge, and potentially adding stale / misleading context.

This gating predicate operationalises the "agentic RAG decides WHEN to retrieve"
technique (from the Marktechpost agentic-RAG tutorial, batch distilled
2026-06-06; ``docs/research/TUTORIAL_DISTILLATION_2026-06-06.md``).

Pure (injected ``score_fn``; no live recall, no network calls under pytest).
Report-only — never invokes retrieval itself; the caller decides whether to act.

Falsifiable checks (item 115)
------------------------------
- knowledge-seeking query → ``True``.
- self-contained query ("hello"/"2+2") → ``False``.
- empty query → ``False`` (no retrieval benefit).
- score == threshold → ``True`` (inclusive ``>=`` boundary).
- score_fn raising → ``False`` (fail-soft, never propagates to caller).
"""

from __future__ import annotations

from collections.abc import Callable


# Default threshold: retrieval is beneficial when score >= 0.5.
# Calibrated to the cohezion semantic-cache encoder thresholds (CA1/exp_OOOO2):
#   0.58 for nomic-embed 768D, 0.45 for FLUME VAE 256D, 0.80 for sentence-transformers.
# A value of 0.5 is a safe mid-point for any encoder.
_DEFAULT_THRESHOLD: float = 0.5

# Callable type: (query: str) -> float, returns a retrieval-benefit score in [0, 1].
ScoreFn = Callable[[str], float]


def should_retrieve(
    query: str,
    *,
    score_fn: ScoreFn,
    threshold: float = _DEFAULT_THRESHOLD,
) -> bool:
    """Decide whether to invoke recall for ``query`` (item 115, Thread P).

    Returns ``True`` iff ``score_fn(query) >= threshold`` — meaning the query is
    likely to benefit from retrieved context.  Returns ``False`` for empty queries,
    when the score is below the threshold, or when ``score_fn`` raises (fail-soft).

    Args:
        query:
            The user or system query to evaluate.
        score_fn:
            Injectable callable ``(query: str) -> float`` that estimates how much
            retrieval would benefit answering ``query``.  The score should be in
            ``[0, 1]`` (though values outside this range are accepted — only the
            ``>= threshold`` comparison is applied).  Called exactly once with the
            unmodified ``query`` string (no truncation / preprocessing in this
            function — that is the caller's responsibility if needed).
        threshold:
            Inclusive lower bound for retrieval.  Queries with
            ``score_fn(query) >= threshold`` are retrieved; those below are
            skipped.  Defaults to :data:`_DEFAULT_THRESHOLD` (0.5).

    Returns:
        ``True`` → invoke recall; ``False`` → skip retrieval.

    Pure (injected ``score_fn``; no I/O, no clock reads, no external state).
    Fail-soft: if ``score_fn`` raises, returns ``False`` without propagating.
    """
    # Gate 1: empty query never benefits from retrieval.
    if not query:
        return False

    # Gate 2: score function result.
    try:
        score: float = score_fn(query)
    except Exception:
        return False

    return score >= threshold
