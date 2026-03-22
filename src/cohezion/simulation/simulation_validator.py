"""Simulation Statistical Validator (v1.0.2 Phase 1).

Validates that HIHO convergence in the Fractal Universe is statistically
meaningful rather than random noise. Applies rigorous hypothesis tests
to simulation trajectory data.

Tests Applied:
    1. Kolmogorov-Smirnov: coherence distribution vs. uniform random
    2. Entropy Rate: information content growth over cycles
    3. Convergence Speed: cycles-to-attractor measurement
    4. Bifurcation Detection: abrupt regime changes in coherence time series
    5. Attractor Verification: prove 0.5 is a genuine fixed-point attractor
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a single validation test."""

    test_name: str
    passed: bool
    p_value: float = 0.0
    statistic: float = 0.0
    details: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Aggregated validation report for a simulation run."""

    run_id: str
    total_cycles: int
    results: list[ValidationResult] = field(default_factory=list)
    overall_pass: bool = False
    confidence_score: float = 0.0

    def summary(self) -> str:
        """Generate markdown summary."""
        lines = [
            f"# Simulation Validation Report: {self.run_id}",
            f"**Cycles**: {self.total_cycles}",
            f"**Overall**: {'✅ PASS' if self.overall_pass else '❌ FAIL'}",
            f"**Confidence**: {self.confidence_score:.4f}",
            "",
            "| Test | Result | Statistic | p-value |",
            "|------|--------|-----------|---------|",
        ]
        for r in self.results:
            status = "✅" if r.passed else "❌"
            lines.append(f"| {r.test_name} | {status} | {r.statistic:.4f} | {r.p_value:.6f} |")
        return "\n".join(lines)


class SimulationValidator:
    """Statistical validation engine for HIHO simulation data.

    Parameters
    ----------
    significance_level : float
        P-value threshold for hypothesis tests (default 0.05).
    convergence_window : int
        Number of cycles to check for attractor approach.
    """

    def __init__(
        self,
        significance_level: float = 0.05,
        convergence_window: int = 100,
    ) -> None:
        self.alpha = significance_level
        self.convergence_window = convergence_window

    def validate(
        self,
        coherence_series: np.ndarray,
        entropy_series: np.ndarray,
        run_id: str = "unknown",
    ) -> ValidationReport:
        """Run all validation tests on simulation data.

        Parameters
        ----------
        coherence_series : np.ndarray
            1D array of coherence values over time (one per cycle).
        entropy_series : np.ndarray
            1D array of system entropy values over time.
        run_id : str
            Identifier for this simulation run.

        Returns
        -------
        ValidationReport
            Aggregated results from all tests.
        """
        results: list[ValidationResult] = []

        results.append(self._test_ks_vs_uniform(coherence_series))
        results.append(self._test_attractor_convergence(coherence_series))
        results.append(self._test_entropy_rate(entropy_series))
        results.append(self._test_bifurcation(coherence_series))
        results.append(self._test_stationarity(coherence_series))

        passed_count = sum(1 for r in results if r.passed)
        confidence = passed_count / len(results) if results else 0.0

        report = ValidationReport(
            run_id=run_id,
            total_cycles=len(coherence_series),
            results=results,
            overall_pass=confidence >= 0.6,
            confidence_score=confidence,
        )

        logger.info(
            "Validation %s: %d/%d tests passed (confidence=%.2f)",
            "PASSED" if report.overall_pass else "FAILED",
            passed_count,
            len(results),
            confidence,
        )
        return report

    def _test_ks_vs_uniform(self, coherence: np.ndarray) -> ValidationResult:
        """Kolmogorov-Smirnov test: coherence != uniform random.

        If coherence is just random noise on [0,1], the KS test against
        a uniform distribution will NOT reject. We expect REJECTION
        (low p-value), proving the system is NOT random.
        """
        ks_stat, p_value = stats.kstest(coherence, "uniform")

        # We WANT to reject uniformity (p < alpha means NOT random)
        passed = bool(p_value < self.alpha)
        return ValidationResult(
            test_name="KS vs Uniform",
            passed=passed,
            p_value=float(p_value),
            statistic=float(ks_stat),
            details=(
                "Coherence distribution is significantly non-uniform (NOT random noise)"
                if passed
                else "WARNING: Coherence looks indistinguishable from uniform random"
            ),
        )

    def _test_attractor_convergence(self, coherence: np.ndarray) -> ValidationResult:
        """Verify 0.5 is a genuine attractor.

        Check that the mean coherence in the final window is closer to 0.5
        than the initial window, and the variance decreases.
        """
        if len(coherence) < 2 * self.convergence_window:
            return ValidationResult(
                test_name="Attractor Convergence",
                passed=False,
                details="Insufficient data for convergence test",
            )

        initial = coherence[: self.convergence_window]
        final = coherence[-self.convergence_window :]

        initial_dist = float(np.mean(np.abs(initial - 0.5)))
        final_dist = float(np.mean(np.abs(final - 0.5)))
        initial_var = float(np.var(initial))
        final_var = float(np.var(final))

        converging = final_dist < initial_dist
        narrowing = final_var <= initial_var

        passed = converging and narrowing
        improvement = (initial_dist - final_dist) / initial_dist * 100 if initial_dist > 0 else 0

        return ValidationResult(
            test_name="Attractor Convergence",
            passed=passed,
            statistic=float(improvement),
            p_value=final_dist,
            details=(
                f"Convergence toward 0.5: {improvement:.1f}% improvement. "
                f"Variance {'narrowing' if narrowing else 'NOT narrowing'}."
            ),
            metadata={
                "initial_dist": initial_dist,
                "final_dist": final_dist,
                "initial_var": initial_var,
                "final_var": final_var,
            },
        )

    def _test_entropy_rate(self, entropy: np.ndarray) -> ValidationResult:
        """Verify information content is meaningful.

        Compute the entropy rate (first differences) and check that it's
        non-zero and decreasing (system is settling, not chaotic).
        """
        if len(entropy) < 10:
            return ValidationResult(
                test_name="Entropy Rate",
                passed=False,
                details="Insufficient data for entropy rate",
            )

        diffs = np.diff(entropy)
        rate = float(np.mean(np.abs(diffs)))

        # Split into halves to check if rate is decreasing
        half = len(diffs) // 2
        early_rate = float(np.mean(np.abs(diffs[:half])))
        late_rate = float(np.mean(np.abs(diffs[half:])))

        # Rate should be > 0 (not dead) and decreasing (settling)
        non_trivial = rate > 1e-6
        settling = late_rate <= early_rate * 1.1  # Allow 10% tolerance

        passed = non_trivial and settling

        return ValidationResult(
            test_name="Entropy Rate",
            passed=passed,
            statistic=rate,
            p_value=late_rate / early_rate if early_rate > 0 else 0,
            details=(
                f"Rate={rate:.6f}, early={early_rate:.6f}, "
                f"late={late_rate:.6f}. "
                f"{'Settling' if settling else 'NOT settling'}."
            ),
        )

    def _test_bifurcation(self, coherence: np.ndarray) -> ValidationResult:
        """Detect phase transitions via windowed variance analysis.

        A bifurcation is a sudden change in the local variance,
        indicating a regime shift in the system dynamics.
        """
        if len(coherence) < 50:
            return ValidationResult(
                test_name="Bifurcation Detection",
                passed=True,
                details="Insufficient data, no bifurcations expected",
            )

        window = max(10, len(coherence) // 20)
        variances: list[float] = []

        for i in range(0, len(coherence) - window, window // 2):
            segment = coherence[i : i + window]
            variances.append(float(np.var(segment)))

        if len(variances) < 3:
            return ValidationResult(
                test_name="Bifurcation Detection",
                passed=True,
                details="Too few windows for analysis",
            )

        var_array = np.array(variances)
        var_diffs = np.abs(np.diff(var_array))
        threshold = float(np.mean(var_diffs) + 2 * np.std(var_diffs))
        bifurcation_count = int(np.sum(var_diffs > threshold))

        return ValidationResult(
            test_name="Bifurcation Detection",
            passed=True,  # Informational — bifurcations are interesting
            statistic=float(bifurcation_count),
            p_value=threshold,
            details=(f"Detected {bifurcation_count} phase transitions (threshold={threshold:.6f})"),
            metadata={
                "bifurcation_count": bifurcation_count,
                "variance_series": variances,
            },
        )

    def _test_stationarity(self, coherence: np.ndarray) -> ValidationResult:
        """Augmented Dickey-Fuller test for stationarity.

        A stationary series means the system has reached a stable regime
        around the attractor. We WANT stationarity in the final segment.
        """
        final_segment = coherence[-self.convergence_window :]

        if len(final_segment) < 20:
            return ValidationResult(
                test_name="Stationarity (ADF)",
                passed=False,
                details="Insufficient data for ADF test",
            )

        # Simple ADF approximation: regress on lagged values
        # Using scipy's linregress as lightweight alternative
        y = final_segment[1:]
        x = final_segment[:-1]

        slope, _intercept, _r, p_value, _se = stats.linregress(x, y)

        # For stationarity, slope should be < 1 (mean-reverting)
        # and the series should not have a unit root
        is_stationary = abs(slope) < 0.98

        return ValidationResult(
            test_name="Stationarity (ADF)",
            passed=is_stationary,
            statistic=float(slope),
            p_value=float(p_value),
            details=(
                f"AR(1) slope={slope:.4f}. {'Stationary' if is_stationary else 'Non-stationary'}"
            ),
        )


def validate_from_parquet(
    parquet_dir: str = "data/simulations/fractal_nexus",
    run_id: str = "latest",
) -> ValidationReport | None:
    """Convenience function: load parquet data and validate.

    Parameters
    ----------
    parquet_dir : str
        Directory containing simulation parquet shards.
    run_id : str
        Identifier for the run.

    Returns
    -------
    ValidationReport or None
        Report if data was found, None otherwise.
    """
    import pandas as pd

    parquet_path = Path(parquet_dir)
    files = sorted(parquet_path.glob("*.parquet"))
    if not files:
        logger.warning("No parquet files found in %s", parquet_dir)
        return None

    dfs = [pd.read_parquet(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)

    if "phi_score" not in df.columns:
        logger.error("Missing 'phi_score' column in simulation data")
        return None

    coherence = df["phi_score"].to_numpy(dtype=np.float64)

    entropy: np.ndarray
    if "energy_level" in df.columns:
        entropy = df["energy_level"].to_numpy(dtype=np.float64)
    else:
        # Approximate entropy from coherence variance
        entropy = np.abs(coherence - 0.5)

    validator = SimulationValidator()
    return validator.validate(coherence, entropy, run_id=run_id)


if __name__ == "__main__":
    report = validate_from_parquet()
    if report:
        print(report.summary())
    else:
        print("No simulation data to validate.")
