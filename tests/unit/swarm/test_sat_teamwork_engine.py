"""Unit tests for Self-Organizing Agent Teams (SAT) collaborative reasoning engine (arXiv:2609.22682)."""

from __future__ import annotations

import pytest

from cohezion.swarm.sat_teamwork_engine import (
    CANONICAL_SAT_STRATEGY_BANK,
    Certificate,
    CertificateAuditor,
    DemonstrabilityEstimator,
    InformationFlowMode,
    SATTeamworkEngine,
    TeamworkStrategy,
)


@pytest.fixture
def sample_certificates() -> tuple[Certificate, Certificate]:
    """Generates a correct and incorrect certificate pair."""
    correct_cert = Certificate(
        strategy_name="mechanistic_step_audit",
        problem_statement="Find the number of valid paths on the grid under parity invariant.",
        candidate_answer="3840",
        reasoning_trace=[
            "Agent 0: Formulate generating function with parity invariant.",
            "Agent 1: Repaired arithmetic counting step: 16 * 240 = 3840.",
            "Agent 2: Certified boundary conditions hold.",
        ],
        participating_agents=["agent_0", "agent_1", "agent_2"],
        load_bearing_claims=["Invariant polynomial degree = 4"],
        audited_corrections=["Agent 1 repaired counting step: 16 * 240 = 3840"],
        confidence=0.95,
        is_ground_truth_correct=True,
    )
    incorrect_cert = Certificate(
        strategy_name="naive_consensus",
        problem_statement="Find the number of valid paths on the grid under parity invariant.",
        candidate_answer="1920",
        reasoning_trace=[
            "Agent 0: Computed naive count 1920.",
            "Agent 1: Concurred without checking symmetry.",
            "Agent 2: Unresolved dispute on boundary factor.",
        ],
        participating_agents=["agent_0", "agent_1", "agent_2"],
        dissent_notes=["Agent 2: Unresolved dispute on missing factor of 2."],
        confidence=0.60,
        is_ground_truth_correct=False,
    )
    return correct_cert, incorrect_cert


def test_canonical_strategy_bank_integrity() -> None:
    assert len(CANONICAL_SAT_STRATEGY_BANK) == 5
    strategy_names = [s.name for s in CANONICAL_SAT_STRATEGY_BANK]
    assert "mechanistic_step_audit" in strategy_names
    assert "minority_reasoning_challenge" in strategy_names
    assert "divergence_reconciliation" in strategy_names
    assert "final_auditor_claim_recovery" in strategy_names
    assert "backward_constraint_validation" in strategy_names

    for strat in CANONICAL_SAT_STRATEGY_BANK:
        assert isinstance(strat, TeamworkStrategy)
        assert len(strat.fingerprint) == 12
        assert len(strat.phases) >= 2
        assert len(strat.teamwork_prompt) > 0


def test_demonstrability_pair_discriminability(
    sample_certificates: tuple[Certificate, Certificate],
) -> None:
    correct_cert, incorrect_cert = sample_certificates

    def mock_sound_judge(cert_a: Certificate, cert_b: Certificate) -> bool:
        # Returns True if cert_a is superior
        return CertificateAuditor.score_certificate(
            cert_a
        ) > CertificateAuditor.score_certificate(cert_b)

    score = DemonstrabilityEstimator.evaluate_pair_discriminability(
        correct_cert, incorrect_cert, mock_sound_judge
    )
    # Sound judge should identify correct certificate regardless of A/B ordering
    assert score == 1.0


def test_demonstrability_prediction_tiers() -> None:
    high_tier = DemonstrabilityEstimator.predict_collaboration_gain(0.85)
    assert high_tier["tier"] == "HIGH"
    assert "DEPLOY_FULL_SAT_SWARM" in high_tier["policy"]

    med_tier = DemonstrabilityEstimator.predict_collaboration_gain(0.60)
    assert med_tier["tier"] == "MODERATE"

    low_tier = DemonstrabilityEstimator.predict_collaboration_gain(0.40)
    assert low_tier["tier"] == "LOW"
    assert "FALLBACK" in low_tier["policy"]


def test_certificate_auditor_scoring_and_selection(
    sample_certificates: tuple[Certificate, Certificate],
) -> None:
    correct_cert, incorrect_cert = sample_certificates
    score_correct = CertificateAuditor.score_certificate(correct_cert)
    score_incorrect = CertificateAuditor.score_certificate(incorrect_cert)

    assert score_correct > score_incorrect
    selected = CertificateAuditor.select_best_certificate([incorrect_cert, correct_cert])
    assert selected.candidate_answer == "3840"
    assert selected.strategy_name == "mechanistic_step_audit"


def test_sat_teamwork_collaborative_lift() -> None:
    """Verifies that SAT achieves collaborative lift beyond independent agent answers."""
    engine = SATTeamworkEngine()

    def mock_collaborative_agent(agent_id: str, prompt: str, problem: str) -> str:
        if agent_id == "agent_0":
            return "Formulate invariant x^2 + y^2 = 25 and candidate 1920."
        elif agent_id == "agent_1":
            return "Repaired counting step: Factor of 2 missing, corrected value is 3840."
        else:
            return "Audited and verified parity: certified final answer is 3840."

    # Independent single agent responses all had WRONG answers
    single_agent_independent = {
        "agent_0": "Candidate 1920",
        "agent_1": "Candidate 960",
        "agent_2": "Candidate 480",
    }

    result = engine.run_collaborative_solving(
        problem_id="hmmt-2026-p6",
        problem="Find the count of symmetric configurations.",
        agent_executor=mock_collaborative_agent,
        ground_truth="3840",
        single_agent_answers=single_agent_independent,
    )

    assert result.accuracy is True
    assert result.team_coverage is True
    # Routing oracle over independent answers fails (none had 3840)
    assert result.routing_oracle_hit is False
    # Team produced a novel correct solution through collaborative repair!
    assert result.collaborative_lift is True
    assert result.selected_certificate.candidate_answer.endswith("3840.") or "3840" in result.selected_certificate.candidate_answer
    assert len(result.candidate_pool) == 5
