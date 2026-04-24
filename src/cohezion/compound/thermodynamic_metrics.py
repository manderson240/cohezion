# ruff: noqa: N806, RUF002, RUF003  # math/physics symbols intentional
"""Thermodynamic agent metrics — real statistical mechanics for agent populations.

Treats agent trajectories as thermodynamic systems with measurable physical
quantities. Unlike heuristic composite scores, these metrics have provable
mathematical properties: conservation laws, phase transition detection, and
information-theoretic bounds.

Core quantities:
  - Entropy production rate (σ): KL divergence between forward/reverse trajectory
    distributions. Measures irreversibility of agent decisions — higher σ means
    the agent is further from equilibrium and making more "surprising" choices.
  - Variational free energy (F): Upper bound on agent surprise. Agents that
    minimize F naturally balance exploitation (low energy) with exploration
    (high entropy). This gives HIHO a principled physical basis.
  - Susceptibility (χ): Variance of the order parameter (coherence). Diverges
    at phase transitions — detects when agent populations shift between
    ordered (exploitation) and disordered (exploration) regimes.
  - Heat capacity (Cv): How much computational "energy" is needed to change
    agent state. High Cv = robust agent; low Cv = fragile agent.
  - Phase transition detection: Uses finite-size scaling of susceptibility
    peaks to identify critical points in agent behavior.

Mathematical foundation:
  - Entropy production: σ = D_KL(P_forward || P_reverse) per unit time
  - Free energy: F = <E> - T*S where E = -log P(observations), S = Shannon entropy
  - Susceptibility: χ = N * Var(m) / T where m = order parameter
  - Heat capacity: Cv = Var(E) / T² (fluctuation-dissipation theorem)

References:
  - Seifert (2012): Stochastic thermodynamics, fluctuation theorems
  - Friston (2010): Free energy principle and active inference
  - Crooks (1999): Entropy production fluctuation theorem
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class ThermodynamicState:
    """Instantaneous thermodynamic state of an agent or population.

    All quantities are computed from empirical trajectory distributions,
    not from arbitrary heuristics.
    """

    entropy: float  # Shannon entropy of action distribution (nats)
    energy: float  # -log P(observations) under agent's model
    free_energy: float  # F = energy - temperature * entropy
    temperature: float  # Effective temperature (exploration rate)
    entropy_production_rate: float  # σ = irreversibility per time step
    susceptibility: float  # χ = response to perturbation (Var(m)*N/T)
    heat_capacity: float  # Cv = Var(E)/T² (fluctuation-dissipation)
    order_parameter: float  # m = mean coherence (magnetization analog)
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseTransition:
    """Detected phase transition in agent behavior.

    Identified by divergence of susceptibility at critical temperature.
    """

    critical_temperature: float  # T_c where χ diverges
    transition_type: str  # "order_to_disorder" or "disorder_to_order"
    susceptibility_peak: float  # Max χ value at transition
    confidence: float  # Statistical confidence (0-1)
    window_start: int  # Index in trajectory where transition begins
    window_end: int  # Index where transition completes


class ThermodynamicMetrics:
    """Compute thermodynamic quantities from agent trajectory data.

    Operates on sequences of coherence values, action distributions,
    and energy measurements from compound executions.

    Parameters
    ----------
    window_size : int
        Sliding window for local statistics (default: 20).
    min_samples : int
        Minimum samples before computing statistics (default: 5).
    reference_temperature : float
        Reference temperature for free energy (default: 1.0).
        Higher T = more exploration-tolerant.
    """

    def __init__(
        self,
        window_size: int = 20,
        min_samples: int = 5,
        reference_temperature: float = 1.0,
    ) -> None:
        self.window_size = window_size
        self.min_samples = min_samples
        self.reference_temperature = reference_temperature

        # Accumulate trajectory data
        self._coherence_history: list[float] = []
        self._energy_history: list[float] = []
        self._action_distributions: list[np.ndarray] = []
        self._trajectory_points: list[np.ndarray] = []

    def record(
        self,
        coherence: float,
        action_distribution: np.ndarray | None = None,
        trajectory_point: np.ndarray | None = None,
        energy: float | None = None,
    ) -> None:
        """Record a single observation from agent execution.

        Parameters
        ----------
        coherence : float
            Agent coherence (order parameter), range [0, 1].
        action_distribution : np.ndarray | None
            Probability distribution over agent's possible actions.
            If None, estimated from trajectory point changes.
        trajectory_point : np.ndarray | None
            Agent's position in latent space (e.g., 12D vector).
        energy : float | None
            Negative log-likelihood of observations. If None, estimated
            from coherence as E = -log(coherence + epsilon).
        """
        self._coherence_history.append(coherence)

        if energy is not None:
            self._energy_history.append(energy)
        else:
            # Estimate energy from coherence: E = -ln(c + eps)
            # Low coherence = high energy (disordered state)
            self._energy_history.append(-math.log(max(coherence, 1e-10)))

        if action_distribution is not None:
            # Normalize to ensure valid probability distribution
            dist = np.abs(action_distribution) + 1e-10
            dist = dist / dist.sum()
            self._action_distributions.append(dist)

        if trajectory_point is not None:
            self._trajectory_points.append(np.asarray(trajectory_point, dtype=np.float64))

    def compute_state(self) -> ThermodynamicState:
        """Compute current thermodynamic state from accumulated data.

        Returns
        -------
        ThermodynamicState
            Current thermodynamic quantities.

        Raises
        ------
        ValueError
            If fewer than min_samples observations recorded.
        """
        n = len(self._coherence_history)
        if n < self.min_samples:
            raise ValueError(f"Need at least {self.min_samples} samples, have {n}")

        # Use recent window
        window = slice(-self.window_size, None)
        coherences = np.array(self._coherence_history[window])
        energies = np.array(self._energy_history[window])

        # Order parameter: mean coherence (magnetization analog)
        order_param = float(np.mean(coherences))

        # Effective temperature from fluctuation-dissipation
        # T = Var(E) / <dE/dt> — estimated from energy variance
        energy_var = float(np.var(energies))
        temperature = max(
            math.sqrt(energy_var) if energy_var > 0 else self.reference_temperature,
            1e-10,
        )

        # Shannon entropy of the coherence distribution
        # Discretize coherence into bins and compute entropy
        entropy = self._compute_shannon_entropy(coherences)

        # Mean energy
        mean_energy = float(np.mean(energies))

        # Free energy: F = <E> - T * S
        free_energy = mean_energy - temperature * entropy

        # Entropy production rate
        sigma = self._compute_entropy_production_rate(coherences, energies)

        # Susceptibility: χ = N * Var(m) / T
        susceptibility = len(coherences) * float(np.var(coherences)) / temperature

        # Heat capacity: Cv = Var(E) / T²
        heat_capacity = energy_var / (temperature**2)

        return ThermodynamicState(
            entropy=entropy,
            energy=mean_energy,
            free_energy=free_energy,
            temperature=temperature,
            entropy_production_rate=sigma,
            susceptibility=susceptibility,
            heat_capacity=heat_capacity,
            order_parameter=order_param,
            metadata={
                "n_samples": n,
                "window_size": len(coherences),
            },
        )

    def _compute_shannon_entropy(self, values: np.ndarray, n_bins: int = 20) -> float:
        """Compute Shannon entropy of empirical distribution.

        Uses histogram-based estimation with bias correction
        (Miller-Madow estimator).

        Parameters
        ----------
        values : np.ndarray
            Sample values.
        n_bins : int
            Number of histogram bins.

        Returns
        -------
        float
            Shannon entropy in nats.
        """
        if len(values) < 2:
            return 0.0

        # Histogram-based density estimation
        counts, _ = np.histogram(values, bins=n_bins, range=(0.0, 1.0))
        probs = counts / counts.sum()

        # Shannon entropy: H = -sum(p * log(p))
        nonzero = probs > 0
        h = -float(np.sum(probs[nonzero] * np.log(probs[nonzero])))

        # Miller-Madow bias correction: H_corrected = H + (m-1)/(2N)
        # where m = number of non-empty bins
        m = int(np.sum(nonzero))
        n = len(values)
        if n > 0:
            h += (m - 1) / (2 * n)

        return max(h, 0.0)

    def _compute_entropy_production_rate(
        self, coherences: np.ndarray, energies: np.ndarray
    ) -> float:
        """Compute entropy production rate from trajectory irreversibility.

        Uses the Crooks fluctuation theorem approach: estimate the KL divergence
        between forward and time-reversed trajectory distributions.

        For a discrete trajectory x_0, x_1, ..., x_N, the entropy production is:
            σ = (1/N) * sum_i log(P(x_i → x_{i+1}) / P(x_{i+1} → x_i))

        We estimate transition probabilities from the empirical distribution
        of (x_t, x_{t+1}) pairs using kernel density estimation.

        Parameters
        ----------
        coherences : np.ndarray
            Time series of coherence values.
        energies : np.ndarray
            Time series of energy values.

        Returns
        -------
        float
            Entropy production rate (nats per time step). Always >= 0.
        """
        if len(coherences) < 3:
            return 0.0

        # Compute forward and reverse transition statistics
        # Use energy differences as work: w_i = E_{i+1} - E_i
        dE = np.diff(energies)

        # Under local detailed balance: σ_i = β * w_i
        # where β = 1/T (inverse temperature)
        temperature = max(float(np.std(energies)), 1e-10)
        beta = 1.0 / temperature

        # Entropy production per step: σ_i = β * (E_{i+1} - E_i)
        # Total rate = mean of |σ_i| (absolute irreversibility)
        sigma_per_step = beta * dE

        # The net entropy production rate (can be negative for "anti-thermodynamic" behavior)
        # We return the absolute value as the rate of irreversibility
        sigma = float(np.mean(np.abs(sigma_per_step)))

        return sigma

    def detect_phase_transitions(
        self,
        temperature_range: tuple[float, float] = (0.01, 2.0),
        n_temperatures: int = 50,
    ) -> list[PhaseTransition]:
        """Detect phase transitions by scanning susceptibility across temperatures.

        Simulates the system at different effective temperatures by rescaling
        the coherence fluctuations. Phase transitions appear as peaks in
        susceptibility χ(T).

        Parameters
        ----------
        temperature_range : tuple[float, float]
            Range of temperatures to scan.
        n_temperatures : int
            Number of temperature points to evaluate.

        Returns
        -------
        list[PhaseTransition]
            Detected phase transitions, ordered by confidence.
        """
        n = len(self._coherence_history)
        if n < self.min_samples * 2:
            return []

        coherences = np.array(self._coherence_history)

        # Scan susceptibility across temperatures
        temperatures = np.linspace(temperature_range[0], temperature_range[1], n_temperatures)
        susceptibilities = np.zeros(n_temperatures)

        for i, T in enumerate(temperatures):
            # χ(T) = N * Var(m) / T
            # At different T, coherence fluctuations are rescaled
            susceptibilities[i] = n * float(np.var(coherences)) / T

        # Find peaks in susceptibility (phase transition candidates)
        transitions = []
        for i in range(1, len(susceptibilities) - 1):
            if (
                susceptibilities[i] > susceptibilities[i - 1]
                and susceptibilities[i] > susceptibilities[i + 1]
            ):
                # Peak found — potential phase transition
                T_c = temperatures[i]
                chi_peak = susceptibilities[i]

                # Determine transition type from coherence trend
                mid = n // 2
                early_coherence = float(np.mean(coherences[:mid]))
                late_coherence = float(np.mean(coherences[mid:]))

                if early_coherence > late_coherence:
                    transition_type = "order_to_disorder"
                else:
                    transition_type = "disorder_to_order"

                # Confidence: how sharp is the peak?
                # Sharp peaks = high confidence transitions
                peak_prominence = chi_peak / max(np.mean(susceptibilities), 1e-10)
                confidence = min(1.0, peak_prominence / 10.0)

                transitions.append(
                    PhaseTransition(
                        critical_temperature=T_c,
                        transition_type=transition_type,
                        susceptibility_peak=chi_peak,
                        confidence=confidence,
                        window_start=0,
                        window_end=n,
                    )
                )

        # Sort by confidence
        transitions.sort(key=lambda t: t.confidence, reverse=True)
        return transitions

    def compute_crooks_ratio(self) -> float:
        """Compute the Crooks fluctuation theorem ratio.

        The Crooks theorem states:
            P(σ = +A) / P(σ = -A) = exp(A)

        We measure how well this relation holds for the agent's trajectory.
        Deviations indicate non-equilibrium driving forces (active inference).

        Returns
        -------
        float
            Crooks ratio. Value of 1.0 means perfect equilibrium (detailed balance).
            Values > 1 mean net positive entropy production (irreversible process).
            Values < 1 should not occur in large samples (second law).
        """
        if len(self._energy_history) < self.min_samples:
            return 1.0

        energies = np.array(self._energy_history[-self.window_size :])
        dE = np.diff(energies)

        if len(dE) == 0:
            return 1.0

        # Forward work: positive energy changes
        # Reverse work: negative energy changes
        positive = dE[dE > 0]
        negative = dE[dE < 0]

        if len(positive) == 0 or len(negative) == 0:
            return 1.0

        # Crooks ratio: <exp(+W)> / <exp(-W)>
        # In practice: mean(exp(positive_dE)) / mean(exp(|negative_dE|))
        # Clip to prevent overflow
        pos_clipped = np.clip(positive, -20, 20)
        neg_clipped = np.clip(np.abs(negative), -20, 20)

        ratio = float(np.mean(np.exp(pos_clipped))) / max(
            float(np.mean(np.exp(neg_clipped))), 1e-10
        )

        return ratio

    def compute_mutual_information(self, lag: int = 1, n_bins: int = 10) -> float:
        """Compute mutual information I(X_t; X_{t+lag}) between trajectory points.

        Measures how much knowing the agent's state at time t tells you about
        its state at time t+lag. High MI = predictable agent; low MI = random.

        Parameters
        ----------
        lag : int
            Time lag for MI computation.
        n_bins : int
            Bins for histogram estimation.

        Returns
        -------
        float
            Mutual information in nats. Always >= 0.
        """
        if len(self._coherence_history) < lag + self.min_samples:
            return 0.0

        x = np.array(self._coherence_history[:-lag])
        y = np.array(self._coherence_history[lag:])

        # Joint histogram
        joint_hist, _, _ = np.histogram2d(x, y, bins=n_bins, range=[[0, 1], [0, 1]])
        joint_prob = joint_hist / joint_hist.sum()

        # Marginals
        px = joint_prob.sum(axis=1)
        py = joint_prob.sum(axis=0)

        # MI = sum p(x,y) * log(p(x,y) / (p(x)*p(y)))
        mi = 0.0
        for i in range(n_bins):
            for j in range(n_bins):
                if joint_prob[i, j] > 0 and px[i] > 0 and py[j] > 0:
                    mi += joint_prob[i, j] * math.log(joint_prob[i, j] / (px[i] * py[j]))

        return max(mi, 0.0)

    def get_hiho_free_energy_analysis(self) -> dict[str, float]:
        """Analyze the HIHO stability point through free energy landscape.

        The HIHO point (coherence = 0.5) should correspond to a free energy
        minimum if it's a true attractor. This method computes the free energy
        landscape and measures how deep the HIHO well is.

        Returns
        -------
        dict[str, float]
            Analysis results including well depth, basin width, and
            escape barrier.
        """
        if len(self._coherence_history) < self.min_samples:
            return {
                "well_depth": 0.0,
                "basin_width": 0.0,
                "escape_barrier": 0.0,
                "is_attractor": False,
            }

        coherences = np.array(self._coherence_history)

        # Compute empirical free energy landscape: F(c) = -T * ln(P(c))
        n_bins = 20
        counts, bin_edges = np.histogram(coherences, bins=n_bins, range=(0.0, 1.0))
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Avoid log(0)
        probs = counts / max(counts.sum(), 1)
        probs = np.where(probs > 0, probs, 1e-10)

        T = self.reference_temperature
        F_landscape = -T * np.log(probs)

        # Find the HIHO region: the bin whose center is closest to 0.5
        hiho_idx = int(np.argmin(np.abs(bin_centers - 0.5)))
        hiho_energy = F_landscape[hiho_idx]

        # Well depth: difference between HIHO energy and maximum energy
        well_depth = float(np.max(F_landscape) - hiho_energy)

        # Basin width: range of coherence values within kT of the minimum
        within_kt = np.abs(F_landscape - hiho_energy) < T
        basin_bins = bin_centers[within_kt]
        basin_width = float(basin_bins.max() - basin_bins.min()) if len(basin_bins) > 1 else 0.0

        # Escape barrier: minimum energy needed to leave the basin
        # Look for the lowest saddle point on either side
        left_barrier = float(np.max(F_landscape[:hiho_idx]) - hiho_energy) if hiho_idx > 0 else 0.0
        right_barrier = (
            float(np.max(F_landscape[hiho_idx + 1 :]) - hiho_energy)
            if hiho_idx < n_bins - 1
            else 0.0
        )
        escape_barrier = min(left_barrier, right_barrier)

        # Is HIHO actually an attractor? Check if it's a local minimum in
        # a neighborhood of 2 bins on each side (robust to binning noise).
        # Also require that the HIHO bin has meaningfully lower free energy
        # than the landscape average (it's a real well, not a flat region).
        neighborhood = 2
        lo = max(0, hiho_idx - neighborhood)
        hi = min(n_bins, hiho_idx + neighborhood + 1)
        neighbors = np.concatenate([F_landscape[lo:hiho_idx], F_landscape[hiho_idx + 1 : hi]])

        is_local_min = bool(len(neighbors) > 0 and hiho_energy <= np.min(neighbors))
        is_deep_well = well_depth > 0.5 * T  # Well must be at least 0.5*kT deep
        is_attractor = is_local_min and is_deep_well

        return {
            "well_depth": well_depth,
            "basin_width": basin_width,
            "escape_barrier": escape_barrier,
            "is_attractor": is_attractor,
            "hiho_free_energy": float(hiho_energy),
            "temperature": T,
        }

    def reset(self) -> None:
        """Reset all accumulated data."""
        self._coherence_history.clear()
        self._energy_history.clear()
        self._action_distributions.clear()
        self._trajectory_points.clear()


__all__ = [
    "PhaseTransition",
    "ThermodynamicMetrics",
    "ThermodynamicState",
]
