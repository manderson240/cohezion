"""Discriminating tests for should_retrieve (item 115, 2026-06-08).

``should_retrieve(query, *, score_fn, threshold)`` returns True iff the query is
knowledge-seeking (score_fn returns a score >= threshold). Returns False for
self-contained queries (low score), empty queries, or when score_fn raises.

Discriminating tests — each kills a plausible wrong implementation:

  1. High-benefit query → True (kills "always return False").
  2. Low-benefit query → False (kills "always return True" = the current always-retrieve
     pattern that item 115 is fixing).
  3. Empty query → False (no retrieval benefit for empty input).
  4. Exact-threshold boundary → True (score == threshold → retrieve; strict >= not >).
     Kills an impl using strict >  for the threshold comparison.
  5. Just-below-threshold → False (kills an impl using >=  from the wrong side).
  6. score_fn raising → False (fail-soft, never propagates exception into the caller).
  7. Injected score_fn is called with the exact query (no truncation/transform).
"""

from __future__ import annotations

from cohezion.compound.adaptive_retrieval import should_retrieve


# ---------------------------------------------------------------------------
# Stub score functions
# ---------------------------------------------------------------------------


def _high_score(query: str) -> float:
    """Always returns 0.9 — represents a knowledge-seeking query."""
    return 0.9


def _low_score(query: str) -> float:
    """Always returns 0.1 — represents a self-contained query."""
    return 0.1


def _threshold_exact(query: str) -> float:
    """Returns exactly 0.5 — the default threshold."""
    return 0.5


def _just_below(query: str) -> float:
    """Returns 0.499 — just below the 0.5 threshold."""
    return 0.499


def _raising(query: str) -> float:
    """Always raises RuntimeError — simulates a broken scorer."""
    raise RuntimeError("score_fn failed")


_SEEN_QUERY: list[str] = []


def _capture_query(query: str) -> float:
    """Records the query it receives; returns 0.9 (retrieve=True)."""
    _SEEN_QUERY.clear()
    _SEEN_QUERY.append(query)
    return 0.9


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_high_benefit_query_retrieves() -> None:
    """A knowledge-seeking query (score=0.9 > threshold=0.5) → retrieve=True.

    Kills an impl that always returns False.
    """
    result = should_retrieve("what did we decide about routing?", score_fn=_high_score)
    assert result is True, "high-benefit query must → retrieve=True"


def test_low_benefit_query_skips() -> None:
    """A self-contained query (score=0.1 < threshold=0.5) → retrieve=False.

    Kills the current always-retrieve pattern (the bug item 115 fixes).
    """
    result = should_retrieve("hello", score_fn=_low_score)
    assert result is False, "self-contained query must → retrieve=False"


def test_empty_query_skips() -> None:
    """Empty query string → retrieve=False (no retrieval benefit for empty input)."""
    result = should_retrieve("", score_fn=_high_score)
    assert result is False, "empty query must → retrieve=False"


def test_exact_threshold_retrieves() -> None:
    """score == threshold → retrieve=True (threshold is inclusive, >= not >).

    Kills an impl that uses strict > for the comparison.
    """
    result = should_retrieve("threshold test", score_fn=_threshold_exact, threshold=0.5)
    assert result is True, (
        "score==threshold must → retrieve=True (threshold is inclusive >= boundary)"
    )


def test_just_below_threshold_skips() -> None:
    """score just below threshold → retrieve=False.

    Kills an impl using the wrong inequality direction.
    """
    result = should_retrieve("borderline query", score_fn=_just_below, threshold=0.5)
    assert result is False, "score=0.499 < threshold=0.5 must → retrieve=False"


def test_raising_score_fn_fails_soft() -> None:
    """A score_fn that raises must be handled gracefully → retrieve=False.

    Kills an impl that propagates score_fn exceptions to the caller.
    """
    # Must not raise; must return False.
    result = should_retrieve("some query", score_fn=_raising)
    assert result is False, "score_fn raising must degrade gracefully → False"


def test_score_fn_receives_exact_query() -> None:
    """score_fn is called with the unmodified query string.

    Kills an impl that truncates, strips, or transforms the query before scoring.
    """
    query = "What did we decide about FLUME VAE kl_weight?"
    _ = should_retrieve(query, score_fn=_capture_query)
    assert len(_SEEN_QUERY) == 1
    assert _SEEN_QUERY[0] == query, f"score_fn must receive exact query; got {_SEEN_QUERY[0]!r}"


def test_default_threshold_is_half() -> None:
    """The default threshold is 0.5; a score of 0.5 should retrieve."""
    result = should_retrieve("knowledge query", score_fn=_threshold_exact)
    assert result is True, "default threshold=0.5; score=0.5 must → True"
