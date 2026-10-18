"""Unit tests for Kaggle Grandmaster Invariant Engine."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.kaggle.grandmaster_invariant_engine import (
    BilateralMirrorTTA,
    ChemicalGraphCleavageReranker,
    DihedralD4EquivarianceWrapper,
    DuckContextEvictionHarness,
    DynamicBudgetPartitionWatchdog,
    KolmogorovEffusionCalibrator,
    SinkhornMarginalBalancer,
    StylometricEntropyExtractor,
    ZobristCycleWatchdog,
)


def test_bilateral_mirror_tta() -> None:
    orig = np.array([0.90, 0.10])
    flipped = np.array([0.80, 0.20])
    blended = BilateralMirrorTTA.blend_tta(orig, flipped, flip_weight=0.5)
    np.testing.assert_allclose(blended, [0.85, 0.15])


def test_kolmogorov_effusion_calibrator() -> None:
    raw_probs = {
        "Abnormal": 0.50,
        "ACL Tear": 0.90,
        "Medial Meniscal Tear": 0.40,
        "Joint Effusion": 0.20,
    }
    projected = KolmogorovEffusionCalibrator.project_probabilities(raw_probs, alpha_effusion=0.85)

    # Invariant 1: P(Effusion) >= 0.85 * max(ACL, Meniscus) = 0.85 * 0.90 = 0.765
    assert projected["Joint Effusion"] >= 0.765

    # Invariant 2: P(Abnormal) >= max_k P_k = 0.90
    assert projected["Abnormal"] >= 0.90

    # Invariant 3: P in [1e-6, 1.0 - 1e-6]
    for p in projected.values():
        assert 1e-6 <= p <= 1.0 - 1e-6


def test_chemical_cleavage_reranker() -> None:
    score = ChemicalGraphCleavageReranker.score_candidate(
        candidate_mass=300.100,
        precursor_mz=300.101,  # ~3.3 ppm error
        exp_peaks=[150.05, 200.08, 250.10],
        cand_formula_cleavages=[150.05, 200.08],
        base_sim=0.70,
    )
    assert 0.0 < score <= 1.0


def test_stylometric_entropy_extractor() -> None:
    text = "The quick brown fox jumps over the lazy dog! What does the fox say? It says hello."
    feats = StylometricEntropyExtractor.extract_features(text)
    assert "function_word_ratio" in feats
    assert "punct_entropy" in feats
    assert feats["function_word_ratio"] > 0.0
    assert feats["punct_entropy"] > 0.0


def test_sinkhorn_marginal_balancer() -> None:
    # 3 samples, 2 classes
    raw_probs = np.array(
        [
            [0.90, 0.10],
            [0.80, 0.20],
            [0.70, 0.30],
        ]
    )
    # Target uniform class priors
    target_priors = np.array([0.5, 0.5])
    balanced = SinkhornMarginalBalancer.balance(raw_probs, target_priors, max_iter=20)

    assert balanced.shape == (3, 2)
    # Check row sums are approximately 1.0
    np.testing.assert_allclose(balanced.sum(axis=1), np.ones(3), atol=1e-3)
    # Check column proportions moved closer to target prior (0.5, 0.5)
    col_sums = balanced.sum(axis=0)
    col_proportions = col_sums / col_sums.sum()
    np.testing.assert_allclose(col_proportions, [0.5, 0.5], atol=1e-2)


def test_dihedral_d4_equivariance() -> None:
    grid = [[1, 2], [3, 4]]
    transforms = DihedralD4EquivarianceWrapper.get_d4_transforms(grid)
    assert len(transforms) == 8  # 4 rotations * 2 reflections


def test_zobrist_cycle_watchdog() -> None:
    watchdog = ZobristCycleWatchdog(max_allowed_cycles=2)
    state = b"grid_state_t1"

    assert not watchdog.record_and_check_cycle(state)  # 1st time: count 1 <= 2
    assert not watchdog.record_and_check_cycle(state)  # 2nd time: count 2 <= 2
    assert watchdog.record_and_check_cycle(state)  # 3rd time: count 3 > 2 (cycle detected!)


def test_duck_context_eviction_harness() -> None:
    evicted = DuckContextEvictionHarness.compress_history(
        system_prompt="You are an expert SWE agent.",
        initial_task="Fix bug in runner.py",
        tool_turns=[{"role": "assistant", "content": "long verbose log"}],
        active_diff="--- a/runner.py\n+++ b/runner.py\n@@ -1 +1 @@",
        failing_traceback="AssertionError: expected 5 got 4",
    )
    assert len(evicted) == 3
    assert "CURRENT ACTIVE PATCH" in evicted[-1]["content"]
    assert "ACTIVE TEST TRACEBACK" in evicted[-1]["content"]


def test_copula_rank_blender() -> None:
    from cohezion.kaggle.grandmaster_invariant_engine import CopulaRankBlender

    p1 = np.array([0.10, 0.40, 0.80, 0.95])
    p2 = np.array([0.05, 0.30, 0.70, 0.90])
    blended = CopulaRankBlender.blend([p1, p2], weights=[0.5, 0.5])

    assert len(blended) == 4
    # Monotonicity preserved
    assert blended[0] < blended[1] < blended[2] < blended[3]
    # Bound-insulation
    assert np.all(blended >= 1e-6)
    assert np.all(blended <= 1.0 - 1e-6)


def test_tautomer_inchikey_canonicalizer() -> None:
    from cohezion.kaggle.grandmaster_invariant_engine import TautomerInChIKeyCanonicalizer

    # Ethanol SMILES
    key14 = TautomerInChIKeyCanonicalizer.canonicalize_inchikey14("CCO")
    assert len(key14) == 14


def test_anti_cyclic_action_gator() -> None:
    from cohezion.kaggle.grandmaster_invariant_engine import AntiCyclicActionGator

    gator = AntiCyclicActionGator(action_dim=4)
    # Action sequence: 0, 1, 0 -> proposed 1 creates a 2-cycle loop
    assert gator.select_action(0) == 0
    assert gator.select_action(1) == 1
    assert gator.select_action(0) == 0
    # Next proposed is 1 -> trap detected! Orthogonal escape pulse triggers
    perturbed = gator.select_action(1)
    assert perturbed != 1  # Successfully escaped the 0 -> 1 -> 0 -> 1 cycle!


def test_ast_patch_preflight_verifier() -> None:
    from cohezion.kaggle.grandmaster_invariant_engine import ASTPatchPreflightVerifier

    valid_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    ok, msg = ASTPatchPreflightVerifier.verify_syntax(valid_code)
    assert ok is True

    invalid_code = "def bad_syntax(:\n    return\n"
    ok, msg = ASTPatchPreflightVerifier.verify_syntax(invalid_code)
    assert ok is False
    assert "SyntaxError" in msg


def test_orthogonal_top2_attempt_generator() -> None:
    from cohezion.kaggle.grandmaster_invariant_engine import OrthogonalTop2AttemptGenerator

    a1 = np.array([[1, 2], [3, 4]])
    a2_duplicate = np.array([[1, 2], [3, 4]])

    out1, out2 = OrthogonalTop2AttemptGenerator.generate(a1, a2_duplicate)
    # Guaranteed non-redundancy: Attempt 2 must not equal Attempt 1
    assert not np.array_equal(out1, out2)
