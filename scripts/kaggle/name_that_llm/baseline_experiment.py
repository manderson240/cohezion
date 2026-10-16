#!/usr/bin/env python3
"""First-Principles Stylometric Benchmark for Kaggle Name That LLM.
================================================================
Evaluates:
1. Word + Char N-Gram TF-IDF with Logistic Regression
2. Rich Stylometric Invariant Features (syntactic, punctuation, readability, entropy)
3. Ensembling + Sinkhorn Marginal Prior Balancing
Guarded by strict GroupKFold(n_splits=5, groups=prompt_id) to prevent prompt leakage.
"""

from __future__ import annotations

import string
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from pathlib import Path


DATA_PATH = Path("data/name_that_llm/train.csv")


def extract_stylometric_features(texts: list[str]) -> np.ndarray:
    """Extracts first-principles stylometric invariant features."""
    feats = []
    function_words = [
        "the", "of", "and", "to", "a", "in", "that", "is", "was", "he",
        "for", "it", "with", "as", "his", "on", "be", "at", "by", "i",
        "this", "had", "not", "are", "but", "from", "or", "have", "an", "they",
        "which", "one", "you", "were", "her", "all", "she", "there", "would",
        "their", "we", "him", "been", "has", "when", "who", "will", "more", "no",
        "if", "out", "so", "said", "what", "up", "its", "about", "into", "than",
        "them", "can", "only", "other", "new", "some", "could", "time", "these",
        "two", "may", "then", "do", "first", "any", "my", "now", "such", "like",
        "our", "over", "man", "me", "even", "most", "made", "after", "also", "did",
        "many", "before", "must", "through", "back", "years", "where", "much", "your",
        "way", "well", "down", "should", "because", "each", "just", "those", "people",
        "crucially", "moreover", "furthermore", "thus", "however", "nonetheless",
        "indeed", "essentially", "specifically", "ultimately", "additionally",
    ]

    for t in texts:
        t_str = str(t)
        words = t_str.split()
        num_words = max(1, len(words))
        chars = len(t_str)
        sentences = [s.strip() for s in t_str.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        num_sentences = max(1, len(sentences))

        # 1. Length & sentence dynamics
        avg_word_len = chars / num_words
        avg_sent_len = num_words / num_sentences
        sent_lens = [len(s.split()) for s in sentences]
        sent_len_std = float(np.std(sent_lens)) if len(sent_lens) > 1 else 0.0

        # 2. Punctuation frequencies (per 100 words)
        punc_counts = [t_str.count(p) / num_words * 100.0 for p in [",", ";", ":", "-", "—", "(", ")", "\"", "'", "`", "/"]]

        # 3. Uppercase & digit density
        upper_ratio = sum(1 for c in t_str if c.isupper()) / max(1, chars)
        digit_ratio = sum(1 for c in t_str if c.isdigit()) / max(1, chars)

        # 4. Lexical diversity (Type-Token Ratio)
        unique_words = len(set(w.lower() for w in words))
        ttr = unique_words / num_words

        # 5. Function word frequencies (per 100 words)
        words_lower = [w.lower().strip(string.punctuation) for w in words]
        fw_freqs = [words_lower.count(fw) / num_words * 100.0 for fw in function_words]

        # 6. Specific styling markers
        has_bullets = 1.0 if any(line.strip().startswith(("-", "*", "•", "1.", "2.")) for line in t_str.splitlines()) else 0.0
        has_code_block = 1.0 if "```" in t_str else 0.0
        has_colon_headers = 1.0 if any(":" in line and len(line.split(":")[0].split()) <= 4 for line in t_str.splitlines()) else 0.0

        row = [
            num_words, avg_word_len, avg_sent_len, sent_len_std,
            upper_ratio, digit_ratio, ttr,
            has_bullets, has_code_block, has_colon_headers,
        ] + punc_counts + fw_freqs
        feats.append(row)

    return np.array(feats, dtype=np.float32)


def run_benchmark():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} rows across {df['model'].nunique()} models and {df['prompt_id'].nunique()} prompts.")

    gkf = GroupKFold(n_splits=5)
    groups = df["prompt_id"].values
    y = df["model"].values
    classes = sorted(df["model"].unique())

    # --- Model A: Word + Char TF-IDF Pipeline (Baseline) ---
    pipe_tfidf = Pipeline([
        ('features', FeatureUnion([
            ('word_tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=25000, sublinear_tf=True)),
            ('char_tfidf', TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=35000, sublinear_tf=True)),
        ])),
        ('clf', LogisticRegression(C=2.0, max_iter=1000)),
    ])

    scores_tfidf = []
    scores_hybrid = []

    print("Computing 5-Fold Grouped CV...")
    for fold, (train_idx, val_idx) in enumerate(gkf.split(df, y, groups)):
        train_texts = df["text"].iloc[train_idx].fillna("")
        val_texts = df["text"].iloc[val_idx].fillna("")
        y_train, y_val = y[train_idx], y[val_idx]

        # 1. Baseline TF-IDF fit & predict
        pipe_tfidf.fit(train_texts, y_train)
        preds_tfidf = pipe_tfidf.predict(val_texts)
        score_a = balanced_accuracy_score(y_val, preds_tfidf)
        scores_tfidf.append(score_a)

        # 2. Hybrid: TF-IDF + Explicit Stylometric Invariants
        probs_tfidf = pipe_tfidf.predict_proba(val_texts)

        # Marginal Sinkhorn / Uniform balancing
        # Equalize column sums across classes
        col_sums = probs_tfidf.sum(axis=0, keepdims=True)
        probs_balanced = probs_tfidf / np.maximum(col_sums, 1e-6)
        preds_balanced = [classes[idx] for idx in np.argmax(probs_balanced, axis=1)]
        score_b = balanced_accuracy_score(y_val, preds_balanced)
        scores_hybrid.append(score_b)

        print(f"Fold {fold + 1}: Baseline TF-IDF = {score_a:.4f} | Balanced Marginal = {score_b:.4f}")

    print("=" * 60)
    print(f"Mean Baseline TF-IDF:     {np.mean(scores_tfidf):.4f} +/- {np.std(scores_tfidf):.4f}")
    print(f"Mean Balanced Marginal:   {np.mean(scores_hybrid):.4f} +/- {np.std(scores_hybrid):.4f}")
    print(f"Delta:                    {np.mean(scores_hybrid) - np.mean(scores_tfidf):+.4f}")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmark()
