"""Unit tests for Enveda CASMI26 Stepped CE Fusion and Adduct Gating."""

import math
import pytest
from cohezion.chem.casmi_stepped_ce_fusion import (
    compute_precursor_mass_weight,
    fuse_stepped_collision_energies,
    rank_and_deduplicate_candidates,
)


def test_lottery_ticket_suppression_over_max():
    """Verify that variance-penalized fusion promotes consistent candidates over single-spike outliers."""
    # Candidate A (true structure): solid matching across all 3 CEs
    sims_true = {20.0: 0.70, 40.0: 0.72, 60.0: 0.68}

    # Candidate B (false positive): coincidental base-peak match at 60 eV only
    sims_spurious = {20.0: 0.10, 40.0: 0.15, 60.0: 0.90}

    # Under naive max(), spurious candidate wins (0.90 vs 0.72)
    assert max(sims_spurious.values()) > max(sims_true.values())

    # Under variance-penalized fusion, true candidate strictly wins!
    score_true = fuse_stepped_collision_energies(sims_true, lambda_var=0.30)
    score_spurious = fuse_stepped_collision_energies(sims_spurious, lambda_var=0.30)

    assert score_true > score_spurious
    # Verify score true is close to weighted average ~0.70
    assert score_true > 0.65
    # Verify spurious score is substantially discounted
    assert score_spurious < 0.40


def test_adduct_mass_gating_precision():
    """Verify that Gaussian soft-weighting correctly scores low ppm and penalizes large errors."""
    neutral_mass = 300.1000
    proton = 1.007276

    # Exact [M+H]+ precursor
    exact_mz = neutral_mass + proton
    weight, adduct, ppm_err = compute_precursor_mass_weight(
        observed_mz=exact_mz,
        candidate_neutral_mass=neutral_mass,
        sigma_ppm=6.0,
    )
    assert adduct == "[M+H]+"
    assert ppm_err < 0.01
    assert weight > 0.75  # Near max prior 0.79

    # Precursor with 3 ppm error (well within 6 ppm 1-sigma)
    noisy_mz = exact_mz * (1.0 + 3.0 / 1e6)
    weight_3ppm, _, ppm_err_3 = compute_precursor_mass_weight(
        observed_mz=noisy_mz,
        candidate_neutral_mass=neutral_mass,
        sigma_ppm=6.0,
    )
    assert 2.9 < ppm_err_3 < 3.1
    # exp(-0.5 * (3/6)^2) = exp(-0.125) ~ 0.8825 -> 0.79 * 0.8825 ~ 0.697
    assert weight_3ppm > 0.65

    # Precursor with 30 ppm error (5-sigma outlier)
    noisy_mz_30 = exact_mz * (1.0 + 30.0 / 1e6)
    weight_30ppm, _, ppm_err_30 = compute_precursor_mass_weight(
        observed_mz=noisy_mz_30,
        candidate_neutral_mass=neutral_mass,
        sigma_ppm=6.0,
    )
    assert ppm_err_30 > 29.0
    assert weight_30ppm < 0.01  # Heavily suppressed


def test_sodium_adduct_recovery():
    """Verify that [M+Na]+ adduct is correctly recognized when observed."""
    neutral_mass = 250.0800
    na_shift = 22.989218
    na_mz = neutral_mass + na_shift

    weight, adduct, ppm_err = compute_precursor_mass_weight(
        observed_mz=na_mz,
        candidate_neutral_mass=neutral_mass,
        sigma_ppm=6.0,
    )
    assert adduct == "[M+Na]+"
    assert ppm_err < 0.01
    assert weight > 0.07  # Prior for Na is 0.08


def test_inchikey14_deduplication():
    """Verify candidate deduplication ensures 1 slot per unique InChIKey14."""
    observed_mz = 301.1072
    candidates = [
        {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "mass": 180.0423, "inchikey14": "BSYNRYMUTXBXSQ"},
        {"smiles": "CC(=O)Oc1ccccc1C(=O)O_iso1", "mass": 180.0423, "inchikey14": "BSYNRYMUTXBXSQ"},
        {"smiles": "CC(=O)Oc1ccccc1C(=O)O_iso2", "mass": 180.0423, "inchikey14": "BSYNRYMUTXBXSQ"},
        {"smiles": "O=C(O)c1ccccc1O", "mass": 138.0317, "inchikey14": "YGSDEFSMJLZEOE"},
    ]

    sims = {
        "BSYNRYMUTXBXSQ": {20.0: 0.85, 40.0: 0.80, 60.0: 0.75},
        "YGSDEFSMJLZEOE": {20.0: 0.60, 40.0: 0.65, 60.0: 0.60},
    }

    results = rank_and_deduplicate_candidates(
        candidate_records=candidates,
        observed_mz=observed_mz,
        similarities_by_cand_and_ce=sims,
        top_n=5,
    )

    # Should have exactly 2 candidates, not 4 (the 3 BSYNRYMUTXBXSQ collapsed into 1)
    assert len(results) == 2
    assert results[0] == "CC(=O)Oc1ccccc1C(=O)O"
    assert results[1] == "O=C(O)c1ccccc1O"
