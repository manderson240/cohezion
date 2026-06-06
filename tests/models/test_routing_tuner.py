"""Discriminating tests for routing-corpus → tuning proposals (2026-06-06, item 9).

Closes the agentic loop: routing_log.jsonl (item 2) → propose_tuning → a measurable
proposal. Each test fails a plausible wrong impl:
  - one that proposes from a HEALTHY corpus (no chronic fallback → nothing to tune),
  - one that proposes from NOISE (below min_samples — a single fallback is not a signal),
  - one that returns a proposal on an EMPTY corpus instead of honest UNPROVEN ([]),
  - one that doesn't rank the worst-offending task class first.
"""
from __future__ import annotations

from pathlib import Path

from cohezion.models.routing_log import (
    TuningProposal,
    propose_tuning,
    propose_tuning_from_log,
    record_routing_decision,
)


def _recs(task_class: str, n: int, fallbacks: int) -> list[dict]:
    return [
        {"task_class": task_class, "chosen_model": "m", "lane": "", "fell_back": i < fallbacks}
        for i in range(n)
    ]


def test_chronic_fallback_task_yields_recruit_proposal() -> None:
    # 8/10 fell back → a specialist is missing for this task class.
    proposals = propose_tuning(_recs("extraction", 10, 8))
    assert len(proposals) == 1
    p = proposals[0]
    assert isinstance(p, TuningProposal)
    assert p.kind == "recruit_specialist" and p.target == "extraction"
    assert p.metric == 0.8


def test_healthy_corpus_yields_no_proposal() -> None:
    # 1/10 fell back → routing is healthy; proposing here would be noise.
    assert propose_tuning(_recs("reasoning", 10, 1)) == []


def test_below_min_samples_is_not_a_signal() -> None:
    # 2/2 fell back looks bad but is statistically meaningless — must NOT propose.
    assert propose_tuning(_recs("vision", 2, 2), min_samples=5) == []


def test_empty_corpus_is_honest_unproven() -> None:
    assert propose_tuning([]) == []


def test_worst_offender_ranked_first() -> None:
    recs = _recs("extraction", 10, 9) + _recs("vision", 10, 6)
    proposals = propose_tuning(recs)
    assert [p.target for p in proposals] == ["extraction", "vision"]  # 0.9 before 0.6


def test_from_log_roundtrips_and_no_log_is_unproven(tmp_path: Path) -> None:
    sink = tmp_path / "routing_log.jsonl"
    for _ in range(6):
        record_routing_decision(
            task_class="ocr_doc", chosen_model=None, fell_back=True, path=sink
        )
    proposals = propose_tuning_from_log(path=sink)
    assert proposals and proposals[0].target == "ocr_doc"
    # No corpus at all → honest UNPROVEN (empty), never a fabricated proposal.
    assert propose_tuning_from_log(path=tmp_path / "gone.jsonl") == []
