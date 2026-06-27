"""Tests for Bunimovich chaotic FD calibration (#100, CC1 complement)."""

from cohezion.inference.fractal_metrics import (
    bunimovich_calibration_sequence,
    higuchi_fd,
)


def test_bunimovich_sequence_length_and_bounds():
    seq = bunimovich_calibration_sequence()
    assert len(seq) == 100
    assert all(0.0 <= x <= 1.0 for x in seq)


def test_bunimovich_sequence_deterministic():
    assert bunimovich_calibration_sequence(50) == bunimovich_calibration_sequence(50)


def test_bunimovich_higuchi_fd_chaotic_regime():
    # EMPIRICAL: r=3.8 logistic is DETERMINISTIC CHAOS (post-period-doubling band),
    # NOT Brownian motion. Its Higuchi FD lands in the chaotic/white-noise regime
    # (FD -> 2.0; this module documents "FD > 1.8 = chaotic"). The original task
    # prose claimed [1.3, 1.7] (the Brownian CC1 band) -- that conflates chaotic
    # determinism with Brownian motion. The Bunimovich stadium is chaotic, so a high
    # FD is the physically correct, complementary anchor to CC1's Brownian one.
    fd = higuchi_fd(bunimovich_calibration_sequence())
    assert fd >= 1.8
