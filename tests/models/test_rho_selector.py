"""Discriminating tests for the RHO self-preference selector (item 22, arXiv 2606.05922).

RHO picks the best candidate harness update by PAIRWISE self-preference over a coreset of
chronically-fallback task classes mined from the routing corpus (item 9). This is the
additive SELECTOR instrument; wiring the winner into SkillRefiner is the deferred
behavior-change. The falsifiable check (item 22): a synthetic trajectory set yields a
self-preferred update that beats baseline on a held-out coverage check; no corpus → UNPROVEN.

Each test fails a plausible wrong impl:
  - a selector that returns the FIRST candidate (ignores the coreset) — T1/T_heldout,
  - one that FABRICATES a pick on an empty corpus instead of UNPROVEN=None — T_empty,
  - one that hardcodes the winner instead of consulting the preference fn — T_injected,
  - one that fabricates a pick when there are no candidates — T_nocand.
"""

from __future__ import annotations

from cohezion.models.rho_selector import (
    HarnessCandidate,
    select_harness_update,
)


def _fallback_corpus(task_class: str, n: int = 6) -> list[dict]:
    # n decisions for one task class, ALL fell back -> a chronically-fallback coreset member.
    return [
        {"task_class": task_class, "chosen_model": None, "fell_back": True, "lane": ""}
        for _ in range(n)
    ]


_A = HarnessCandidate("A", "route CODE_GEN elsewhere", frozenset({"CODE_GEN"}))
_B = HarnessCandidate("B", "recruit a RERANK specialist", frozenset({"RERANK"}))


def test_rho_selects_the_candidate_covering_the_fallback_coreset() -> None:
    # RERANK chronically falls back -> coreset={RERANK}. B covers it, A does not.
    sel = select_harness_update(_fallback_corpus("RERANK"), [_A, _B])
    assert sel.winner is not None
    assert sel.winner.candidate_id == "B"  # a first-candidate impl would pick A
    assert "RERANK" in sel.coreset


def test_rho_winner_beats_baseline_on_held_out_coverage() -> None:
    # The item's falsifiable check: the self-preferred winner covers MORE of the coreset
    # than the loser (the baseline). Strict inequality — a tie/no-op would fail.
    sel = select_harness_update(_fallback_corpus("RERANK"), [_A, _B])
    core = set(sel.coreset)
    assert sel.winner is not None
    win_cov = len(sel.winner.targets & core)
    base_cov = len(_A.targets & core)  # A is the baseline (irrelevant candidate)
    assert win_cov > base_cov


def test_rho_unproven_on_empty_corpus() -> None:
    # No corpus -> no coreset -> honest UNPROVEN (None), NEVER a fabricated pick.
    sel = select_harness_update([], [_A, _B])
    assert sel.winner is None
    assert sel.coreset == ()


def test_rho_unproven_on_no_candidates() -> None:
    sel = select_harness_update(_fallback_corpus("RERANK"), [])
    assert sel.winner is None


def test_rho_consults_the_injected_preference_function() -> None:
    # Inject a preference that ALWAYS prefers A. A wins despite covering nothing -> proves the
    # tournament uses the preference fn (a hardcoded-coverage impl would still pick B and fail).
    sel = select_harness_update(
        _fallback_corpus("RERANK"), [_A, _B], prefer=lambda a, b, coreset: _A
    )
    assert sel.winner is not None
    assert sel.winner.candidate_id == "A"
