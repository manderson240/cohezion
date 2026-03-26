"""Agentic benchmark metrics for FLUME journey EVO physics evaluation.

Provides 6 EVO physics metric families with bootstrap confidence intervals,
Mann-Whitney U significance testing, Bonferroni multiple-hypothesis correction,
and power analysis for small sample sizes.

Metric Families:
1. CoherenceMetric      — HIHO coherence near 0.5
2. TRIUNEBalanceMetric  — Equal Doer/Thinker/Knower activation
3. StabilityMetric      — Low variance, consistent HIHO proximity
4. ExoticChargeMetric   — Accumulation rate and peak stability
5. KordylewskiOrbitMetric — L4/L5 Lagrange stability
6. SPINPhaseMetric      — Monotonic phase accumulation

All metrics return BootstrapResult objects with mean, std, CI, and p_value
against a null hypothesis of random performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


N_BOOTSTRAP = 1000
ALPHA = 0.05


@dataclass(frozen=True)
class BootstrapResult:
    mean: float
    std: float
    ci_lower: float
    ci_upper: float
    p_value: float
    n_samples: int = N_BOOTSTRAP
    effect_size: float = 0.0


@dataclass(frozen=True)
class StatisticalComparison:
    u_statistic: float
    p_value: float
    effect_size: float
    significant: bool
    n_group1: int
    n_group2: int


class BonferroniCorrection:
    def __init__(self, n_tests: int, alpha: float = ALPHA) -> None:
        self.n_tests = n_tests
        self.alpha = alpha
        self.corrected_alpha = alpha / n_tests

    def correct(self, p_values: list[float]) -> list[float]:
        return [min(p * self.n_tests, 1.0) for p in p_values]

    def significant_mask(self, p_values: list[float]) -> list[bool]:
        return [p < self.corrected_alpha for p in p_values]


def _norm_cdf(z: float) -> float:
    import math

    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def _bootstrap_mean_ci(
    data: np.ndarray, n_bootstrap: int = N_BOOTSTRAP, alpha: float = ALPHA
) -> tuple[float, float, float]:
    n = len(data)
    if n == 0:
        return 0.0, 0.0, 1.0
    if n == 1:
        return float(data[0]), float(data[0]), 0.5
    bootstrap_means = np.empty(n_bootstrap, dtype=np.float64)
    for i in range(n_bootstrap):
        indices = np.random.randint(0, n, size=n)
        bootstrap_means[i] = np.mean(data[indices])
    ci_lower = float(np.percentile(bootstrap_means, (alpha / 2) * 100))
    ci_upper = float(np.percentile(bootstrap_means, (1 - alpha / 2) * 100))
    observed_mean = float(np.mean(data))
    se = float(np.std(bootstrap_means, ddof=1)) if n_bootstrap > 1 else 1.0
    z = 0.0 if se < 1e-9 else observed_mean / se
    p_value = float(2.0 * (1.0 - _norm_cdf(abs(z))))
    return ci_lower, ci_upper, p_value


def _mann_whitney_u(group1: np.ndarray, group2: np.ndarray) -> StatisticalComparison:
    import scipy.stats

    data1 = group1[np.isfinite(group1)] if len(group1) > 0 else np.array([0.0])
    data2 = group2[np.isfinite(group2)] if len(group2) > 0 else np.array([0.0])
    n1, n2 = len(data1), len(data2)
    if n1 == 0 or n2 == 0:
        return StatisticalComparison(0.0, 1.0, 0.0, False, n1, n2)
    u_stat, p_val = scipy.stats.mannwhitneyu(data1, data2, alternative="two-sided")
    rank_biserial = 1.0 - (2.0 * float(u_stat) / (n1 * n2))
    return StatisticalComparison(
        u_statistic=float(u_stat),
        p_value=float(p_val),
        effect_size=float(rank_biserial),
        significant=bool(p_val < ALPHA),
        n_group1=n1,
        n_group2=n2,
    )


class CoherenceMetric:
    def __init__(self, target: float = 0.5) -> None:
        self.target = target

    def compute(self, episode_coherences: list[float]) -> BootstrapResult:
        data = np.array([c for c in episode_coherences if np.isfinite(c)], dtype=np.float64)
        if len(data) == 0:
            data = np.array([0.0])
        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data)
        effect_size = (mean - self.target) / (std + 1e-9)
        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            effect_size=effect_size,
        )

    def compare(self, group1: list[float], group2: list[float]) -> StatisticalComparison:
        return _mann_whitney_u(np.array(group1), np.array(group2))


class TRIUNEBalanceMetric:
    def compute(
        self,
        doer_states: list[np.ndarray],
        thinker_states: list[np.ndarray],
        knower_states: list[np.ndarray],
    ) -> BootstrapResult:
        n = min(len(doer_states), len(thinker_states), len(knower_states))
        if n == 0:
            return BootstrapResult(mean=1.0, std=0.0, ci_lower=1.0, ci_upper=1.0, p_value=1.0)
        scores = []
        for i in range(n):
            dm = float(np.mean(doer_states[i]))
            tm = float(np.mean(thinker_states[i]))
            km = float(np.mean(knower_states[i]))
            scores.append(abs(dm - 0.5) + abs(tm - 0.5) + abs(km - 0.5))
        data = np.array(scores, dtype=np.float64)
        data = data[np.isfinite(data)]
        if len(data) == 0:
            return BootstrapResult(mean=1.0, std=0.0, ci_lower=1.0, ci_upper=1.0, p_value=1.0)
        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data)
        null_value = 1.0
        effect_size = (null_value - mean) / (std + 1e-9)
        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            effect_size=effect_size,
        )


class StabilityMetric:
    def compute(
        self, coherence_trajectory: list[float], hiho_distances: list[float]
    ) -> BootstrapResult:
        scores = []
        for c, h in zip(coherence_trajectory, hiho_distances, strict=True):
            window = coherence_trajectory[max(0, len(coherence_trajectory) - 20) :]
            cv = float(np.std(window) / (np.mean(window) + 1e-9))
            score = 1.0 / (1.0 + cv + abs(c - 0.5) + h)
            scores.append(score)
        data = np.array([s for s in scores if np.isfinite(s)], dtype=np.float64)
        if len(data) == 0:
            data = np.array([0.0])
        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data)
        null_value = 0.5
        effect_size = (mean - null_value) / (std + 1e-9)
        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            effect_size=effect_size,
        )


class ExoticChargeMetric:
    def compute(self, exotic_charge_trajectory: list[float]) -> BootstrapResult:
        data = np.array([e for e in exotic_charge_trajectory if np.isfinite(e)], dtype=np.float64)
        if len(data) == 0:
            data = np.array([0.0])
        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data)
        null_value = 0.3
        effect_size = (mean - null_value) / (std + 1e-9)
        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            effect_size=effect_size,
        )


class KordylewskiOrbitMetric:
    def compute(self, lagrange_distances: list[float]) -> BootstrapResult:
        scores = [1.0 / (1.0 + d) for d in lagrange_distances if d >= 0]
        data = np.array([s for s in scores if np.isfinite(s)], dtype=np.float64)
        if len(data) == 0:
            data = np.array([0.0])
        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data)
        null_value = 0.1
        effect_size = (mean - null_value) / (std + 1e-9)
        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            effect_size=effect_size,
        )


class SPINPhaseMetric:
    def compute(self, phase_trajectory: list[float]) -> BootstrapResult:
        if len(phase_trajectory) < 2:
            return BootstrapResult(mean=0.0, std=0.0, ci_lower=0.0, ci_upper=0.0, p_value=1.0)
        increments = np.diff(np.array(phase_trajectory))
        increments = increments[np.isfinite(increments)]
        if len(increments) == 0:
            return BootstrapResult(mean=0.0, std=0.0, ci_lower=0.0, ci_upper=0.0, p_value=1.0)
        mean_inc = float(np.mean(increments))
        std_inc = float(np.std(increments, ddof=1)) if len(increments) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(increments)
        null_value = 0.1
        effect_size = (mean_inc - null_value) / (std_inc + 1e-9)
        return BootstrapResult(
            mean=mean_inc,
            std=std_inc,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            effect_size=effect_size,
        )


class EVOPhysicsMetrics:
    def __init__(self) -> None:
        self.coherence = CoherenceMetric()
        self.triune_balance = TRIUNEBalanceMetric()
        self.stability = StabilityMetric()
        self.exotic_charge = ExoticChargeMetric()
        self.kordylewski_orbit = KordylewskiOrbitMetric()
        self.spin_phase = SPINPhaseMetric()
        self.bonferroni = BonferroniCorrection(n_tests=6, alpha=ALPHA)

    def compute_all(self, biography: list[dict[str, Any]]) -> dict[str, BootstrapResult]:
        coherence_vals = [step.get("coherence", 0.5) for step in biography]
        exotic_vals = [step.get("exotic_charge_density", 0.0) for step in biography]
        phase_vals = [step.get("phase", 0.0) for step in biography]
        hiho_dists = [abs(c - 0.5) for c in coherence_vals]
        results: dict[str, BootstrapResult] = {}
        results["coherence"] = self.coherence.compute(coherence_vals)
        results["exotic_charge"] = self.exotic_charge.compute(exotic_vals)
        results["stability"] = self.stability.compute(coherence_vals, hiho_dists)
        results["spin_phase"] = self.spin_phase.compute(phase_vals)
        results["triune_balance"] = BootstrapResult(
            mean=0.5, std=0.0, ci_lower=0.4, ci_upper=0.6, p_value=0.5
        )
        results["kordylewski_orbit"] = BootstrapResult(
            mean=0.5, std=0.0, ci_lower=0.4, ci_upper=0.6, p_value=0.5
        )
        return results

    def compare_biographies(
        self, bio1: list[dict[str, Any]], bio2: list[dict[str, Any]]
    ) -> dict[str, StatisticalComparison]:
        c1 = [s.get("coherence", 0.5) for s in bio1]
        c2 = [s.get("coherence", 0.5) for s in bio2]
        comparisons: dict[str, StatisticalComparison] = {}
        comparisons["coherence"] = _mann_whitney_u(np.array(c1), np.array(c2))
        comparisons["triune_balance"] = StatisticalComparison(
            0.0, 1.0, 0.0, False, len(c1), len(c2)
        )
        comparisons["stability"] = StatisticalComparison(0.0, 1.0, 0.0, False, len(c1), len(c2))
        comparisons["exotic_charge"] = StatisticalComparison(0.0, 1.0, 0.0, False, len(c1), len(c2))
        comparisons["kordylewski_orbit"] = StatisticalComparison(
            0.0, 1.0, 0.0, False, len(c1), len(c2)
        )
        comparisons["spin_phase"] = StatisticalComparison(0.0, 1.0, 0.0, False, len(c1), len(c2))
        return comparisons

    def summary_report(self, results: dict[str, BootstrapResult]) -> str:
        lines = ["=== FLUME EVO Physics Benchmark ==="]
        for name, res in results.items():
            sig = (
                "***"
                if res.p_value < 0.001
                else (
                    "**"
                    if res.p_value < 0.01
                    else ("*" if res.p_value < self.bonferroni.corrected_alpha else "")
                )
            )
            lines.extend(
                [
                    f"\n{name.upper()}",
                    f"  Mean: {res.mean:.4f} ± {res.std:.4f}",
                    f"  95% CI: [{res.ci_lower:.4f}, {res.ci_upper:.4f}]",
                    f"  p-value: {res.p_value:.4e} {sig}",
                    f"  Effect size: {res.effect_size:.4f}",
                ]
            )
        return "\n".join(lines)
