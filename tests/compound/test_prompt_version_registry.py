"""Tests for PromptVersionRegistry golden-fixture gate.

V-model pairing:
  Structural: gate method exists and is callable
  Behavioral: fail-open on no fixtures, allow on low drift, block on high drift
  Integration: SkillRefiner.refine() returns None when gate blocks
"""

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.prompt_version_registry import (
    DRIFT_THRESHOLD,
    PromptVersionRegistry,
    _centroid,
    _cosine,
)


# ── structural invariant ──────────────────────────────────────────────────────


def test_structural_check_drift_is_callable():
    """Structural: PromptVersionRegistry.check_drift exists and accepts (skill_name, content)."""
    import inspect

    sig = inspect.signature(PromptVersionRegistry.check_drift)
    assert "skill_name" in sig.parameters
    assert "new_content" in sig.parameters


# ── pure math ─────────────────────────────────────────────────────────────────


def test_cosine_identical_vectors():
    a = [1.0, 0.0, 0.0]
    assert _cosine(a, a) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert _cosine(a, b) == pytest.approx(0.0)


def test_centroid_two_vectors():
    vecs = [[2.0, 4.0], [4.0, 2.0]]
    c = _centroid(vecs)
    assert c == pytest.approx([3.0, 3.0])


# ── behavioral: fail-open paths ───────────────────────────────────────────────


def test_no_fixtures_registered_allows():
    """Fail-open: no golden fixtures → allow promotion."""
    reg = PromptVersionRegistry()
    with patch.object(reg, "_load_fixtures", return_value=[]):
        assert reg.check_drift("my-skill", "some new insight") is True


def test_fixtures_without_embeddings_allows():
    """Fail-open: fixtures exist but no embedding_768d stored → allow."""
    reg = PromptVersionRegistry()
    with patch.object(reg, "_load_fixtures", return_value=[{"skill_name": "my-skill"}]):
        assert reg.check_drift("my-skill", "some new insight") is True


def test_embed_failure_allows():
    """Fail-open: Lemonade unavailable → allow."""
    reg = PromptVersionRegistry()
    fixture_with_emb = [{"embedding_768d": [1.0, 0.0, 0.0]}]
    with patch.object(reg, "_load_fixtures", return_value=fixture_with_emb):
        with patch.object(reg, "_embed", return_value=None):
            assert reg.check_drift("my-skill", "any text") is True


def test_db_exception_allows():
    """Fail-open: SurrealDB unreachable → allow (exception swallowed)."""
    reg = PromptVersionRegistry()
    with patch.object(reg, "_load_fixtures", side_effect=ConnectionError("db down")):
        assert reg.check_drift("my-skill", "some text") is True


# ── behavioral: gate decisions ────────────────────────────────────────────────


def test_low_drift_allows():
    """Allow: new content very similar to fixture corpus (drift < 0.35)."""
    reg = PromptVersionRegistry()
    fixture_emb = [1.0, 0.0, 0.0]
    similar_emb = [0.98, 0.14, 0.0]  # cosine ≈ 0.98 → dist ≈ 0.02 < 0.35
    with patch.object(reg, "_load_fixtures", return_value=[{"embedding_768d": fixture_emb}]):
        with patch.object(reg, "_embed", return_value=similar_emb):
            with patch.object(reg, "_log_run"):
                assert reg.check_drift("my-skill", "similar text") is True


def test_high_drift_blocks():
    """Block: new content orthogonal to fixture corpus (drift = 1.0 >= 0.35)."""
    reg = PromptVersionRegistry()
    fixture_emb = [1.0, 0.0, 0.0]
    orthogonal_emb = [0.0, 1.0, 0.0]  # cosine = 0 → dist = 1.0 >= 0.35
    with patch.object(reg, "_load_fixtures", return_value=[{"embedding_768d": fixture_emb}]):
        with patch.object(reg, "_embed", return_value=orthogonal_emb):
            with patch.object(reg, "_log_run"):
                assert reg.check_drift("my-skill", "wildly different text") is False


def test_drift_threshold_boundary():
    """Exactly at threshold (dist == DRIFT_THRESHOLD) → block."""
    reg = PromptVersionRegistry()
    # cos(θ) = 1 - DRIFT_THRESHOLD means dist == DRIFT_THRESHOLD exactly
    target_cos = 1.0 - DRIFT_THRESHOLD
    # fixture=[1,0], embed=[cos,sin] → cosine = cos
    import math

    sin_val = math.sqrt(1.0 - target_cos**2)
    fixture_emb = [1.0, 0.0]
    boundary_emb = [target_cos, sin_val]
    with patch.object(reg, "_load_fixtures", return_value=[{"embedding_768d": fixture_emb}]):
        with patch.object(reg, "_embed", return_value=boundary_emb):
            with patch.object(reg, "_log_run"):
                assert reg.check_drift("my-skill", "boundary text") is False


# ── integration: SkillRefiner honours the gate ────────────────────────────────


def test_skill_refiner_respects_gate_block():
    """SkillRefiner.refine() returns None when golden-fixture gate blocks."""
    from cohezion.compound.skill_refiner import LearningSignal, SkillRefiner

    refiner = SkillRefiner()
    fake_signal = LearningSignal(
        skill_name="test-skill",
        operation_type="generate",
        key_insight="potentially drifted insight",
        metric_change="+5% quality",
        recommendation="keep",
        confidence=0.9,
    )
    fake_prime = MagicMock()

    with (
        patch.object(refiner, "_extract_metrics") as mock_metrics,
        patch.object(refiner, "_generate_learning_signal", return_value=fake_signal),
        patch.object(refiner, "_find_prime_file", return_value=fake_prime),
        patch("cohezion.compound.prompt_version_registry.PromptVersionRegistry") as MockGate,
    ):
        mock_metrics.return_value = MagicMock(success=True)
        MockGate.return_value.check_drift.return_value = False  # gate blocks

        result = refiner.refine(
            "test-skill", "generate", {"success": True, "metrics": {}, "token_metrics": {}}
        )

    assert result is None
    MockGate.return_value.check_drift.assert_called_once_with("test-skill", fake_signal.key_insight)
