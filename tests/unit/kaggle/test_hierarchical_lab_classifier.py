"""Tests for Hierarchical Lab & Perplexity Classifier for Name That LLM."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.kaggle.name_that_llm.hierarchical_lab_classifier import (
    ALL_LABS,
    ALL_MODELS,
    HierarchicalLabClassifier,
    MODEL_TO_LAB,
    extract_compression_and_stylometric_features,
    sinkhorn_knopp_balance,
)


def test_model_to_lab_mapping_integrity() -> None:
    """Verify all 18 models are mapped to valid labs and bidirectional mappings match."""
    assert len(ALL_MODELS) == 18
    assert len(MODEL_TO_LAB) == 18
    for m in ALL_MODELS:
        assert m in MODEL_TO_LAB
        assert MODEL_TO_LAB[m] in ALL_LABS


def test_extract_compression_and_stylometric_features() -> None:
    """Verify compression ratios, Shannon entropy, and formatting features extract cleanly."""
    samples = [
        "Certainly! Here is the solution to your problem:\n* First point\n* Second point\n```python\nprint('hello')\n```",
        "To answer this question, we must analyze the data:\n1. Analysis\n2. Conclusion.\n",
        "Sure thing, here's the details.\n- Step A\n- Step B",
    ]
    feats = extract_compression_and_stylometric_features(samples)

    assert isinstance(feats, np.ndarray)
    assert feats.shape[0] == 3
    assert feats.shape[1] > 20
    # No NaNs or infinities
    assert not np.isnan(feats).any()
    assert not np.isinf(feats).any()


def test_sinkhorn_knopp_balance() -> None:
    """Verify Sinkhorn-Knopp algorithm balances column marginals to uniform target."""
    np.random.seed(42)
    # 100 samples, 4 classes
    raw_probs = np.random.uniform(0.1, 1.0, size=(100, 4))
    raw_probs /= raw_probs.sum(axis=1, keepdims=True)

    balanced = sinkhorn_knopp_balance(raw_probs, max_iter=30)

    # Row sums must be 1.0
    row_sums = balanced.sum(axis=1)
    np.testing.assert_allclose(row_sums, 1.0, atol=1e-3)

    # Column sums should be approximately equal (100 / 4 = 25 each)
    col_sums = balanced.sum(axis=0)
    expected_col_sums = np.full(4, 25.0)
    np.testing.assert_allclose(col_sums, expected_col_sums, atol=1.0)


def test_hierarchical_classifier_fit_predict() -> None:
    """Verify hierarchical classifier trains Level-1 and Level-2 and outputs 18-class probabilities."""
    # Create synthetic dataset with samples from multiple labs
    texts = [
        "Certainly! I would be pleased to help you with Python programming.",
        "Here is the markdown code you requested:\n* Bullet 1\n* Bullet 2",
        "Sure, let's look at the implementation step by step.",
        "As an AI, I can provide the analysis below:\n- Item 1\n- Item 2",
        "To answer this prompt, consider the following mathematical formula.",
        "Here's the concise explanation with code examples:\n```python\npass\n```",
        "Certainly! Let's examine this carefully with thorough reasoning.",
        "Sure, here is how you can achieve this in Linux.",
    ]
    labels = [
        "claude-sonnet-5",
        "claude-opus-4-6",
        "gpt-5.5",
        "gpt-5.6-luna",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "qwen3.8-max",
        "kimi-k3",
    ]

    clf = HierarchicalLabClassifier(c_lab=1.0, c_intra=1.0, apply_sinkhorn=False)
    clf.fit(texts, labels)

    test_texts = [
        "Certainly! Let's examine the detailed implementation.",
        "Sure, here is a quick overview.",
    ]
    probs = clf.predict_proba(test_texts)

    assert isinstance(probs, np.ndarray)
    assert probs.shape == (2, 18)
    # Check probabilities sum to 1.0
    np.testing.assert_allclose(probs.sum(axis=1), 1.0, atol=1e-4)

    preds = clf.predict(test_texts)
    assert len(preds) == 2
    assert preds[0] in ALL_MODELS
    assert preds[1] in ALL_MODELS
