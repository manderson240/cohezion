"""SR1 integration tests for MGPO state → FLUME manifold geometry (Task #26).

V-Model level: SR1 (System Requirements) — verifies that SkillStateEncoder
produces a FLUME manifold where the encoding topology matches MGPO semantics.

V-Model contracts:
  SR1: Boundary-skill vectors cluster closer together than to mastered-skill vectors
       (cosine similarity is topology-preserving for the MGPO bell curve)
  SR2: MGPO weight dim (12) varies monotonically with the MGPO bell-curve formula
  SR3: Rubric verdict dim (14) isolates the pass/fail signal without disturbing
       the fingerprint region — two otherwise-identical skill states with different
       rubric_passed differ ONLY at dim 14 (discriminating manifold topology test)
  SR4: Success-rate progression produces ordered fingerprint-independent variation
       at dim 13; lower/higher dim values don't drift with success_rate
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.compound.rubric_middleware import RubricVerdict
from cohezion.flume.skill_state_encoder import SkillStateEncoder


@pytest.fixture
def enc() -> SkillStateEncoder:
    return SkillStateEncoder()


def _mgpo_subspace_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity in the MGPO scalar subspace (dims [12:16])."""
    a_sub = a[12:16]
    b_sub = b[12:16]
    a_norm = a_sub / (np.linalg.norm(a_sub) + 1e-9)
    b_norm = b_sub / (np.linalg.norm(b_sub) + 1e-9)
    return float(np.dot(a_norm, b_norm))


# ── SR1: manifold topology — boundary skills cluster together in MGPO subspace


def test_boundary_states_cluster_in_mgpo_subspace(enc):
    """In the MGPO scalar subspace [12:16], boundary states (sr≈0.5) are more
    similar to each other than to mastered states, proving that dims [12:16]
    encode the MGPO bell-curve topology.

    NOTE: The full 256D cosine similarity is dominated by the 227D SHA-256
    fingerprint (correct architecture — fingerprint encodes *identity*, MGPO
    dims encode *priority*). This test projects onto the priority axis.
    """
    boundary_a = enc.encode_skill("skill_alpha", mgpo_weight=0.99, success_rate=0.50)
    boundary_b = enc.encode_skill("skill_beta", mgpo_weight=0.95, success_rate=0.52)
    mastered = enc.encode_skill("skill_alpha", mgpo_weight=0.08, success_rate=1.00)

    sim_bb = _mgpo_subspace_similarity(boundary_a, boundary_b)
    sim_bm = _mgpo_subspace_similarity(boundary_a, mastered)
    assert sim_bb > sim_bm, (
        f"Boundary↔Boundary MGPO-subspace similarity ({sim_bb:.4f}) must exceed "
        f"Boundary↔Mastered MGPO-subspace similarity ({sim_bm:.4f})"
    )


def test_mgpo_dim_clearly_separates_boundary_from_non_boundary(enc):
    """dim 12 (mgpo_weight) creates clear magnitude separation: boundary skills
    have dim[12] >> stuck/mastered skills. Stuck and mastered share the same
    low MGPO weight but differ at dim 13 (success_rate) — the encoding captures
    both priority and position along the success axis simultaneously."""
    boundary = enc.encode_skill("skill_gamma", mgpo_weight=0.99, success_rate=0.50)
    stuck = enc.encode_skill("skill_gamma", mgpo_weight=0.08, success_rate=0.00)
    mastered = enc.encode_skill("skill_gamma", mgpo_weight=0.08, success_rate=1.00)

    # Boundary has the highest MGPO weight dim
    assert boundary[12] > stuck[12], (
        f"Boundary dim[12] ({boundary[12]:.3f}) must exceed stuck ({stuck[12]:.3f})"
    )
    assert boundary[12] > mastered[12], (
        f"Boundary dim[12] ({boundary[12]:.3f}) must exceed mastered ({mastered[12]:.3f})"
    )
    # Stuck and mastered share the same low MGPO weight (bell-curve symmetry)
    assert abs(stuck[12] - mastered[12]) < 1e-5, (
        f"Stuck and mastered MGPO weight must match; got {stuck[12]:.4f} vs {mastered[12]:.4f}"
    )
    # But success_rate (dim 13) distinguishes them along the progress axis
    assert stuck[13] < boundary[13] < mastered[13], (
        f"success_rate dim must be ordered: stuck({stuck[13]:.3f}) < "
        f"boundary({boundary[13]:.3f}) < mastered({mastered[13]:.3f})"
    )


# ── SR2: MGPO weight monotonicity at dim 12 ──────────────────────────────────


def test_mgpo_weight_dim_reflects_bell_curve_ordering(enc):
    """Dim 12 must encode the actual MGPO weight: boundary (sr=0.5) should have
    the highest weight, tapering toward 0 and 1."""
    # Expected MGPO weights: exp(-5 * |sr - 0.5|)
    #   sr=0.5 → w≈1.0, sr=0.3 → w≈0.37, sr=0.1 → w≈0.08
    v_boundary = enc.encode_skill("same_skill", mgpo_weight=1.0, success_rate=0.5)
    v_mid = enc.encode_skill("same_skill", mgpo_weight=0.37, success_rate=0.3)
    v_far = enc.encode_skill("same_skill", mgpo_weight=0.08, success_rate=0.1)

    assert v_boundary[12] > v_mid[12] > v_far[12], (
        f"dim 12 must be ordered: boundary({v_boundary[12]:.3f}) > "
        f"mid({v_mid[12]:.3f}) > far({v_far[12]:.3f})"
    )


# ── SR3: rubric dim isolates pass/fail with no fingerprint drift ──────────────


def test_rubric_verdict_isolates_to_dim_14_in_manifold(enc):
    """Changing rubric_passed must affect ONLY dim 14 in the full 256D vector.
    This verifies manifold isolation: rubric quality does not corrupt the
    fingerprint region used for nearest-neighbour skill lookup."""
    verdict_pass = RubricVerdict(passed=True, reason="all good")
    verdict_fail = RubricVerdict(passed=False, reason="hallucinated")

    v_pass = enc.encode_rubric_verdict(
        "isolation_skill", verdict_pass, mgpo_weight=0.5, success_rate=0.5
    )
    v_fail = enc.encode_rubric_verdict(
        "isolation_skill", verdict_fail, mgpo_weight=0.5, success_rate=0.5
    )

    # dim 14 must differ
    assert abs(v_pass[14] - v_fail[14]) > 0.9, (
        f"dim 14 must differ by ~1.0; got pass={v_pass[14]}, fail={v_fail[14]}"
    )

    # ALL other dims must be identical
    other_pass = np.concatenate([v_pass[:14], v_pass[15:]])
    other_fail = np.concatenate([v_fail[:14], v_fail[15:]])
    np.testing.assert_allclose(
        other_pass, other_fail, atol=1e-6, err_msg="Changing rubric_passed must affect ONLY dim 14"
    )


# ── SR4: success rate is independent of fingerprint region ────────────────────


def test_success_rate_only_varies_dim_13_not_fingerprint(enc):
    """Changing success_rate must update dim 13 without altering the fingerprint
    region [29:256]. The manifold topology must decouple scalar metrics from the
    semantic fingerprint."""
    v_low = enc.encode_skill("stable_skill", mgpo_weight=0.5, success_rate=0.1)
    v_high = enc.encode_skill("stable_skill", mgpo_weight=0.5, success_rate=0.9)

    # dim 13 must differ
    assert abs(v_low[13] - v_high[13]) > 0.5, (
        f"dim 13 must differ for different success_rates; got {v_low[13]:.4f} vs {v_high[13]:.4f}"
    )

    # Fingerprint region [29:256] must be identical (same skill_name, same context)
    np.testing.assert_array_equal(
        v_low[29:],
        v_high[29:],
        err_msg="Fingerprint region [29:256] must not vary with success_rate",
    )


# ── SR1 end-to-end: MGPO subspace preserves boundary cluster topology ─────────


def test_mgpo_subspace_boundary_cluster_end_to_end(enc):
    """End-to-end SR1 test: in the MGPO priority subspace, two boundary skills
    (different identities) are more similar than either is to a mastered skill.

    This validates the full wiring: encode_skill → dims [12:16] encode MGPO
    state in a way that clusters skills by capability-boundary proximity.
    """
    b1 = enc.encode_skill("routing_skill", mgpo_weight=0.99, success_rate=0.48)
    b2 = enc.encode_skill("analysis_skill", mgpo_weight=0.97, success_rate=0.51)
    m1 = enc.encode_skill("routing_skill", mgpo_weight=0.08, success_rate=0.99)

    sim_b1_b2 = _mgpo_subspace_similarity(b1, b2)
    sim_b1_m1 = _mgpo_subspace_similarity(b1, m1)

    assert sim_b1_b2 > sim_b1_m1, (
        f"Boundary MGPO-subspace similarity ({sim_b1_b2:.4f}) must exceed "
        f"Boundary↔Mastered MGPO-subspace similarity ({sim_b1_m1:.4f})"
    )
