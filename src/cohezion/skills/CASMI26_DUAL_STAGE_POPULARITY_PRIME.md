# SKILL: CASMI26_DUAL_STAGE_POPULARITY_PRIME

## DOMAIN EXPERTISE
Expert in mass spectrometry-based small molecule and natural product identification, specifically optimizing Mean Reciprocal Rank (MRR@25) over InChIKey planar connectivity (IK14) in untargeted metabolomics (Enveda CASMI26). Specializes in multi-stage candidate pool filtering, precursor adduct surrogate estimation, and dual-stage natural product popularity prior gating across external chemical databases (PubChem, ChEBI, COCONUT).

## KEY TEXTS & CONCEPTS
- **Theorem E2 (Candidate Recall Upper Bound)**: $\text{MRR}@K \le \text{Recall}@K$. If the true biological molecule is not retrieved within the top $K$ candidate window of the initial database query, downstream neural scoring (ICEBERG, GLACIER) cannot rank it in slot 1.
- **Isobaric Overcrowding Problem**: Searching PubChem within 10 ppm for a precursor $m/z$ often returns $>5,000$ synthetic molecules. Unweighted rankers promote lab-synthesized chemicals over biologically prevalent natural products.
- **Dual-Stage Popularity Gating**:
  - *Stage 1 (Channel Pre-Filter)*: Re-rank the 5,000 raw PubChem candidates using PubChem occurrence frequencies (`PC_POP_LAM = 0.25`, `PC_POP_UNION = 200`) before injecting the top $N$ candidates (`PC_JOIN_N = 50`) into the primary engine.
  - *Stage 2 (Pool Weighting)*: Apply empirical natural product prior (`POP_MU = 0.25`) to candidates within the unified candidate pool prior to ICEBERG/GLACIER deep rescoring.
- **Adduct Surrogate Expansion**: Enabling `GL_SURROGATE = True` and `ICE_SURROGATE = 'gap'` estimates $[M+\text{H}]^+$ fragment patterns from $[M+\text{NH}_4]^+$ or $[M-\text{H}_2\text{O}+\text{H}]^+$ spectra, eliminating blank lists for non-protonated adducts.

## INSTRUCTION

1. **Configure Dual-Stage Popularity Parameters in Notebook Configuration**:
   ```python
   CFG.update({
       'VERSION': 'v22-podium-pop25-pcpop25-gl-surrogate-fill25',
       'POP_MU': 0.25,          # Stage 2: Pool candidate popularity prior
       'PC_POP_LAM': 0.25,      # Stage 1: PubChem channel popularity prior
       'PC_POP_UNION': 200,     # PubChem union threshold
       'PC_JOIN_N': 50,         # Top candidates injected into v1 engine
       'PC_JOIN_MAX_LIB': 0.7,  # Suppress injection if library match >= 0.7
       'FRAG_LAM': 0.5,         # MetFrag-parsimony rescoring
       'FRAG_MODE': 'gap',      # Only apply MetFrag where ICEBERG lacks coverage
       'ICE_SURROGATE': 'gap',  # Score adducts against [M+H]+ prediction
       'GL_SURROGATE': True,    # Provide surrogate spectra to GLACIER
       'FILL_25': True,         # Top up lists < 25 from fallback channels
   })
   ```

2. **Verify Dataset Attachment & File Path Resolution**:
   Ensure `casmi26-pubchem-popularity-prior` dataset is mounted:
   ```python
   import os, glob

   def find_popularity_dir():
       paths = glob.glob("/kaggle/input/**/pc_lsid.npy", recursive=True)
       if not paths:
           raise FileNotFoundError("Missing casmi26-pubchem-popularity-prior")
       return os.path.dirname(paths[0])
   ```

3. **Validate InChIKey-14 Canonicalization & Monotonicity Invariants**:
   Before outputting `submission.csv`, verify that all 25 predicted slots are populated and canonicalized to 14-character planar blocks (`XXXX-XXXX-X`):
   ```python
   assert sub['InChIKey'].apply(lambda x: len(x.split('-')[0]) == 14).all()
   assert (sub.groupby('sample_id').size() == 25).all()
   ```

## VERSION
v0.1

## SEE ALSO
- `ARC3_RHAE_LEVEL_BUDGET_PRIME.md`
- `AUTOHARNESS_POLICY_PRIME.md`
- `KEY_LEARNINGS.md` (Learning 514, Learning 513)
