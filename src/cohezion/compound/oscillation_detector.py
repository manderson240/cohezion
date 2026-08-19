"""Oscillation (limit-cycle) detection for quality-metric series — OBSERVE-ONLY.

WHY THIS EXISTS
---------------
`higuchi_fd` measures path roughness and is **blind to periodicity**. Worse, the blindness
lands where it hurts: measured against the real `higuchi_fd`, a pure tone reads across the
whole FD range depending only on its period relative to sampling —

    period 32 -> FD 1.044 (reads "stuck", correct)
    period 16 -> FD 1.106 (reads "stuck", correct)
    period  8 -> FD 1.412  <-- INSIDE the CC1 "healthy HIHO equilibrium" band [1.3, 1.7]
    period  4 -> FD 2.000 (reads "chaotic")

A perfectly periodic signal carries zero surprise. A compound loop thrashing A->B->A->B is
neither healthy exploration nor chaos — it is a limit cycle, and at period ~8 the FD band
calls it healthy.

WHY THIS SHAPE OF DETECTOR
--------------------------
Two earlier designs were built and REJECTED by measurement:

1. Spectral concentration (top-decile FFT power). Worked at n=64; **failed at the production
   n=20 window** — 11 rfft bins and a non-integer cycle count smear the power (period-8
   thrash scored 0.495, no flag).
2. Raw max-autocorrelation. Caught the thrash but **fired on healthy Brownian drift** (0.821),
   because a random walk is autocorrelated by construction.

This design requires a SIGN FLIP: autocorrelation strongly positive at lag k and strongly
negative near k/2. A cycle alternates; a drift or monotone ramp never does. That is the
property which separates oscillation from mere correlation.

STATUS: OBSERVE-ONLY. It does not gate, route, or alert. See `score()` docstring for why.
"""

from __future__ import annotations

import numpy as np


# Below this, treat as no oscillation. Chosen from a synthetic separation where non-thrash
# scored <=0.206 and thrash scored 1.000 — deliberately mid-gap, and NOT yet validated on
# production data (see module docstring / OS3).
OSCILLATION_THRESHOLD = 0.6

MIN_SAMPLES = 8


def _autocorr(x: np.ndarray, lag: int) -> float:
    if lag <= 0 or lag >= len(x):
        return 0.0
    a, b = x[:-lag], x[lag:]
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def score(series: list[float] | np.ndarray) -> float:
    """Return an oscillation score in [0, 1]. Higher = more clearly a limit cycle.

    Returns 0.0 for series shorter than MIN_SAMPLES or with zero variance — a constant is
    "stuck", which `higuchi_fd` already reports correctly (FD ~= 1.0); this detector exists
    only for the case FD gets WRONG.

    OBSERVE-ONLY. Validation status, stated so no caller over-trusts it: the detector
    separates 7 synthetic cases cleanly (non-thrash <=0.206, thrash 1.000), but on the only
    real corpus available (326 coherence series from `journey_point`) it **never fires** —
    max score 0.139, p99 0.000 — because 98% of those series carry <=2 distinct values. That
    is evidence of a low false-positive rate on near-constant data and NOT evidence that it
    catches real thrash. Do not gate on this until real oscillating data exists.
    """
    x = np.asarray(series, dtype=float)
    if len(x) < MIN_SAMPLES:
        return 0.0
    x = x - x.mean()
    if x.std() == 0:
        return 0.0

    best = 0.0
    for k in range(4, len(x) // 2 + 1):
        pos = _autocorr(x, k)
        neg = _autocorr(x, max(2, k // 2))
        if pos > 0 and neg < 0:
            # Both halves of the signature must be strong; the weaker one bounds the score.
            best = max(best, min(pos, -neg))

    # Period-2 alternation (A/B/A/B) has no k/2 lag to test, so it needs its own case:
    # a strongly NEGATIVE lag-1 autocorrelation is exactly the alternating signature.
    lag1 = _autocorr(x, 1)
    if lag1 < -0.5:
        best = max(best, -lag1)

    return float(min(1.0, best))


def is_hidden_thrash(series: list[float] | np.ndarray, fd: float) -> bool:
    """True when FD calls a series healthy but it is actually oscillating.

    This is the whole point: the interesting case is not "oscillation detected" but
    "oscillation detected *while the fractal-dimension band says healthy*", because that is
    the region where FD alone is silently wrong.
    """
    return 1.3 <= fd <= 1.7 and score(series) > OSCILLATION_THRESHOLD
