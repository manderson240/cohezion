"""Tests for RSNA Knee Anatomical Covariance Calibrator."""

import numpy as np
import pytest

from cohezion.medical.rsna_anatomical_covariance import (
    CLINICAL_COVARIANCE_PRIOR,
    RSNA_12_LABELS,
    calibrate_predictions_with_anatomical_prior,
)


def test_covariance_dimensions():
    assert len(RSNA_12_LABELS) == 12
    assert CLINICAL_COVARIANCE_PRIOR.shape == (12, 12)
    assert np.all(np.diag(CLINICAL_COVARIANCE_PRIOR) == 1.0)
    # Check symmetry
    assert np.allclose(CLINICAL_COVARIANCE_PRIOR, CLINICAL_COVARIANCE_PRIOR.T)


def test_calibration_shape_and_bounds():
    rng = np.random.RandomState(42)
    raw = rng.uniform(0.01, 0.99, size=(50, 12))
    cal = calibrate_predictions_with_anatomical_prior(raw, alpha=0.15)
    assert cal.shape == (50, 12)
    assert np.all(cal > 0.0)
    assert np.all(cal < 1.0)
    assert np.all(np.isfinite(cal))


def test_clinical_co_occurrence_boosting():
    # Synthetic patient with high ACL tear prob (0.90) and high Bone Contusion (0.85),
    # but marginal Lateral Meniscus prob (0.35) due to noisy slice artifact.
    # Because ACL + Lateral Meniscus + Bone Contusion is the classic pivot-shift triad,
    # the anatomical prior should boost the subtle Lateral Meniscus probability!
    raw = np.full((1, 12), 0.10)
    raw[0, RSNA_12_LABELS.index("ACL")] = 0.92
    raw[0, RSNA_12_LABELS.index("Contusion")] = 0.88
    raw[0, RSNA_12_LABELS.index("Lateral Meniscus")] = 0.35

    cal = calibrate_predictions_with_anatomical_prior(raw, alpha=0.25)
    idx_lmen = RSNA_12_LABELS.index("Lateral Meniscus")
    assert cal[0, idx_lmen] > raw[0, idx_lmen], "Lateral Meniscus should be boosted by ACL+Contusion triad"
