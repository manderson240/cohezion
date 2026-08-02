# Gap 4 Spec: Temporal Dynamics — Operational Utility

**Priority**: Fifth (depends on all prior gaps for validated, grounded, causal metrics)
**Timeline**: Weeks 6-8 of the research program
**Risk if skipped**: System guarantees eventual stability but not predictable stability

---

## Problem Statement

FLUME agents have a designed attractor at coherence 0.5 (HIHO), stabilized by two mechanisms:

1. **BioelectricEngine**: `voltage = (coherence - 0.5) * 2`, `magnitude = intensity * (1.0 - |voltage|)` — negative feedback that slows movement at extremes
2. **LCSP predictor**: `prediction = 0.5 * prediction + 0.5 * previous_state` — damping that pulls toward the mean

Mean-reversion toward HIHO is **structurally guaranteed** by these mechanisms. What is *not* guaranteed or characterized:

- **Per-dimension recovery timescales**: Do all 12 dimensions recover at the same rate?
- **Nonlinear regime boundaries**: At what perturbation magnitude does recovery cease to be exponential?
- **Free energy landscape under load**: Does the HIHO well remain deep under sustained operation, or does it flatten (making recovery slower)?
- **Interruption recovery profiles**: How many operations restore trajectory quality after context loss?
- **Cross-agent variation**: Do agents with different operational histories recover differently?

The existing `ThermodynamicMetrics` module computes entropy, susceptibility, heat capacity, and free energy — but these have never been used in controlled experiments. The `TopologicalPersistence` module can detect structural trajectory changes — but no one has checked whether topological recovery matches point-wise recovery.

---

## Component 1: PerturbationInjector

**File**: `src/cohezion/compound/perturbation_injector.py`

### Purpose

Apply controlled perturbations to agent trajectories and measure recovery. This is the experimental apparatus for temporal dynamics studies.

### Interface

```python
from dataclasses import dataclass
from enum import Enum


class PerturbationType(Enum):
    IMPULSE = "impulse"  # Single sharp kick, then observe recovery
    STEP = "step"  # Sustained offset, then release
    NOISE = "noise"  # Continuous random perturbation
    DIMENSIONAL = "dimensional"  # Perturb only specific dimensions
    DIRECTIONAL = "directional"  # Perturb along a specific 12D direction


@dataclass
class PerturbationConfig:
    """Configuration for a single perturbation experiment."""

    perturbation_type: PerturbationType
    magnitude: float  # Size of perturbation (0.0-1.0)
    target_dimensions: list[int] | None  # None = all dimensions
    direction: np.ndarray | None  # For DIRECTIONAL type
    duration_steps: int  # For STEP type: how long to sustain
    noise_std: float  # For NOISE type: standard deviation


@dataclass
class RecoveryObservation:
    """A single observation during recovery."""

    step: int  # Steps since perturbation
    state_12d: np.ndarray  # Current 12D state
    coherence: float  # Current coherence
    distance_from_target: float  # L2 distance from pre-perturbation state
    per_dim_distance: np.ndarray  # (12,) per-dimension distance
    thermodynamic_state: dict  # Entropy, energy, free energy at this step
    topological_summary: dict | None  # H0, H1 features if enough history


class PerturbationInjector:
    """Inject controlled perturbations and observe recovery dynamics.

    Works with BioelectricEngine and LCSP predictor to observe how
    the system's built-in recovery mechanisms respond to disturbances.
    """

    def __init__(
        self,
        engine: BioelectricEngine,
        tracker: JourneyTracker | None = None,
        thermo: ThermodynamicMetrics | None = None,
    ): ...

    def inject_and_observe(
        self,
        initial_state: np.ndarray,  # Pre-perturbation 12D state
        config: PerturbationConfig,
        observation_steps: int = 100,  # How long to observe recovery
    ) -> list[RecoveryObservation]:
        """Inject perturbation and record recovery trajectory.

        Protocol:
        1. Record initial_state as baseline
        2. Apply perturbation according to config
        3. Let BioelectricEngine.step() evolve the state
        4. Record observations at each step
        5. Continue until observation_steps reached or full recovery
        """

    def sweep_magnitudes(
        self,
        initial_state: np.ndarray,
        perturbation_type: PerturbationType,
        magnitudes: list[float],  # e.g., [0.1, 0.2, 0.3, ..., 0.9]
        observation_steps: int = 100,
    ) -> dict[float, list[RecoveryObservation]]:
        """Run the same perturbation at multiple magnitudes.

        Returns magnitude → observation_list mapping.
        Essential for finding nonlinear regime boundaries.
        """

    def sweep_dimensions(
        self,
        initial_state: np.ndarray,
        magnitude: float,
        observation_steps: int = 100,
    ) -> dict[int, list[RecoveryObservation]]:
        """Perturb each dimension individually and observe recovery.

        Returns dim_index → observation_list mapping.
        Essential for measuring per-dimension recovery timescales.
        """

    def sustained_load(
        self,
        initial_state: np.ndarray,
        load_config: PerturbationConfig,  # NOISE type recommended
        total_steps: int = 500,
        measurement_interval: int = 10,
    ) -> list[RecoveryObservation]:
        """Apply sustained perturbation and observe long-term dynamics.

        Unlike inject_and_observe (which applies once and watches),
        this continuously perturbs while measuring. Tests whether
        the HIHO well flattens under sustained load.
        """
```

---

## Component 2: RecoveryCurveAnalyzer

**File**: `src/cohezion/compound/recovery_curve_analyzer.py`

### Purpose

Fit mathematical models to recovery observations and extract characteristic timescales, regime boundaries, and anisotropy.

### Interface

```python
@dataclass
class RecoveryTimescale:
    """Fitted recovery timescale for a single dimension."""

    dimension_index: int
    dimension_label: str
    tau: float  # Characteristic recovery time (in steps)
    regime: str  # "exponential", "power_law", "non_recovering"
    fit_quality: float  # R² of the fit
    half_life: float  # Steps to recover 50% of perturbation
    full_recovery_steps: int | None  # Steps to recover 95% (None if non-recovering)


@dataclass
class RecoveryProfile:
    """Complete recovery characterization for an agent."""

    per_dimension: list[RecoveryTimescale]
    mean_tau: float  # Average recovery timescale
    anisotropy: float  # std(tau) / mean(tau) — higher = more anisotropic
    fastest_dim: int  # Quickest to recover
    slowest_dim: int  # Slowest to recover
    nonlinear_threshold: float  # Perturbation magnitude where regime changes
    topology_recovers: bool  # Does persistence diagram return to baseline?


class RecoveryCurveAnalyzer:
    """Fit recovery curves and extract temporal dynamics parameters."""

    def __init__(self): ...

    def fit_single_dimension(
        self,
        observations: list[RecoveryObservation],
        dimension_index: int,
    ) -> RecoveryTimescale:
        """Fit recovery curve for a single dimension.

        Tries three models in order:
        1. Exponential: d(t) = d₀ · exp(-t/τ)
        2. Power law: d(t) = d₀ · t^(-α)
        3. Linear: d(t) = d₀ - βt

        Selects best fit by R². If none fits (R² < 0.5),
        classifies as "non_recovering".
        """

    def fit_full_profile(
        self,
        observations: list[RecoveryObservation],
    ) -> RecoveryProfile:
        """Fit recovery curves for all 12 dimensions.

        Computes per-dimension timescales and aggregate metrics.
        """

    def find_nonlinear_threshold(
        self,
        magnitude_sweeps: dict[float, list[RecoveryObservation]],
    ) -> float:
        """Find the perturbation magnitude where recovery regime changes.

        For small perturbations, recovery is exponential (linear regime).
        At some threshold, recovery becomes slower (nonlinear regime).

        Method: Fit exponential at each magnitude, plot τ vs. magnitude.
        The threshold is where τ starts increasing superlinearly.
        """

    def compare_profiles(
        self,
        profile_a: RecoveryProfile,
        profile_b: RecoveryProfile,
    ) -> dict:
        """Compare recovery profiles of two agents.

        Returns per-dimension tau ratios and overall similarity score.
        Useful for understanding cross-agent variation.
        """
```

### Recovery Regime Visualization

```
Recovery distance from baseline vs. steps after perturbation

     d(t)
     │
  1.0│ ●                              ← Perturbation magnitude
     │  ●
     │    ●
     │      ●●                         Linear regime: d(t) = d₀·e^(-t/τ)
     │          ●●●                    τ ≈ 10 steps (typical for small perturbation)
     │              ●●●●●
     │                    ●●●●●●●●●●●  ← 95% recovery at ~30 steps
  0.0│─────────────────────────────────
     0        10       20       30
                    steps

At larger perturbations (magnitude > threshold):

     d(t)
     │
  1.0│ ●                              ← Large perturbation
     │  ●
     │   ●
     │    ●●
     │      ●●●
     │         ●●●●●●                  Power law regime: d(t) = d₀·t^(-α)
     │               ●●●●●●●●●●       Much slower recovery
     │                         ●●●●●●  τ ≈ 50+ steps
  0.2│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  ← May not fully recover
     0        20       40       60
                    steps
```

---

## Component 3: FreeEnergyLandscapeMonitor

**File**: `src/cohezion/compound/free_energy_monitor.py`

### Purpose

Track how the HIHO stability well evolves under sustained operational load. The existing `ThermodynamicMetrics` computes free energy at a point in time; this component tracks how the landscape changes over time.

### Interface

```python
@dataclass
class WellDepthMeasurement:
    """A single measurement of the HIHO well depth."""

    timestamp: float
    step: int
    well_depth: float  # Free energy at HIHO minus maximum
    well_width: float  # Distance from HIHO where F > F_max - kT
    entropy: float
    temperature: float  # Effective temperature from ThermodynamicMetrics
    susceptibility: float  # Response to perturbation
    is_stable: bool  # well_depth > critical threshold


@dataclass
class LandscapeEvolution:
    """How the free energy landscape changed over an observation period."""

    measurements: list[WellDepthMeasurement]
    well_depth_trend: float  # Slope of well_depth over time (negative = flattening)
    well_width_trend: float  # Slope of well_width over time
    temperature_trend: float  # Is the system "heating up"?
    time_to_instability: float | None  # Projected steps until well_depth < threshold
    phase_transitions_detected: int  # Count of detected phase transitions


class FreeEnergyLandscapeMonitor:
    """Monitor HIHO well stability over time.

    Uses ThermodynamicMetrics to compute free energy landscape,
    then tracks how the landscape evolves under operational load.
    """

    def __init__(
        self,
        thermo: ThermodynamicMetrics,
        measurement_interval: int = 10,
        critical_well_depth: float = 0.1,
    ):
        """
        Parameters
        ----------
        thermo : ThermodynamicMetrics
            Existing thermodynamic computation module.
        measurement_interval : int
            Steps between measurements.
        critical_well_depth : float
            Well depth below which the system is considered unstable.
        """

    def measure_well(
        self,
        trajectory_window: np.ndarray,  # (W, 12) recent trajectory points
    ) -> WellDepthMeasurement:
        """Take a single well depth measurement.

        Uses ThermodynamicMetrics.get_hiho_free_energy_analysis()
        to compute current free energy landscape, then extracts
        well depth and width.
        """

    def monitor_session(
        self,
        observations: list[RecoveryObservation],
    ) -> LandscapeEvolution:
        """Track landscape evolution over a session.

        Takes measurements at measurement_interval steps,
        fits trends to well_depth and well_width over time.
        """

    def predict_instability(
        self,
        evolution: LandscapeEvolution,
    ) -> float | None:
        """Predict when the HIHO well will become too shallow.

        Extrapolates well_depth_trend forward. Returns steps until
        well_depth < critical_well_depth, or None if trend is
        stable/deepening.
        """
```

---

## Component 4: InterruptionSimulator

**File**: `src/cohezion/compound/interruption_simulator.py`

### Purpose

Simulate context loss (as would happen with session interruptions, context window truncation, or agent switching) and measure how many operations are needed to restore trajectory quality.

### Interface

```python
@dataclass
class InterruptionConfig:
    """Configuration for an interruption simulation."""

    context_loss_fraction: float  # 0.0 = no loss, 1.0 = total amnesia
    preserved_state: list[str]  # Which state components survive
    recovery_task_type: str  # What type of tasks to use for recovery
    n_recovery_tasks: int  # Maximum tasks to attempt


@dataclass
class InterruptionResult:
    """Result of an interruption simulation."""

    pre_interruption_coherence: float
    post_interruption_coherence: float
    coherence_drop: float
    recovery_trajectory: list[float]  # Coherence at each recovery step
    tasks_to_50_percent: int | None  # Tasks to recover 50% of lost coherence
    tasks_to_95_percent: int | None  # Tasks to recover 95%
    full_recovery_achieved: bool
    topological_recovery: bool  # Persistence diagram returned to baseline?


class InterruptionSimulator:
    """Simulate context loss and measure recovery operations."""

    def __init__(
        self,
        engine: BioelectricEngine,
        tracker: JourneyTracker,
    ): ...

    def simulate_interruption(
        self,
        current_state: np.ndarray,  # Pre-interruption 12D state
        trajectory_history: np.ndarray,  # (T, 12) history before interruption
        config: InterruptionConfig,
    ) -> InterruptionResult:
        """Simulate an interruption and recovery.

        1. Record pre-interruption state and coherence
        2. Apply context loss: zero out (1 - preserved) fraction of state
           Dimension selection strategy for zeroing:
           - Default: zero the HIGHEST-entropy dimensions first
             (high-entropy dims represent the most "recent" or volatile state,
              mimicking real context truncation which drops recent tokens first)
           - Alternative: uniform random selection (use for sensitivity analysis)
           - Alternative: zero lowest-coherence dimensions first (worst-case scenario)
           The choice of strategy significantly affects recovery time interpretation.
           Always record which strategy was used in InterruptionResult metadata.
        3. Record post-interruption coherence
        4. Run recovery tasks (BioelectricEngine.step() toward HIHO)
        5. Track coherence recovery over each task
        6. Report how many tasks to 50% and 95% recovery
        """

    def sweep_context_loss(
        self,
        current_state: np.ndarray,
        trajectory_history: np.ndarray,
        loss_fractions: list[float],  # e.g., [0.1, 0.3, 0.5, 0.7, 0.9]
    ) -> dict[float, InterruptionResult]:
        """Run interruption at multiple context loss levels.

        Returns loss_fraction → InterruptionResult mapping.
        Reveals relationship between context loss severity and recovery time.
        """

    def compare_recovery_strategies(
        self,
        current_state: np.ndarray,
        trajectory_history: np.ndarray,
        strategies: list[str],  # e.g., ["easy_tasks_first", "same_domain", "mixed"]
    ) -> dict[str, InterruptionResult]:
        """Compare different recovery task selection strategies.

        Which approach gets agents back to full capability fastest?
        """
```

---

## Component 5: RecoveryAwareScheduler

**File**: `src/cohezion/compound/recovery_scheduler.py`

### Purpose

The operational deliverable of Gap 4: predict when a perturbed agent will be ready for specific operation types, and schedule tasks accordingly.

### Interface

```python
@dataclass
class ReadinessState:
    """Current readiness assessment for an agent."""

    agent_id: str
    overall_readiness: float  # 0.0 = fully impaired, 1.0 = fully ready
    per_operation_readiness: dict[str, float]  # operation_type → readiness
    estimated_recovery_steps: dict[str, int]  # Steps until ready for each op type
    recommended_task_type: str | None  # Easiest task for current state, or None if ready
    recovery_phase: str  # "perturbed", "recovering", "recovered", "steady"


class RecoveryAwareScheduler:
    """Predict agent readiness and recommend task scheduling.

    Uses recovery profiles (from RecoveryCurveAnalyzer) and current
    trajectory state to predict when an agent will be ready for
    specific operation types.
    """

    def __init__(
        self,
        analyzer: RecoveryCurveAnalyzer,
        thresholds: dict[str, float] | None = None,
    ):
        """
        Parameters
        ----------
        analyzer : RecoveryCurveAnalyzer
            Provides recovery timescale parameters.
        thresholds : dict[str, float], optional
            Per-operation-type coherence thresholds for readiness.
            Priority order:
            1. Explicitly passed thresholds (highest priority)
            2. `OperationStratifiedValidator.get_thresholds()` output from Gap 3
               (available after Gap 3 completes; provides empirically derived per-op thresholds)
            3. Global threshold 0.60 (fallback only; do NOT hardcode as primary default)
            At Gap 4 implementation time, Gap 3 should already have produced per-op
            thresholds. Load them explicitly rather than using 0.60 as the default.
        """

    def assess_readiness(
        self,
        agent_id: str,
        current_state: np.ndarray,
        recent_trajectory: np.ndarray,  # (T, 12) recent history
        recovery_profile: RecoveryProfile | None = None,
    ) -> ReadinessState:
        """Assess current readiness of an agent.

        Method:
        1. Compute current coherence from state
        2. Detect if agent is in recovery (coherence below baseline,
           trending upward)
        3. Use recovery_profile.tau to estimate remaining recovery time
        4. Check per-operation-type thresholds
        5. Recommend easiest task if still recovering
        """

    def schedule_task(
        self,
        agents: list[tuple[str, ReadinessState]],
        task: dict,
    ) -> str:
        """Select best agent for a task based on readiness.

        Parameters
        ----------
        agents : list of (agent_id, ReadinessState)
            Available agents with their readiness assessments.
        task : dict
            Task to schedule, with 'operation_type' key.

        Returns
        -------
        str
            agent_id of the selected agent.
        """

    def suggest_recovery_plan(
        self,
        readiness: ReadinessState,
    ) -> list[dict]:
        """Suggest a sequence of tasks to accelerate recovery.

        Returns a list of task specifications, ordered by difficulty,
        designed to gradually restore full capability.

        Strategy: Start with easy tasks in the agent's strongest
        dimensions, progressively increase difficulty.
        """
```

### Integration with Compound Loop

```
                 ┌──────────────────────────────────┐
                 │     ExecutionOrchestrator          │
                 │                                    │
                 │  1. Receive task                   │
                 │  2. Query RecoveryAwareScheduler   │◄─── NEW
                 │     for agent readiness            │
                 │  3. If agent recovering:           │
                 │     a. Schedule easy task instead   │
                 │     b. Or pick different agent      │
                 │  4. Execute task                   │
                 │  5. Update trajectory               │
                 │  6. Re-assess readiness            │
                 └──────────────────────────────────┘
```

---

## Experiment Protocol

### Experiment 4.1: Per-Dimension Recovery Timescales

```
1. Start from HIHO origin (0.5, 0.5, ..., 0.5)
2. For each of 12 dimensions:
   a. Apply impulse perturbation of magnitude 0.3 to that dimension only
   b. Observe recovery for 100 steps
   c. Fit exponential decay: d(t) = d₀·exp(-t/τ)
   d. Record τ for this dimension
3. Report: τ per dimension, anisotropy measure
4. Repeat at magnitudes 0.1, 0.2, ..., 0.9 to find nonlinear threshold
```

### Experiment 4.2: Interruption Recovery

```
1. Run 50 simulation agents for 100 steps each (build trajectory history)
2. At step 100, simulate interruption with context_loss_fraction = [0.1, 0.3, 0.5, 0.7, 0.9]
3. For each loss fraction:
   a. Record post-interruption coherence
   b. Run recovery tasks for 100 steps
   c. Record steps to 50% and 95% recovery
4. Report: recovery curve as function of context loss severity
5. Test three recovery strategies: easy_tasks_first, same_domain, mixed
```

### Experiment 4.3: Free Energy Landscape Under Load

```
1. Start from HIHO origin
2. Apply sustained NOISE perturbation (std=0.1) for 500 steps
3. Measure HIHO well depth every 10 steps
4. Fit well_depth trend: depth(t) = depth₀ + slope·t
5. If slope < 0: well is flattening (system "heating up")
6. Increase noise to std=0.2, 0.3, ... until well collapses
7. Report: noise threshold for HIHO well collapse
```

---

## Validation Criteria (Gap 4 Complete When)

1. **Per-dimension timescales measured**: τ values for all 12 canonical dimensions, with fit R² > 0.7 for ≥8 dimensions
2. **Nonlinear threshold identified**: Perturbation magnitude where τ increases >2× over linear regime value
3. **Interruption recovery characterized**: Recovery curves measured at 5 context loss levels, with 95% recovery times reported
4. **Free energy well stability assessed**: Well depth trend measured under sustained load, with collapse threshold identified
5. **Recovery-aware scheduling functional**: Scheduler correctly recommends easy tasks for recovering agents and delays hard tasks until ready

---

## Tests

```python
# tests/compound/test_perturbation_injector.py
def test_impulse_recovery():
    injector = PerturbationInjector(BioelectricEngine())
    initial = np.full(12, 0.5)
    config = PerturbationConfig(
        perturbation_type=PerturbationType.IMPULSE,
        magnitude=0.3,
        target_dimensions=None,
        direction=None,
        duration_steps=1,
        noise_std=0.0,
    )
    observations = injector.inject_and_observe(initial, config, observation_steps=50)
    # Should eventually return close to initial state
    final_distance = observations[-1].distance_from_target
    initial_distance = observations[0].distance_from_target
    assert final_distance < initial_distance * 0.5  # At least 50% recovery


def test_per_dimension_perturbation():
    injector = PerturbationInjector(BioelectricEngine())
    initial = np.full(12, 0.5)
    results = injector.sweep_dimensions(initial, magnitude=0.3)
    assert len(results) == 12
    for dim_idx, obs in results.items():
        assert len(obs) > 0
        assert obs[0].per_dim_distance[dim_idx] > 0.1  # Perturbation applied


# tests/compound/test_recovery_curve.py
def test_exponential_fit():
    analyzer = RecoveryCurveAnalyzer()
    # Synthetic exponential decay
    observations = []
    target_state = np.full(12, 0.5)  # HIHO origin
    for t in range(50):
        d = 0.3 * np.exp(-t / 10.0)
        state = target_state + d  # Decaying offset
        obs = RecoveryObservation(
            step=t,
            state_12d=state,
            coherence=float(state[4]),
            distance_from_target=d * np.sqrt(12),  # L2 distance
            per_dim_distance=np.full(12, d),
            thermodynamic_state={"entropy": 0.5, "free_energy": 0.1},
            topological_summary=None,
        )
        observations.append(obs)
    timescale = analyzer.fit_single_dimension(observations, 0)
    assert abs(timescale.tau - 10.0) < 2.0  # Should recover tau ≈ 10
    assert timescale.regime == "exponential"


# tests/compound/test_recovery_scheduler.py
def test_recovering_agent_gets_easy_tasks():
    scheduler = RecoveryAwareScheduler(analyzer=RecoveryCurveAnalyzer())
    # Agent with low coherence should be flagged as recovering
    state = np.full(12, 0.3)  # Below HIHO
    readiness = scheduler.assess_readiness("agent-1", state, ...)
    assert readiness.recovery_phase == "recovering"
    assert readiness.overall_readiness < 0.5
    assert readiness.recommended_task_type is not None  # Should suggest easy task
```
