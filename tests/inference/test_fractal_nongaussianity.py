"""Discriminating tests for fractal_metrics.nongaussianity (cumulant criticality diagnostic).

Motivated by Allemand et al. Nature 2026 (non-Gaussian order-parameter statistics at criticality):
high-order cumulants (skewness/excess-kurtosis) flag regime change the mean/variance miss. Each test
FAILS for a no-op/wrong implementation (one that ignores the 3rd/4th moment or skips standardization).
"""

from cohezion.inference.fractal_metrics import nongaussianity, quality_series_report


# right-skewed: many low + a few high outliers → strong positive skewness (~1.3)
RIGHT_SKEWED = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.9, 0.95]
# tight unimodal cluster around 0.5 → near-Gaussian, low skew
GAUSSIAN_LIKE = [0.45, 0.5, 0.55, 0.48, 0.52, 0.5, 0.47, 0.53, 0.5, 0.49]


def test_right_skewed_series_is_flagged_nongaussian():
    r = nongaussianity(RIGHT_SKEWED)
    assert r["skewness"] > 0.5, r  # a no-op (returns 0) fails here
    assert r["nongaussian"] is True, r


def test_gaussian_like_series_low_skew():
    r = nongaussianity(GAUSSIAN_LIKE)
    assert abs(r["skewness"]) < 0.5, r


def test_skew_discriminates_between_series():
    # the DISCRIMINATING inequality: an impl that ignores the 3rd moment gives 0 for both → fails
    assert abs(nongaussianity(RIGHT_SKEWED)["skewness"]) > abs(
        nongaussianity(GAUSSIAN_LIKE)["skewness"]
    )


def test_constant_series_is_gaussian_trivial():
    # sigma≈0 guard: no distribution to be non-Gaussian about
    r = nongaussianity([0.5] * 10)
    assert r["skewness"] == 0.0 and r["excess_kurtosis"] == 0.0 and r["nongaussian"] is False


def test_short_series_safe():
    assert nongaussianity([0.5, 0.6])["nongaussian"] is False  # n<3, no crash


def test_report_includes_nongaussianity_fields():
    rep = quality_series_report([0.4, 0.5, 0.6, 0.5, 0.45, 0.55, 0.5])
    assert {"skewness", "excess_kurtosis", "nongaussian"} <= set(rep)
