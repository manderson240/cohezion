"""Discriminating tests for the RHO proposal audit record (item 42, 2026-06-06).

`rho_proposal_record(records)` runs the FULL autonomous chain (generate_harness_candidates →
select_harness_update) and returns ONE human-reviewable dict — the single artifact a human reviews
before applying any harness change (RHO proposes, never auto-applies). Composes items 9/22/33.

Each test fails a plausible wrong impl:
  - returns a winner on a healthy/empty corpus (fabricates a proposal) → test_healthy/empty_unproven,
  - drops a key / wrong key set → test_record_shape,
  - mutates the input corpus or is non-deterministic → test_pure_deterministic,
  - candidate_count not tied to the generated candidates → test_fallback_heavy.
"""

from __future__ import annotations

from cohezion.models.rho_selector import rho_proposal_record


_KEYS = {"winner_id", "targets", "coreset", "wins", "rationale", "candidate_count"}


def _fallback_corpus(task_class: str, n: int = 6) -> list[dict]:
    return [
        {"task_class": task_class, "chosen_model": None, "fell_back": True, "lane": ""}
        for _ in range(n)
    ]


def _healthy_corpus(task_class: str, n: int = 6) -> list[dict]:
    return [
        {"task_class": task_class, "chosen_model": "m", "fell_back": False, "lane": "igpu"}
        for _ in range(n)
    ]


def test_fallback_heavy_corpus_yields_winner() -> None:
    rec = rho_proposal_record(_fallback_corpus("RERANK"))
    assert rec["winner_id"] is not None
    assert "RERANK" in rec["coreset"]
    assert rec["candidate_count"] >= 1
    assert rec["targets"], "a winner must name the task classes it addresses"


def test_healthy_corpus_is_unproven() -> None:
    rec = rho_proposal_record(_healthy_corpus("RERANK"))
    assert rec["winner_id"] is None
    assert rec["coreset"] == []
    assert rec["candidate_count"] == 0
    assert rec["targets"] == []


def test_empty_corpus_is_unproven() -> None:
    rec = rho_proposal_record([])
    assert rec["winner_id"] is None
    assert rec["coreset"] == []
    assert rec["candidate_count"] == 0


def test_record_has_exact_key_set() -> None:
    rec = rho_proposal_record(_fallback_corpus("RERANK"))
    assert set(rec) == _KEYS


def test_pure_deterministic_no_mutation() -> None:
    corpus = _fallback_corpus("RERANK")
    before = list(corpus)
    r1 = rho_proposal_record(corpus)
    r2 = rho_proposal_record(corpus)
    assert r1 == r2, "must be deterministic"
    assert corpus == before, "must not mutate the input corpus"
