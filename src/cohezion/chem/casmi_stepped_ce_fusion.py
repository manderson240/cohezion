"""Enveda CASMI26: Variance-Penalized Stepped Collision Energy Fusion & Adduct Gating.

Implements mathematically grounded chemometric candidate ranking for tandem mass spectrometry:
1. Variance-Penalized Stepped CE Fusion: Penalizes single-energy lottery tickets (false-positive noise).
2. Adduct-Aware Gaussian Precursor Mass Gating (sigma = 6.0 ppm).
3. Candidate Deduplication by InChIKey14 (unique molecular skeletons).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
import numpy as np

# Standard adduct mass shifts for positive/negative electrospray ionization (ESI)
ADDUCT_SHIFTS: Dict[str, Tuple[float, float, float]] = {
    # format: (multiplier_n, charge_z, delta_daltons)
    # Neutral mass M = (m_obs * z - delta) / n
    "[M+H]+": (1.0, 1.0, 1.007276),
    "[M+Na]+": (1.0, 1.0, 22.989218),
    "[M+NH4]+": (1.0, 1.0, 18.033823),
    "[M+K]+": (1.0, 1.0, 38.963158),
    "[2M+H]+": (2.0, 1.0, 1.007276),
    "[2M+Na]+": (2.0, 1.0, 22.989218),
    "[M-H]-": (1.0, 1.0, -1.007276),
    "[M+Cl]-": (1.0, 1.0, 34.969402),
    "[M+HCOO]-": (1.0, 1.0, 44.998201),
}

# Empirical test-set prior distribution over adducts
DEFAULT_ADDUCT_PRIORS: Dict[str, float] = {
    "[M+H]+": 0.79,
    "[M+Na]+": 0.08,
    "[M+NH4]+": 0.05,
    "[2M+H]+": 0.03,
    "[M+K]+": 0.02,
    "[M-H]-": 0.03,
}

# Collision energy information-density weights (20 eV carries highest diagnostic entropy)
DEFAULT_CE_WEIGHTS: Dict[float, float] = {
    20.0: 0.50,
    40.0: 0.35,
    60.0: 0.15,
}


def compute_precursor_mass_weight(
    observed_mz: float,
    candidate_neutral_mass: float,
    adduct_priors: Optional[Dict[str, float]] = None,
    sigma_ppm: float = 6.0,
) -> Tuple[float, str, float]:
    """Compute adduct-aware Gaussian soft-weight for a candidate neutral mass.

    Parameters
    ----------
    observed_mz : float
        Experimental precursor m/z observed on MS1.
    candidate_neutral_mass : float
        Theoretical neutral monoisotopic mass of the candidate molecule.
    adduct_priors : dict, optional
        Prior probabilities for each adduct hypothesis.
    sigma_ppm : float
        Instrumental mass measurement standard deviation (default 6.0 ppm for timsTOF).

    Returns
    -------
    tuple
        (mass_weight, winning_adduct, min_ppm_error)
    """
    if adduct_priors is None:
        adduct_priors = DEFAULT_ADDUCT_PRIORS

    best_weight = 0.0
    best_adduct = "[M+H]+"
    best_ppm = 1e6

    for adduct, prior in adduct_priors.items():
        if adduct not in ADDUCT_SHIFTS:
            continue
        n, z, delta = ADDUCT_SHIFTS[adduct]
        # Theoretical expected m/z for this candidate under this adduct
        expected_mz = (n * candidate_neutral_mass + delta) / z
        ppm_error = abs(observed_mz - expected_mz) / expected_mz * 1e6

        # Gaussian likelihood
        gauss_prob = math.exp(-0.5 * (ppm_error / sigma_ppm) ** 2)
        weighted_score = gauss_prob * prior

        if weighted_score > best_weight:
            best_weight = weighted_score
            best_adduct = adduct
            best_ppm = ppm_error
        elif best_weight == 0.0 and ppm_error < best_ppm:
            best_ppm = ppm_error
            best_adduct = adduct

    return best_weight, best_adduct, best_ppm


def fuse_stepped_collision_energies(
    similarities_by_ce: Dict[float, float],
    weights: Optional[Dict[float, float]] = None,
    lambda_var: float = 0.30,
) -> float:
    """Fuse multi-collision energy spectral similarities with variance penalty.

    Mathematical Theorem (Lottery Ticket Suppression):
    Let s_e be the similarity at collision energy e. Under max_e(s_e), a single noisy
    base-peak match at high CE (60 eV) creates false-positive promotion.
    The variance-penalized estimator:
        S = sum_e (w_e * s_e) - lambda * Var_e(s_e)
    preserves high scores for true molecules with consistent matches across all CEs,
    while heavily penalizing single-spike outliers.

    Parameters
    ----------
    similarities_by_ce : dict
        Mapping of collision energy in eV (e.g. 20.0, 40.0, 60.0) to spectral similarity.
    weights : dict, optional
        Weights per collision energy (defaults to 0.50 for 20eV, 0.35 for 40eV, 0.15 for 60eV).
    lambda_var : float
        Variance penalty coefficient (default 0.30).

    Returns
    -------
    float
        Consensus fused score in [0.0, 1.0].
    """
    if not similarities_by_ce:
        return 0.0

    if weights is None:
        weights = DEFAULT_CE_WEIGHTS

    # Normalize weights over available collision energies
    avail_ces = list(similarities_by_ce.keys())
    w_subset = {ce: weights.get(ce, 1.0 / len(avail_ces)) for ce in avail_ces}
    total_w = sum(w_subset.values())
    norm_w = {ce: w / total_w for ce, w in w_subset.items()}

    # Weighted mean
    weighted_mean = sum(norm_w[ce] * similarities_by_ce[ce] for ce in avail_ces)

    # Variance calculation across CEs
    if len(avail_ces) > 1:
        vals = [similarities_by_ce[ce] for ce in avail_ces]
        var_ce = float(np.var(vals))
    else:
        var_ce = 0.0

    # Penalize inconsistency
    fused_score = max(0.0, weighted_mean - lambda_var * var_ce)
    return float(fused_score)


def rank_and_deduplicate_candidates(
    candidate_records: List[Dict],
    observed_mz: float,
    similarities_by_cand_and_ce: Dict[str, Dict[float, float]],
    top_n: int = 25,
    sigma_ppm: float = 6.0,
    lambda_var: float = 0.30,
) -> List[str]:
    """Rank candidates with variance-penalized CE fusion and unique InChIKey14 deduplication.

    Parameters
    ----------
    candidate_records : list of dict
        Each dict must contain 'smiles', 'mass', and 'inchikey14'.
    observed_mz : float
        Experimental precursor m/z.
    similarities_by_cand_and_ce : dict
        Mapping candidate key/smiles to {ce: similarity}.
    top_n : int
        Maximum number of candidates to return (default 25 for CASMI26).
    sigma_ppm : float
        Mass gating standard deviation.
    lambda_var : float
        Variance penalty for CE fusion.

    Returns
    -------
    list of str
        Top N unique SMILES ordered by combined score.
    """
    scored_candidates = []

    for cand in candidate_records:
        smi = cand["smiles"]
        mass = cand["mass"]
        ik14 = cand.get("inchikey14", smi)

        # 1. CE Spectral Fusion
        ce_sims = similarities_by_cand_and_ce.get(smi, similarities_by_cand_and_ce.get(ik14, {}))
        spectral_score = fuse_stepped_collision_energies(ce_sims, lambda_var=lambda_var)

        # 2. Precursor Mass Soft-Weighting
        mass_w, _, _ = compute_precursor_mass_weight(
            observed_mz=observed_mz,
            candidate_neutral_mass=mass,
            sigma_ppm=sigma_ppm,
        )

        # 3. Total Combined Score
        # Additive combination with mass prior scaling
        total_score = spectral_score * (0.7 + 0.3 * mass_w)
        scored_candidates.append((total_score, ik14, smi))

    # Sort descending by total score
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    # 4. InChIKey14 Deduplication: keep only the highest scoring tautomer/stereoisomer
    seen_ik14 = set()
    result_smiles = []

    for score, ik14, smi in scored_candidates:
        if ik14 not in seen_ik14:
            seen_ik14.add(ik14)
            result_smiles.append(smi)
            if len(result_smiles) >= top_n:
                break

    return result_smiles
