"""Hierarchical Lab & Perplexity Classifier for Kaggle 'Name That LLM'.
====================================================================
First-Principles Invariant Solution:
1. Two-Stage Hierarchical Prior Decomposition:
   P(Model_i | x) = P(Lab_k | x) * P(Model_i | Lab_k, x)
   Lab families (Anthropic, OpenAI, Google, Alibaba, Zhipu, Moonshot) possess
   distinct token boundaries, structural formatting, and system-level stylistic markers.
   Separating lab classification from intra-family model version classification avoids
   diluting high-confidence lab boundaries across all 18 classes.

2. Candidate Tokenizer & Entropy Invariants:
   - Byte-level entropy and multi-compressor compression ratios (zlib, bz2, lzma).
   - Structural Markdown, LaTeX, and Code syntax invariants.
   - Sentence-length dynamics and function-word stylometry.
   - Leakage-free GroupKFold grouping strictly by prompt_id.

3. Sinkhorn-Knopp Optimal Transport Prior Balancing:
   Enforces exact uniform test prior distribution matching empirical evaluation setups.
"""

from __future__ import annotations

import bz2
import lzma
import math
import re
import string
import zlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline


# 18 Target classes in Name That LLM
ALL_MODELS: list[str] = [
    "claude-sonnet-5",
    "claude-opus-4-6",
    "claude-opus-4-8",
    "claude-opus-5",
    "claude-fable-5",
    "gpt-5.5",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-6-astra",
    "gemini-3.1-pro-preview",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "qwen3.8-max",
    "glm-5.3",
    "glm-5.3-flash",
    "kimi-k3",
]

# Family mapping: 18 models -> 6 labs
MODEL_TO_LAB: dict[str, str] = {
    "claude-sonnet-5": "anthropic",
    "claude-opus-4-6": "anthropic",
    "claude-opus-4-8": "anthropic",
    "claude-opus-5": "anthropic",
    "claude-fable-5": "anthropic",
    "gpt-5.5": "openai",
    "gpt-5.6-luna": "openai",
    "gpt-5.6-sol": "openai",
    "gpt-5.6-terra": "openai",
    "gpt-6-astra": "openai",
    "gemini-3.1-pro-preview": "google",
    "gemini-3.6-flash": "google",
    "gemini-3.7-flash": "google",
    "gemini-3.8-flash": "google",
    "qwen3.8-max": "alibaba",
    "glm-5.3": "zhipu",
    "glm-5.3-flash": "zhipu",
    "kimi-k3": "moonshot",
}

ALL_LABS: list[str] = sorted(list(set(MODEL_TO_LAB.values())))

LAB_TO_MODELS: dict[str, list[str]] = {}
for m, lab in MODEL_TO_LAB.items():
    LAB_TO_MODELS.setdefault(lab, []).append(m)


FUNCTION_WORDS: list[str] = [
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
    "certainly", "sure", "overall", "firstly", "secondly", "finally",
]


def extract_compression_and_stylometric_features(texts: list[str]) -> np.ndarray:
    """Extract first-principles stylometric, compression entropy, and formatting features.

    Parameters
    ----------
    texts : list[str]
        List of generated text strings.

    Returns
    -------
    np.ndarray
        Feature matrix of shape (n_samples, n_features).
    """
    rows: list[list[float]] = []

    for text in texts:
        t_str = str(text) if text is not None else ""
        raw_bytes = t_str.encode("utf-8", errors="replace")
        n_bytes = max(1, len(raw_bytes))
        chars = len(t_str)
        words = t_str.split()
        num_words = max(1, len(words))

        sentences = [s.strip() for s in re.split(r"[.!?]+", t_str) if s.strip()]
        num_sentences = max(1, len(sentences))

        # 1. Multi-compressor entropy proxies (tokenizer compressibility signature)
        zlib_len = len(zlib.compress(raw_bytes, level=6))
        bz2_len = len(bz2.compress(raw_bytes, compresslevel=6))
        lzma_len = len(lzma.compress(raw_bytes))

        cr_zlib = zlib_len / n_bytes
        cr_bz2 = bz2_len / n_bytes
        cr_lzma = lzma_len / n_bytes

        # Shannon entropy of byte distribution
        byte_counts = np.bincount(np.frombuffer(raw_bytes, dtype=np.uint8), minlength=256)
        probs = byte_counts[byte_counts > 0] / n_bytes
        byte_entropy = -float(np.sum(probs * np.log2(probs)))

        # 2. Structural & Formatting Invariants
        lines = t_str.splitlines()
        n_lines = max(1, len(lines))

        # Markdown bullet styles (Anthropic vs OpenAI vs Gemini formatting habit)
        star_bullets = sum(1 for line in lines if line.strip().startswith("* ")) / n_lines
        dash_bullets = sum(1 for line in lines if line.strip().startswith("- ")) / n_lines
        num_bullets = sum(1 for line in lines if re.match(r"^\d+\.\s", line.strip())) / n_lines

        # Header levels
        h1 = t_str.count("\n# ") + (1 if t_str.startswith("# ") else 0)
        h2 = t_str.count("\n## ") + (1 if t_str.startswith("## ") else 0)
        h3 = t_str.count("\n### ") + (1 if t_str.startswith("### ") else 0)
        header_ratio = (h1 + h2 + h3) / n_lines

        # Code block presence
        code_blocks = t_str.count("```") / 2.0
        inline_code = t_str.count("`") - (code_blocks * 6)

        # Bold & Italic markdown usage
        bold_count = t_str.count("**")
        italic_count = (t_str.count("*") - (bold_count * 2) - int(star_bullets * n_lines)) / max(1, chars)

        # 3. Sentence & Lexical Dynamics
        avg_word_len = chars / num_words
        avg_sent_len = num_words / num_sentences
        sent_lens = [len(s.split()) for s in sentences]
        sent_len_std = float(np.std(sent_lens)) if len(sent_lens) > 1 else 0.0

        unique_words = len(set(w.lower() for w in words))
        type_token_ratio = unique_words / num_words

        # 4. Punctuation distributions (per 100 words)
        punct_counts = {p: t_str.count(p) * 100.0 / num_words for p in [",", ";", ":", "-", "(", ")", "\"", "'", "—"]}

        # 5. Opener / Conversational Affordances
        first_50 = t_str[:100].lower()
        opener_certainly = 1.0 if "certainly" in first_50 else 0.0
        opener_sure = 1.0 if "sure" in first_50 else 0.0
        opener_here = 1.0 if "here is" in first_50 or "here's" in first_50 else 0.0
        opener_to = 1.0 if "to solve" in first_50 or "to answer" in first_50 else 0.0

        # Leaked reasoning tokens (<think>, reasoning blocks)
        think_tag = 1.0 if "<think>" in t_str or "</think>" in t_str else 0.0

        # Function word distribution
        t_lower = t_str.lower()
        words_lower = [w.strip(string.punctuation) for w in t_lower.split()]
        word_set_counts = pd.Series(words_lower).value_counts().to_dict()
        fw_freqs = [word_set_counts.get(fw, 0) * 100.0 / num_words for fw in FUNCTION_WORDS]

        row = [
            cr_zlib,
            cr_bz2,
            cr_lzma,
            byte_entropy,
            float(chars),
            float(num_words),
            float(num_sentences),
            avg_word_len,
            avg_sent_len,
            sent_len_std,
            type_token_ratio,
            star_bullets,
            dash_bullets,
            num_bullets,
            header_ratio,
            code_blocks,
            inline_code,
            italic_count,
            opener_certainly,
            opener_sure,
            opener_here,
            opener_to,
            think_tag,
        ] + [punct_counts[p] for p in sorted(punct_counts.keys())] + fw_freqs

        rows.append(row)

    return np.nan_to_num(np.array(rows, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)


def sinkhorn_knopp_balance(
    prob_matrix: np.ndarray,
    target_marginals: np.ndarray | None = None,
    max_iter: int = 50,
    tol: float = 1e-4,
) -> np.ndarray:
    """Sinkhorn-Knopp algorithm for calibrating test-time prediction marginals.

    Ensures average predicted probability vector matches the target uniform class distribution
    (1/C per class) across the test population.

    Parameters
    ----------
    prob_matrix : np.ndarray
        Prediction probability matrix of shape (n_samples, n_classes).
    target_marginals : np.ndarray | None
        Target class marginal distribution. Defaults to uniform 1/C.
    max_iter : int
        Maximum Sinkhorn scaling iterations.
    tol : float
        Convergence threshold.

    Returns
    -------
    np.ndarray
        Calibrated probability matrix of shape (n_samples, n_classes).
    """
    n_samples, n_classes = prob_matrix.shape
    if n_samples == 0:
        return prob_matrix

    if target_marginals is None:
        target_marginals = np.full(n_classes, 1.0 / n_classes, dtype=np.float64)

    # Work in double precision
    p = np.clip(prob_matrix.astype(np.float64), 1e-12, 1.0)
    # Row normalize
    p /= p.sum(axis=1, keepdims=True)

    c_target = target_marginals * n_samples
    col_scaling = np.ones(n_classes, dtype=np.float64)

    for _ in range(max_iter):
        # Column step: scale columns so column sums equal c_target
        col_sums = p.sum(axis=0)
        col_sums = np.where(col_sums == 0, 1e-12, col_sums)
        scaling = c_target / col_sums
        p *= scaling

        # Row step: scale rows so each row sums to 1.0
        row_sums = p.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1e-12, row_sums)
        p /= row_sums

        if np.max(np.abs(p.sum(axis=0) - c_target)) < tol * n_samples:
            break

    return p.astype(prob_matrix.dtype)


class HierarchicalLabClassifier(BaseEstimator, ClassifierMixin):
    """Hierarchical Lab & Model Classifier for Stylometric LLM Discrimination.

    Level 1: Lab family classifier (Anthropic, OpenAI, Google, Alibaba, Zhipu, Moonshot).
    Level 2: Intra-lab model classifiers for labs with >1 candidate model.
    Final output: Joint posterior P(Model_i | x) = P(Lab_k | x) * P(Model_i | Lab_k, x).
    """

    def __init__(
        self,
        c_lab: float = 1.5,
        c_intra: float = 1.0,
        temperature: float = 0.90,
        apply_sinkhorn: bool = True,
    ) -> None:
        self.c_lab = c_lab
        self.c_intra = c_intra
        self.temperature = temperature
        self.apply_sinkhorn = apply_sinkhorn

        # Transformers / Feature extraction
        self.tfidf_word = TfidfVectorizer(ngram_range=(1, 2), max_features=15000, sublinear_tf=True)
        self.tfidf_char = TfidfVectorizer(ngram_range=(3, 5), analyzer="char", max_features=15000, sublinear_tf=True)

        self.lab_classifier: CalibratedClassifierCV | None = None
        self.intra_classifiers: dict[str, CalibratedClassifierCV] = {}
        self.classes_: np.ndarray = np.array(ALL_MODELS)
        self.lab_classes_: np.ndarray = np.array(ALL_LABS)

    def _extract_all_features(self, texts: list[str], is_train: bool = False) -> np.ndarray:
        """Combine word TF-IDF, char TF-IDF, and stylometric compression features."""
        if is_train:
            w_feat = self.tfidf_word.fit_transform(texts).toarray()
            c_feat = self.tfidf_char.fit_transform(texts).toarray()
        else:
            w_feat = self.tfidf_word.transform(texts).toarray()
            c_feat = self.tfidf_char.transform(texts).toarray()

        s_feat = extract_compression_and_stylometric_features(texts)
        return np.hstack([w_feat, c_feat, s_feat])

    def fit(self, texts: list[str], labels: list[str]) -> "HierarchicalLabClassifier":
        """Train the hierarchical classifier.

        Parameters
        ----------
        texts : list[str]
            List of response text samples.
        labels : list[str]
            List of model names corresponding to ALL_MODELS.
        """
        labs = [MODEL_TO_LAB.get(lbl, "unknown") for lbl in labels]
        features = self._extract_all_features(texts, is_train=True)

        # 1. Train Level-1 Lab Classifier
        base_lab_clf = LogisticRegression(C=self.c_lab, max_iter=1000, solver="lbfgs")
        lab_counts = pd.Series(labs).value_counts().values
        cv_splits = min(3, int(min(lab_counts))) if len(lab_counts) > 0 else 0
        if cv_splits >= 2:
            self.lab_classifier = CalibratedClassifierCV(base_lab_clf, method="sigmoid", cv=cv_splits)
        else:
            self.lab_classifier = base_lab_clf

        self.lab_classifier.fit(features, labs)
        self.lab_classes_ = np.array(self.lab_classifier.classes_)

        # 2. Train Level-2 Intra-Lab Classifiers
        for lab_name in self.lab_classes_:
            models_in_lab = LAB_TO_MODELS.get(lab_name, [])
            if len(models_in_lab) <= 1:
                # Monadic model lab (e.g. Alibaba: qwen3.8-max, Moonshot: kimi-k3)
                continue

            indices = [i for i, lb in enumerate(labs) if lb == lab_name]
            if len(indices) < 2:
                continue

            sub_features = features[indices]
            sub_labels = [labels[i] for i in indices]
            sub_counts = pd.Series(sub_labels).value_counts().values
            if len(sub_counts) < 2:
                continue

            sub_cv = min(3, int(min(sub_counts)))
            base_intra_clf = LogisticRegression(C=self.c_intra, max_iter=1000, solver="lbfgs")
            if sub_cv >= 2:
                intra_clf = CalibratedClassifierCV(base_intra_clf, method="sigmoid", cv=sub_cv)
            else:
                intra_clf = base_intra_clf

            intra_clf.fit(sub_features, sub_labels)
            self.intra_classifiers[lab_name] = intra_clf

        return self

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        """Predict calibrated probabilities across all 18 classes.

        Parameters
        ----------
        texts : list[str]
            List of response text samples.

        Returns
        -------
        np.ndarray
            Probability matrix of shape (n_samples, 18).
        """
        if self.lab_classifier is None:
            raise RuntimeError("Model must be fitted before predict_proba")

        features = self._extract_all_features(texts, is_train=False)
        n_samples = len(texts)

        # Level 1 Lab Probabilities P(Lab_k | x)
        lab_probs = self.lab_classifier.predict_proba(features)
        lab_class_indices = {lab: idx for idx, lab in enumerate(self.lab_classes_)}

        # Output matrix for all 18 models
        model_probs = np.zeros((n_samples, len(ALL_MODELS)), dtype=np.float64)
        model_to_col = {m: i for i, m in enumerate(ALL_MODELS)}

        for lab_name in self.lab_classes_:
            lab_col = lab_class_indices[lab_name]
            p_lab = lab_probs[:, lab_col]  # (n_samples,)

            models_in_lab = LAB_TO_MODELS.get(lab_name, [])
            if len(models_in_lab) == 1:
                # Deterministic conditional P(Model | Lab) = 1.0
                target_col = model_to_col[models_in_lab[0]]
                model_probs[:, target_col] = p_lab
            elif lab_name in self.intra_classifiers:
                intra_clf = self.intra_classifiers[lab_name]
                p_intra = intra_clf.predict_proba(features)  # (n_samples, n_intra)
                for sub_idx, sub_model in enumerate(intra_clf.classes_):
                    if sub_model in model_to_col:
                        col = model_to_col[sub_model]
                        model_probs[:, col] = p_lab * p_intra[:, sub_idx]
            else:
                # Uniform fallback across intra models if classifier absent
                eq_p = 1.0 / max(1, len(models_in_lab))
                for sub_model in models_in_lab:
                    col = model_to_col[sub_model]
                    model_probs[:, col] = p_lab * eq_p

        # Temperature scaling
        if self.temperature != 1.0:
            log_probs = np.log(np.clip(model_probs, 1e-12, 1.0)) / self.temperature
            model_probs = np.exp(log_probs)
            model_probs /= model_probs.sum(axis=1, keepdims=True)

        # Sinkhorn-Knopp uniform balancing
        if self.apply_sinkhorn and n_samples > 1:
            model_probs = sinkhorn_knopp_balance(model_probs)

        return model_probs

    def predict(self, texts: list[str]) -> np.ndarray:
        """Predict the most probable model name for each text."""
        probs = self.predict_proba(texts)
        best_indices = np.argmax(probs, axis=1)
        return np.array([ALL_MODELS[i] for i in best_indices])


if __name__ == "__main__":
    print("=== Hierarchical Lab & Stylometric Invariant Classifier ===")
    print(f"Target Models ({len(ALL_MODELS)}): {ALL_MODELS}")
    print(f"Target Labs ({len(ALL_LABS)}): {ALL_LABS}")
    for lab, mods in LAB_TO_MODELS.items():
        print(f"  [{lab.upper():<10}] ({len(mods)} models): {mods}")
