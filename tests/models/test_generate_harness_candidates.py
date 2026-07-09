"""Discriminating tests for autonomous RHO candidate generation (item 33, 2026-06-06).

`generate_harness_candidates(records)` turns each chronically-fallback task class (via item-9
`propose_tuning`) into ONE `HarnessCandidate` recruiting a specialist for it — closing item-27's
loop so `select_harness_update` no longer needs candidates handed in.

Each test fails a plausible wrong impl:
  - lump all classes into one candidate (ignore per-class targeting) → T_k,
  - propose for a healthy corpus → T_healthy,
  - treat below-min_samples noise as a signal → T_noise,
  - generate the wrong target so RHO's winner misses the worst-fallback class → T_e2e.
"""

from __future__ import annotations

from cohezion.models.rho_selector import (
    generate_harness_candidates,
    select_harness_update,
)


def _fb(task: str, n: int = 6, *, fell_back: bool = True) -> list[dict]:
    return [
        {"task_class": task, "fell_back": fell_back, "lane": "" if fell_back else "igpu"}
        for _ in range(n)
    ]


def test_k_fallback_classes_yield_k_candidates_each_targeting_one() -> None:
    corpus = _fb("RERANK") + _fb("OCR_DOC")
    cands = generate_harness_candidates(corpus)
    assert len(cands) == 2  # one per chronically-fallback class (NOT one lumped candidate)
    targets = {next(iter(c.targets)): c for c in cands}
    assert set(targets) == {"RERANK", "OCR_DOC"}
    for c in cands:
        assert len(c.targets) == 1  # each candidate addresses exactly its own class
        assert c.candidate_id == f"recruit:{next(iter(c.targets))}"


def test_healthy_corpus_yields_no_candidates() -> None:
    # Every decision succeeded (no fallback) → nothing to recruit. Wrong impl always-proposing fails.
    assert generate_harness_candidates(_fb("CODE_GEN", fell_back=False)) == []


def test_empty_corpus_yields_no_candidates() -> None:
    assert generate_harness_candidates([]) == []


def test_below_min_samples_is_noise_not_a_candidate() -> None:
    # 3 fallback samples < min_samples=5 → noise, not a signal (no fabricated candidate).
    assert generate_harness_candidates(_fb("RERANK", 3)) == []


def test_end_to_end_rho_winner_covers_the_worst_fallback_class() -> None:
    # A single dominant chronically-fallback class → its candidate must win RHO and cover it.
    corpus = _fb("RERANK") + _fb("CODE_GEN", fell_back=False)
    cands = generate_harness_candidates(corpus)
    sel = select_harness_update(corpus, cands)
    assert sel.winner is not None
    assert "RERANK" in sel.winner.targets  # the winner covers the worst-fallback class
