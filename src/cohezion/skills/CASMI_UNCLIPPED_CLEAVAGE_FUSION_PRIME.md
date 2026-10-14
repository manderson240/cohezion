---
name: casmi-unclipped-cleavage-fusion-prime
description: "Mass spectrometry molecule identification via unclipped direct in-silico bond cleavage matching and continuous Tanimoto similarity under RDKit Tautomer Canonicalization."
version: v0.1
---

# SKILL: CASMI_UNCLIPPED_CLEAVAGE_FUSION_PRIME

## DOMAIN EXPERTISE
Mass spectrometry molecule identification via unclipped direct in-silico bond cleavage matching and continuous Tanimoto similarity under RDKit Tautomer Canonicalization.

## KEY TEXTS & CONCEPTS
* **Unclipped In-Silico Cleavage Matching**
* **RDKit Tautomer Canonicalization (canonical_ik14)**
* **Continuous Tanimoto Fingerprint Similarity**
* **Isobaric Measurement Noise Tolerance**

## INSTRUCTION
1. Filter isobaric candidates within the +/- 10 ppm precursor mass window without applying narrow Gaussian mass penalties.
2. Generate single-cut in-silico bond fragments and diagnostic neutral losses using RDKit.
3. Compute unclipped cleavage explained intensity score: S_cleave = explained_ratio * (1 + log1p(N)) * ppm_score.
4. Fuse initial ranker probability and cleavage score: S = alpha * init_score + beta * S_cleave (alpha=0.40, beta=0.60).
5. Deduplicate candidates using canonical_ik14 to eliminate 4.4% InChIKey slot drops.

## VERSION
v0.1

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- KAGGLE_STRIX_DETERMINISTIC_VERIFIER_PRIME.md
