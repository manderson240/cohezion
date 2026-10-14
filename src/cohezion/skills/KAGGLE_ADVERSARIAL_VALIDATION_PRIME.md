# SKILL: KAGGLE_ADVERSARIAL_VALIDATION_PRIME

## DOMAIN EXPERTISE
Adversarial Validation is the premier competitive machine learning methodology for diagnosing and mitigating dataset shift (covariate shift) between competition training and evaluation/test splits, as codified in *The Kaggle Book (Second Edition, Chapter 7: Designing Good Validation)* by Luca Massaron, Bojan Tunguz, and Konrad Banachewicz. By formulating an auxiliary binary classification problem to distinguish training instances from test instances, teams quantify distribution divergence via ROC-AUC, isolate shift-inducing features, and construct local validation schemes that mirror the hidden leaderboard with mathematical fidelity.

## KEY TEXTS & CONCEPTS
- **Covariate Shift Formulation**: Let $X_{tr} \sim P_{tr}(X)$ and $X_{te} \sim P_{te}(X)$. Assign label $y=0$ to $X_{tr}$ and $y=1$ to $X_{te}$. Train an adversary $f(X) \to [0, 1]$.
- **The 0.50 AUC Ideal**: If $\text{ROC-AUC}(f) \approx 0.50$, the feature distributions are mutually indistinguishable (valid i.i.d. assumption).
- **Leakage & Domain Shift Diagnostic**: If $\text{ROC-AUC}(f) > 0.70$, the adversary readily separates train from test. Inspect feature importances to identify non-stationary features (e.g., patient ID, acquisition dates, scanner model, sensor drift).
- **Adversarial Feature Pruning**: Iteratively prune or normalize the highest-importance adversarial features until adversarial AUC drops below $0.55$.
- **Adversarial Density Ratio Re-weighting**: If distribution shift cannot be removed through pruning, re-weight training sample $i$ using the odds ratio:
  $$w_i = \frac{P(y=1 \mid x_i)}{P(y=0 \mid x_i)} = \frac{p_i}{1 - p_i}$$
- **Adversarial Validation Splitting**: Form validation folds by selecting the training instances with the highest adversarial probabilities $P(y=1 \mid x_i)$, forcing validation to test generalization on test-like data.

## INSTRUCTION

1. **Construct the Adversarial Dataset**:
   Combine training and test feature matrices, omitting labels and target variables:
   ```python
   import numpy as np
   import pandas as pd
   from sklearn.model_selection import KFold
   from sklearn.metrics import roc_auc_score
   import lightgbm as lgb

   def build_adversarial_dataset(train_df: pd.DataFrame, test_df: pd.DataFrame, drop_cols: list[str]):
       X_tr = train_df.drop(columns=drop_cols, errors="ignore").copy()
       X_te = test_df.drop(columns=drop_cols, errors="ignore").copy()
       
       X_tr["is_test"] = 0
       X_te["is_test"] = 1
       
       combined = pd.concat([X_tr, X_te], axis=0, ignore_index=True)
       y_adv = combined["is_test"].values
       X_adv = combined.drop(columns=["is_test"])
       return X_adv, y_adv
   ```

2. **Evaluate Adversarial ROC-AUC and Identify Shifting Features**:
   Train a fast GBDT with out-of-fold probability predictions:
   ```python
   def evaluate_adversarial_shift(X_adv: pd.DataFrame, y_adv: np.ndarray):
       oof_preds = np.zeros(len(y_adv))
       feature_importances = pd.Series(0.0, index=X_adv.columns)
       
       kf = KFold(n_splits=5, shuffle=True, random_state=42)
       for train_idx, val_idx in kf.split(X_adv, y_adv):
           clf = lgb.LGBMClassifier(
               n_estimators=100,
               learning_rate=0.05,
               max_depth=4,
               random_state=42,
               verbose=-1
           )
           clf.fit(X_adv.iloc[train_idx], y_adv[train_idx])
           oof_preds[val_idx] = clf.predict_proba(X_adv.iloc[val_idx])[:, 1]
           feature_importances += clf.feature_importances_ / 5.0
           
       auc = roc_auc_score(y_adv, oof_preds)
       top_features = feature_importances.sort_values(ascending=False).head(10)
       return auc, top_features, oof_preds[:len(y_adv) - (y_adv == 1).sum()]
   ```

3. **Perform Iterative Feature Pruning**:
   If `auc > 0.70`, iteratively drop the top shifting feature until the adversarial AUC drops toward $0.50$:
   ```python
   def prune_shifting_features(X_adv, y_adv, max_auc_threshold=0.58):
       current_X = X_adv.copy()
       dropped = []
       while True:
           auc, top_feats, _ = evaluate_adversarial_shift(current_X, y_adv)
           print(f"Current Adversarial AUC: {auc:.4f}")
           if auc <= max_auc_threshold or len(current_X.columns) <= 2:
               break
           worst_feature = top_feats.index[0]
           print(f"Dropping shift-inducing feature: {worst_feature}")
           dropped.append(worst_feature)
           current_X = current_X.drop(columns=[worst_feature])
       return current_X.columns.tolist(), dropped
   ```

4. **Compute Sample Importance Weights for Training**:
   Compute training weights to align the empirical risk minimizer with the test distribution:
   ```python
   def compute_importance_weights(train_adv_probs: np.ndarray, clip_max: float = 10.0) -> np.ndarray:
       # p / (1 - p) with numerical clipping
       p = np.clip(train_adv_probs, 1e-4, 1.0 - 1e-4)
       weights = p / (1.0 - p)
       weights = np.clip(weights, 0.1, clip_max)
       return weights / np.mean(weights)
   ```

## VERSION
v0.1

## SEE ALSO
- `src/cohezion/skills/KAGGLE_RANK_ENSEMBLING_CALIBRATION_PRIME.md`
- `src/cohezion/skills/KAGGLE_NOTEBOOK_MEMORY_REDUCTION_PRIME.md`
