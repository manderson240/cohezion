# SKILL: KAGGLE_STRICT_MONOTONIC_ATTEMPT_ENSEMBLE_PRIME

## DOMAIN EXPERTISE
Mathematical multi-hypothesis ensembling, monotonic attempt invariants, and copula rank alignment for multi-guess and multi-label Kaggle code competitions (ARC Prize ARC-AGI-2/3, RSNA Knee Abnormality Detection, Enveda CASMI26).

## KEY TEXTS & CONCEPTS
- *The Kaggle Book (2nd Edition)* (Packt, 2025): Chapters 7, 8, 10 — Adversarial Validation, Ensembling, and Calibration.
- Monotonic Improvement Invariant: For $K$-guess competitions (ARC-AGI-2/3), secondary heuristic models must never destroy distinct primary neural predictions ($A_1 \neq A_2$).
- Copula Rank Alignment: Under macro ROC-AUC, heterogeneous model heads (e.g. CNN vs ViT) must be mapped to standard uniform copulas $U(0, 1)$ via column-wise percentile ranking before weighted combination to eliminate variance dominance.
- Flat-top isobar tolerance: Mass spectral candidate reranking must avoid Gaussian penalties within the precursor isobar window.

## INSTRUCTION

### 1. Enforcing Monotonic Attempt Invariant in $K$-Guess Competitions
When combining a primary neural model (e.g. Qwen3-4B LoRA) with a symbolic/heuristic synthesizer (e.g. DSL program synthesis) in a $K=2$ setting:

```python
def resolve_monotonic_attempts(
    target_pred: dict,
    dsl_solution: list | None,
    is_invalid_fn: callable,
) -> dict:
    """Guarantees Score(Combined) >= Score(Neural Baseline)."""
    cur_attempt_1 = target_pred.get("attempt_1")
    cur_attempt_2 = target_pred.get("attempt_2")

    # 1. If attempt_1 is invalid or dummy [[0]], replace with DSL
    if is_invalid_fn(cur_attempt_1):
        if dsl_solution and not is_invalid_fn(dsl_solution):
            target_pred["attempt_1"] = dsl_solution

    # 2. Strict Monotonic Invariant: Only inject DSL into attempt_2 if
    #    attempt_2 is invalid OR identical to attempt_1!
    #    If the neural model produced two distinct valid guesses (attempt_1 != attempt_2),
    #    KEEP BOTH to prevent destroying valid neural wins.
    elif is_invalid_fn(cur_attempt_2) or (cur_attempt_2 == cur_attempt_1):
        if dsl_solution and not is_invalid_fn(dsl_solution):
            if dsl_solution != cur_attempt_1:
                target_pred["attempt_2"] = dsl_solution

    return target_pred
```

### 2. Copula Rank Alignment for Macro ROC-AUC Ensembling
Before linearly weighting multiple model predictions $P_1, P_2, \dots, P_M$ on multi-label targets:

```python
import numpy as np
import pandas as pd

def copula_rank_blend(
    df_primary: pd.DataFrame,
    df_secondary: pd.DataFrame,
    labels: list[str],
    weights: dict[str, float],
) -> pd.DataFrame:
    """Equalizes marginal variances to Var(R) = 1/12 via copula rank normalization."""
    # 1. Project both arms to uniform copula percentiles [0, 1]
    r_primary = df_primary[labels].rank(method="average", pct=True)
    r_secondary = df_secondary[labels].rank(method="average", pct=True)

    # 2. Linear combination on aligned copula manifold
    df_blend = df_primary.copy()
    for col in labels:
        w = float(weights.get(col, 0.50))
        df_blend[col] = (1.0 - w) * r_primary[col] + w * r_secondary[col]

    # 3. Final intra-column percentile ranking for ROC-AUC invariance
    df_blend[labels] = df_blend[labels].rank(method="average", pct=True)
    return df_blend
```

### 3. Verification Protocol
1. Check that AST syntax parses across all cells.
2. Run adversarial test suite in `tests/ivv/`.
3. Obtain cryptographic assertion from `IVVAuthorityService`.
4. Dispatch via `scripts/kaggle/kaggle_submit.py notebook ... -w`.

## VERSION
v1.0

## SEE ALSO
- `HARNESS_ENGINEERING_ETCLOVG_PRIME.md`
- `KAGGLE_RANK_ENSEMBLING_CALIBRATION_PRIME.md`
- `KAGGLE_ADVERSARIAL_VALIDATION_PRIME.md`
