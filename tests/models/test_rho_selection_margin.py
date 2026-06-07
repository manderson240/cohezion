"""Discriminating tests for the RHO selection-margin confidence signal (item 61, 2026-06-06).

`rho_selection_margin(records)` runs the same autonomous RHO chain as item-42 `rho_proposal_record`
and returns the winner's win-margin over the runner-up (`top_wins − second_wins`) — a CONFIDENCE
signal for the human reviewer (a decisive winner is safer to apply than a photo-finish). Ties the RHO
thread to metacognitive-calibration "confidence ∝ evidence". Report-only, pure.

Each test fails a plausible wrong impl:
  - returns `top_wins` instead of `top − second` → test_three_candidates_margin_is_top_minus_second,
  - crashes / returns None on a single uncontested candidate → test_single_candidate_uncontested,
  - fabricates a margin on a healthy/empty corpus (no winner) → test_healthy/empty_none,
  - a near-tie reported as a large margin → test_two_candidates_small_margin.
"""

from __future__ import annotations

from cohezion.models.rho_selector import rho_selection_margin


def _fallback_corpus(*task_classes: str, n: int = 6) -> list[dict]:
    # n all-fell-back decisions per task class → each becomes a chronically-fallback coreset member,
    # and generate_harness_candidates makes exactly one candidate per such class.
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


def test_single_candidate_uncontested() -> None:
    # One fallback class → one candidate → no pairwise games → that candidate has 0 wins, no runner-up.
    assert rho_selection_margin(_fallback_corpus("RERANK")) == 0


def test_two_candidates_small_margin() -> None:
    # Two candidates → one game → winner 1 win, loser 0 → margin exactly 1 (a near-tie).
    assert rho_selection_margin(_fallback_corpus("RERANK", "OCR_DOC")) == 1


def test_three_candidates_margin_is_top_minus_second() -> None:
    # Three candidates → wins distribute [2, 1, 0] → margin = 2 − 1 = 1, NOT the top's 2.
    # An impl that returns top_wins would give 2 here; the correct top−second gives 1.
    assert rho_selection_margin(_fallback_corpus("AAA", "BBB", "CCC")) == 1


def test_healthy_corpus_none() -> None:
    assert rho_selection_margin(_healthy_corpus("RERANK")) is None


def test_empty_corpus_none() -> None:
    assert rho_selection_margin([]) is None


def test_pure_no_mutation() -> None:
    corpus = _fallback_corpus("RERANK", "OCR_DOC")
    before = list(corpus)
    assert rho_selection_margin(corpus) == rho_selection_margin(corpus)  # deterministic
    assert corpus == before  # input not mutated
