"""Discriminating tests for loop_recall_context (item 108, Thread P).

Falsifiable checks (pure, no live services — all external deps injected):
  - An item with no relevant memory → empty hits, never fabricated.
  - Fail-soft: unreachable vault → honest [] (no exception raised).
  - Neuron store injection: neurons returned only when tags match.
  - vault_search_fn injection: hits from fn are surfaced faithfully.
  - Empty / whitespace-only item_text → empty result with error note.
  - Result is frozen (never mutates after construction).
  - Report dict contains all required keys.

Each test fails a plausible wrong implementation:
  - one that returns fabricated hits on empty input → T_empty_item
  - one that raises instead of returning [] on vault failure → T_vault_failure
  - one that fabricates neuron hits when no tags match → T_no_matching_neurons
  - one that drops vault hits from the injected fn → T_injected_vault_fn
  - one that returns mutable result objects → T_frozen_result
"""

from __future__ import annotations

import pytest

from cohezion.compound.loop_recall import (
    RecallHit,
    loop_recall_context,
    loop_recall_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hit(title: str = "x", relevance: float = 0.9) -> RecallHit:
    return RecallHit(
        source="vault",
        title=title,
        content_snippet="snippet",
        country="",
        relevance=relevance,
    )


def _vault_fn_returning(hits: list[RecallHit]):
    """Inject a vault search fn that always returns the given hits."""

    def _fn(query: str, top_k: int) -> list[RecallHit]:  # noqa: ARG001
        return hits[:top_k]

    return _fn


def _vault_fn_raises():
    """Inject a vault search fn that always raises."""

    def _fn(query: str, top_k: int) -> list[RecallHit]:  # noqa: ARG001
        raise ConnectionError("vault MCP unavailable")

    return _fn


# ---------------------------------------------------------------------------
# T_empty_item: empty / whitespace → empty result with error note, not fabricated hits
# ---------------------------------------------------------------------------


def test_empty_item_text_returns_empty_with_error() -> None:
    result = loop_recall_context("")
    assert result.is_empty
    assert result.error is not None


def test_whitespace_only_item_text_returns_empty_with_error() -> None:
    result = loop_recall_context("   \n\t  ")
    assert result.is_empty
    assert result.error is not None


# ---------------------------------------------------------------------------
# T_vault_failure: vault_search_fn raises → [] returned, no exception propagated
# ---------------------------------------------------------------------------


def test_vault_search_failure_returns_empty_no_exception() -> None:
    # A selector that raises MUST NOT propagate the exception to the caller.
    result = loop_recall_context(
        "item text",
        vault_search_fn=_vault_fn_raises(),
    )
    # The vault error is captured in result.error, never re-raised.
    assert result.vault_hits == []
    assert result.error is not None
    assert "raised" in result.error.lower() or "vault" in result.error.lower()


# ---------------------------------------------------------------------------
# T_no_relevant_memory: item with no matching vault/neuron → empty
# ---------------------------------------------------------------------------


def test_no_relevant_memory_returns_empty_hits() -> None:
    result = loop_recall_context(
        "some backlog item with no matching memory",
        vault_search_fn=_vault_fn_returning([]),  # no vault hits
        neuron_store=[],  # no neurons
    )
    assert result.vault_hits == []
    assert result.neuron_hits == []
    assert result.is_empty
    assert result.error is None  # no error — just no hits


# ---------------------------------------------------------------------------
# T_injected_vault_fn: hits from injected fn are surfaced faithfully
# ---------------------------------------------------------------------------


def test_injected_vault_fn_hits_appear_in_result() -> None:
    hits = [_hit("doc-A", 0.95), _hit("doc-B", 0.80)]
    result = loop_recall_context(
        "relevant item text",
        vault_search_fn=_vault_fn_returning(hits),
        neuron_store=[],
    )
    assert len(result.vault_hits) == 2
    titles = {h.title for h in result.vault_hits}
    assert "doc-A" in titles
    assert "doc-B" in titles


# ---------------------------------------------------------------------------
# T_no_matching_neurons: neuron store present but no matching tags → no hits
# ---------------------------------------------------------------------------


def test_neuron_store_with_no_matching_tags_returns_empty_neurons() -> None:
    store = [
        {"country": "inference", "tags": ["other-key"], "id": "n1", "content": "c"},
    ]
    result = loop_recall_context(
        "vault-recall augmentation backlog item",
        vault_search_fn=_vault_fn_returning([]),
        neuron_store=store,
    )
    # "vault-recall augmentation backlog item" is not in tags=["other-key"]
    assert result.neuron_hits == []


# ---------------------------------------------------------------------------
# T_matching_neurons: neuron with matching tag IS returned
# ---------------------------------------------------------------------------


def test_neuron_with_matching_tag_is_returned() -> None:
    query_key = "vault-recall augmentation backlog item"
    store = [
        {
            "country": "inference",
            "tags": [query_key],
            "id": "neuron-99",
            "content": "prior experience about vault recall",
        }
    ]
    result = loop_recall_context(
        query_key,
        vault_search_fn=_vault_fn_returning([]),
        neuron_store=store,
    )
    assert len(result.neuron_hits) == 1
    assert result.neuron_hits[0].title == "neuron-99"
    assert result.neuron_hits[0].country == "inference"
    assert result.neuron_hits[0].source == "neuron"


# ---------------------------------------------------------------------------
# T_frozen_result: LoopRecallResult is immutable after construction
# ---------------------------------------------------------------------------


def test_loop_recall_result_is_frozen() -> None:
    result = loop_recall_context("x", vault_search_fn=_vault_fn_returning([]), neuron_store=[])
    with pytest.raises(Exception):
        result.vault_hits = []  # type: ignore[misc]


def test_recall_hit_is_frozen() -> None:
    h = _hit()
    with pytest.raises(Exception):
        h.title = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T_top_k: vault hits are capped at top_k
# ---------------------------------------------------------------------------


def test_vault_hits_capped_at_top_k() -> None:
    hits = [_hit(f"doc-{i}") for i in range(10)]
    result = loop_recall_context(
        "some item",
        top_k=3,
        vault_search_fn=_vault_fn_returning(hits),
        neuron_store=[],
    )
    assert len(result.vault_hits) <= 3


# ---------------------------------------------------------------------------
# loop_recall_report: contract tests
# ---------------------------------------------------------------------------


def test_report_contains_required_keys() -> None:
    report = loop_recall_report(
        "test item",
        vault_search_fn=_vault_fn_returning([]),
        neuron_store=[],
    )
    for key in ("query", "vault_hits", "neuron_hits", "total_hits", "error"):
        assert key in report, f"missing key: {key}"


def test_report_total_hits_matches_sum() -> None:
    hits = [_hit("doc-A")]
    report = loop_recall_report(
        "test item",
        vault_search_fn=_vault_fn_returning(hits),
        neuron_store=[],
    )
    assert report["total_hits"] == len(report["vault_hits"]) + len(report["neuron_hits"])


def test_report_error_is_none_on_clean_run() -> None:
    report = loop_recall_report(
        "test item",
        vault_search_fn=_vault_fn_returning([]),
        neuron_store=[],
    )
    assert report["error"] is None


# ---------------------------------------------------------------------------
# Query truncation (item_text_truncated does not exceed _QUERY_TRUNCATE)
# ---------------------------------------------------------------------------


def test_long_item_text_is_truncated_in_result() -> None:
    long_text = "x" * 2000
    result = loop_recall_context(
        long_text,
        vault_search_fn=_vault_fn_returning([]),
        neuron_store=[],
    )
    assert len(result.item_text_truncated) <= 512
