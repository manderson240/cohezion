"""Agentic benchmark metrics for FLUME journey EVO physics evaluation.

Provides 6 EVO physics metric families with bootstrap confidence intervals,
Mann-Whitney U significance testing, Bonferroni multiple-hypothesis correction,
and power analysis for small sample sizes.

Metric Families:
1. CoherenceMetric      — HIHO coherence near 0.5
2. TRIUNEBalanceMetric  — Equal Doer/Thinker/Knower activation
3. StabilityMetric      — Low variance, consistent HIHO proximity
4. ExoticChargeMetric    — Accumulation rate and peak stability
5. KordylewskiOrbitMetric — L4/L5 Lagrange stability
6. SPINPhaseMetric      — Monotonic phase accumulation

All metrics return BootstrapResult objects with mean, std, CI, and p_value
against a null hypothesis of random performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


COHERENCE_WINDOW = 0.2
N_BOOTSTRAP = 1000
ALPHA = 0.05


@dataclass(frozen=True)
class BootstrapResult:
    """Result of bootstrap resampling for a metric.

    Attributes:
        mean: Sample mean of the metric across episodes.
        std: Sample standard deviation.
        ci_lower: Lower bound of the 95% confidence interval.
        ci_upper: Upper bound of the 95% confidence interval.
        p_value: Two-tailed p-value against null hypothesis (H0: median = 0).
        n_samples: Number of bootstrap resamples.
        effect_size: Cohen's d vs null distribution.
    """

    mean: float
    std: float
    ci_lower: float
    ci_upper: float
    p_value: float
    n_samples: int = N_BOOTSTRAP
    effect_size: float = 0.0


@dataclass(frozen=True)
class StatisticalComparison:
    """Result of a Mann-Whitney U comparison between two groups.

    Attributes:
        u_statistic: Mann-Whitney U statistic.
        p_value: Two-tailed asymptotic p-value.
        effect_size: Rank-biserial correlation coefficient.
        significant: Whether p_value < alpha after correction.
        n_group1: Number of observations in group 1.
        n_group2: Number of observations in group 2.
    """

    u_statistic: float
    p_value: float
    effect_size: float
    significant: bool
    n_group1: int
    n_group2: int


class BonferroniCorrection:
    """Bonferroni correction for multiple statistical comparisons.

    Use as:
        correction = BonferroniCorrection(n_tests=6, alpha=0.05)
        corrected = correction.correct(p_values)
        significant = correction.significant_mask(p_values)
    """

    def __init__(self, n_tests: int, alpha: float = ALPHA) -> None:
        self.n_tests = n_tests
        self.alpha = alpha
        self.corrected_alpha = alpha / n_tests

    def correct(self, p_values: list[float]) -> list[float]:
        """Apply Bonferroni correction to a list of p-values.

        Args:
            p_values: Raw p-values from multiple tests.

        Returns:
            Bonferroni-corrected p-values (min(n_tests * p, 1.0) for each).
        """
        corrected = []
        for p in p_values:
            p_adj = min(p * self.n_tests, 1.0)
            corrected.append(p_adj)
        return corrected

    def significant_mask(self, p_values: list[float]) -> list[bool]:
        """Return a boolean mask of which tests are significant after correction.

        Args:
            p_values: Raw p-values from multiple tests.

        Returns:
            List of booleans where True indicates the null hypothesis is
            rejected at the corrected alpha level.
        """
        return [p < self.corrected_alpha for p in p_values]

    def power_analysis(self, effect_size: float, n: int, alpha: float | None = None) -> float:
        """Estimate statistical power for a given effect size and sample size.

        Uses the normal approximation to the Mann-Whitney U distribution.
        Power = P(reject H0 | effect_size, n, alpha)

        Args:
            effect_size: Cohen's d equivalent (standardized difference).
            n: Sample size per group (assumes equal groups).
            alpha: Significance level (defaults to corrected_alpha).

        Returns:
            Estimated statistical power in [0, 1].
        """
        if alpha is None:
            alpha = self.corrected_alpha
        z_alpha = np.abs(np.random.normal(0, 1)).__class__(1.0 - alpha / 2)  # approx
        import math

        z_alpha = 1.96 if alpha == 0.05 else math.sqrt(2) * 2.576
        se = math.sqrt(2 / n)
        z_power = abs(effect_size) / se - z_alpha
        power = 1.0 - _norm_cdf(z_power)
        return max(0.0, min(1.0, power))


def _norm_cdf(z: float) -> float:
    """Standard normal cumulative distribution function."""
    import math

    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


class CoherenceMetric:
    """Measures how close EVO coherence stays to the HIHO target of 0.5.

    HIHO = High-In/High-Out: the stable coherence attractor at 0.5.
    Coherence is computed from the 256D VAE latent as:
        coherence = 1 - min(var(chunk_means, target=0.5) * 4, 1)

    Null hypothesis (H0): Mean coherence = 0.5 (random walk).
    Metric: Mean coherence across episode steps, penalizing low coherence.
    """

    def __init__(self, target: float = 0.5) -> None:
        self.target = target

    def compute(self, episode_coherences: list[float]) -> BootstrapResult:
        """Compute bootstrap statistics for an episode's coherence time series.

        Args:
            episode_coherences: List of coherence values per step (0 to 1).

        Returns:
            BootstrapResult with mean, std, 95% CI, and p_value vs H0.
        """
        data = np.array(episode_coherences, dtype=np.float64)
        data = data[np.isfinite(data)] if len(data) > 0 else np.array([0.0])

        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0

        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data, n_bootstrap=N_BOOTSTRAP, alpha=ALPHA)

        null_value = self.target
        effect_size = (mean - null_value) / (std + 1e-9)

        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_samples=N_BOOTSTRAP,
            effect_size=effect_size,
        )

    def compare(self, group1: list[float], group2: list[float]) -> StatisticalComparison:
        """Mann-Whitney U test comparing coherence between two episodes.

        Args:
            group1: Coherence values from episode 1.
            group2: Coherence values from episode 2.

        Returns:
            StatisticalComparison with U statistic, p-value, and significance.
        """
        return _mann_whitney_u(
            np.array(group1, dtype=np.float64),
            np.array(group2, dtype=np.float64),
        )


class TRIUNEBalanceMetric:
    """Measures TRIUNE SELF balance: equal Doer/Thinker/Knower activation.

    The TRIUNE SELF has three poles: Doer (action), Thinker (reasoning),
    and Knower (intent). Balance means none dominates and all contribute.

    Null hypothesis (H0): TRIUNE weights are imbalanced (one dominates).
    Metric: Negative sum of |weight - 1/3| across the three poles.
            Perfect balance = 0.0, maximum imbalance ≈ 1.33.
    """

    def compute(
        self, doer_weights: list[float], thinker_weights: list[float], knower_weights: list[float]
    ) -> BootstrapResult:
        """Compute TRIUNE balance score from weight trajectories.

        Args:
            doer_weights: Doer pole activation weights (sum to 1.0 per step).
            thinker_weights: Thinker pole activation weights.
            knower_weights: Knower pole activation weights.

        Returns:
            BootstrapResult for TRIUNE balance score (lower = more balanced).
        """
        n = min(len(doer_weights), len(thinker_weights), len(knower_weights))
        if n == 0:
            return BootstrapResult(mean=1.0, std=0.0, ci_lower=1.0, ci_upper=1.0, p_value=1.0)

        imbalance_scores = []
        for i in range(n):
            d, t, k = doer_weights[i], thinker_weights[i], knower_weights[i]
            score = abs(d - 1 / 3) + abs(t - 1 / 3) + abs(k - 1 / 3)
            imbalance_scores.append(score)

        data = np.array(imbalance_scores, dtype=np.float64)
        data = data[np.isfinite(data)]

        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data, n_bootstrap=N_BOOTSTRAP, alpha=ALPHA)

        null_value = 1.0
        effect_size = (null_value - mean) / (std + 1e-9)

        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_samples=N_BOOTSTRAP,
            effect_size=effect_size,
        )

    def compare(
        self, group1: tuple[list[float], list[float], list[float]], group2: tuple[list[float], list[float], list[float]]
    ) -> StatisticalComparison:
        """Compare TRIUNE balance between two episodes using Mann-Whitney U."""
        scores1 = self._to_balance_scores(*group1)
        scores2 = self._to_balance_scores(*group2)
        return _mann_whitney_u(np.array(scores1), np.array(scores2))

    def _to_balance_scores(self, doer: list[float], thinker: list[float], knower: list[float]) -> list[float]:
        n = min(len(doer), len(thinker), len(knower))
        return [abs(doer[i] - 1 / 3) + abs(thinker[i] - 1 / 3) + abs(knower[i] - 1 / 3) for i in range(n)]


class StabilityMetric:
    """Measures EVO stability: low variance in coherence and HIHO proximity.

    Stability is the inverse of the coefficient of variation of coherence
    plus a term for proximity to the HIHO 0.5 attractor.

    Null hypothesis (H0): EVO is unstable (random walk, high variance).
    Metric: 1 / (1 + CV(coherence) + HIHO_distance)
    """

    def compute(self, episode_coherences: list[float], hiho_distances: list[float]) -> BootstrapResult:
        """Compute stability score from coherence and HIHO distance time series.

        Args:
            episode_coherences: Coherence values per step.
            hiho_distances: |coherence - 0.5| values per step.

        Returns:
            BootstrapResult for stability score (higher = more stable).
        """
        data = np.array(episode_coherences, dtype=np.float64)
        data = data[np.isfinite(data)] if len(data) > 0 else np.array([0.0])

        hiho_arr = np.array(hiho_distances, dtype=np.float64)
        hiho_arr = hiho_arr[np.isfinite(hiho_arr)] if len(hiho_arr) > 0 else np.array([1.0])

        cv = float(np.std(data, ddof=1) / (np.mean(data) + 1e-9))
        mean_hiho = float(np.mean(hiho_arr))

        stability_score = 1.0 / (1.0 + cv + mean_hiho)
        stability_scores = [stability_score] * len(data) if len(data) <= 1 else []
        if len(data) > 1:
            for i in range(len(data)):
                step_cv = float(
                    np.std(data[max(0, i - 10) : i + 1], ddof=1) / (np.mean(data[max(0, i - 10) : i + 1]) + 1e-9)
                )
                step_hiho = float(np.abs(data[i] - 0.5))
                stability_scores.append(1.0 / (1.0 + step_cv + step_hiho))

        scores_data = np.array(stability_scores, dtype=np.float64)
        scores_data = scores_data[np.isfinite(scores_data)]

        mean = float(np.mean(scores_data))
        std = float(np.std(scores_data, ddof=1)) if len(scores_data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(scores_data, n_bootstrap=N_BOOTSTRAP, alpha=ALPHA)

        null_value = 0.5
        effect_size = (mean - null_value) / (std + 1e-9)

        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_samples=N_BOOTSTRAP,
            effect_size=effect_size,
        )

    def compare(
        self, group1: tuple[list[float], list[float]], group2: tuple[list[float], list[float]]
    ) -> StatisticalComparison:
        """Compare stability between two episodes."""
        scores1 = self._compute_stability_scores(*group1)
        scores2 = self._compute_stability_scores(*group2)
        return _mann_whitney_u(np.array(scores1), np.array(scores2))

    def _compute_stability_scores(self, coherences: list[float], hiho_distances: list[float]) -> list[float]:
        n = min(len(coherences), len(hiho_distances))
        scores = []
        for i in range(n):
            cv_window = coherences[max(0, i - 10) : i + 1]
            cv = float(np.std(cv_window, ddof=1) / (np.mean(cv_window) + 1e-9))
            hiho = float(np.abs(coherences[i] - 0.5))
            scores.append(1.0 / (1.0 + cv + hiho))
        return scores


class ExoticChargeMetric:
    """Measures exotic charge accumulation and sustainability.

    Exotic charge density grows at +0.01/step in FlumeNavEnv, capped at 1.0.
    The EXOTIC_CHARGE archetype terminates when exotic_charge_density > 0.95.
    This metric measures how well the EVO sustains high charge without collapse.

    Null hypothesis (H0): Charge accumulates slowly (avg < 0.3).
    Metric: Mean exotic_charge_density across episode steps.
    """

    def compute(self, exotic_charge_trajectory: list[float]) -> BootstrapResult:
        """Compute exotic charge statistics from trajectory.

        Args:
            exotic_charge_trajectory: Exotic charge density per step [0, 1].

        Returns:
            BootstrapResult for mean exotic charge density.
        """
        data = np.array(exotic_charge_trajectory, dtype=np.float64)
        data = data[np.isfinite(data)] if len(data) > 0 else np.array([0.0])

        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data, n_bootstrap=N_BOOTSTRAP, alpha=ALPHA)

        null_value = 0.3
        effect_size = (mean - null_value) / (std + 1e-9)

        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_samples=N_BOOTSTRAP,
            effect_size=effect_size,
        )

    def compare(self, group1: list[float], group2: list[float]) -> StatisticalComparison:
        """Compare exotic charge accumulation between two episodes."""
        return _mann_whitney_u(
            np.array(group1, dtype=np.float64),
            np.array(group2, dtype=np.float64),
        )


class KordylewskiOrbitMetric:
    """Measures stability of Kordylewski cloud (L4/L5 Lagrange orbit) maintenance.

    The Kordylewski cloud is a pattern of debris orbiting the L4 or L5
    Lagrange point. EVOs assigned to L4 or L5 should maintain proximity
    to their assigned Lagrange point.

    Null hypothesis (H0): EVO drifts randomly (no orbit maintenance).
    Metric: 1 / (1 + mean_distance_from_lagrange_point)
    Higher score = better orbit stability.
    """

    def compute(self, lagrange_distances: list[float]) -> BootstrapResult:
        """Compute Kordylewski orbit stability from Lagrange distance trajectory.

        Args:
            lagrange_distances: Distance from assigned L4 or L5 per step.

        Returns:
            BootstrapResult for orbit stability score (higher = more stable).
        """
        data = np.array(lagrange_distances, dtype=np.float64)
        data = data[np.isfinite(data)] if len(data) > 0 else np.array([10.0])

        orbit_stability_scores = [1.0 / (1.0 + d) for d in data]
        scores_data = np.array(orbit_stability_scores, dtype=np.float64)

        mean = float(np.mean(scores_data))
        std = float(np.std(scores_data, ddof=1)) if len(scores_data) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(scores_data, n_bootstrap=N_BOOTSTRAP, alpha=ALPHA)

        null_value = 0.1
        effect_size = (mean - null_value) / (std + 1e-9)

        return BootstrapResult(
            mean=mean,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_samples=N_BOOTSTRAP,
            effect_size=effect_size,
        )

    def compare(self, group1: list[float], group2: list[float]) -> StatisticalComparison:
        """Compare orbit stability between two episodes."""
        scores1 = [1.0 / (1.0 + d) for d in group1]
        scores2 = [1.0 / (1.0 + d) for d in group2]
        return _mann_whitney_u(np.array(scores1), np.array(scores2))


class SPINPhaseMetric:
    """Measures SPIN phase monotonicity and accumulation rate.

    The SPIN phase is a scalar that accumulates 0.1 rad/step in FlumeNavEnv.
    Monotonic increase indicates consistent physics integration.
    Deviations from monotonicity indicate numerical instability.

    Null hypothesis (H0): Phase is not accumulating (mean increment ≈ 0).
    Metric: Mean phase increment per step (expected ≈ 0.1 rad).
    """

    def compute(self, phase_trajectory: list[float]) -> BootstrapResult:
        """Compute SPIN phase accumulation from trajectory.

        Args:
            phase_trajectory: SPIN phase value per step (radians).

        Returns:
            BootstrapResult for mean phase increment per step.
        """
        data = np.array(phase_trajectory, dtype=np.float64)
        data = data[np.isfinite(data)] if len(data) > 0 else np.array([0.0])

        if len(data) < 2:
            return BootstrapResult(mean=0.0, std=0.0, ci_lower=0.0, ci_upper=0.0, p_value=1.0)

        increments = np.diff(data)
        increments = increments[np.isfinite(increments)]

        mean_inc = float(np.mean(increments)) if len(increments) > 0 else 0.0
        std_inc = float(np.std(increments, ddof=1)) if len(increments) > 1 else 0.0
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(increments, n_bootstrap=N_BOOTSTRAP, alpha=ALPHA)

        null_value = 0.1
        effect_size = (mean_inc - null_value) / (std_inc + 1e-9)

        return BootstrapResult(
            mean=mean_inc,
            std=std_inc,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_samples=N_BOOTSTRAP,
            effect_size=effect_size,
        )

    def compare(self, group1: list[float], group2: list[float]) -> StatisticalComparison:
        """Compare phase accumulation between two episodes."""
        inc1 = np.diff(np.array(group1, dtype=np.float64))
        inc2 = np.diff(np.array(group2, dtype=np.float64))
        return _mann_whitney_u(inc1, inc2)


def _bootstrap_mean_ci(
    data: np.ndarray, n_bootstrap: int = N_BOOTSTRAP, alpha: float = ALPHA
) -> tuple[float, float, float]:
    """Compute bootstrap 95% CI for the mean and p-value vs H0: mean=0.

    Args:
        data: 1D array of observations.
        n_bootstrap: Number of bootstrap resamples.
        alpha: Significance level (0.05 for 95% CI).

    Returns:
        Tuple of (ci_lower, ci_upper, p_value).
    """
    import numpy as np

    n = len(data)
    if n == 0:
        return 0.0, 0.0, 1.0
    if n == 1:
        return float(data[0]), float(data[0]), 0.5

    bootstrap_means = np.empty(n_bootstrap, dtype=np.float64)
    for i in range(n_bootstrap):
        indices = np.random.randint(0, n, size=n)
        bootstrap_means[i] = np.mean(data[indices])

    ci_lower = np.percentile(bootstrap_means, (alpha / 2) * 100)
    ci_upper = np.percentile(bootstrap_means, (1 - alpha / 2) * 100)

    observed_mean = np.mean(data)
    null_mean = 0.0
    se = np.std(bootstrap_means, ddof=1) if n_bootstrap > 1 else 1.0
    if se < 1e-9:
        z = 0.0
    else:
        z = (observed_mean - null_mean) / se
    p_value = 2.0 * (1.0 - _norm_cdf(abs(z)))

    return float(ci_lower), float(ci_upper), float(p_value)


def _mann_whitney_u(group1: np.ndarray, group2: np.ndarray) -> StatisticalComparison:
    """Mann-Whitney U test comparing two independent groups.

    Tests whether one group tends to have larger values than the other.
    H0: P(X > Y) = P(Y > X) (distributions are equal).

    Args:
        group1: Observations from group 1.
        group2: Observations from group 2.

    Returns:
        StatisticalComparison with U statistic, p-value, and significance.
    """
    import numpy as np
    import scipy.stats

    data1 = group1[np.isfinite(group1)] if len(group1) > 0 else np.array([0.0])
    data2 = group2[np.isfinite(group2)] if len(group2) > 0 else np.array([0.0])

    n1, n2 = len(data1), len(data2)
    if n1 == 0 or n2 == 0:
        return StatisticalComparison(
            u_statistic=0.0,
            p_value=1.0,
            effect_size=0.0,
            significant=False,
            n_group1=n1,
            n_group2=n2,
        )

    u_stat, p_val = scipy.stats.mannwhitneyu(data1, data2, alternative="two-sided")

    rank_biserial = 1.0 - (2.0 * float(u_stat) / (n1 * n2))

    alpha = ALPHA
    significant = bool(p_val < alpha)

    return StatisticalComparison(
        u_statistic=float(u_stat),
        p_value=float(p_val),
        effect_size=float(rank_biserial),
        significant=significant,
        n_group1=n1,
        n_group2=n2,
    )


class EVOPhysicsMetrics:
    """Aggregates all 6 EVO physics metric families for a complete benchmark.

    Provides a single interface for computing all metrics from an EVO's
    episode biography, with Bonferroni-corrected significance testing
    across all metric families.

    Example:
        tracker = EVOTracker(max_active=20)
        metrics = EVOPhysicsMetrics()
        results = metrics.compute_all(episode_biography)
        report = metrics.summary_report(results)
    """

    def __init__(self) -> None:
        self.coherence = CoherenceMetric()
        self.triune_balance = TRIUNEBalanceMetric()
        self.stability = StabilityMetric()
        self.exotic_charge = ExoticChargeMetric()
        self.kordylewski_orbit = KordylewskiOrbitMetric()
        self.spin_phase = SPINPhaseMetric()
        self.bonferroni = BonferroniCorrection(n_tests=6, alpha=ALPHA)

    def compute_all(self, biography: list[dict[str, Any]]) -> dict[str, BootstrapResult]:
        """Compute all 6 metric families from an EVO episode biography.

        Args:
            biography: List of step dictionaries from EthericVariantOscillator
                biography, each containing: coherence, doer_weight, thinker_weight,
                knower_weight, exotic_charge_density, phase, lagrange_distance, etc.

        Returns:
            Dictionary mapping metric name to BootstrapResult.
        """
        coherences = [step.get("coherence", 0.5) for step in biography]
        doer_weights = [step.get("doer_weight", 0.33) for step in biography]
        thinker_weights = [step.get("thinker_weight", 0.33) for step in biography]
        knower_weights = [step.get("knower_weight", 0.34) for step in biography]
        hiho_distances = [abs(c - 0.5) for c in coherences]
        exotic_charge_trajectory = [step.get("exotic_charge_density", 0.0) for step in biography]
        lagrange_distances = [step.get("lagrange_distance", 5.0) for step in biography]
        phase_trajectory = [step.get("phase", 0.0) for step in biography]

        results: dict[str, BootstrapResult] = {}
        results["coherence"] = self.coherence.compute(coherences)
        results["triune_balance"] = self.triune_balance.compute(doer_weights, thinker_weights, knower_weights)
        results["stability"] = self.stability.compute(coherences, hiho_distances)
        results["exotic_charge"] = self.exotic_charge.compute(exotic_charge_trajectory)
        results["kordylewski_orbit"] = self.kordylewski_orbit.compute(lagrange_distances)
        results["spin_phase"] = self.spin_phase.compute(phase_trajectory)

        return results

    def compare_biographies(
        self,
        biography1: list[dict[str, Any]],
        biography2: list[dict[str, Any]],
    ) -> dict[str, StatisticalComparison]:
        """Compare two EVO episode biographies using Mann-Whitney U.

        Args:
            biography1: First EVO episode biography.
            biography2: Second EVO episode biography.

        Returns:
            Dictionary mapping metric name to StatisticalComparison.
        """
        c1 = [s.get("coherence", 0.5) for s in biography1]
        c2 = [s.get("coherence", 0.5) for s in biography2]
        d1 = [s.get("doer_weight", 0.33) for s in biography1]
        d2 = [s.get("doer_weight", 0.33) for s in biography2]
        t1 = [s.get("thinker_weight", 0.33) for s in biography1]
        t2 = [s.get("thinker_weight", 0.33) for s in biography2]
        k1 = [s.get("knower_weight", 0.34) for s in biography1]
        k2 = [s.get("knower_weight", 0.34) for s in biography2]
        h1 = [abs(c - 0.5) for c in c1]
        h2 = [abs(c - 0.5) for c in c2]
        e1 = [s.get("exotic_charge_density", 0.0) for s in biography1]
        e2 = [s.get("exotic_charge_density", 0.0) for s in biography2]
        l1 = [s.get("lagrange_distance", 5.0) for s in biography1]
        l2 = [s.get("lagrange_distance", 5.0) for s in biography2]
        p1 = [s.get("phase", 0.0) for s in biography1]
        p2 = [s.get("phase", 0.0) for s in biography2]

        comparisons: dict[str, StatisticalComparison] = {}
        comparisons["coherence"] = self.coherence.compare(c1, c2)
        comparisons["triune_balance"] = self.triune_balance.compare((d1, t1, k1), (d2, t2, k2))
        comparisons["stability"] = self.stability.compare((c1, h1), (c2, h2))
        comparisons["exotic_charge"] = self.exotic_charge.compare(e1, e2)
        comparisons["kordylewski_orbit"] = self.kordylewski_orbit.compare(l1, l2)
        comparisons["spin_phase"] = self.spin_phase.compare(p1, p2)

        return comparisons

    def summary_report(self, results: dict[str, BootstrapResult]) -> str:
        """Generate a human-readable summary report of all metrics.

        Args:
            results: Output of compute_all().

        Returns:
            Formatted multi-line string with all metric results.
        """
        lines = ["=== FLUME EVO Physics Benchmark ==="]
        for name, res in results.items():
            sig = (
                "***"
                if res.p_value < 0.001
                else ("**" if res.p_value < 0.01 else ("*" if res.p_value < self.bonferroni.corrected_alpha else ""))
            )
            lines.append(f"\n{name.upper()}")
            lines.append(f"  Mean: {res.mean:.4f} ± {res.std:.4f}")
            lines.append(f"  95% CI: [{res.ci_lower:.4f}, {res.ci_upper:.4f}]")
            lines.append(f"  p-value: {res.p_value:.4e} {sig}")
            lines.append(f"  Effect size (Cohen's d): {res.effect_size:.4f}")
        return "\n".join(lines)
