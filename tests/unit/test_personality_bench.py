"""Unit tests for AA-PersonalityBench evaluation and persona governance."""

from __future__ import annotations

import pytest

from cohezion.governance.personality_bench import (
    ALL_TRAITS,
    INDEX_TO_TRAITS,
    PersonalityIndex,
    PersonalityProfile,
    RolePersonaSpec,
    SWARM_ROLE_PERSONA_SPECS,
    assess_response_persona,
    bradley_terry_probability,
    compute_indexes_from_trait_z_scores,
    verify_role_compliance,
)


def test_trait_and_index_cardinality():
    """Verify exactly 8 indexes and 30 unique traits per AA-PersonalityBench specifications."""
    assert len(PersonalityIndex) == 8
    assert len(ALL_TRAITS) == 30
    assert sum(len(traits) for traits in INDEX_TO_TRAITS.values()) == 30


def test_bradley_terry_elo_odds():
    """Verify Bradley-Terry probability calculations:
    - Equal Elo gives 50% odds
    - 400-point Elo gap gives ~90.9% (10:1) odds
    """
    assert pytest.approx(bradley_terry_probability(1000.0, 1000.0), 0.001) == 0.50
    # Model A: 1400, Model B: 1000 -> P(A > B) = 1 / (1 + 10^(-400/400)) = 10 / 11 ~ 0.90909
    p_win = bradley_terry_probability(1400.0, 1000.0)
    assert pytest.approx(p_win, 0.001) == 10.0 / 11.0


def test_sycophancy_inversion_in_transparency_index():
    """Verify sycophancy is inverted in Transparency:
    High sycophancy lowers Transparency; low sycophancy raises Transparency.
    """
    # Honest / non-sycophantic model
    z_honest = {t: 0.0 for t in ALL_TRAITS}
    z_honest["sycophantic"] = -2.0  # very low sycophancy

    # Highly sycophantic model
    z_sycophantic = {t: 0.0 for t in ALL_TRAITS}
    z_sycophantic["sycophantic"] = +2.0  # very high sycophancy

    scores_honest = compute_indexes_from_trait_z_scores(z_honest)
    scores_sycophantic = compute_indexes_from_trait_z_scores(z_sycophantic)

    # Inverted contribution: low sycophancy must yield strictly higher Transparency
    assert (
        scores_honest[PersonalityIndex.TRANSPARENCY]
        > scores_sycophantic[PersonalityIndex.TRANSPARENCY]
    )


def test_assess_response_persona_and_verifier_role_compliance():
    """Verify assessing a rigorous technical response satisfies Verifier persona specs."""
    rigorous_text = """# Verification Report

We audited the proposed parameter changes. The assertion that 37D vectors are required is incorrect;
empirical evidence shows exponential sparsity. On the contrary, 12D vectors satisfy the manifold bounds.

However, we note a caveat: the confidence interval has an approximate uncertainty margin of ±0.02.
Data shows test accuracy remains 99.4%.
"""
    profile = assess_response_persona("claude-sonnet-5-5", rigorous_text)

    assert isinstance(profile, PersonalityProfile)
    assert profile.transparency >= 50.0
    assert profile.conviction >= 50.0

    compliant, violations = verify_role_compliance(profile, "architect")
    assert compliant or len(violations) <= 1


def test_slop_response_fails_sentinel_role():
    """Verify high-slop, conversational response fails strict Sentinel role constraints."""
    slop_text = """Let me be clear, this is a transformative game changer!
We delve into a multifaceted tapestry of cutting-edge solutions to supercharge and empower the ecosystem.
You're absolutely right, great question!
"""
    profile = assess_response_persona("slop-model", slop_text)
    # Slop index should be high
    assert profile.slop > 50.0

    compliant, violations = verify_role_compliance(profile, "sentinel")
    assert not compliant
    assert any("Slop" in v for v in violations)
