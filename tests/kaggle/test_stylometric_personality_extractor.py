"""Tests for StylometricPersonalityExtractor in Kaggle competitions."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.kaggle.stylometric_personality_extractor import (
    StylometricPersonalityExtractor,
    StylometricPersonalityFeatureVector,
)


@pytest.fixture
def extractor() -> StylometricPersonalityExtractor:
    return StylometricPersonalityExtractor()


def test_feature_vector_dimension_and_names(extractor: StylometricPersonalityExtractor) -> None:
    text = (
        "## Method Overview\n"
        "We hypothesize that rank-based metrics are invariant under monotonic transformations.\n"
        "* Point 1: First order convergence.\n"
        "* Point 2: Empirical boundary conditions.\n"
        "```python\ndef solve(): pass\n```\n"
    )
    feat = extractor.extract_features(text)
    arr = feat.to_numpy()
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (29,)
    assert len(StylometricPersonalityFeatureVector.feature_names()) == 29
    assert feat.headings == 1.0
    assert feat.lists == 2.0


def test_pairwise_differential_features(extractor: StylometricPersonalityExtractor) -> None:
    text_claude = (
        "Here is a structured analysis of the problem:\n"
        "1. First, we identify the governing equations.\n"
        "2. Next, we verify edge-case boundaries.\n"
        "Therefore, the solution holds under all conditions."
    )
    text_gpt = (
        "Great question! I would be delighted to help you explore this topic! 🎉\n"
        "What specific aspects are you most excited to learn more about?"
    )
    
    pair = extractor.extract_pairwise_diff(text_claude, text_gpt)
    assert "vec_a" in pair
    assert "vec_b" in pair
    assert "diff" in pair
    assert "abs_diff" in pair
    assert "combined" in pair
    assert pair["combined"].shape == (87,)
    
    feat_a = extractor.extract_features(text_claude)
    feat_b = extractor.extract_features(text_gpt)
    assert feat_b.ends_with_question == 1.0
    assert feat_a.ends_with_question == 0.0
    assert pair["diff"][20] == -1.0  # ends_with_question diff index 20


def test_gemma4_developer_agent_compliance(extractor: StylometricPersonalityExtractor) -> None:
    clean_dev_output = (
        "### Root Cause\n"
        "The index check failed due to off-by-one indexing.\n"
        "```python\n"
        "def fix(x):\n"
        "    return x[:-1]\n"
        "```\n"
        "Verification: All unit tests pass.\n"
    )
    passed, report = extractor.evaluate_gemma4_agent_compliance(clean_dev_output)
    assert passed is True
    assert report["slop"] <= 25.0

    slop_output = (
        "Certainly! It is an absolute privilege to craft this wonderful code for you today! "
        "I am so very eager to help you succeed! In conclusion, I hope this splendid response assists you greatly!"
    )
    passed_slop, report_slop = extractor.evaluate_gemma4_agent_compliance(slop_output)
    assert passed_slop is False
