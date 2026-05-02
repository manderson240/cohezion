"""Tests for RetrospectionValidator."""

import pytest

from cohezion.compound.retrospection_validator import RetrospectionValidator, ValidationResult


def _make_points(coherences: list[float], timestamps: list[float] | None = None) -> list[dict]:
    """Build minimal journey-point dicts for testing."""
    ts = timestamps or list(range(len(coherences)))
    return [{"coherence": c, "timestamp": t} for c, t in zip(coherences, ts)]


@pytest.fixture
def validator() -> RetrospectionValidator:
    return RetrospectionValidator()


# ---------------------------------------------------------------------------
# test_valid_summary_passes
# ---------------------------------------------------------------------------
def test_valid_summary_passes(validator: RetrospectionValidator) -> None:
    points = _make_points([0.4, 0.5, 0.6])
    summary = {"coherence_delta": 0.2, "steps_executed": 3, "success": True}
    result = validator.validate_summary(summary, points)
    assert result.valid
    assert result.discrepancies == []
    assert result.confidence == 1.0


# ---------------------------------------------------------------------------
# test_coherence_claim_mismatch_detected
# ---------------------------------------------------------------------------
def test_coherence_claim_mismatch_detected(validator: RetrospectionValidator) -> None:
    points = _make_points([0.4, 0.5, 0.6])  # actual delta = 0.2
    summary = {"coherence_delta": 0.9}  # fabricated claim
    result = validator.validate_summary(summary, points)
    assert not result.valid
    assert any("coherence_delta" in d for d in result.discrepancies)
    assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# test_step_count_mismatch_detected
# ---------------------------------------------------------------------------
def test_step_count_mismatch_detected(validator: RetrospectionValidator) -> None:
    points = _make_points([0.5, 0.6, 0.7])  # 3 points
    summary = {"steps_executed": 10}  # wrong count
    result = validator.validate_summary(summary, points)
    assert not result.valid
    assert any("steps_executed" in d for d in result.discrepancies)


# ---------------------------------------------------------------------------
# test_success_claim_mismatch_detected
# ---------------------------------------------------------------------------
def test_success_claim_mismatch_detected(validator: RetrospectionValidator) -> None:
    # Final coherence 0.1 is well below the 0.3 success threshold
    points = _make_points([0.5, 0.2, 0.1])
    summary = {"success": True}
    result = validator.validate_summary(summary, points)
    assert not result.valid
    assert any("success=True" in d for d in result.discrepancies)


# ---------------------------------------------------------------------------
# test_empty_journey_low_confidence
# ---------------------------------------------------------------------------
def test_empty_journey_low_confidence(validator: RetrospectionValidator) -> None:
    summary = {"coherence_delta": 0.5, "steps_executed": 5, "success": True}
    result = validator.validate_summary(summary, [])
    # No journey data → cannot verify anything → confidence 0.0
    assert isinstance(result, ValidationResult)
    assert result.confidence == 0.0
    # Empty journey is not treated as invalid — just unverifiable
    assert result.valid
