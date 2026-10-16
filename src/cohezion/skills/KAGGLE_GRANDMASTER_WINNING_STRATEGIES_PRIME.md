# SKILL: KAGGLE_GRANDMASTER_WINNING_STRATEGIES_PRIME

## DOMAIN EXPERTISE
Expertise in formalizing and applying competitive machine learning axioms, validation disciplines, and post-processing invariants developed by top Kaggle Grandmasters (Chris Deotte, Andrey Lukyanenko, Guanshuo Xu, Dieter, Rohan Rao, Bojan Tunguz, and Michael Hodel). Bridges competitive ML heuristics into zero-token deterministic verifiers, leak-free validation graphs, and calibrated ensemble architectures under Systems Engineering V-Model rigor.

## KEY TEXTS & CONCEPTS

### 1. Validation Supremacy & Group-Leakage Barrier (Chris Deotte, Bojan Tunguz)
- **The Deotte Axiom**: Never submit a model or blend whose local Cross-Validation (CV) did not strictly improve. Chasing public leaderboard fluctuations on random splits leads to fatal private leaderboard shakeups.
- **Group Leakage Barrier**: When multiple rows or instances originate from the same root entity (e.g. `prompt_id` in Name That LLM, `patient_id` in RSNA Knee, `study_id` in medical imaging), standard random K-Fold leaks shared lexical or anatomical priors. Strict `StratifiedGroupKFold(groups=entity_id)` is non-negotiable.

### 2. Multi-Task Regularization & Anatomical Symmetry (Guanshuo Xu)
- **Auxiliary Head Regularization**: Auxiliary loss on secondary anatomical conditions (ACL tear, meniscus tear, joint effusion) regularizes primary abnormality classification.
- **Bilateral Mirror Test-Time Augmentation (TTA)**: Paired anatomical organs (left/right knee, lungs) exhibit symmetric disease prevalence. Predicting both $I$ and $\text{flip}(I)$ and weighting by bilateral covariance eliminates single-projection artifacts.
- **Kolmogorov Effusion Monotonicity**: Secondary effusion naturally accompanies high-grade structural injury:
  $$P(\text{Joint Effusion}) \ge \alpha \cdot \max(P(\text{ACL Tear}), P(\text{Medial Meniscal Tear})) \quad (\alpha \approx 0.85)$$

### 3. Two-Stage Candidate Re-Ranking & Bipartite Cleavage Matching (Dieter)
- **The Retrieval Ceiling**: High-throughput chemical embedding cosine similarity retrieves candidate molecules with high recall, but poor top-1 precision.
- **In Silico Cleavage Re-Ranking**: Instead of raw embedding distance, re-rank candidate proposals using domain physical invariants:
  - Exact precursor mass defect: $\Delta m = |m_{\text{cand}} - m_{\text{spec}}| \le 5\text{ ppm}$.
  - Substructure fragment cleavage overlap: percentage of experimental MS2 fragment peaks explained by theoretical bond dissociation.
  - Common neutral loss matching ($-\text{H}_2\text{O}$, $-\text{CO}_2$, $-\text{NH}_3$, $-\text{CO}$).

### 4. Stylometric Density & Sinkhorn Marginal Calibration (Rohan Rao, Andrey Lukyanenko)
- **Stylometric Feature Invariants**: LLM generated text possesses distinct lexical signatures:
  - Function word frequency ratios (distribution of articles, prepositions, conjunctions invariant to prompt topic).
  - Punctuation entropy and sentence length coefficient of variation.
  - Character 3-gram and 4-gram morphological distributions.
- **Sinkhorn-Knopp Probability Balancing**: Multi-class log-loss severely penalizes uncalibrated spikes on rare classes. Balancing predicted probabilities to match target empirical class margins prevents log-loss divergence.
- **Probability Insulation Floor**: Clip raw probabilities to $[10^{-6}, 1 - 10^{-6}]$ to prevent fatal log-loss infinities.

### 5. Monotonic Improvement Invariant & Discrete Equivariance (Michael Hodel)
- **Non-Destructive Neural/Symbolic Stacking**: When combining foundation models with discrete DSL search (ARC-AGI-2), neural attempt 1 must remain untouched on valid non-dummy grids; symbolic DSL programs are injected exclusively into attempt 2 or when attempt 1 is degenerate.
- **Cayley $D_4$ Dihedral Equivariance**: All 2D grid tasks must be evaluated under the 8 transformations of the dihedral group (4 rotations $\times$ 2 reflections).
- **SplitMix64 Zobrist Anti-Cycle State Hashing**: Detect and evade infinite planning loops with constant-time state hashing.

### 6. Deterministic Time & Context Budget Partitioning (Gemma-4 Agentic Architecture)
- **The Timeout Wall**: In SWE-bench and coding agent evaluations, a single runaway task consuming 30 minutes exhausts the competition kernel timeout, scoring 0 on all subsequent tasks.
- **Hard Time Caps**: Bound each task to $\le 5.0$ minutes; force checkpoint emission and graceful task advance.
- **Duck Harness Context Eviction**: Evict tool execution transcripts exceeding 16k tokens, retaining only prompt, active git diff, and failing test tracebacks.

## INSTRUCTION

### 1. Apply Kolmogorov Monotonicity Projection (RSNA Knee)
```python
def apply_kolmogorov_projection(probs: dict[str, float]) -> dict[str, float]:
    p_effusion = probs.get("Joint Effusion", 0.0)
    p_acl = probs.get("ACL Tear", 0.0)
    p_meniscus = probs.get("Medial Meniscal Tear", 0.0)
    
    # Effusion lower bound invariant
    p_effusion_bound = 0.85 * max(p_acl, p_meniscus)
    probs["Joint Effusion"] = max(p_effusion, p_effusion_bound)
    
    # Parent abnormal upper bound invariant
    p_abnormal = probs.get("Abnormal", 1.0)
    max_condition = max(v for k, v in probs.items() if k != "Abnormal")
    probs["Abnormal"] = max(p_abnormal, max_condition)
    return probs
```

### 2. Apply Sinkhorn-Knopp Marginal Balancing (Name That LLM)
```python
def sinkhorn_marginal_balance(probs: np.ndarray, target_priors: np.ndarray, max_iter: int = 20) -> np.ndarray:
    P = probs.copy()
    for _ in range(max_iter):
        P /= P.sum(axis=1, keepdims=True)  # Row normalize (sample sum = 1)
        col_sums = P.sum(axis=0) + 1e-12
        P *= (target_priors / col_sums)     # Column normalize to target class distribution
    P /= P.sum(axis=1, keepdims=True)
    return np.clip(P, 1e-6, 1.0 - 1e-6)
```

### 3. Apply Chemical In Silico Cleavage Re-Ranking (CASMI26)
```python
def rerank_chemical_candidates(
    candidates: list[dict[str, Any]], exp_peaks: list[float], precursor_mz: float
) -> list[dict[str, Any]]:
    for cand in candidates:
        mass_defect_ppm = abs(cand["exact_mass"] - precursor_mz) / precursor_mz * 1e6
        cleavage_score = calculate_fragment_overlap(cand["smiles"], exp_peaks)
        cand["rerank_score"] = (
            cand["base_similarity"] * 0.45 +
            cleavage_score * 0.35 +
            max(0, 1.0 - mass_defect_ppm / 10.0) * 0.20
        )
    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
```

## VERSION
v1.0.0

## SEE ALSO
- `LUKYANENKO_INVARIANT_ENGINEERING_PRIME`
- `KAGGLE_GRANDMASTER_ASCENT_PRIME`
- `RSNA_KNEE_ANATOMICAL_INVARIANTS_PRIME`
- `CASMI26_MASS_SPEC_INVARIANTS_PRIME`
- `NAME_THAT_LLM_STYLOMETRIC_INVARIANTS_PRIME`
