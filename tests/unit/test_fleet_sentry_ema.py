import pytest

from scripts.fleet_sentry import EmaRateFilter


def test_ema_rate_filter_smoothing():
    ema = EmaRateFilter(alpha=0.40)
    assert ema.filtered_rate is None

    # Step 1: Initial observation initializes filter directly
    r1 = ema.update(-0.5)
    assert r1 == -0.5

    # Step 2: Instantaneous noise spike to -2.0
    r2 = ema.update(-2.0)
    # Expected: 0.40 * (-2.0) + 0.60 * (-0.5) = -0.80 - 0.30 = -1.10
    assert pytest.approx(r2, abs=1e-5) == -1.10

    # Step 3: Returns to normal (-0.2)
    r3 = ema.update(-0.2)
    # Expected: 0.40 * (-0.2) + 0.60 * (-1.10) = -0.08 - 0.66 = -0.74
    assert pytest.approx(r3, abs=1e-5) == -0.74


def test_ema_rate_filter_reset():
    ema = EmaRateFilter()
    ema.update(10.0)
    assert ema.filtered_rate == 10.0
    ema.reset()
    assert ema.filtered_rate is None
