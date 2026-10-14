# SKILL: KAGGLE_RANK_ENSEMBLING_CALIBRATION_PRIME

## DOMAIN EXPERTISE
Rank Ensembling and Calibration is the elite mathematical ensembling methodology for competitive machine learning, as formulated in *The Kaggle Book (Second Edition, Chapter 10: Ensembling with Blending and Stacking Solutions)* by Luca Massaron, Bojan Tunguz, and Konrad Banachewicz. By mapping disparate model predictions to uniform empirical quantiles prior to linear or simplex blending, practitioners immunize ensembles against miscalibration and scale distortion, while post-blend Kolmogorov monotonicity projections guarantee structural coherence in hierarchical multi-label domains.

## KEY TEXTS & CONCEPTS
- **Quantile Rank Averaging**: Given $M$ model predictions $p^{(1)}, \dots, p^{(M)}$, convert raw scores to normalized rank percentiles:
  $$r_i^{(m)} = \frac{\operatorname{rank}\left(p_i^{(m)}\right)}{N} \in [0, 1]$$
  This equalizes the variance across disparate model families (e.g. GBDTs, ConvNets, Transformers), preventing overconfident models from dominating the blend.
- **Rank Averaging vs. Probability Averaging**:
  - In rank-based evaluation metrics (ROC-AUC, PR-AUC, Gini coefficient), rank averaging is invariant to monotonic transformations and strictly outperforms raw probability averaging.
  - In log-loss metrics, apply post-rank probability recalibration (e.g., Platt scaling or isotonic regression) to restore calibrated posterior margins.
- **Nelder-Mead Simplex Weight Optimization**: Optimize model blend weights $w_1, \dots, w_M$ directly against the out-of-fold (OOF) competition evaluation metric using bounded simplex optimization ($\sum w_m = 1, w_m \ge 0$).
- **Kolmogorov Monotonicity Invariant**: In hierarchical medical diagnosis (e.g., RSNA Knee Detection), the presence of any specific sub-pathology $k$ implies the general condition "Abnormal":
  $$P(\text{Abnormal}) \ge \max_{k \in \text{conditions}} P(k)$$
  Any rank transformation applied independently per column can violate this invariant, causing severe leaderboard score degradation. Re-project the maximum across sub-pathologies back to the parent condition.

## INSTRUCTION

1. **Perform Column-Wise Quantile Rank Normalization**:
   Transform raw model predictions to uniform percentile ranks:
   ```python
   import numpy as np
   import pandas as pd
   from scipy.stats import rankdata

   def rank_normalize_predictions(preds: np.ndarray) -> np.ndarray:
       """Convert array of predictions to percentile ranks in [0, 1]."""
       return rankdata(preds, method="average") / len(preds)
   ```

2. **Optimize Out-of-Fold Blend Weights via Nelder-Mead Simplex**:
   Find the optimal non-negative convex combination of models on OOF data:
   ```python
   from scipy.optimize import minimize
   from sklearn.metrics import roc_auc_score

   def optimize_blend_weights(oof_predictions: list[np.ndarray], y_true: np.ndarray) -> np.ndarray:
       """Find optimal ensemble weights maximizing ROC-AUC on OOF predictions."""
       M = len(oof_predictions)
       
       # Convert each model OOF to ranks
       ranked_oof = [rank_normalize_predictions(p) for p in oof_predictions]
       
       def loss_func(weights):
           # Softmax projection to enforce simplex constraints
           w = np.exp(weights) / np.sum(np.exp(weights))
           blend = np.zeros_like(ranked_oof[0])
           for i in range(M):
               blend += w[i] * ranked_oof[i]
           return -roc_auc_score(y_true, blend)
       
       init_weights = np.zeros(M)
       res = minimize(loss_func, init_weights, method="Nelder-Mead")
       optimal_w = np.exp(res.x) / np.sum(np.exp(res.x))
       return optimal_w
   ```

3. **Enforce Kolmogorov Monotonicity Projection**:
   Re-project composite parent probabilities to satisfy the probability calculus invariant:
   ```python
   def enforce_kolmogorov_monotonicity(
       pred_df: pd.DataFrame,
       parent_col: str = "Abnormal",
       subcondition_cols: list[str] | None = None
   ) -> pd.DataFrame:
       """Guarantee P(parent) >= max(P(subconditions)) across all rows."""
       df = pred_df.copy()
       if subcondition_cols is None:
           subcondition_cols = [c for c in df.columns if c != parent_col and c != "row_id"]
       
       max_subconditions = df[subcondition_cols].max(axis=1)
       df[parent_col] = np.maximum(df[parent_col].values, max_subconditions.values)
       
       # AutoHarness verification invariant
       violations = (df[parent_col] < max_subconditions).sum()
       assert violations == 0, f"Found {violations} Kolmogorov monotonicity violations!"
       return df
   ```

4. **Combine Rank Blending, Simplex Weights, and Monotonicity**:
   Execute the full ensembling pipeline:
   ```python
   def assemble_sota_ensemble(
       model_test_preds: dict[str, pd.DataFrame],
       weights: dict[str, float],
       parent_col: str = "Abnormal"
   ) -> pd.DataFrame:
       """Full rank ensembling pipeline with monotonicity guarantee."""
       first_df = next(iter(model_test_preds.values()))
       result = pd.DataFrame(index=first_df.index)
       
       cols = [c for c in first_df.columns if c != "row_id"]
       for col in cols:
           ranked_sum = np.zeros(len(first_df))
           for model_name, df in model_test_preds.items():
               w = weights[model_name]
               ranked_sum += w * rank_normalize_predictions(df[col].values)
           result[col] = ranked_sum
           
       # Re-project monotonicity
       if parent_col in result.columns:
           result = enforce_kolmogorov_monotonicity(result, parent_col=parent_col)
           
       return result
   ```

## VERSION
v0.1

## SEE ALSO
- `src/cohezion/skills/KAGGLE_ADVERSARIAL_VALIDATION_PRIME.md`
- `src/cohezion/skills/KAGGLE_NOTEBOOK_MEMORY_REDUCTION_PRIME.md`
- `src/cohezion/skills/HARNESS_ENGINEERING_ETCLOVG_PRIME.md`
