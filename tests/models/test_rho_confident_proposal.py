"""Discriminating tests for the RHO confidence-gated proposal (item 91, 2026-06-09).

`rho_confident_proposal(records, *, min_margin)` annotates the item-42 `rho_proposal_record` dict
with `{margin, confident}`, where `confident = margin is not None and margin >= min_margin`
(item-61 `rho_selection_margin`). A decisive winner is endorsed; a photo-finish is flagged but the
winner is still named; an UNPROVEN corpus is never confident. Report-only, pure.

Each test fails a plausible wrong impl:
  - `confident = winner_id is not None` (gates on winner existence, not margin)
    → test_gate_is_on_margin_not_winner_existence,
  - drops the winner when low-confidence → test_photo_finish_not_confident_but_winner_kept,
  - missing the `margin is not None` guard (crashes on None >= min_margin)
    → test_unproven_corpus_not_confident,
  - re-deriving a different winner than rho_proposal_record → test_decisive_winner_is_confident.
"""

from __future__ import annotations

from cohezion.models.rho_selector import rho_confident_proposal, rho_proposal_record


def _fallback_corpus(*task_classes: str, n: int = 6) -> list[dict]:
    # n all-fell-back decisions per class → one chronically-fallback candidate per class.
    return [
        {"task_class": tc, "chosen_model": None, "fell_back": True, "lane": ""}
        for tc in task_classes
        for _ in range(n)
    ]


def _healthy_corpus(task_class: str, n: int = 6) -> list[dict]:
    return [
        {"task_class": task_class, "chosen_model": "m", "fell_back": False, "lane": "igpu"}
        for _ in range(n)
    ]


def test_decisive_winner_is_confident() -> None:
    # Two candidates → margin 1; threshold 1 → endorsed. Winner must match rho_proposal_record's.
    corpus = _fallback_corpus("RERANK", "OCR_DOC")
    out = rho_confident_proposal(corpus, min_margin=1)
    assert out["confident"] is True
    assert out["margin"] == 1
    assert out["winner_id"] == rho_proposal_record(corpus)["winner_id"]  # annotated, not re-derived


def test_photo_finish_not_confident_but_winner_kept() -> None:
    # SAME margin-1 corpus, threshold 2 → photo-finish: not endorsed, but the winner is STILL named.
    corpus = _fallback_corpus("RERANK", "OCR_DOC")
    out = rho_confident_proposal(corpus, min_margin=2)
    assert out["confident"] is False
    assert out["winner_id"] is not None  # kills an impl that drops the winner when low-confidence
    assert out["margin"] == 1


def test_gate_is_on_margin_not_winner_existence() -> None:
    # DISCRIMINATING: one candidate → a winner EXISTS but margin is 0. With threshold 1, an impl
    # that gates on `winner_id is not None` wrongly says confident; the margin gate says False.
    corpus = _fallback_corpus("RERANK")
    out = rho_confident_proposal(corpus, min_margin=1)
    assert out["winner_id"] is not None  # a winner DOES exist
    assert out["margin"] == 0
    assert out["confident"] is False  # ...but margin 0 < 1 gates it out


def test_unproven_corpus_not_confident() -> None:
    # No winner (healthy corpus) → margin None → not confident, no crash on `None >= min_margin`.
    out = rho_confident_proposal(_healthy_corpus("RERANK"), min_margin=1)
    assert out["winner_id"] is None
    assert out["margin"] is None
    assert out["confident"] is False


def test_pure_no_mutation() -> None:
    corpus = _fallback_corpus("RERANK", "OCR_DOC")
    before = list(corpus)
    rho_confident_proposal(corpus, min_margin=1)
    assert corpus == before  # input not mutated
