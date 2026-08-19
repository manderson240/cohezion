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

A perfectly periodic signal carries zero surprise. A limit cycle is neither healthy exploration
nor chaos, and at period ~8 the FD band calls it healthy.

**Narrowed 2026-08-19 — the original framing here overclaimed.** "A compound loop thrashing
A->B->A->B is reported healthy" is FALSE, and an outside consult caught it. Measured:

    discrete A/B alternation   FD 2.000 -> CHAOTIC  (flagged)
    square wave, period 8      FD 1.086 -> STUCK    (mislabeled, but still flagged, and STUCK
                                                     triggers its own escalation path)
    SMOOTH sine, period 8      FD 1.391 -> HIHO     <-- the actual hidden case

So the hidden region is narrower than advertised: it is *smooth* oscillation at period ~4-9
within the window, not discrete state-flapping. Discrete thrash is caught by FD already. The
blindness is real and worth an instrument; it is just not the story originally told about it.

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

MEASURED BLIND SPOTS (6-lane adversarial review, 2026-08-19)
------------------------------------------------------------
Every number below was RUN, not reasoned about. Claims that failed verification are recorded
in the vault digest rather than here, because a limitation list is only useful if every entry
on it is real. Threshold is 0.6:

    three-state rotation A->B->C->A  0.478  MISSED  (found independently by two lanes)
    pure period-3 tone               0.478  MISSED  (same root cause — see below)
    duty cycle 75/25                 0.327  MISSED
    amplitude-modulated period-8     0.423  MISSED
    period drift 8 -> 12             0.243  MISSED  (window-dependent, see below)
    pure period-12 tone              0.345  MISSED  ** WINDOW ARTIFACT, NOT INTRINSIC **
    period-8 buried in linear trend  0.601  fires, but by 0.001 — effectively a coin flip

**Every number above is at n=20, and that qualifier was missing from the first version of this
list.** It matters: period-12 scores 0.345 at n=20 but **1.000 from n>=40** — it is not a blind
spot at all once the window is long enough, it is an artifact of scanning `k in range(4, n//2+1)`
with too little data. A limitation list that does not state its window assumption is itself
miscalibrated, which is precisely the standard applied to everything else here.

Intrinsic vs window-dependent, so a future reader does not chase the wrong ones:
  INTRINSIC  — period-3 and three-state rotation. A 3-cycle's half-lag autocorrelation is
               exactly -0.5, sitting on the strict `< -0.5` boundary; it scores ~0.48-0.51 at
               every n from 20 to 200, so no scan-range change reaches it without loosening the
               sign-flip requirement itself. Duty-cycle asymmetry is likewise structural.
  WINDOW     — period-12 (confirmed), and period-drift (likely, same mechanism).

Root cause of the period-3 family: the scan starts at `k=4`, and a 3-cycle's first positive
autocorrelation is at lag 3 with lag-1 at exactly -0.5, while the alternation branch requires
strictly `< -0.5`. It falls between the two branches. Periods 4-9 are all caught (0.805-1.000),
so this is a specific gap, not a general weakness.

These are NOT patched. Widening the detector to catch them means loosening the sign-flip
requirement, which is the single property separating oscillation from ordinary correlation —
and the rejected raw-autocorrelation design shows what loosening it costs (fired on healthy
Brownian drift at 0.821). With no real oscillating data to calibrate against, tuning to
synthetic cases would be fitting noise. Documented and left, deliberately.

STATUS: OBSERVE-ONLY. It does not gate, route, or alert. See `score()` docstring for why.
"""

from __future__ import annotations

import numpy as np

from cohezion.inference.fractal_metrics import FractalRegime, classify_fd


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

    OBSERVE-ONLY. The detector separates 7 synthetic cases cleanly (non-thrash <=0.206,
    thrash 1.000). Its behaviour on real data is **UNKNOWN**, and the reason is worth stating
    precisely, because two earlier versions of this paragraph stated it wrongly.

    VALIDATION STATUS: NO EVIDENCE EITHER WAY.

    Earlier versions cited "326 coherence series from `journey_point`, never fires, max score
    0.139" as evidence of a low false-positive rate. **That evidence is void — it was measured
    on the wrong lineage.** There are two unrelated `coherence` signals in this system:

      journey_point.coherence  <- swarm/quadrature_nexus.py: `1 - min(var(scores)*4, 1)` over
                                  FOUR HARDCODED CONSTANTS (0.7/0.75/0.8/0.65) with keyword
                                  bumps. var of those four bases gives EXACTLY 0.9875, which
                                  is the corpus mode at 81,469 of 278,741 rows. The whole
                                  corpus holds 43 distinct values, 99.4% of them >= 0.9. It
                                  is not a measurement of anything and never carried loop
                                  telemetry.

      mean_coherence           <- what THIS detector actually consumes. executor.py Step 5.8
                                  (line ~1347) -> `coherence_val` (1649) -> `check_degradation`
                                  (1661). Mean of a success-coupled binary (0.7 on success,
                                  0.2 on failure), an anomaly-health score, and an optional
                                  intent match.

    So "never fires" measured a formula over literals, not this detector's input. It is
    evidence of nothing — not of low false positives, not of low sensitivity.

    What can be said: the live signal contains a genuine success/failure binary, so it CAN
    move; and a real success/failure limit cycle would present as two-valued alternation,
    which this detector scores at 1.000. That is an argument the instrument is pointed at a
    live signal. It is NOT a measurement, and must not be recorded as one.

    To actually close this: persist DegradationDetector coherence-baseline snapshots and
    re-run the firing analysis on the executor lineage. Until then, do not gate on this.

    ⚠ THAT PATH IS CURRENTLY BLOCKED, and the block is not obvious. `DegradationDetector`'s
    CB7 persistence (`to_dict`/`from_dict`/`end_session`) has **no production caller** — its
    only `to_dict`/`from_dict` references in `src/` are inside its own definition file, and
    the `.end_session(` hits elsewhere belong to unrelated session managers. So every baseline
    this detector accumulates, INCLUDING the `"oscillation"` one written here, lives in memory
    and dies at process exit. Collecting the evidence needed to validate this detector
    therefore requires wiring CB7 persistence first. Do not assume the corpus is accruing.
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

    The healthy band is NOT re-implemented here. An earlier version hard-coded
    ``1.3 <= fd <= 1.7``, which duplicated the harness-canonical CC1 boundaries that
    ``classify_fd`` exists to own — its docstring says outright "Do not re-implement these
    boundaries in compound loop consumers." Adversarial review caught it. Delegating means a
    CC1 recalibration propagates here instead of silently desynchronising, and it also means
    this module inherits whatever float-boundary behaviour the canonical definition has rather
    than inventing a second, subtly different one.
    """
    return classify_fd(fd) is FractalRegime.HIHO and score(series) > OSCILLATION_THRESHOLD
