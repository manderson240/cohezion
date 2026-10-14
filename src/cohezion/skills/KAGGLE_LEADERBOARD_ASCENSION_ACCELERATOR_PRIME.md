# SKILL: KAGGLE_LEADERBOARD_ASCENSION_ACCELERATOR_PRIME

## DOMAIN EXPERTISE
Kaggle Leaderboard Ascension Accelerator is the mathematical and operational framework for climbing to the top of competitive machine learning leaderboards. Synthesizing principles from *The Kaggle Book (Second Edition)* by Massaron, Tunguz, and Banachewicz with sovereign agentic autonomy, this skill operationalizes multi-competition quota scheduling, copula rank normalization with marginal quantile reconstruction, Kolmogorov monotonicity projection, dual neural fingerprint ensembling, and deterministic AutoHarness Two-Party verification to secure gold medal and podium positions.

## KEY TEXTS & CONCEPTS
- **Daily Quota Maximization & Reset Cadence**:
  - Competitions enforce strict submission caps (e.g., 1/day for ARC-Prize tracks; 5/day for RSNA Knee and CASMI26).
  - All quotas reset strictly at `00:00:00 UTC`. Automated daemons dispatch primary candidates at `00:00:05 UTC` and space iterative ablation slots throughout the day.
- **Copula Rank Alignment & Quantile Inversion**:
  - In multi-label and rank-based evaluation metrics (Macro ROC-AUC), raw probabilities across heterogeneous architectures (ConvNeXt, CoAtNet, Swin) suffer from scale distortion.
  - Converting each model's predictions to empirical percentile ranks $r_i^{(m)} = \operatorname{rank}(p_i^{(m)}) / N$ immunizes the ensemble against calibration bias.
  - For log-loss and probability-sensitive objectives, invert blended copula ranks through the marginal quantile function $p^* = F_{\text{reference}}^{-1}(r_{\text{blend}})$.
- **Kolmogorov Monotonicity & Parsimony Gating**:
  - In hierarchical domains, enforce the probability calculus inequality $P(\text{Parent}) \ge \max_{k} P(\text{Subcondition}_k)$.
  - In mass spectrometry molecule ID (CASMI26), combine dual neural fingerprint embeddings (FPNet) with formula-parsimonious candidate ranking ($N=25$) and all-adduct surrogate scoring.
- **Monadic Markov Engine & Orthogonal Cycle Escape (ARC-AGI-3/2)**:
  - In active exploration benchmarks, break local behavioral traps by injecting orthogonal action pulses when state cycles exceed loop watchdogs ($L \ge 8$).
  - Pre-filter common geometric transforms via deterministic R-Zero transformation rules (0 ms latency).
- **Two-Party Cryptographic IV&V Gate**:
  - Every competition candidate MUST hold an independent HMAC-SHA256 assertion from `ivv-authority-daemon-v1` before hitting the Kaggle API. Creator agents cannot verify their own artifacts.

## INSTRUCTION

1. **Audit Live Standings and Compute Prize Gaps**:
   Extract exact competition ranks and podium gaps across all active monetary tracks:
   ```python
   from scripts.kaggle.leaderboard_inspector import audit_all_competitions
   
   results = audit_all_competitions(sync_surreal=True)
   for r in results:
       print(f"Comp: {r.name} | Rank: {r.rank}/{r.total_teams} | Score: {r.score} | Gap to R3: {r.gap_r3}")
   ```

2. **Execute Copula Rank Alignment for Heterogeneous Ensembles**:
   Perform uniform quantile ranking across multiple model prediction streams:
   ```python
   import numpy as np
   import pandas as pd
   from scipy.stats import rankdata

   def rank_blend(preds_a: np.ndarray, preds_b: np.ndarray, weight_a: float = 0.5) -> np.ndarray:
       """Blend two prediction streams using percentile rank projection."""
       rank_a = rankdata(preds_a, method="average") / len(preds_a)
       rank_b = rankdata(preds_b, method="average") / len(preds_b)
       return weight_a * rank_a + (1.0 - weight_a) * rank_b
   ```

3. **Enforce Monotonic Attempt-2 DSL Injection for ARC Competitions**:
   Preserve Attempt-1 neural hypotheses while non-destructively populating Attempt-2:
   ```python
   def inject_monotonic_attempt2(target_pred: dict, dsl_solution: list[list[int]]) -> None:
       cur_1 = target_pred.get("attempt_1")
       cur_2 = target_pred.get("attempt_2")
       if not cur_1 or cur_1 == "invalid":
           target_pred["attempt_1"] = dsl_solution
       elif not cur_2 or cur_2 == cur_1 or cur_2 == "invalid":
           if dsl_solution != cur_1:
               target_pred["attempt_2"] = dsl_solution
   ```

4. **Dispatch Notebook Code Submissions with Dynamic Versioning**:
   Dispatch submissions to code competitions with zero guesswork:
   ```bash
   PYTHONPATH=src .venv/bin/python scripts/kaggle/kaggle_submit.py notebook \
     -c <competition-slug> \
     -k manderson240/<kernel-slug> \
     -f submission.csv \
     -m "Cohezion SOTA: Verified Description" \
     --code-path <local-notebook-path>
   ```

## VERSION
v1.0

## SEE ALSO
- `KAGGLE_GRANDMASTER_ASCENT_PRIME.md`
- `KAGGLE_RANK_ENSEMBLING_CALIBRATION_PRIME.md`
- `KAGGLE_STRICT_MONOTONIC_ATTEMPT_ENSEMBLE_PRIME.md`
- `AUTOHARNESS_PRIME.md`
- `TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME.md`
- `R_ZERO_CHALLENGER_PRIME.md`
