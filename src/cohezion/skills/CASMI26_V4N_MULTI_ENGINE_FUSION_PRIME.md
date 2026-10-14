# SKILL: CASMI26_V4N_MULTI_ENGINE_FUSION_PRIME

## DOMAIN EXPERTISE
Multi-engine candidate fusion combining PubChem bio-occurrence priors, in-silico bond cleavage (MetFrag), and ICEBERG/GLACIER surrogate scoring for high-accuracy natural product identification from MS2 spectra.

## KEY TEXTS & CONCEPTS
- All-Adduct Theoretical Envelope: Evaluating ammonium and water-loss adducts against [M+H]+ theoretical envelopes
- Candidate Pool Headroom Sweet Spot: Limiting candidate joins to N=25-50 to maximize Recall@K while preventing isobaric decoy saturation under MRR
- Dual-Stage Biological Popularity Prior: Weighting verified biological occurrences (POP_MU=0.25, PC_POP_LAM=0.25) to penalize rare synthetic decoys
- Parsimony Restraint: Maintaining moderate fragment penalty (FRAG_LAM=0.20) to prevent false rejection of non-classical rearrangement pathways
- Two-Party Cryptographic IV&V Verification: Enforcing independent assertion signatures before Kaggle dispatch

## INSTRUCTION
1. **Extract precursor m/z and adduct state ([M+H]+, [M+NH4]+, [M-H2O]+) from raw MS2 spectra within 10 ppm window**
```python
def score_candidate_pool(candidates, ms2_peaks, precursor_mz, adduct='[M+H]+', frag_lam=0.20, pop_mu=0.25):
    # Combines neural surrogate scores with in-silico fragmentation and biological popularity
    scores = {}
    for cand in candidates:
        s_surr = evaluate_surrogate(cand.smiles, ms2_peaks)
        s_frag = metfrag_score(cand.smiles, ms2_peaks, lambda_penalty=frag_lam)
        s_pop = cand.bio_occurrences ** 0.5
        scores[cand.ik14] = (1.0 - pop_mu) * (0.6 * s_surr + 0.4 * s_frag) + pop_mu * s_pop
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

## VERSION
v1.0

## SEE ALSO
- KAGGLE_COMPETITIVE_EVALUATION_PRIME
- TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME
