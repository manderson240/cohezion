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

import math


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
        quality_score
        * math.exp(-lambda_cost * cost_usd)
        * math.exp(-LAMBDA_ENERGY * energy_joules)
    )


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
    engaged = 1.3 <= fd <= 1.7 and dev < 0.1

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

    if fd < 1.2:
        interp = "System stuck — over-exploiting. Increase exploration (lower quality gate)."
    elif fd < 1.4:
        interp = "Below HIHO. Approaching equilibrium but not there."
    elif fd <= 1.6:
        interp = "HIHO equilibrium. Healthy exploration/exploitation balance."
    elif fd <= 1.8:
        interp = "Above HIHO. Slightly over-exploring. Tighten quality gates."
    else:
        interp = "Chaotic. Quality oscillating wildly. Check model health."

    return {
        "fd": round(fd, 3),
        "hiho_deviation": round(dev, 4),
        "hiho_engaged": engaged,
        "feynman_dominant_tier": dominant,
        "interpretation": interp,
    }
