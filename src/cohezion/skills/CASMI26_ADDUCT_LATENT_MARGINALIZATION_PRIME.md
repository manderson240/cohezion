# SKILL: CASMI26_ADDUCT_LATENT_MARGINALIZATION_PRIME

## DOMAIN EXPERTISE
High-Resolution Mass Spectrometry Adduct Latent Marginalization & Cross-Adduct Consistency

## KEY TEXTS & CONCEPTS
- Latent-variable adduct marginalization P(spectrum | candidate) = sum P(peaks | candidate, adduct) P(adduct | candidate)
- Cross-adduct consistency potential rewarding multi-adduct concordance
- Precursor neutral mass reconstruction across [M+H]+, [M+Na]+, [M+NH4]+, [M-H2O]+
- Stepped collision energy (10, 20, 40 eV) spectral weighting

## INSTRUCTION
1. **Reconstruct multiple candidate neutral precursor masses M_neutral from detected parent m/z across adduct hypotheses.**
```python
def reconstruct_neutral_mass(mz_observed: float, adduct: str) -> float:
    shifts = {"[M+H]+": 1.007276, "[M+Na]+": 22.989218, "[M+NH4]+": 18.033823}
    return mz_observed - shifts[adduct]
```

2. **Filter candidate molecules within <10 ppm tolerance of any reconstructed neutral mass.**
```python
def adduct_marginal_likelihood(candidate, spectrum, adducts, priors):
    return sum(priors[a] * match_score(candidate, spectrum, a) for a in adducts)
```

3. **Marginalize over adduct priors calibrated on E007 natural product spectra.**
```python
# Cross-adduct log-linear concordance bonus
if len(matching_adducts) > 1: score += 0.15 * log(len(matching_adducts))
```

## VERSION
v0.1

## SEE ALSO
- KAGGLE_COMPETITIVE_EVALUATION_PRIME
- TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME
