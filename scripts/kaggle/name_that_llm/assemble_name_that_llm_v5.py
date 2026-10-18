#!/usr/bin/env python3
"""Assemble Cohezion Name That LLM SOTA v5: Soft Bayesian Prior Gating & Dual Model Ensemble.
=============================================================================================
Slot 3 Invariant Hypothesis (Daily Allotment Cycle 2026-10-18):
- Derived from verified SOTA v7 Canonical Base (scored 0.309 public balanced accuracy).
- Invariant Hypothesis:
  1. Soft Bayesian Prior Gating: Combines Hierarchical 6-Lab tree with a Global Flat LinearSVC:
     P_ensemble = 0.85 * P_hierarchical + 0.15 * P_flat
     Insulates the solution against Level 1 Lab misclassification cascades.
  2. Multi-Compressor Tokenizer Entropy Signatures: zlib, bz2, lzma ratios + byte-entropy.
  3. Sinkhorn-Knopp Uniform Marginal Balancing across 18 classes.
  4. Valid submission schema: ['id', 'model'] in submission.parquet.
"""

from __future__ import annotations

import json
from pathlib import Path

NB_DIR = Path("scripts/kaggle/name_that_llm")
NB_PATH = NB_DIR / "cohezion-name-that-llm-sota-starter.ipynb"
CANONICAL_BASE = NB_DIR / "cohezion-name-that-llm-sota-starter.canonical_base.ipynb"


def main() -> None:
    if not CANONICAL_BASE.exists():
        raise FileNotFoundError(f"{CANONICAL_BASE} does not exist")

    with open(CANONICAL_BASE, encoding="utf-8") as f:
        nb = json.load(f)

    # Cell 0: Header markdown
    nb["cells"][0]["source"] = [
        "# Cohezion Name That LLM: SOTA v5 Soft Bayesian Prior Gating & Dual Model Ensemble\n",
        "\n",
        "**Competition**: [Name That LLM](https://www.kaggle.com/competitions/name-that-llm) ($50,000 USD Featured Track)\n",
        "**Evaluation Metric**: `Balanced Accuracy Score` across 18 Generative LLM classes\n",
        "\n",
        "### SOTA v5 Architecture:\n",
        "1. **Soft Bayesian Prior Gating**: 85% Hierarchical 6-Lab Tree + 15% Global Flat LinearSVC hedge.\n",
        "2. **Multi-Compressor Tokenizer Entropy Signatures**: zlib, bz2, lzma compression ratios + byte entropy.\n",
        "3. **Sinkhorn-Knopp Uniform Marginal Balancing**: Solves optimal transport dual variables to enforce exact $1/18$ model distribution on test.\n",
    ]

    # Cell 4: Hierarchical + Global Flat Ensemble
    c4_source = [
        "# Cell 4: Soft Bayesian Prior Gating (Hierarchical + Flat Ensemble) & Inference\n",
        "from sklearn.feature_extraction.text import TfidfVectorizer\n",
        "from sklearn.linear_model import LogisticRegression\n",
        "from sklearn.svm import LinearSVC\n",
        "from sklearn.calibration import CalibratedClassifierCV\n",
        "from sklearn.preprocessing import StandardScaler, Normalizer\n",
        "from scipy.sparse import hstack, csr_matrix\n",
        "\n",
        "ALL_MODELS = sorted(list(train_df['model'].unique()))\n",
        "\n",
        "MODEL_TO_LAB = {\n",
        "    'claude-sonnet-5': 'anthropic', 'claude-opus-4-6': 'anthropic',\n",
        "    'claude-opus-4-8': 'anthropic', 'claude-opus-5': 'anthropic',\n",
        "    'claude-fable-5': 'anthropic',\n",
        "    'gpt-5.5': 'openai', 'gpt-5.6-luna': 'openai', 'gpt-5.6-sol': 'openai',\n",
        "    'gpt-5.6-terra': 'openai', 'gpt-6-astra': 'openai',\n",
        "    'gemini-3.1-pro-preview': 'google', 'gemini-3.6-flash': 'google',\n",
        "    'gemini-3.7-flash': 'google', 'gemini-3.8-flash': 'google',\n",
        "    'qwen3.8-max': 'alibaba', 'glm-5.3': 'zhipu', 'glm-5.3-flash': 'zhipu',\n",
        "    'kimi-k3': 'moonshot',\n",
        "}\n",
        "\n",
        "ALL_LABS = sorted(list(set(MODEL_TO_LAB.values())))\n",
        "LAB_TO_MODELS = {}\n",
        "for m, lab in MODEL_TO_LAB.items():\n",
        "    LAB_TO_MODELS.setdefault(lab, []).append(m)\n",
        "\n",
        "print('=== EXTRACTING MULTI-STREAM REPRESENTATIONS ===')\n",
        "text_col = 'text' if 'text' in train_df.columns else ('response' if 'response' in train_df.columns else train_df.columns[1])\n",
        "test_text_col = 'text' if 'text' in test_df.columns else ('response' if 'response' in test_df.columns else test_df.columns[1])\n",
        "train_texts = train_df[text_col].fillna('').tolist()\n",
        "test_texts = test_df[test_text_col].fillna('').tolist()\n",
        "y_train = train_df['model'].values\n",
        "labs_train = [MODEL_TO_LAB.get(m, 'unknown') for m in y_train]\n",
        "\n",
        "tfidf_word = TfidfVectorizer(ngram_range=(1, 2), max_features=12000, sublinear_tf=True)\n",
        "tfidf_char = TfidfVectorizer(ngram_range=(3, 5), analyzer='char', max_features=12000, sublinear_tf=True)\n",
        "\n",
        "print('Fitting TF-IDF representations...')\n",
        "X_tr_w = tfidf_word.fit_transform(train_texts)\n",
        "X_te_w = tfidf_word.transform(test_texts)\n",
        "X_tr_c = tfidf_char.fit_transform(train_texts)\n",
        "X_te_c = tfidf_char.transform(test_texts)\n",
        "\n",
        "print('Extracting compression entropy & stylometric features...')\n",
        "X_tr_s = extract_compression_and_stylometric_features(train_texts)\n",
        "X_te_s = extract_compression_and_stylometric_features(test_texts)\n",
        "scaler = StandardScaler()\n",
        "normalizer = Normalizer(norm='l2')\n",
        "X_tr_s_scaled = normalizer.transform(scaler.fit_transform(X_tr_s))\n",
        "X_te_s_scaled = normalizer.transform(scaler.transform(X_te_s))\n",
        "\n",
        "X_train_all = hstack([X_tr_w, X_tr_c, csr_matrix(X_tr_s_scaled)]).tocsr()\n",
        "X_test_all = hstack([X_te_w, X_te_c, csr_matrix(X_te_s_scaled)]).tocsr()\n",
        "print(f'Combined feature matrix: train={X_train_all.shape}, test={X_test_all.shape}')\n",
        "\n",
        "print('=== COMPONENT 1: Hierarchical 6-Lab Decomposition ===')\n",
        "lab_clf = LogisticRegression(C=1.5, max_iter=250, solver='lbfgs', random_state=42)\n",
        "lab_clf.fit(X_train_all, labs_train)\n",
        "test_lab_probs = lab_clf.predict_proba(X_test_all)\n",
        "lab_classes = list(lab_clf.classes_)\n",
        "\n",
        "intra_clfs = {}\n",
        "for lab_name in lab_classes:\n",
        "    models_in_lab = LAB_TO_MODELS.get(lab_name, [])\n",
        "    if len(models_in_lab) <= 1:\n",
        "        continue\n",
        "    sub_idx = [i for i, lb in enumerate(labs_train) if lb == lab_name]\n",
        "    if len(sub_idx) < 2:\n",
        "        continue\n",
        "    sub_X = X_train_all[sub_idx]\n",
        "    sub_y = [y_train[i] for i in sub_idx]\n",
        "    intra_clf = LogisticRegression(C=1.2, max_iter=250, solver='lbfgs', random_state=42)\n",
        "    intra_clf.fit(sub_X, sub_y)\n",
        "    intra_clfs[lab_name] = intra_clf\n",
        "\n",
        "n_test = len(test_texts)\n",
        "hier_probs = np.zeros((n_test, len(ALL_MODELS)), dtype=np.float64)\n",
        "model_to_col = {m: i for i, m in enumerate(ALL_MODELS)}\n",
        "\n",
        "for lab_name in lab_classes:\n",
        "    lab_col = lab_classes.index(lab_name)\n",
        "    p_lab = test_lab_probs[:, lab_col]\n",
        "    models_in_lab = LAB_TO_MODELS.get(lab_name, [])\n",
        "    if len(models_in_lab) == 1:\n",
        "        col = model_to_col[models_in_lab[0]]\n",
        "        hier_probs[:, col] = p_lab\n",
        "    elif lab_name in intra_clfs:\n",
        "        intra_clf = intra_clfs[lab_name]\n",
        "        p_intra = intra_clf.predict_proba(X_test_all)\n",
        "        for sub_i, sub_mod in enumerate(intra_clf.classes_):\n",
        "            if sub_mod in model_to_col:\n",
        "                col = model_to_col[sub_mod]\n",
        "                hier_probs[:, col] = p_lab * p_intra[:, sub_i]\n",
        "    else:\n",
        "        eq_p = 1.0 / max(1, len(models_in_lab))\n",
        "        for sub_mod in models_in_lab:\n",
        "            col = model_to_col[sub_mod]\n",
        "            hier_probs[:, col] = p_lab * eq_p\n",
        "\n",
        "print('=== COMPONENT 2: Global Flat Calibrated Linear Classifier ===')\n",
        "flat_base = LinearSVC(C=0.5, max_iter=2000, random_state=42)\n",
        "flat_clf = CalibratedClassifierCV(estimator=flat_base, method='sigmoid', cv=3)\n",
        "flat_clf.fit(X_train_all, y_train)\n",
        "flat_test_probs = flat_clf.predict_proba(X_test_all)\n",
        "flat_classes = list(flat_clf.classes_)\n",
        "flat_probs_aligned = np.zeros((n_test, len(ALL_MODELS)), dtype=np.float64)\n",
        "for i, m in enumerate(flat_classes):\n",
        "    if m in model_to_col:\n",
        "        flat_probs_aligned[:, model_to_col[m]] = flat_test_probs[:, i]\n",
        "\n",
        "print('=== BLENDING: 85% Hierarchical Tree + 15% Global Flat Hedge ===')\n",
        "model_probs = 0.85 * hier_probs + 0.15 * flat_probs_aligned\n",
        "\n",
        "T = 1.0\n",
        "logits = np.log(np.clip(model_probs, 1e-9, 1.0))\n",
        "scaled_probs = np.exp(logits / T)\n",
        "scaled_probs /= scaled_probs.sum(axis=1, keepdims=True)\n",
        "\n",
        "if n_test >= len(ALL_MODELS):\n",
        "    target_marginals = np.full(len(ALL_MODELS), 1.0 / len(ALL_MODELS))\n",
        "    p_balanced = np.clip(scaled_probs, 1e-12, 1.0)\n",
        "    p_balanced /= p_balanced.sum(axis=1, keepdims=True)\n",
        "    c_target = target_marginals * n_test\n",
        "    for _ in range(40):\n",
        "        col_sums = p_balanced.sum(axis=0)\n",
        "        col_sums = np.where(col_sums == 0, 1e-12, col_sums)\n",
        "        p_balanced *= (c_target / col_sums)\n",
        "        row_sums = p_balanced.sum(axis=1, keepdims=True)\n",
        "        row_sums = np.where(row_sums == 0, 1e-12, row_sums)\n",
        "        p_balanced /= row_sums\n",
        "    p_final = np.clip(p_balanced, 1e-6, 1.0 - 1e-6)\n",
        "    p_final /= p_final.sum(axis=1, keepdims=True)\n",
        "else:\n",
        "    p_final = scaled_probs\n",
        "\n",
        "final_pred_indices = np.argmax(p_final, axis=1)\n",
        "final_preds = [ALL_MODELS[idx] for idx in final_pred_indices]\n",
        "\n",
        "sub_df = pd.DataFrame({\n",
        "    'id': test_df['id'].values,\n",
        "    'model': final_preds,\n",
        "})\n",
        "sub_df.to_parquet('submission.parquet', index=False)\n",
        "print(f'Successfully wrote {len(sub_df)} predictions to submission.parquet!')\n",
        "print(sub_df.head(10))\n",
    ]
    nb["cells"][4]["source"] = c4_source

    if len(nb["cells"]) > 5:
        nb["cells"] = nb["cells"][:5]

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"✓ Successfully assembled Name That LLM SOTA v5 in {NB_PATH}")


if __name__ == "__main__":
    main()
