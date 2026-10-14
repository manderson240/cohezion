---
name: casmi26-adduct-surrogate-fusion-prime
description: "High-resolution adduct consistency filtering, ICEBERG frame-shifted surrogate scoring, and 2-cut bond cleavage fusion for mass spectrometry molecule ID."
version: v0.1
---

# SKILL: CASMI26_ADDUCT_SURROGATE_FUSION_PRIME

## DOMAIN EXPERTISE
High-precision untargeted metabolomics identification for Enveda CASMI26 and mass spectrometry challenges using adduct-aware precursor gating, frame-shifted deep spectral surrogate alignment, in-silico bond cleavage matching, and RDKit Tautomer Canonicalization to maximize MRR@25.

## KEY TEXTS & CONCEPTS
* **Mass-Consistent Precursor Adduct Gating**: Explicit filtering of ionization adducts ($[M+H]^+$, $[M+NH_4]^+$, $[M+Na]^+$, $[M-H_2O+H]^+$) preventing false ~17 Da neutral mass drift.
* **Frame-Shifted Surrogate Alignment**: Re-aligning $[M+H]^+$ ICEBERG surrogate predictions to experimental adduct states via log-sum-exp mixture marginalization.
* **In-Silico 2-Cut Cleavage Matching**: Combinatorial bond fragmentation using atom bitmasks with bond dissociation energy (BDE) cost weighting.
* **Substructure Diagnostic Loss & Ion Probing**: Augmenting spectral scoring with chemical motif evidence (hexose 162.053 Da, glucuronide 176.032 Da).
* **Per-Query MAD Standardization**: Median/MAD scaling preventing dominant terms from swamping ranking variance.
* **RDKit Tautomer Canonicalization (`canonical_ik14`)**: Guaranteeing InChIKey14 deduplication to eliminate wasteful duplicate slots in top-25 ranking.

## INSTRUCTION

1. **Adduct Precursor Compatibility Filter**:
```python
ADDUCT_SHIFTS = {
    "[M+H]+": 1.00728,
    "[M+NH4]+": 18.03383,
    "[M+Na]+": 22.98922,
    "[M-H2O+H]+": -17.00329,
}

def get_plausible_adducts(candidate_neutral_mass: float, precursor_mz: float, ppm_tol: float = 10.0) -> list[str]:
    """Returns all ionization adducts consistent with measured precursor within ppm tolerance."""
    valid_adducts = []
    for adduct, shift in ADDUCT_SHIFTS.items():
        theoretical_mz = candidate_neutral_mass + shift
        error_ppm = abs(theoretical_mz - precursor_mz) / precursor_mz * 1e6
        if error_ppm <= ppm_tol:
            valid_adducts.append(adduct)
    return valid_adducts
```

2. **Frame-Shifted Surrogate Alignment ($S_{\text{ICE}}$)**:
```python
import numpy as np

def score_iceberg_adduct_mixture(pred_peaks: list[tuple[float, float]], exp_peaks: list[tuple[float, float]],
                                 plausible_adducts: list[str], tau: float = 0.1, gamma: float = 0.85) -> float:
    """
    Computes log-sum-exp over plausible adduct frames with frame-shift penalty gamma.
    """
    if not plausible_adducts:
        return -10.0

    adduct_priors = {"[M+H]+": 0.55, "[M+NH4]+": 0.15, "[M+Na]+": 0.15, "[M-H2O+H]+": 0.12}
    total_prior = sum(adduct_priors.get(a, 0.05) for a in plausible_adducts)

    cosines = []
    priors = []
    for a in plausible_adducts:
        shift_delta = ADDUCT_SHIFTS[a] - ADDUCT_SHIFTS["[M+H]+"]
        # Match peaks at p or p + shift_delta
        cos = compute_shifted_cosine(pred_peaks, exp_peaks, shift_delta, gamma)
        cosines.append(cos)
        priors.append(adduct_priors.get(a, 0.05) / total_prior)

    # Log-sum-exp marginalization
    lse = tau * np.log(np.sum([pi * np.exp(c / tau) for pi, c in zip(priors, cosines)]))
    return float(lse)
```

3. **In-Silico 2-Cut Fragment Matcher ($S_{\text{MF}}$)**:
```python
BOND_COSTS = {"SINGLE": 1.0, "AROMATIC": 2.0, "DOUBLE": 2.5, "TRIPLE": 3.5}

def score_metfrag_cleavages(fragments: list[dict], exp_peaks: list[tuple[float, float]],
                           tau_f: float = 2.0, ppm_tol: float = 15.0) -> float:
    """
    Calculates explained intensity weighted by fragment cleavage energy penalty.
    """
    total_intensity = sum(np.sqrt(intensity) for _, intensity in exp_peaks)
    if total_intensity <= 0:
        return 0.0

    matched_intensity = 0.0
    for mz_exp, intensity in exp_peaks:
        sqrt_i = np.sqrt(intensity)
        best_cost = 999.0
        for frag in fragments:
            if abs(frag["mz"] - mz_exp) / mz_exp * 1e6 <= ppm_tol:
                if frag["cost"] < best_cost:
                    best_cost = frag["cost"]
        if best_cost < 999.0:
            matched_intensity += sqrt_i * np.exp(-best_cost / tau_f)

    return float(matched_intensity / total_intensity)
```

4. **Robust Per-Query MAD Standardization & Multi-Head Fusion**:
```python
def mad_standardize(scores: np.ndarray, min_spread: float = 0.05) -> np.ndarray:
    med = np.median(scores)
    mad = np.median(np.abs(scores - med)) * 1.4826
    spread = max(mad, min_spread)
    return (scores - med) / spread

def fuse_candidate_scores(s_ice: np.ndarray, counts: np.ndarray, s_mf: np.ndarray,
                          substructure_delta: np.ndarray, lam_mf: float = 0.35) -> np.ndarray:
    z_ice = mad_standardize(s_ice)
    z_pop = mad_standardize(np.log1p(np.minimum(counts, 100000)))
    z_mf = mad_standardize(s_mf)
    total_score = z_ice + 0.42 * z_pop + lam_mf * z_mf + np.clip(substructure_delta, -1.0, 1.0)
    return total_score
```

5. **Deduplication via RDKit Tautomer Canonicalization**:
```python
def deduplicate_inchikey14(ranked_candidates: list[dict]) -> list[str]:
    """Ensures each of the top 25 positions has a distinct canonical InChIKey14."""
    seen_ik14 = set()
    output_ik14 = []
    for cand in ranked_candidates:
        ik14 = cand["canonical_ik14"]
        if ik14 not in seen_ik14:
            seen_ik14.add(ik14)
            output_ik14.append(ik14)
            if len(output_ik14) == 25:
                break
    return output_ik14
```

## VERSION
v0.1

## SEE ALSO
- CASMI_UNCLIPPED_CLEAVAGE_FUSION_PRIME.md
- KAGGLE_STRICT_MONOTONIC_ATTEMPT_ENSEMBLE_PRIME.md
- RETROSPECTIVE_SKILL.md
