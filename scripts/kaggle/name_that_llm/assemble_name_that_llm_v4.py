#!/usr/bin/env python3
"""Assemble Cohezion Name That LLM SOTA v4: 5-Stream Stylometric LinearSVC + HistGradientBoosting Dual-Model Ensemble.
========================================================================================================================
Slot 3 Invariant Hypothesis:
- Multi-scale stylometric representations: word (1,2), char (3,5), shape topology, function-word syntax, dense indicators.
- Dual-model diversity:
  * Model 1: Calibrated LinearSVC (L2-loss, primal/dual calibrated margin).
  * Model 2: HistGradientBoostingClassifier (histogram-binned gradient boosted trees on TruncatedSVD 64 components + dense stylometrics).
- Probability blend: 0.60 * P_LinearSVC + 0.40 * P_HistGBM.
- Test-time Sinkhorn uniform marginal balancing across all 18 LLM classes (target prior 1/18).
"""

from __future__ import annotations

import json
from pathlib import Path


NB_DIR = Path("scripts/kaggle/name_that_llm")
NB_PATH = NB_DIR / "cohezion-name-that-llm-sota-starter.ipynb"
BAK_PATH = NB_DIR / "cohezion-name-that-llm-sota-starter.ipynb.v3.bak"


def main():
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")

    import shutil

    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up notebook to {BAK_PATH}")

    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    # Cell 0: Header markdown
    nb["cells"][0]["source"] = [
        "# Cohezion Name That LLM: SOTA v4 Dual-Model Ensemble (LinearSVC + HistGradientBoosting) & Sinkhorn Balancing\n",
        "\n",
        "**Competition**: [Name That LLM](https://www.kaggle.com/competitions/name-that-llm) ($50,000 USD Featured Track)\n",
        "**Evaluation Metric**: `Balanced Accuracy Score` across 18 Generative LLM classes\n",
        "\n",
        "### SOTA v4 Architecture:\n",
        "1. **5-Stream Stylometric Features**: Lexical n-grams, character n-grams, casing/punctuation shape topology, syntactic function-word sequences, and dense statistical indicators.\n",
        "2. **Dual-Model Ensemble**:\n",
        "   - **LinearSVC** (Platt-calibrated / softmax temperature-scaled margins).\n",
        "   - **HistGradientBoostingClassifier** (Histogram gradient-boosted decision trees on TruncatedSVD components).\n",
        "3. **Log-Probability Blending**: $P = 0.60 \\times P_{\\text{LinearSVC}} + 0.40 \\times P_{\\text{HistGBM}}$.\n",
        "4. **Sinkhorn Uniform Marginal Balancing**: Solves optimal transport dual variables to enforce uniform $1/18$ model distribution on test.\n",
    ]

    # Cell 4: Modeling & Inference
    c4_source = [
        "# Cell 4: Model Training, Dual Ensemble, Sinkhorn Balancing, and Parquet Output\n",
        "import numpy as np\n",
        "import pandas as pd\n",
        "from sklearn.svm import LinearSVC\n",
        "from sklearn.calibration import CalibratedClassifierCV\n",
        "from sklearn.decomposition import TruncatedSVD\n",
        "from sklearn.ensemble import HistGradientBoostingClassifier\n",
        "from scipy.special import softmax\n",
        "\n",
        "print('=== TRAINING MODEL 1: Calibrated LinearSVC on Multi-Stream Sparse Matrix ===')\n",
        "base_svc = LinearSVC(C=0.45, max_iter=2500, random_state=42)\n",
        "model_svc = CalibratedClassifierCV(estimator=base_svc, method='sigmoid', cv=3)\n",
        "model_svc.fit(X_train_sparse, y_train)\n",
        "svc_test_probs = model_svc.predict_proba(X_test_sparse)\n",
        "\n",
        "print('=== TRAINING MODEL 2: HistGradientBoosting on TruncatedSVD Latent Space ===')\n",
        "svd = TruncatedSVD(n_components=64, random_state=42)\n",
        "X_train_svd = np.hstack([svd.fit_transform(X_train_sparse), X_train_dense])\n",
        "X_test_svd = np.hstack([svd.transform(X_test_sparse), X_test_dense])\n",
        "\n",
        "model_hgb = HistGradientBoostingClassifier(\n",
        "    max_iter=120,\n",
        "    learning_rate=0.08,\n",
        "    max_depth=5,\n",
        "    min_samples_leaf=15,\n",
        "    random_state=42,\n",
        ")\n",
        "model_hgb.fit(X_train_svd, y_train)\n",
        "hgb_test_probs = model_hgb.predict_proba(X_test_svd)\n",
        "\n",
        "print('=== BLENDING PROBABILITIES (0.60 LinearSVC + 0.40 HistGBM) ===')\n",
        "blended_probs = 0.60 * svc_test_probs + 0.40 * hgb_test_probs\n",
        "\n",
        "def sinkhorn_marginal_balancing(probs: np.ndarray, target_col_sum: float = 1.0, max_iter: int = 100, tol: float = 1e-6) -> np.ndarray:\n",
        "    N, K = probs.shape\n",
        "    P = np.clip(probs, 1e-9, 1.0)\n",
        "    target_row = np.ones(N)\n",
        "    target_col = np.full(K, target_col_sum * (N / K))\n",
        "    for _ in range(max_iter):\n",
        "        row_sum = P.sum(axis=1, keepdims=True)\n",
        "        P = P / np.maximum(row_sum, 1e-12) * target_row[:, None]\n",
        "        col_sum = P.sum(axis=0, keepdims=True)\n",
        "        if np.max(np.abs(col_sum - target_col)) < tol:\n",
        "            break\n",
        "        P = P / np.maximum(col_sum, 1e-12) * target_col\n",
        "    P = P / P.sum(axis=1, keepdims=True)\n",
        "    return P\n",
        "\n",
        "print('Applying Sinkhorn Uniform Marginal Balancing...')\n",
        "balanced_probs = sinkhorn_marginal_balancing(blended_probs)\n",
        "final_preds_idx = np.argmax(balanced_probs, axis=1)\n",
        "final_preds_labels = [target_classes[idx] for idx in final_preds_idx]\n",
        "\n",
        "sub_df = pd.DataFrame({\n",
        "    'id': test_df['id'].values,\n",
        "    'model': final_preds_labels\n",
        "})\n",
        "\n",
        "output_path = pathlib.Path('submission.parquet')\n",
        "sub_df.to_parquet(output_path, index=False)\n",
        "print(f'✓ Successfully generated {output_path} ({len(sub_df)} rows)')\n",
        "print(sub_df.head(10))\n",
    ]

    nb["cells"][4]["source"] = c4_source

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully assembled Name That LLM SOTA v4 notebook.")


if __name__ == "__main__":
    main()
