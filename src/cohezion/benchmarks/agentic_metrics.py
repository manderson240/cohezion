"""Agentic Metrics - EVO Physics-based benchmark metrics.

Implements 6 EVO physics-based metrics with full statistical rigor:
1. EVO Coherence Amplitude - Peak coherence over journey (HIHO stability)
2. Phase Locking Rate - % steps where SPIN rotation aligns with precession
3. Exotic Charge Lifetime - Steps before exotic_charge_density > 0.95 (survival analysis)
4. Kordylewski Orbit Quality - 1 - (orbit_radius_variance / baseline_variance)
5. TRIUNE Balance Index - 1 - std(doer/thinker/knower activation)
6. Recovery Basin Radius - Max HIHO distance with recovery success

Statistical rigor:
- Bootstrap 95% CIs (1000 samples)
- Mann-Whitney U (non-parametric)
- Bonferroni correction (6 metrics x N task archetypes)
- Power analysis (minimum detectable effect size)

Example:
    ```python
    from cohezion.benchmarks.agentic_metrics import AgenticMetrics

    metrics = AgenticMetrics(random_state=42)
    journeys = [
        {
            "trajectory": [
                {"coherence": 0.5, "hiho_distance": 0.1, ...},
            ],
        }
    ]

    results = metrics.compute_all_metrics(journeys, n_bootstrap=1000)
    print(f"EVO Coherence: {results.evo_coherence_amplitude:.3f}")
    print(f"95% CI: {results.confidence_intervals['evo_coherence_amplitude']}")
    ```
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats


logger = logging.getLogger(__name__)


@dataclass
class AgenticResults:
    """Results from agentic EVO physics-based metrics.

    Attributes:
        evo_coherence_amplitude: Peak coherence over journey (HIHO stability measure)
        phase_locking_rate: % steps where SPIN rotation aligns with precession
        exotic_charge_lifetime: Steps before exotic_charge_density > 0.95 (survival)
        kordylewski_orbit_quality: 1 - (orbit_radius_variance / baseline_variance)
        triune_balance_index: 1 - std(doer/thinker/knower activation)
        recovery_basin_radius: Max HIHO distance with recovery success
        composite_score: Weighted average of all 6 metrics
        confidence_intervals: 95% bootstrap CIs for each metric
        statistical_tests: Mann-Whitney U, Bonferroni correction results
    """

    evo_coherence_amplitude: float
    phase_locking_rate: float
    exotic_charge_lifetime: float
    kordylewski_orbit_quality: float
    triune_balance_index: float
    recovery_basin_radius: float
    composite_score: float
    confidence_intervals: dict[str, tuple[float, float]] = field(default_factory=dict)
    statistical_tests: dict[str, dict] = field(default_factory=dict)


class AgenticMetrics:
    """EVO Physics-based metrics with statistical rigor.

    Implements 6 metric families derived from HIHO physics:
    - Coherence dynamics (EVO amplitude, phase locking)
    - Exotic charge (lifetime, survival analysis)
    - Orbital mechanics (Kordylewski quality)
    - TRIUNE activation balance (doer/thinker/knower)
    - Recovery dynamics (basin radius)

    Statistical methods:
    - Bootstrap confidence intervals (1000 samples default)
    - Mann-Whitney U (non-parametric comparison)
    - Bonferroni correction (multiple comparisons)
    - Power analysis (minimum detectable effect)

    Attributes:
        random_state: Random seed for reproducibility
        phase_locking_threshold: Max angle (radians) for phase alignment
        exotic_charge_threshold: Threshold for exotic charge decay (> 0.95 = decay)
        max_exotic_charge_lifetime: Max steps for normalization (200 default)
    """

    PHASE_LOCKING_THRESHOLD: float = 0.2
    EXOTIC_CHARGE_THRESHOLD: float = 0.95
    MAX_EXOTIC_CHARGE_LIFETIME: int = 200
    N_BOOTSTRAP_DEFAULT: int = 1000

    WEIGHT_EVO_AMPLITUDE: float = 0.20
    WEIGHT_PHASE_LOCKING: float = 0.15
    WEIGHT_EXOTIC_CHARGE: float = 0.20
    WEIGHT_ORBIT_QUALITY: float = 0.15
    WEIGHT_TRIUNE_BALANCE: float = 0.15
    WEIGHT_RECOVERY_BASIN: float = 0.15

    def __init__(self, random_state: int = 42):
        """Initialize agentic metrics.

        Args:
            random_state: Random seed for bootstrap reproducibility
        """
        self.random_state = random_state
        self.rng = np.random.RandomState(random_state)
        logger.debug("Initialized AgenticMetrics with seed=%d", random_state)

    def compute_all_metrics(
        self,
        journeys: list[dict[str, Any]],
        n_bootstrap: int = N_BOOTSTRAP_DEFAULT,
    ) -> AgenticResults:
        """Compute all 6 EVO physics-based metrics with bootstrap CIs.

        Args:
            journeys: List of journey dictionaries with trajectory data
            n_bootstrap: Number of bootstrap samples for CI estimation

        Returns:
            AgenticResults with all metrics and statistical tests
        """
        if not journeys:
            return self._empty_results()

        evo_amps = [self._compute_evo_coherence_amplitude(j) for j in journeys]
        phase_rates = [self._compute_phase_locking_rate(j) for j in journeys]
        charge_lifetimes = [self._compute_exotic_charge_lifetime(j) for j in journeys]
        orbit_qualities = [self._compute_kordylewski_orbit_quality(j) for j in journeys]
        triune_balances = [self._compute_triune_balance_index(j) for j in journeys]
        recovery_radii = [self._compute_recovery_basin_radius(j) for j in journeys]

        evo_amp_ci = self._compute_bootstrap_ci(evo_amps, n_bootstrap=n_bootstrap)
        phase_ci = self._compute_bootstrap_ci(phase_rates, n_bootstrap=n_bootstrap)
        charge_ci = self._compute_bootstrap_ci(charge_lifetimes, n_bootstrap=n_bootstrap)
        orbit_ci = self._compute_bootstrap_ci(orbit_qualities, n_bootstrap=n_bootstrap)
        triune_ci = self._compute_bootstrap_ci(triune_balances, n_bootstrap=n_bootstrap)
        recovery_ci = self._compute_bootstrap_ci(recovery_radii, n_bootstrap=n_bootstrap)

        composite = self._compute_composite_score(
            evo_coherence_amplitude=np.mean(evo_amps),
            phase_locking_rate=np.mean(phase_rates),
            exotic_charge_lifetime=np.mean(charge_lifetimes),
            kordylewski_orbit_quality=np.mean(orbit_qualities),
            triune_balance_index=np.mean(triune_balances),
            recovery_basin_radius=np.mean(recovery_radii),
        )

        statistical_tests = self._compute_statistical_tests(evo_amps, phase_rates)

        return AgenticResults(
            evo_coherence_amplitude=float(np.mean(evo_amps)),
            phase_locking_rate=float(np.mean(phase_rates)),
            exotic_charge_lifetime=float(np.mean(charge_lifetimes)),
            kordylewski_orbit_quality=float(np.mean(orbit_qualities)),
            triune_balance_index=float(np.mean(triune_balances)),
            recovery_basin_radius=float(np.mean(recovery_radii)),
            composite_score=composite,
            confidence_intervals={
                "evo_coherence_amplitude": evo_amp_ci,
                "phase_locking_rate": phase_ci,
                "exotic_charge_lifetime": charge_ci,
                "kordylewski_orbit_quality": orbit_ci,
                "triune_balance_index": triune_ci,
                "recovery_basin_radius": recovery_ci,
            },
            statistical_tests=statistical_tests,
        )

    def _empty_results(self) -> AgenticResults:
        """Return empty results for empty journeys."""
        return AgenticResults(
            evo_coherence_amplitude=0.0,
            phase_locking_rate=0.0,
            exotic_charge_lifetime=0.0,
            kordylewski_orbit_quality=0.0,
            triune_balance_index=0.0,
            recovery_basin_radius=0.0,
            composite_score=0.0,
            confidence_intervals={},
            statistical_tests={},
        )

    def _compute_evo_coherence_amplitude(self, journey: dict[str, Any]) -> float:
        """Compute peak coherence over journey trajectory.

        Measures HIHO stability by finding the maximum coherence
        value achieved during the journey trajectory.

        Args:
            journey: Journey dict with 'trajectory' list

        Returns:
            Peak coherence value [0, 1]
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return 0.0

        coherences = [step.get("coherence", 0.0) for step in trajectory]
        return float(max(coherences))

    def _compute_phase_locking_rate(self, journey: dict[str, Any]) -> float:
        """Compute % steps where SPIN rotation aligns with precession.

        Phase locking occurs when the angular difference between
        spin and precession vectors is below the threshold.

        Args:
            journey: Journey dict with 'trajectory' list

        Returns:
            Fraction of steps with phase alignment [0, 1]
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return 0.0

        aligned_count = 0
        total_count = 0

        for step in trajectory:
            spin = step.get("spin")
            precession = step.get("precession")
            if spin is None or precession is None:
                continue

            total_count += 1
            diff = abs(spin - precession)
            diff = min(diff, 1.0 - diff)
            if diff <= self.PHASE_LOCKING_THRESHOLD:
                aligned_count += 1

        if total_count == 0:
            return 0.0

        return aligned_count / total_count

    def _compute_exotic_charge_lifetime(self, journey: dict[str, Any]) -> float:
        """Compute steps before exotic_charge_density exceeds threshold.

        Survival analysis: measures how long the exotic charge
        persists before decaying above the threshold (0.95).

        Args:
            journey: Journey dict with 'trajectory' list

        Returns:
            Steps before threshold crossing, or full trajectory length
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return 0.0

        for i, step in enumerate(trajectory):
            density = step.get("exotic_charge_density", 0.0)
            if density > self.EXOTIC_CHARGE_THRESHOLD:
                return float(i)

        return float(len(trajectory))

    def _compute_kordylewski_orbit_quality(self, journey: dict[str, Any]) -> float:
        """Compute orbit stability: 1 - (variance / baseline_variance).

        Kordylewski orbits are stable when their radius variance
        is small relative to a baseline (random walk variance).

        Args:
            journey: Journey dict with 'trajectory' and 'baseline_orbit_variance'

        Returns:
            Orbit quality [0, 1], higher = more stable
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return 0.5

        radii = [step.get("orbit_radius", 1.0) for step in trajectory]
        orbit_variance = float(np.var(radii)) if len(radii) > 1 else 0.0

        baseline_variance = journey.get("baseline_orbit_variance")
        if baseline_variance is None or baseline_variance <= 0:
            return 0.5

        quality = 1.0 - (orbit_variance / baseline_variance)
        return max(0.0, min(1.0, quality))

    def _compute_triune_balance_index(self, journey: dict[str, Any]) -> float:
        """Compute TRIUNE balance: 1 - std(doer/thinker/knower activation).

        The TRIUNE brain model has three activation modes.
        Balance occurs when all three are equally activated.

        Args:
            journey: Journey dict with 'trajectory' containing activation fields

        Returns:
            Balance index [0, 1], higher = more balanced
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return 0.0

        activations = []
        for step in trajectory:
            doer = step.get("doer_activation")
            thinker = step.get("thinker_activation")
            knower = step.get("knower_activation")

            if doer is not None and thinker is not None and knower is not None:
                activations.append([doer, thinker, knower])

        if not activations:
            return 0.0

        stds = [float(np.std(act)) for act in activations]
        mean_std = float(np.mean(stds))
        balance = 1.0 - min(mean_std, 1.0)

        return max(0.0, min(1.0, balance))

    def _compute_recovery_basin_radius(self, journey: dict[str, Any]) -> float:
        """Compute max HIHO distance with successful recovery.

        Recovery basin radius measures how far from equilibrium
        the system can go and still recover successfully.

        Args:
            journey: Journey dict with 'trajectory' containing hiho_distance, recovered

        Returns:
            Maximum successful recovery distance [0, 1]
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return 0.0

        max_radius = 0.0
        for step in trajectory:
            hiho_dist = step.get("hiho_distance")
            recovered = step.get("recovered")

            if hiho_dist is None:
                continue

            if recovered is True and hiho_dist > max_radius:
                max_radius = hiho_dist
            elif recovered is False:
                break

        return float(max_radius)

    def _compute_composite_score(
        self,
        evo_coherence_amplitude: float,
        phase_locking_rate: float,
        exotic_charge_lifetime: float,
        kordylewski_orbit_quality: float,
        triune_balance_index: float,
        recovery_basin_radius: float,
    ) -> float:
        """Compute weighted composite score from 6 metrics.

        Normalizes exotic_charge_lifetime to [0,1] using max lifetime,
        then computes weighted average.

        Args:
            evo_coherence_amplitude: Peak coherence [0, 1]
            phase_locking_rate: Phase alignment fraction [0, 1]
            exotic_charge_lifetime: Steps before decay [0, MAX]
            kordylewski_orbit_quality: Orbit stability [0, 1]
            triune_balance_index: Activation balance [0, 1]
            recovery_basin_radius: Max recovery distance [0, 1]

        Returns:
            Composite score [0, 1]
        """
        normalized_lifetime = min(exotic_charge_lifetime / self.MAX_EXOTIC_CHARGE_LIFETIME, 1.0)

        composite = (
            self.WEIGHT_EVO_AMPLITUDE * evo_coherence_amplitude
            + self.WEIGHT_PHASE_LOCKING * phase_locking_rate
            + self.WEIGHT_EXOTIC_CHARGE * normalized_lifetime
            + self.WEIGHT_ORBIT_QUALITY * kordylewski_orbit_quality
            + self.WEIGHT_TRIUNE_BALANCE * triune_balance_index
            + self.WEIGHT_RECOVERY_BASIN * recovery_basin_radius
        )

        return max(0.0, min(1.0, composite))

    def _compute_bootstrap_ci(
        self,
        data: list[float],
        n_bootstrap: int = N_BOOTSTRAP_DEFAULT,
        ci: float = 0.95,
    ) -> tuple[float, float]:
        """Compute bootstrap confidence interval.

        Uses percentile method for bootstrap CI estimation.

        Args:
            data: List of metric values to bootstrap
            n_bootstrap: Number of bootstrap samples
            ci: Confidence level (default 0.95 for 95% CI)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if len(data) < 2:
            return (float("nan"), float("nan"))

        alpha = 1.0 - ci
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1.0 - alpha / 2) * 100

        bootstrap_means = []
        data_array = np.array(data)

        for _ in range(n_bootstrap):
            sample = self.rng.choice(data_array, size=len(data_array), replace=True)
            bootstrap_means.append(float(np.mean(sample)))

        lower = float(np.percentile(bootstrap_means, lower_percentile))
        upper = float(np.percentile(bootstrap_means, upper_percentile))

        return (lower, upper)

    def _compute_mann_whitney_u(
        self,
        group1: list[float],
        group2: list[float],
        alternative: str = "two-sided",
    ) -> dict[str, float]:
        """Compute Mann-Whitney U test (non-parametric).

        Tests whether observations from one group tend to be
        greater than observations from another group.

        Args:
            group1: First group of values
            group2: Second group of values
            alternative: 'two-sided', 'less', or 'greater'

        Returns:
            Dict with 'u_stat' and 'p_value'
        """
        if len(group1) == 0 or len(group2) == 0:
            return {"u_stat": 0.0, "p_value": 1.0}

        u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative=alternative)
        return {"u_stat": float(u_stat), "p_value": float(p_value)}

    def _bonferroni_correction(self, alpha: float, n_comparisons: int) -> float:
        """Apply Bonferroni correction for multiple comparisons.

        Divides alpha by number of comparisons to control
        family-wise error rate.

        Args:
            alpha: Original significance level (e.g., 0.05)
            n_comparisons: Number of comparisons/tests

        Returns:
            Adjusted alpha level
        """
        if n_comparisons <= 0:
            return alpha
        return alpha / n_comparisons

    def _compute_minimum_detectable_effect(
        self,
        alpha: float = 0.05,
        power: float = 0.8,
        n1: int = 30,
        n2: int = 30,
    ) -> float:
        """Compute minimum detectable effect size (Cohen's d).

        Uses normal approximation for power analysis for two independent groups.
        Formula: d = (z_alpha + z_beta) / sqrt((n1 + n2) / (n1 * n2) * (n1 + n2) / 2)

        Args:
            alpha: Significance level
            power: Desired power (1 - beta), typically 0.8
            n1: Sample size for group 1
            n2: Sample size for group 2

        Returns:
            Minimum detectable effect size (Cohen's d)
        """
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)

        n_harmonic = 2 / (1 / n1 + 1 / n2)
        mde = (z_alpha + z_beta) / math.sqrt(n_harmonic)

        return float(mde)

    def _compute_statistical_tests(
        self,
        metric1_values: list[float],
        metric2_values: list[float],
    ) -> dict[str, Any]:
        """Compute statistical tests for metrics.

        Args:
            metric1_values: Values for first metric (e.g., evo_coherence)
            metric2_values: Values for second metric (e.g., phase_locking)

        Returns:
            Dict with Mann-Whitney and Bonferroni results
        """
        mw_result = self._compute_mann_whitney_u(metric1_values, metric2_values)

        adjusted_alpha = self._bonferroni_correction(alpha=0.05, n_comparisons=6)

        mde = self._compute_minimum_detectable_effect(alpha=adjusted_alpha, power=0.8, n1=30, n2=30)

        return {
            "mann_whitney": mw_result,
            "bonferroni": {
                "adjusted_alpha": adjusted_alpha,
                "original_alpha": 0.05,
                "n_comparisons": 6,
            },
            "power_analysis": {
                "minimum_detectable_effect": mde,
                "target_power": 0.8,
                "assumed_n1": 30,
                "assumed_n2": 30,
            },
        }

    def compare_task_archetypes(
        self,
        journeys: list[dict[str, Any]],
        archetype_key: str = "task_archetype",
    ) -> dict[str, Any]:
        """Compute metrics grouped by task archetype with statistical comparisons.

        Args:
            journeys: List of journey dictionaries
            archetype_key: Key in journey dict for archetype classification

        Returns:
            Dict mapping archetype -> metrics, plus cross-archetype tests
        """
        archetype_map: dict[str, list[dict[str, Any]]] = {}

        for journey in journeys:
            archetype = journey.get(archetype_key, "unknown")
            if archetype not in archetype_map:
                archetype_map[archetype] = []
            archetype_map[archetype].append(journey)

        archetype_metrics: dict[str, Any] = {}

        for archetype, archetype_journeys in archetype_map.items():
            results = self.compute_all_metrics(archetype_journeys)
            archetype_metrics[archetype] = {
                "evo_coherence_amplitude": results.evo_coherence_amplitude,
                "phase_locking_rate": results.phase_locking_rate,
                "exotic_charge_lifetime": results.exotic_charge_lifetime,
                "kordylewski_orbit_quality": results.kordylewski_orbit_quality,
                "triune_balance_index": results.triune_balance_index,
                "recovery_basin_radius": results.recovery_basin_radius,
                "composite_score": results.composite_score,
                "n_journeys": len(archetype_journeys),
            }

        if len(archetype_map) >= 2:
            archetypes = list(archetype_map.keys())
            metrics_list = [archetype_metrics[a]["evo_coherence_amplitude"] for a in archetypes]

            if len(metrics_list) == 2:
                mw = self._compute_mann_whitney_u([metrics_list[0]], [metrics_list[1]])
            else:
                mw = {"u_stat": 0.0, "p_value": 1.0}

            adjusted_alpha = self._bonferroni_correction(alpha=0.05, n_comparisons=len(archetypes) * 6)

            archetype_metrics["mann_whitney"] = mw
            archetype_metrics["bonferroni"] = {
                "adjusted_alpha": adjusted_alpha,
                "n_archetypes": len(archetype_map),
                "n_metrics": 6,
                "total_comparisons": len(archetype_map) * 6,
            }

        return archetype_metrics
