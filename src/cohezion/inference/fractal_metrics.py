"""Fractal metrics for compound loop quality analysis.

Feynman + fractal synthesis:
- The tier routing IS a Feynman path integral: each tier is a path, the
  quality score is the amplitude, and the system selects the dominant path.
  Σ A(tier_i) where A = quality_score × exp(-cost_penalty)

- The AUTODQA quality time series should have Higuchi fractal dimension ≈ 1.5
  (Brownian motion) when the system is at HIHO equilibrium. FD < 1.2 means
  the loop is stuck; FD > 1.8 means it's oscillating chaotically.

- The 4x(1-x) coherence kernel IS the logistic map at r=4. At x=0.5 (HIHO),
  this is the onset of the Feigenbaum universality — the period-doubling
  route to chaos. The HIHO threshold is the fixed point of the map.
"""

from __future__ import annotations

import collections
import enum
import math


# HIHO deviation gate: |mean(scores) - 0.5| must be below this for the compound
# loop to be considered "at the HIHO attractor" (in addition to FD in [1.3, 1.7]).
# This is the canonical threshold — do not re-implement the 0.1 literal anywhere else.
_HIHO_DEVIATION_THRESHOLD: float = 0.1


class FractalRegime(enum.Enum):
    """Named HIHO regime derived from Higuchi fractal dimension.

    Boundary values are harness-canonical (CC1):
    - FD < 1.3  → STUCK    (over-exploitation, no exploration)
    - 1.3 ≤ FD ≤ 1.7 → HIHO (Brownian equilibrium, healthy compound loop)
    - FD > 1.7  → CHAOTIC  (over-exploration, wildly oscillating quality)

    These thresholds are the SINGLE source of truth for FD regime classification.
    Do not re-implement these boundaries in compound loop consumers.
    """

    STUCK = "stuck"
    HIHO = "hiho"
    CHAOTIC = "chaotic"


def classify_fd(fd: float) -> FractalRegime:
    """Return the named HIHO regime for a Higuchi fractal dimension value.

    Encodes the harness-canonical CC1 thresholds in one place:
    - FD < 1.3  → FractalRegime.STUCK
    - 1.3 ≤ FD ≤ 1.7 → FractalRegime.HIHO
    - FD > 1.7  → FractalRegime.CHAOTIC

    Parameters
    ----------
    fd : float
        Higuchi fractal dimension from higuchi_fd().

    Returns
    -------
    FractalRegime
        Named regime — actionable for compound loop routing decisions.

    Examples
    --------
    >>> classify_fd(1.5)
    <FractalRegime.HIHO: 'hiho'>
    >>> classify_fd(1.1)
    <FractalRegime.STUCK: 'stuck'>
    >>> classify_fd(1.9)
    <FractalRegime.CHAOTIC: 'chaotic'>
    """
    if fd < 1.3:
        return FractalRegime.STUCK
    if fd <= 1.7:
        return FractalRegime.HIHO
    return FractalRegime.CHAOTIC


def higuchi_fd(series: list[float], k_max: int = 5) -> float:
    """Compute Higuchi fractal dimension of a time series.

    Higuchi (1988): measures complexity of a 1D time series.
    - FD ≈ 1.0: smooth, predictable (straight line)
    - FD ≈ 1.5: Brownian motion (HIHO equilibrium)
    - FD ≈ 2.0: fully random (white noise)

    Parameters
    ----------
    series : list[float]
        Quality scores or coherence values, length ≥ 4.
    k_max : int
        Maximum interval length. Higher = more accurate, but needs longer series.

    Returns
    -------
    float
        Fractal dimension in [1.0, 2.0]. Returns 1.0 on insufficient data.
    """
    n = len(series)
    if n < 4:
        return 1.0

    lk: list[tuple[float, float]] = []
    for k in range(1, min(k_max + 1, n // 2)):
        lengths: list[float] = []
        for m in range(1, k + 1):
            n_eff = (n - m) // k  # number of complete intervals
            if n_eff < 1:
                continue
            # Higuchi normalization: (N-1) / (n_eff × k²)
            norm = (n - 1) / (n_eff * k * k)
            total = 0.0
            for j in range(1, n_eff + 1):
                total += abs(series[m - 1 + j * k] - series[m - 1 + (j - 1) * k])
            lengths.append(total * norm)
        length_sum = sum(lengths)
        if lengths and length_sum > 0.0:
            lk.append((math.log(k), math.log(length_sum / len(lengths))))

    if len(lk) < 2:
        return 1.0

    # Linear regression slope = -FD (Higuchi)
    xs = [p[0] for p in lk]
    ys = [p[1] for p in lk]
    n_pts = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(xs[i] * ys[i] for i in range(n_pts))
    denom = n_pts * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 1.0
    slope = (n_pts * sxy - sx * sy) / denom
    return max(1.0, min(2.0, -slope))


# Energy penalty coefficient (1/joule). On a $0 local fleet the cost term is uniformly 0, so
# electricity is the ONLY thing distinguishing NPU (~2 W) from iGPU (~35 W) from CPU (~55 W).
# NEEDS-CALIBRATION: 0.01 is a sensible starting weight (a 55 J CPU turn → ~0.58× amplitude, a
# 4 J NPU turn → ~0.96×) but the exact value should be tuned against real tokens-per-watt
# telemetry (hardware_telemetry.tokens_per_watt) before being treated as load-bearing.
LAMBDA_ENERGY = 0.01


def feynman_path_weight(
    quality_score: float, cost_usd: float = 0.0, energy_joules: float = 0.0
) -> float:
    """Feynman path integral amplitude for a tier — quality vs DOLLARS vs ELECTRICITY.

    A(tier) = quality_score × exp(-lambda_cost × cost_usd) × exp(-LAMBDA_ENERGY × energy_joules)

    - lambda_cost = 100 (CC2, calibrated: $0.01 halves the amplitude). UNCHANGED.
    - LAMBDA_ENERGY penalizes joules so that, among $0 local tiers, the lower-wattage lane wins
      when quality ties. ``energy_joules`` defaults to 0.0 → identical to the prior CC2 behavior
      (the CC2 harness check, which passes energy=0, is byte-for-byte unaffected).

    At zero cost AND zero energy, A = quality_score. The dominant tier is argmax(A): maximize
    quality, penalize dollars (cloud), then penalize watts (NPU > iGPU > CPU among local).
    """
    lambda_cost = 100.0
    return (
        quality_score * math.exp(-lambda_cost * cost_usd) * math.exp(-LAMBDA_ENERGY * energy_joules)
    )


def feynman_amplitude_rank(
    candidates: list[tuple[str, float, float, float]],
) -> list[str]:
    """Rank candidate tiers best-first by Feynman amplitude (quality × cost × energy).

    Each candidate is ``(name, quality_score, cost_usd, energy_joules)``. Returns the names
    ordered by descending ``feynman_path_weight``. Quality dominates (it is the linear factor);
    cost and energy are exponential penalties that only break ties among equal-quality lanes —
    a higher-quality heavier lane still wins. Stable: equal-amplitude candidates keep input
    order. With ``energy_joules=0`` everywhere the ranking reduces to the CC2 cost-only order.
    """
    scored = [
        (feynman_path_weight(q, cost, joules), idx, name)
        for idx, (name, q, cost, joules) in enumerate(candidates)
    ]
    scored.sort(key=lambda t: (-t[0], t[1]))  # amplitude desc, then stable by input index
    return [name for _, _, name in scored]


def hiho_fixed_point_deviation(scores: list[float]) -> float:
    """Measure deviation of quality score mean from the HIHO fixed point (0.5).

    The logistic map f(x) = 4x(1-x) has fixed point at x=0.5.
    If the compound loop's quality scores cluster near 0.5, the system
    is operating at the HIHO attractor — the optimal exploration/exploitation
    balance (Feigenbaum universality).

    Returns
    -------
    float
        |mean(scores) - 0.5|. Values < 0.05 = HIHO attractor engaged.
    """
    if not scores:
        return float("inf")
    return abs(sum(scores) / len(scores) - 0.5)


def nongaussianity(series: list[float]) -> dict[str, float | bool]:
    """Non-Gaussianity of a quality/coherence series via standardized cumulants.

    Motivated by Allemand et al. (Nature 2026, doi:10.1038/s41586-026-10811-1): near a phase
    transition the order parameter's high-order cumulants become non-zero and change sign — a
    criticality signature the mean/variance miss. Here the "order parameter" is the coherence
    series; a run approaching a regime change (stuck<->hiho<->chaotic) develops skew/heavy tails
    BEFORE ``higuchi_fd`` fully crosses a band, so this complements (never replaces) the FD signal.

    Returns skewness (3rd standardized moment), excess_kurtosis (4th - 3; 0 = Gaussian), and a
    ``nongaussian`` flag. A degenerate (near-constant) series is Gaussian-trivially: zeros, flag False.
    """
    n = len(series)
    if n < 3:
        return {"skewness": 0.0, "excess_kurtosis": 0.0, "nongaussian": False}
    mean = sum(series) / n
    var = sum((x - mean) ** 2 for x in series) / n
    sigma = math.sqrt(var)
    if sigma < 1e-9:  # near-constant: no distribution to be non-Gaussian about
        return {"skewness": 0.0, "excess_kurtosis": 0.0, "nongaussian": False}
    m3 = sum((x - mean) ** 3 for x in series) / n
    m4 = sum((x - mean) ** 4 for x in series) / n
    skew = m3 / (sigma**3)
    excess_kurt = m4 / (sigma**4) - 3.0
    # Gaussian => (0, 0). Flag when either cumulant departs materially from Gaussian.
    nongaussian = abs(skew) > 0.5 or abs(excess_kurt) > 1.0
    return {
        "skewness": round(skew, 4),
        "excess_kurtosis": round(excess_kurt, 4),
        "nongaussian": nongaussian,
    }


def quality_series_report(scores: list[float]) -> dict[str, float | str]:
    """Comprehensive fractal + Feynman report for an AUTODQA quality series.

    Parameters
    ----------
    scores : list[float]
        Quality scores (0.0–1.0) from AutoDQA.evaluate() calls.

    Returns
    -------
    dict
        fd: Higuchi fractal dimension
        hiho_deviation: |mean - 0.5|
        hiho_engaged: True if FD in [1.3, 1.7] AND deviation < 0.1
        regime: named FractalRegime.value — "stuck" / "hiho" / "chaotic"
        feynman_dominant_tier: theoretical dominant path at this quality level
        interpretation: plain-text description
    """
    if not scores:
        return {
            "fd": 1.0,
            "hiho_deviation": 0.5,
            "hiho_engaged": False,
            "interpretation": "no data",
        }

    fd = higuchi_fd(scores)
    dev = hiho_fixed_point_deviation(scores)
    engaged = classify_fd(fd) is FractalRegime.HIHO and dev < _HIHO_DEVIATION_THRESHOLD

    mean_score = sum(scores) / len(scores)
    # Dominant tier based on mean quality and zero-cost local silicon
    if mean_score >= 0.9:
        dominant = "npu"
    elif mean_score >= 0.7:
        dominant = "igpu"
    elif mean_score >= 0.5:
        dominant = "cpu"
    else:
        dominant = "cloud (escalation needed)"

    regime = classify_fd(fd)
    if regime is FractalRegime.STUCK:
        interp = "System stuck — over-exploiting. Increase exploration (lower quality gate)."
    elif regime is FractalRegime.HIHO:
        interp = "HIHO equilibrium. Healthy exploration/exploitation balance."
    else:  # CHAOTIC
        interp = "Chaotic. Quality oscillating wildly. Check model health."

    ng = nongaussianity(scores)
    return {
        "fd": round(fd, 3),
        "hiho_deviation": round(dev, 4),
        "hiho_engaged": engaged,
        "regime": regime.value,
        "feynman_dominant_tier": dominant,
        "skewness": ng["skewness"],
        "excess_kurtosis": ng["excess_kurtosis"],
        "nongaussian": ng["nongaussian"],
        "interpretation": interp,
    }


def gwtc5_calibration_sequence(n: int = 100) -> list[float]:
    """Poisson process time series anchored to GWTC-5 GW detection rate.

    GWTC-5 (arXiv:2506.05718v1, LVK 2025) reports 390 gravitational-wave events
    over O1–O4, equivalent to a rate λ ≈ 3.5 detections/week in O4 sensitivity.
    Poisson inter-event times are Exponential(λ), and the cumulative-detection curve
    is a random walk whose Higuchi fractal dimension falls in the Brownian range
    [1.3, 1.7] — the HIHO equilibrium band of CC1.

    Use as an empirically-grounded CC1 calibration anchor (complements the purely
    synthetic Brownian-motion test in CC1). A Higuchi FD far outside [1.3, 1.7] on
    this sequence would indicate a problem with the FD implementation.

    Fixed seed 390 (= GWTC-5 event count) for deterministic output.
    The GWTC-5 weekly event-rate fluctuation is drawn from Poisson(λ=3.5),
    de-meaned so it oscillates around zero — this gives a Brownian-range FD.
    """
    import random

    rng = random.Random(390)  # fixed seed = GWTC-5 event count
    lam = 3.5  # mean events per week (O4 sensitivity, 2025)
    p_daily = lam / 7.0  # P(GW event in one day)
    cumulative = 0.0
    result: list[float] = []
    for _ in range(n):
        # Weekly GW count ~ Binomial(7, p_daily). De-mean → zero-mean innovation.
        # Cumulative sum of de-meaned innovations = Brownian motion → FD ≈ 1.5.
        week_count = sum(1 for _ in range(7) if rng.random() < p_daily)
        cumulative += week_count - lam  # de-mean: subtract expected count λ
        result.append(cumulative)
    # Normalize to [0, 1]
    mn, mx = min(result), max(result)
    span = mx - mn if mx > mn else 1.0
    return [(v - mn) / span for v in result]


def bunimovich_calibration_sequence(n: int = 100) -> list[float]:
    """Chaotic time series via logistic map r=3.8 -- same universality class as Bunimovich stadium.

    The Bunimovich stadium billiard is the canonical deterministically-chaotic dynamical
    system (positive Lyapunov exponent, ergodic). The logistic map at r=3.8 lives in the
    same chaotic band past the period-doubling cascade, so its Higuchi fractal dimension
    sits in the *chaotic* regime (FD -> 2.0, ``FD > 1.8`` per this module's interpretation),
    NOT the Brownian ``[1.3, 1.7]`` band used by the CC1 quality-series invariant. It is a
    deterministic high-FD calibration anchor complementing CC1's Brownian-motion anchor.
    """
    x = 0.3
    result: list[float] = []
    for _ in range(n):
        x = 3.8 * x * (1 - x)
        result.append(x)
    return result


class RollingRegimeTracker:
    """Streaming HIHO regime tracker over a fixed-size rolling window of quality scores.

    Designed for incremental injection into compound loop consumers (DegradationDetector,
    CompoundExecutor) without buffering unbounded histories. Each call to `update()` appends
    one score, evicts the oldest when the window is full, and returns the current regime.

    Parameters
    ----------
    window_size : int
        Number of recent quality scores to keep. Minimum effective window for a reliable
        Higuchi FD estimate is 20; smaller windows give FD = 1.0 (insufficient data).
    min_samples : int
        Gate: do not compute FD until at least this many samples have been seen.
        Defaults to the same as window_size (fill the window before the first report).
    """

    def __init__(self, window_size: int = 80, min_samples: int | None = None) -> None:
        if window_size < 4:
            raise ValueError(f"window_size must be ≥ 4, got {window_size}")
        self._window_size = window_size
        self._min_samples = min_samples if min_samples is not None else window_size
        self._scores: collections.deque[float] = collections.deque(maxlen=window_size)
        self._regime_history: list[FractalRegime] = []

    # ── Public API ────────────────────────────────────────────────────────

    def update(self, score: float) -> FractalRegime | None:
        """Append a quality score and return the current regime (or None if below min_samples).

        Parameters
        ----------
        score : float
            A quality score in [0.0, 1.0].

        Returns
        -------
        FractalRegime or None
            Current regime after update, or None if fewer than min_samples seen.
        """
        self._scores.append(score)
        if len(self._scores) < self._min_samples:
            return None
        report = quality_series_report(list(self._scores))
        regime = FractalRegime(report["regime"])
        self._regime_history.append(regime)
        return regime

    def current_regime(self) -> FractalRegime | None:
        """Return the regime computed at the last update() call, or None if below min_samples."""
        if not self._regime_history:
            return None
        return self._regime_history[-1]

    def is_hiho(self) -> bool:
        """Return True iff the latest regime is HIHO. False if below min_samples."""
        return self.current_regime() is FractalRegime.HIHO

    def deviation(self) -> float:
        """Return |mean(window) - 0.5|. Returns 0.5 (max deviation) if no scores yet."""
        if not self._scores:
            return 0.5
        return hiho_fixed_point_deviation(list(self._scores))

    def regime_history(self) -> list[FractalRegime]:
        """Return a copy of all regime values computed since the tracker was created."""
        return list(self._regime_history)

    def __len__(self) -> int:
        """Number of scores currently in the rolling window."""
        return len(self._scores)

    def reset(self) -> None:
        """Clear the window and regime history (start fresh)."""
        self._scores.clear()
        self._regime_history.clear()
