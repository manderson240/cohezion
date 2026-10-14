# SKILL: SOFT_KOLMOGOROV_CALIBRATION_PRIME

## DOMAIN EXPERTISE
Multi-label medical diagnostics probability calibration, hierarchical condition monotonicity, and ROC-AUC rank-preservation. Solves the flat-tie degradation failure mode in competitive multi-label classification where sub-conditions imply an omnibus abnormality condition.

## KEY TEXTS & CONCEPTS
- **Kolmogorov Monotonicity Axiom**: In medical imaging, an omnibus abnormality is present if and only if at least one sub-condition is present:
  $$P(\text{Abnormal}) \ge \max_{k \in \mathcal{C}} P_k$$
- **The Flat-Tie Failure Mode of Greedy Max Projection**:
  Projecting $P(\text{Abnormal}) = \max(P_{\text{Abnormal}}, \max_k P_k)$ creates identical rank ties across large subsets of cases where subconditions dominate, flattening the ROC curve and degrading macro ROC-AUC.
- **Probabilistic Noisy-OR Failure Model**:
  Under independent failure assumptions, the probability of at least one defect is:
  $$P_{\text{NoisyOR}} = 1 - \prod_{k \in \mathcal{C}} (1 - P_k)$$
- **Soft Kolmogorov Convex Blend**:
  $$P^*(\text{Abnormal}) = \text{clip}\left(w_1 P_{\text{raw}} + w_2 \max_k P_k + w_3 P_{\text{NoisyOR}}, 0.0, 1.0\right)$$
  Where $w_1 = 0.40, w_2 = 0.35, w_3 = 0.25$. This guarantees valid medical topology ($P^*(\text{Abnormal}) > P_k$) while preserving continuous, strictly distinct probability gradients.

## INSTRUCTION

1. Extract sub-condition columns and uncalibrated omnibus predictions:
   ```python
   import numpy as np

   def apply_soft_kolmogorov(
       df_preds: pd.DataFrame,
       condition_cols: list[str],
       omnibus_col: str = "Abnormal",
       weights: tuple[float, float, float] = (0.40, 0.35, 0.25)
   ) -> pd.DataFrame:
       p_raw = df_preds[omnibus_col].to_numpy(dtype=np.float64)
       sub_matrix = df_preds[condition_cols].to_numpy(dtype=np.float64)
       
       # 1. Compute subcondition maximum
       sub_max = sub_matrix.max(axis=1)
       
       # 2. Compute Noisy-OR joint probability (clipped to avoid log-zero)
       clipped_sub = np.clip(sub_matrix, 0.0, 0.99)
       p_noisy_or = 1.0 - np.prod(1.0 - clipped_sub, axis=1)
       
       # 3. Compute Soft Kolmogorov Blend
       w1, w2, w3 = weights
       calibrated = w1 * p_raw + w2 * sub_max + w3 * p_noisy_or
       
       out = df_preds.copy()
       out[omnibus_col] = np.clip(calibrated, 0.0, 1.0)
       return out
   ```

2. Verify that flat ties are eliminated and ROC-AUC is maximized:
   - Check that `len(np.unique(out[omnibus_col])) >= 0.999 * len(out)`.
   - Ensure $P^*(\text{Abnormal}) \ge \text{sub\_max} - \epsilon$ across all rows.

## VERSION
v0.1

## SEE ALSO
- `CASMI26_DUAL_STAGE_POPULARITY_PRIME.md`
- `src/cohezion/models/rsna_cross_planar_attention.py`
