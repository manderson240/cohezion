"""Unit Tests for Stateless Language Agents (arXiv:2610.07625).
============================================================
Verifies:
1. Outcome Partitioning & Disambiguation (Inconclusive vs Non-Improvement vs Improvement).
2. Role-Specific Context Reconstruction for Advisor & Workers.
3. Local Candidate Retention (k-trial budget) with Global Reset.
4. SLA Harness Multi-Epoch Search Simulation and Monotonic Best Tracking.
5. Projected Token Efficiency & Zero-Conversation Invariant.
"""

from __future__ import annotations

import pytest
import asyncio
from typing import Tuple

from cohezion.compound.stateless_language_agent import (
    CandidateOutcome,
    ResearchCandidate,
    EvidenceSummary,
    EvidenceSummarizer,
    AdvisorAssignment,
    StatelessAdvisor,
    StatelessWorker,
    SLAHarness,
)


@pytest.mark.asyncio
async def test_evidence_summarizer_failure_disambiguation():
    """Verify that syntax/runtime errors are classified as INCONCLUSIVE_FAILURE, not negative evidence."""
    # Syntax error / crash
    outcome_err = EvidenceSummarizer.classify_outcome(
        score=0.0,
        baseline_score=0.5,
        is_error=True,
        error_msg="SyntaxError: invalid syntax",
    )
    assert outcome_err == CandidateOutcome.INCONCLUSIVE_FAILURE

    # Clean run, but score <= baseline
    outcome_non_imp = EvidenceSummarizer.classify_outcome(
        score=0.45,
        baseline_score=0.5,
        is_error=False,
    )
    assert outcome_non_imp == CandidateOutcome.MEASURED_NON_IMPROVEMENT

    # Clean run, score > baseline
    outcome_imp = EvidenceSummarizer.classify_outcome(
        score=0.62,
        baseline_score=0.5,
        is_error=False,
    )
    assert outcome_imp == CandidateOutcome.MEASURED_IMPROVEMENT


@pytest.mark.asyncio
async def test_evidence_summary_formatting():
    """Verify that EvidenceSummary properly formats diagnostic insight for untest vs tested hypotheses."""
    candidates = [
        ResearchCandidate(
            candidate_id="c1",
            code="def foo(): pass",
            score=0.55,
            outcome=CandidateOutcome.MEASURED_IMPROVEMENT,
            diagnostics="",
            direction_id="dir_kernel",
            hypothesis="Use polynomial kernel",
            worker_id="w0",
            epoch=1,
            trial_index=0,
        ),
        ResearchCandidate(
            candidate_id="c2",
            code="def foo(): error",
            score=0.0,
            outcome=CandidateOutcome.INCONCLUSIVE_FAILURE,
            diagnostics="NameError: name 'error' is not defined",
            direction_id="dir_ensemble",
            hypothesis="Stack 3 GBDT models",
            worker_id="w1",
            epoch=1,
            trial_index=0,
        ),
        ResearchCandidate(
            candidate_id="c3",
            code="def foo(): pass",
            score=0.52,
            outcome=CandidateOutcome.MEASURED_NON_IMPROVEMENT,
            diagnostics="",
            direction_id="dir_ensemble",
            hypothesis="Stack 3 GBDT models",
            worker_id="w1",
            epoch=2,
            trial_index=1,
        ),
    ]

    summary = EvidenceSummarizer.summarize(
        candidates=candidates,
        epoch=2,
        global_best_candidate=candidates[0],
        higher_is_better=True,
    )

    assert summary.epoch == 2
    assert summary.global_best_score == 0.55
    assert summary.global_best_candidate_id == "c1"
    assert "dir_kernel" in summary.direction_stats
    assert "dir_ensemble" in summary.direction_stats

    # dir_ensemble has 1 inconclusive and 1 non-improvement
    ens_stat = summary.direction_stats["dir_ensemble"]
    assert ens_stat["inconclusive_failures"] == 1
    assert ens_stat["non_improvements"] == 1
    assert ens_stat["improvements"] == 0

    # Ensure markdown contains note that hypothesis remains untested for inconclusive
    assert "UNTESTED" in summary.formatted_markdown
    assert "NameError" in summary.formatted_markdown


@pytest.mark.asyncio
async def test_stateless_advisor_prompt_and_heuristic():
    """Verify Advisor prompt reconstruction and deterministic heuristic assignment."""
    task = "Optimize ARC-AGI-2 grid transformation DSL"
    initial_dirs = [
        {"direction_id": "dir_d4", "hypothesis": "D4 Dihedral symmetry expansion"},
        {"direction_id": "dir_cc", "hypothesis": "Connected component flood-fill"},
    ]
    advisor = StatelessAdvisor(task_description=task, initial_directions=initial_dirs)

    summary = EvidenceSummary(
        epoch=1,
        global_best_candidate_id="seed",
        global_best_score=0.3181,
        total_candidates=1,
        direction_stats={},
        formatted_markdown="### Empty summary",
    )

    workers = ["worker_0", "worker_1"]
    prompt = advisor.build_prompt(summary, workers)
    assert task in prompt
    assert "worker_0" in prompt
    assert "worker_1" in prompt
    assert "INCONCLUSIVE_FAILURE" in prompt

    assignments = await advisor.assign(summary, workers)
    assert len(assignments) == 2
    assert assignments[0].worker_id == "worker_0"
    assert assignments[0].direction_id in ["dir_d4", "dir_cc"]
    assert assignments[1].worker_id == "worker_1"


@pytest.mark.asyncio
async def test_stateless_worker_prompt_and_mutation():
    """Verify Worker prompt contains zero global conversational history, only working candidate + local diagnostics."""
    worker = StatelessWorker(worker_id="w_test")
    assignment = AdvisorAssignment(
        worker_id="w_test",
        direction_id="dir_d4",
        hypothesis="Apply D4 rotation",
        instructions="Rotate input grid 90 deg",
        reset_to_best=False,
    )

    base_code = "def transform(x):\n    return x"
    diag = "IndexError: list index out of range"
    prompt = worker.build_prompt(assignment, base_code, diagnostics=diag, trial_index=1)

    assert "dir_d4" in prompt
    assert "Apply D4 rotation" in prompt
    assert "def transform(x):" in prompt
    assert "IndexError: list index out of range" in prompt
    # Ensure no peer workers mentioned
    assert "worker_0" not in prompt

    mutated = await worker.propose_code(assignment, base_code, diagnostics=diag, trial_index=1)
    assert "dir_d4" in mutated
    assert "def transform(x):" in mutated


@pytest.mark.asyncio
async def test_sla_harness_multi_epoch_search_and_retention():
    """Simulate a multi-epoch search in SLAHarness verifying local retention, reset, and monotonic best improvement."""
    initial_code = "def solve(x): return x"
    eval_call_count = 0

    async def mock_evaluator(code: str) -> Tuple[float, str, bool]:
        nonlocal eval_call_count
        eval_call_count += 1

        # Seed evaluation
        if "Baseline initialization" in code or eval_call_count == 1:
            return 0.30, "", False

        # Inconclusive failure for trial 1 of worker_0
        if "w0" in code and "trial 0" in code:
            return 0.0, "SyntaxError: unexpected EOF", True

        # Breakthrough on trial 1 of worker_0
        if "w0" in code and "trial 1" in code:
            return 0.38, "", False

        # Moderate result for worker_1
        if "w1" in code:
            return 0.32, "", False

        return 0.25, "", False

    initial_dirs = [
        {"direction_id": "dir_a", "hypothesis": "Hypothesis A"},
        {"direction_id": "dir_b", "hypothesis": "Hypothesis B"},
    ]

    harness = SLAHarness(
        initial_code=initial_code,
        task_description="Mock optimization task",
        initial_directions=initial_dirs,
        evaluator_fn=mock_evaluator,
        worker_ids=["w0", "w1"],
        local_retention_k=3,
        higher_is_better=True,
    )

    # Initialize
    seed = await harness.initialize()
    assert seed.score == 0.30
    assert harness.global_best_candidate.score == 0.30

    # Epoch 1: w0 encounters syntax error (INCONCLUSIVE), w1 gets 0.32 (IMPROVEMENT over seed 0.30)
    rep1 = await harness.run_epoch()
    assert rep1["epoch"] == 1
    assert rep1["evaluated_candidates"] == 2
    assert harness.global_best_candidate.score >= 0.32

    # w0 had inconclusive error, so its working candidate was retained/handled with diagnostic
    assert harness.worker_local_state["w0"]["trial_count"] == 1
    assert "SyntaxError" in harness.worker_local_state["w0"]["last_diagnostics"]

    # Epoch 2: w0 tries again with trial 1 and achieves breakthrough 0.38!
    rep2 = await harness.run_epoch()
    assert rep2["epoch"] == 2
    assert harness.global_best_candidate.score == 0.38
    assert rep2["improvements_found"] >= 1

    # Epoch 3: verify efficiency report
    rep3 = await harness.run_epoch()
    eff = harness.compute_efficiency_report()

    assert eff["total_candidates"] >= 7  # seed + 2*3 candidates
    assert eff["improvements"] >= 2
    assert eff["inconclusive_failures"] == 1
    assert eff["global_best_score"] == 0.38
    assert eff["projected_token_savings_pct"] > 0.0
