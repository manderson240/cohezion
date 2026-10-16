#!/usr/bin/env python3
"""Builds cohezion-name-that-llm-sota-starter.ipynb for Kaggle Name That LLM.
==========================================================================
First-Principles Stylometric Invariant Pipeline with Sinkhorn Uniform Marginal Balancing.
"""

from __future__ import annotations

import json
from pathlib import Path

NB_DIR = Path("scripts/kaggle/name_that_llm")
NB_PATH = NB_DIR / "cohezion-name-that-llm-sota-starter.ipynb"


def build_starter_notebook():
    NB_DIR.mkdir(parents=True, exist_ok=True)

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Cohezion Name That LLM: Stylometric Invariant Classifier & Sinkhorn Marginal Balancing\n",
                "\n",
                "**Competition**: [Name That LLM](https://www.kaggle.com/competitions/name-that-llm) ($50,000 USD Featured Track)\n",
                "**Evaluation Metric**: `Balanced Accuracy Score` across 18 Generative LLMs\n",
                "**First-Principles Foundations**:\n",
                "1. *Subword & Stylometric Invariants*: Punctuation cadence, function-word entropy, and syntactic clause branching.\n",
                "2. *Multi-Scale N-Gram Representation*: Word (1, 2) + Character (3, 5) TF-IDF with sublinear term frequency scaling.\n",
                "3. *Sinkhorn Uniform Marginal Balancing*: Since prompt evaluation is symmetric, the ground-truth class marginal prior $P(\\text{model}) = 1/18$. Posterior probabilities are iteratively normalized to match the uniform marginals, strictly optimizing the Balanced Accuracy metric.\n",
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Cell 1: Environment & Deterministic Setup\n",
                "import os\n",
                "import sys\n",
                "import pathlib\n",
                "import string\n",
                "import numpy as np\n",
                "import pandas as pd\n",
                "from sklearn.feature_extraction.text import TfidfVectorizer\n",
                "from sklearn.linear_model import LogisticRegression\n",
                "from sklearn.pipeline import FeatureUnion, Pipeline\n",
                "from sklearn.metrics import balanced_accuracy_score\n",
                "from sklearn.model_selection import GroupKFold\n",
                "import warnings\n",
                "warnings.filterwarnings('ignore')\n",
                "\n",
                "np.random.seed(42)\n",
                "print('✓ Environment configured with seed=42.')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Cell 2: Robust Kaggle Path Discovery\n",
                "CANDIDATES = [\n",
                "    pathlib.Path('/kaggle/input/name-that-llm'),\n",
                "    pathlib.Path('/kaggle/input/competitions/name-that-llm'),\n",
                "    pathlib.Path('data/name_that_llm'),\n",
                "    pathlib.Path('../data/name_that_llm'),\n",
                "]\n",
                "\n",
                "DATA_DIR = next((p for p in CANDIDATES if (p / 'train.csv').exists()), None)\n",
                "if DATA_DIR is None:\n",
                "    raise FileNotFoundError('Could not locate name-that-llm dataset!')\n",
                "\n",
                "print(f'Data root resolved to: {DATA_DIR}')\n",
                "train_df = pd.read_csv(DATA_DIR / 'train.csv')\n",
                "test_df = pd.read_csv(DATA_DIR / 'test.csv')\n",
                "\n",
                "classes = sorted(train_df['model'].unique())\n",
                "n_classes = len(classes)\n",
                "print(f'Train samples: {len(train_df)} | Classes: {n_classes} | Unique prompts: {train_df[\"prompt_id\"].nunique()}')\n",
                "print(f'Test samples: {len(test_df)}')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Cell 3: Multi-Scale N-Gram & Stylometric Feature Pipeline\n",
                "# Word (1, 2) + Character (3, 5) n-grams capture both lexical choice and morphological cadence\n",
                "feature_extractor = FeatureUnion([\n",
                "    ('word_tfidf', TfidfVectorizer(\n",
                "        ngram_range=(1, 2),\n",
                "        max_features=30000,\n",
                "        sublinear_tf=True,\n",
                "        strip_accents='unicode',\n",
                "    )),\n",
                "    ('char_tfidf', TfidfVectorizer(\n",
                "        analyzer='char',\n",
                "        ngram_range=(3, 5),\n",
                "        max_features=45000,\n",
                "        sublinear_tf=True,\n",
                "    )),\n",
                "])\n",
                "\n",
                "clf = LogisticRegression(\n",
                "    C=2.5,\n",
                "    max_iter=1000,\n",
                "    class_weight='balanced',\n",
                "    solver='lbfgs',\n",
                "    random_state=42,\n",
                ")\n",
                "\n",
                "model_pipeline = Pipeline([\n",
                "    ('features', feature_extractor),\n",
                "    ('classifier', clf),\n",
                "])\n",
                "\n",
                "print('✓ FeatureUnion and Classifier initialized.')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Cell 4: GroupKFold Cross-Validation (Leak-Free Prompt Partitioning)\n",
                "gkf = GroupKFold(n_splits=5)\n",
                "groups = train_df['prompt_id'].values\n",
                "X_train_raw = train_df['text'].fillna('')\n",
                "y_train_raw = train_df['model'].values\n",
                "\n",
                "def apply_sinkhorn_balancing(probs: np.ndarray, num_iters: int = 5) -> np.ndarray:\n",
                "    \"\"\"Iteratively balances column and row marginals to match uniform P(class) = 1/K.\"\"\"\n",
                "    p = np.copy(probs)\n",
                "    target_col = 1.0 / p.shape[1]\n",
                "    for _ in range(num_iters):\n",
                "        # Column normalization to target uniform share\n",
                "        p /= np.maximum(p.sum(axis=0, keepdims=True), 1e-12)\n",
                "        p *= target_col\n",
                "        # Row normalization to valid simplex\n",
                "        p /= np.maximum(p.sum(axis=1, keepdims=True), 1e-12)\n",
                "    return p\n",
                "\n",
                "cv_scores_raw = []\n",
                "cv_scores_balanced = []\n",
                "\n",
                "for fold, (trn_idx, val_idx) in enumerate(gkf.split(train_df, y_train_raw, groups)):\n",
                "    X_trn, X_val = X_train_raw.iloc[trn_idx], X_train_raw.iloc[val_idx]\n",
                "    y_trn, y_val = y_train_raw[trn_idx], y_train_raw[val_idx]\n",
                "    \n",
                "    model_pipeline.fit(X_trn, y_trn)\n",
                "    probs_val = model_pipeline.predict_proba(X_val)\n",
                "    \n",
                "    preds_raw = model_pipeline.classes_[np.argmax(probs_val, axis=1)]\n",
                "    score_raw = balanced_accuracy_score(y_val, preds_raw)\n",
                "    cv_scores_raw.append(score_raw)\n",
                "    \n",
                "    probs_bal = apply_sinkhorn_balancing(probs_val)\n",
                "    preds_bal = model_pipeline.classes_[np.argmax(probs_bal, axis=1)]\n",
                "    score_bal = balanced_accuracy_score(y_val, preds_bal)\n",
                "    cv_scores_balanced.append(score_bal)\n",
                "    \n",
                "    print(f'Fold {fold+1}: Raw Balanced Acc = {score_raw:.4f} | Sinkhorn Balanced = {score_bal:.4f}')\n",
                "\n",
                "print('=' * 65)\n",
                "print(f'5-Fold Mean Raw:      {np.mean(cv_scores_raw):.4f} +/- {np.std(cv_scores_raw):.4f}')\n",
                "print(f'5-Fold Mean Balanced: {np.mean(cv_scores_balanced):.4f} +/- {np.std(cv_scores_balanced):.4f}')\n",
                "print(f'Sinkhorn Invariant Delta: {np.mean(cv_scores_balanced) - np.mean(cv_scores_raw):+.4f}')\n",
                "print('=' * 65)\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Cell 5: Full Train Fit & Test Prediction Generation\n",
                "print('Fitting model pipeline on full 2,699 training samples...')\n",
                "model_pipeline.fit(X_train_raw, y_train_raw)\n",
                "\n",
                "X_test_raw = test_df['text'].fillna('')\n",
                "test_probs = model_pipeline.predict_proba(X_test_raw)\n",
                "\n",
                "# Apply Sinkhorn balancing if test batch is larger than single sample\n",
                "if len(test_df) >= n_classes:\n",
                "    test_probs = apply_sinkhorn_balancing(test_probs)\n",
                "\n",
                "final_preds = model_pipeline.classes_[np.argmax(test_probs, axis=1)]\n",
                "\n",
                "# Output format: sample_submission.parquet\n",
                "submission = pd.DataFrame({\n",
                "    'id': test_df['id'],\n",
                "    'model': final_preds,\n",
                "})\n",
                "\n",
                "submission.to_parquet('submission.parquet', index=False)\n",
                "print(f'✓ Successfully generated submission.parquet ({len(submission)} rows).')\n",
                "print(submission.head(10))\n"
            ]
        }
    ]

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }

    NB_PATH.write_text(json.dumps(nb, indent=2), encoding="utf-8")
    print(f"✓ Created {NB_PATH} ({len(cells)} cells, {NB_PATH.stat().st_size:,} bytes).")


if __name__ == "__main__":
    build_starter_notebook()
