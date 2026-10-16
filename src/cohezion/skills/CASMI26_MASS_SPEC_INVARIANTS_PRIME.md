---
name: casmi26-mass-spec-invariants
metadata:
  version: "1.0.0"
description: >-
  Chemical mass spectrometry invariants, dual forward/backward predictors, neutral loss parsimony, and candidate re-ranking for Enveda CASMI26.
---

# SKILL: CASMI26_MASS_SPEC_INVARIANTS_PRIME

## DOMAIN EXPERTISE
Expertise in high-resolution tandem mass spectrometry (MS/MS), electrospray ionization adduct formation ($[M+H]^+$, $[M+Na]^+$, $[M-H]^-$), candidate retrieval and re-ranking, forward spectrum prediction, neutral loss cleavage trees, and natural product de novo molecular discovery.

## KEY TEXTS & CONCEPTS
- **The Candidate Re-Ranking Ceiling**: Candidate retrieval easily achieves $>84\%$ recall in Regime A and $>58\%$ in Regime B. The true competitive differentiator is the re-ranking score function evaluating candidate SMILES against observed m/z peaks.
- **Dual Forward/Backward Modeling**: 
  - *Backward retriever*: Maps $(m/z, \text{intensity}, \text{adduct}) \to \text{candidate formulas/SMILES}$.
  - *Forward predictor*: Evaluates candidate SMILES $+ \text{adduct} \to \text{simulated MS/MS peaks}$. Scores cosine spectral entropy similarity between simulated fragments and experimental spectra.
- **Stoichiometric Monoisotopic Adduct Mass Defect**: Exact precursor mass error must be $\le 15.0\text{ ppm}$ under the specified adduct ionization mode:
  $$\Delta m_{\text{ppm}} = 10^6 \times \frac{|m_{\text{obs}} - (m_{\text{mono}} + m_{\text{adduct}})|}{m_{\text{mono}} + m_{\text{adduct}}}$$
- **Fragment Neutral Loss Parsimony**: Peak differences $\Delta m = m_i - m_j$ must match biochemically parsimonious neutral losses ($\text{H}_2\text{O}: 18.0106$, $\text{CO}: 27.9949$, $\text{NH}_3: 17.0265$, $\text{CO}_2: 43.9898$). Candidate structures unable to explain major neutral loss ladders are penalized.
- **Quarantine the Dummy Test Leak**: Public notebooks assigning the 400 visible `test.parquet` dummy IDs to rank 1 overfit the public dummy artifact. Real evaluation replaces these rows with hidden natural product spectra. Never join or condition on visible dummy molecule IDs.
- **NIST Data Disqualification Rule**: NIST-20/23 datasets carry restrictive non-redistribution licenses. Solutions trained on or utilizing NIST weights are strictly disqualified from commercial prize eligibility.

## INSTRUCTION
1. Compute Stoichiometric Adduct Invariant Filter:
   ```python
   ADDUCT_MASSES = {
       "[M+H]+": 1.007276,
       "[M+Na]+": 22.989218,
       "[M-H]-": -1.007276,
   }

   def verify_adduct_mass_defect(obs_mz: float, mono_mass: float, adduct: str, max_ppm: float = 15.0) -> bool:
       expected = mono_mass + ADDUCT_MASSES[adduct]
       ppm = abs(obs_mz - expected) / expected * 1e6
       return ppm <= max_ppm
   ```

2. Re-Rank Candidates via Neutral Loss and Forward Spectral Match:
   ```python
   def rank_candidates_by_parsimony(candidates: list[dict], observed_peaks: list[float], observed_losses: list[float]) -> list[dict]:
       for cand in candidates:
           pred_peaks = set(cand.get("predicted_peaks", []))
           matched_peaks = sum(1 for p in observed_peaks if any(abs(p - pp) < 0.02 for pp in pred_peaks))
           cand["spectral_score"] = matched_peaks / max(1, len(observed_peaks))
       return sorted(candidates, key=lambda c: c["spectral_score"], reverse=True)
   ```

## VERSION
v1.0

## SEE ALSO
- `first-principles-invariant-science`
- `lukyanenko-invariant-engineering`
