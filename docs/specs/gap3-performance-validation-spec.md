# Gap 3 Spec: Performance Validation — Empirical Anchor

**Priority**: Second (depends on Gap 5 canonical labels)
**Timeline**: Weeks 2-4 of the research program
**Risk if skipped**: Compound loop optimizes meaningless proxy metrics — epistemic corruption

---

## Problem Statement

Every autonomous decision in Cohezion depends on coherence thresholds:

- `DegradationDetector`: alerts at coherence < 0.60
- `ModelQualityClassifier`: forecasts coherence trends for model switching
- `CostAwareRouter`: uses coherence to select model tier
- `SkillRefiner`: optimizes skill definitions against phi score
- `BudgetEnforcer`: gates spending based on quality metrics

**None of these thresholds have been empirically validated.** The 0.60 threshold is a design choice, not a measured boundary. The phi score formula `0.5·coherence + 0.3·smoothness + 0.2·convergence` has weights chosen by intuition, not data. The HIHO theory predicts optimal performance at coherence 0.5, not 1.0 — this has never been tested.

Three specific risks:

1. **Tautological smoothness**: In `_step_to_axiomatic`, the quality_weight blends trajectory coordinates with coherence via `quality_weight = 0.5 * coherence + 0.5 * efficiency`. This means the "smoothness" dimension is mechanically coupled to coherence — measuring both together inflates apparent predictive power.

2. **Thermostat effect**: Control loops (retry on failure, model switching on low coherence, degradation alerts) filter the observable data. Low-coherence executions that would have succeeded are systematically re-routed, so we never observe the natural coherence-success relationship.

3. **Operation-type conflation**: Each operation type (generate, analyze, search, transform, persist) has different modulation profiles in JourneyTracker. A "coherence" value of 0.6 means different things for a search task vs. a code generation task. The single 0.60 threshold treats them as interchangeable.

---

## Component 1: AblationController

**File**: `src/cohezion/compound/ablation_controller.py`

### Purpose

Selectively disable control loops to observe the natural coherence-success relationship. Used during validation experiments, not in production.

### Interface

```python
from contextlib import contextmanager
from enum import Flag, auto

class ControlLoop(Flag):
    """Control loops that can be ablated."""
    RETRY_ON_FAILURE = auto()          # ExecutionOrchestrator retry logic
    MODEL_SWITCHING = auto()           # DynamicModelRouter fallback
    DEGRADATION_ALERTS = auto()        # DegradationDetector alerts
    BUDGET_ENFORCEMENT = auto()        # BudgetEnforcer gates
    COHERENCE_ROUTING = auto()         # CostAwareRouter coherence-based routing
    SKILL_REFINEMENT = auto()          # SkillRefiner updates during execution

    ALL = (RETRY_ON_FAILURE | MODEL_SWITCHING | DEGRADATION_ALERTS |
           BUDGET_ENFORCEMENT | COHERENCE_ROUTING | SKILL_REFINEMENT)
    NONE = 0

class AblationController:
    """Toggle control loops on/off for validation experiments.

    Thread-safe. Changes are scoped to context managers to prevent
    accidental production impact.
    """

    def __init__(self):
        self._disabled: ControlLoop = ControlLoop.NONE
        self._experiment_id: str | None = None

    @contextmanager
    def ablate(
        self,
        loops: ControlLoop,
        experiment_id: str,
    ):
        """Disable specified control loops for the duration of the context.

        Parameters
        ----------
        loops : ControlLoop
            Which loops to disable. Use ControlLoop.ALL for full ablation.
        experiment_id : str
            Identifier for this experiment (for logging/audit).

        Example
        -------
        controller = AblationController()
        with controller.ablate(ControlLoop.RETRY_ON_FAILURE | ControlLoop.MODEL_SWITCHING,
                               experiment_id="validation-001"):
            # Execute tasks without retries or model switching
            results = run_tasks(tasks)
        """

    def is_disabled(self, loop: ControlLoop) -> bool:
        """Check if a specific control loop is currently disabled."""

    @property
    def active_experiment(self) -> str | None:
        """Return current experiment ID, or None if no ablation active."""
```

### Integration Points

Each control loop checks the AblationController before acting:

```python
# In ExecutionOrchestrator (existing code, modified)
if not ablation_controller.is_disabled(ControlLoop.RETRY_ON_FAILURE):
    # existing retry logic
    ...

# In DynamicModelRouter (existing code, modified)
if not ablation_controller.is_disabled(ControlLoop.MODEL_SWITCHING):
    # existing model switching logic
    ...
```

The controller is injected via dependency injection, defaulting to a no-op instance in production.

---

## Component 2: CoherenceSuccessCorrelator

**File**: `src/cohezion/compound/coherence_success.py`

### Purpose

Collect paired (coherence, task_success) observations with proper controls. The key insight is that "success" must be measured independently of coherence — no circular dependency.

### Interface

```python
@dataclass
class PairedObservation:
    """A single (metric, outcome) pair for correlation analysis."""
    execution_id: str
    timestamp: float
    operation_type: str

    # Predictor variables (from FLUME)
    coherence: float
    phi_score: float
    smoothness: float
    convergence: float
    trajectory_12d: np.ndarray

    # Outcome variables (independent of coherence computation)
    task_completed: bool
    test_pass_rate: float | None
    output_quality: float | None     # External rating
    error_count: int
    wall_time_seconds: float

    # Control variables
    control_loops_active: list[str]  # Which loops were enabled
    model_used: str
    task_difficulty: float | None    # If available

@dataclass
class CorrelationResult:
    """Statistical analysis of coherence-success relationship."""
    pearson_r: float
    spearman_rho: float
    p_value: float
    n_observations: int
    confidence_interval_95: tuple[float, float]

    # HIHO test
    optimal_coherence: float         # Coherence value that maximizes success
    hiho_supported: bool             # Is optimal ≈ 0.5 (within 0.1)?
    monotonic: bool                  # Is relationship monotonically increasing?

    # Operation-type breakdown
    per_operation: dict[str, "CorrelationResult"]

class CoherenceSuccessCorrelator:
    """Collect and analyze coherence-success paired observations."""

    def __init__(self, storage_path: str = "data/validation/coherence_success.jsonl"):
        ...

    def record(self, observation: PairedObservation) -> None:
        """Record a single paired observation. Append-only."""

    def analyze(
        self,
        min_observations: int = 50,
        operation_type: str | None = None,
    ) -> CorrelationResult:
        """Compute coherence-success correlation.

        If operation_type is specified, analyzes only that operation type.
        """

    def test_hiho_hypothesis(
        self,
        coherence_bins: int = 10,
    ) -> dict:
        """Test HIHO prediction: is success maximized at coherence ≈ 0.5?

        Bins observations by coherence, computes mean success per bin,
        finds the bin with highest success rate.

        Bin count guidance:
          - Default 10 bins over [0.2, 0.9] → bin width ≈ 0.07 (~50 samples/bin at 500 obs)
          - Use coherence_bins=20 only with ≥1000 observations to maintain ≥25 samples/bin
          - Fewer bins reduce noise at the cost of resolution; 10 is a robust default

        Returns
        -------
        dict with:
            peak_coherence: float (bin center with highest success)
            peak_success: float
            hiho_supported: bool (peak within 0.4-0.6)
            quadratic_fit: tuple (a, b, c) for ax² + bx + c
            n_bins_used: int (may be fewer than coherence_bins if data is sparse)
        """

    def get_observations(
        self,
        operation_type: str | None = None,
        min_timestamp: float | None = None,
    ) -> list[PairedObservation]:
        """Retrieve stored observations for custom analysis."""
```

### Independent Success Measurement

The critical design constraint: success must be measured without reference to coherence.

```
┌──────────────────────────┐     ┌──────────────────────────┐
│  FLUME Metric Pipeline   │     │  Independent Outcome     │
│  (produces coherence)    │     │  (produces success)      │
│                          │     │                          │
│  JourneyTracker          │     │  Test runner results     │
│       ↓                  │     │  Lint/type-check pass    │
│  ExperienceEncoder       │     │  Human quality rating    │
│       ↓                  │     │  Task completion flag    │
│  coherence = f(12D)      │     │  Error count             │
│                          │     │  Wall-clock time         │
└──────────┬───────────────┘     └──────────┬───────────────┘
           │                                │
           └──────────── PAIRED ────────────┘
                         │
                         ▼
              CoherenceSuccessCorrelator
```

---

## Component 3: PhiScoreDecomposer

**File**: `src/cohezion/compound/phi_score_decomposer.py`

### Purpose

Test whether the phi score formula's components contribute independent predictive power, or whether smoothness and convergence are redundant with coherence.

### Interface

```python
@dataclass
class DecompositionResult:
    """Result of phi score component analysis."""

    # Individual component correlations with success
    coherence_r: float           # Pearson r of coherence alone vs. success
    smoothness_r: float          # Pearson r of smoothness alone vs. success
    convergence_r: float         # Pearson r of convergence alone vs. success

    # Incremental predictive power
    smoothness_delta_r2: float   # R² gain from adding smoothness to coherence
    convergence_delta_r2: float  # R² gain from adding convergence to coherence + smoothness

    # Component independence
    coherence_smoothness_r: float    # Correlation between components
    coherence_convergence_r: float
    smoothness_convergence_r: float

    # Optimal weights (learned from data)
    optimal_weights: tuple[float, float, float]  # (w_coh, w_smooth, w_conv)
    current_weights: tuple[float, float, float]  # (0.5, 0.3, 0.2) — current

    # Tautology test
    smoothness_tautological: bool    # True if coherence-smoothness r > 0.9
    explanation: str

class PhiScoreDecomposer:
    """Analyze phi score components for independent predictive power."""

    def __init__(self, correlator: CoherenceSuccessCorrelator):
        self.correlator = correlator

    def decompose(self, min_observations: int = 100) -> DecompositionResult:
        """Run full decomposition analysis.

        Steps:
        1. Get paired observations from correlator
        2. Compute individual correlations (each component vs. success)
        3. Compute incremental R² (hierarchical regression)
        4. Test component independence (inter-component correlations)
        5. Find optimal weights via linear regression
        6. Test smoothness tautology
        """

    def suggest_weights(self) -> tuple[float, float, float]:
        """Return empirically optimal phi score weights."""
```

### Tautology Detection

The smoothness tautology test specifically checks the mechanical coupling in `_step_to_axiomatic`:

```python
def _test_smoothness_tautology(
    self,
    observations: list[PairedObservation],
) -> tuple[bool, str]:
    """Test if smoothness is mechanically coupled to coherence.

    In JourneyTracker._step_to_axiomatic():
        quality_weight = 0.5 * coherence + 0.5 * efficiency
        trajectory = (1 - quality_weight) * hash_projection + quality_weight * op_profile

    This means smoothness (trajectory continuity) is partially determined
    by coherence (via quality_weight). If Pearson r > 0.9 between coherence
    and smoothness, the smoothness component is tautological.
    """
    coherence_vals = np.array([o.coherence for o in observations])
    smoothness_vals = np.array([o.smoothness for o in observations])
    r, p = scipy.stats.pearsonr(coherence_vals, smoothness_vals)

    is_tautological = abs(r) > 0.9
    explanation = (
        f"Coherence-smoothness correlation: r={r:.3f} (p={p:.2e}). "
        f"{'TAUTOLOGICAL: smoothness adds no independent signal.' if is_tautological else 'Independent signal detected.'}"
    )
    return is_tautological, explanation
```

---

## Component 4: OperationStratifiedValidator

**File**: `src/cohezion/validation/operation_stratified.py`

### Purpose

Test whether the single 0.60 degradation threshold should be replaced with per-operation-type thresholds.

### Interface

```python
@dataclass
class StratifiedThreshold:
    """Optimal threshold for a single operation type."""
    operation_type: str
    optimal_threshold: float       # Threshold maximizing F1 score
    f1_at_threshold: float
    n_observations: int
    confidence_interval: tuple[float, float]

@dataclass
class StratificationResult:
    """Full stratification analysis."""
    global_threshold: float        # Current: 0.60
    global_f1: float               # F1 at current threshold
    per_operation: dict[str, StratifiedThreshold]
    stratification_improves: bool  # True if per-op thresholds beat global
    f1_improvement: float          # Delta F1 from stratification
    recommendation: str

class OperationStratifiedValidator:
    """Test whether per-operation-type degradation thresholds outperform
    the single global threshold."""

    def __init__(self, correlator: CoherenceSuccessCorrelator):
        self.correlator = correlator

    def validate(self, min_per_operation: int = 30) -> StratificationResult:
        """Run stratification analysis.

        For each operation type:
        1. Collect (coherence, success) pairs
        2. Sweep thresholds from 0.3 to 0.9
        3. Compute F1 score at each threshold
        4. Find optimal threshold
        5. Compare aggregate stratified F1 vs. global F1
        """

    def apply_to_detector(
        self,
        detector: DegradationDetector,
        result: StratificationResult,
        require_per_threshold_improvement: bool = True,
    ) -> None:
        """Update DegradationDetector with per-operation thresholds.

        Safety guards (both must pass before any threshold is updated):

        1. Global guard: stratification_improves must be True
           (aggregate F1 with per-op thresholds beats global F1)

        2. Per-threshold guard (when require_per_threshold_improvement=True):
           Each individual per-operation threshold is only applied if its
           per-op F1 score exceeds the global threshold's F1 for that
           specific operation type. This prevents a threshold that improves
           aggregate F1 (by helping some op-types) from degrading a specific
           op-type where the global threshold was already optimal.

        Example:
            Global threshold 0.60 → F1 = 0.72 (search), 0.65 (generate)
            Stratified: search threshold 0.55 → F1 = 0.75 (better → apply)
                        generate threshold 0.65 → F1 = 0.63 (worse → skip)
            Result: search gets updated, generate keeps global 0.60
        """
```

---

## Experiment Protocol

### Experiment 3.1: Natural Coherence-Success Relationship

```
1. Collect 500+ execution traces across all 5 operation types
2. For each trace, record:
   - FLUME metrics (coherence, phi, smoothness, convergence)
   - Independent success measures (test pass, quality rating, completion)
3. Run with AblationController:
   a. Baseline: all control loops active (100 traces)
   b. No retries: disable RETRY_ON_FAILURE (100 traces)
   c. No model switching: disable MODEL_SWITCHING (100 traces)
   d. No degradation alerts: disable DEGRADATION_ALERTS (100 traces)
   e. Full ablation: disable ALL (100 traces)
4. Compute correlations for each condition
5. Compare: does the thermostat effect suppress natural variation?
```

### Experiment 3.2: HIHO Optimality Test

```
1. Collect 500+ observations with coherence values spanning 0.2 to 0.9
   (Recommended: 1000+ for statistical power with 10-bin analysis)
2. Bin by coherence (10 bins of width 0.07 — robust default for 500 observations)
   Use 20 bins only if observations ≥ 1000, to maintain ≥ 25 samples/bin
3. Compute mean success rate per bin
4. Fit quadratic: success = a·coherence² + b·coherence + c
5. Find peak: coherence_optimal = -b/(2a)
6. Test: is coherence_optimal within [0.4, 0.6]?
   - If yes → HIHO supported (optimal is near 0.5)
   - If no → HIHO refuted (optimal is elsewhere)
7. Report confidence: narrow CI around peak_coherence requires dense per-bin sampling
```

### Experiment 3.3: Phi Score Decomposition

```
1. From 500+ observations, extract (coherence, smoothness, convergence, success)
2. Hierarchical regression:
   - Model 1: success ~ coherence (R²₁)
   - Model 2: success ~ coherence + smoothness (R²₂)
   - Model 3: success ~ coherence + smoothness + convergence (R²₃)
3. Incremental R²: ΔR²_smooth = R²₂ - R²₁, ΔR²_conv = R²₃ - R²₂
4. If ΔR²_smooth < 0.01 → smoothness is redundant
5. Test coherence-smoothness correlation for tautology
6. Optimal weights via multivariate regression
```

---

## Validation Criteria (Gap 3 Complete When)

1. **Coherence-success correlation measured**: Pearson r and Spearman ρ computed with 95% CI on ≥500 observations
2. **HIHO hypothesis tested**: Quadratic fit determines whether optimal coherence is ≈0.5 or elsewhere
3. **Phi score decomposed**: Each component's incremental R² quantified; tautology flag resolved
4. **Operation stratification evaluated**: Per-op-type thresholds compared to global 0.60 threshold with F1 scores
5. **Thermostat effect quantified**: Ablated vs. non-ablated correlation difference measured

---

## Tests

```python
# tests/compound/test_ablation_controller.py
def test_ablation_scoped():
    ctrl = AblationController()
    assert not ctrl.is_disabled(ControlLoop.RETRY_ON_FAILURE)
    with ctrl.ablate(ControlLoop.RETRY_ON_FAILURE, "test-001"):
        assert ctrl.is_disabled(ControlLoop.RETRY_ON_FAILURE)
    assert not ctrl.is_disabled(ControlLoop.RETRY_ON_FAILURE)

def test_multiple_loops():
    ctrl = AblationController()
    loops = ControlLoop.RETRY_ON_FAILURE | ControlLoop.MODEL_SWITCHING
    with ctrl.ablate(loops, "test-002"):
        assert ctrl.is_disabled(ControlLoop.RETRY_ON_FAILURE)
        assert ctrl.is_disabled(ControlLoop.MODEL_SWITCHING)
        assert not ctrl.is_disabled(ControlLoop.DEGRADATION_ALERTS)

# tests/compound/test_coherence_success.py
def test_record_and_analyze(tmp_path):
    correlator = CoherenceSuccessCorrelator(storage_path=str(tmp_path / "test.jsonl"))
    for i in range(100):
        obs = PairedObservation(
            execution_id=f"exec-{i}",
            timestamp=float(i),
            operation_type="generate",
            coherence=random.random(),
            phi_score=random.random(),
            smoothness=random.random(),
            convergence=random.random(),
            trajectory_12d=np.zeros(12),
            task_completed=random.random() > 0.3,
            test_pass_rate=None,
            output_quality=None,
            error_count=0,
            wall_time_seconds=1.0,
            control_loops_active=["retry"],
            model_used="claude-opus-4-6",
            task_difficulty=None,
        )
        correlator.record(obs)
    result = correlator.analyze()
    assert result.n_observations == 100
    assert -1.0 <= result.pearson_r <= 1.0

def test_hiho_hypothesis(tmp_path):
    correlator = CoherenceSuccessCorrelator(storage_path=str(tmp_path / "hiho.jsonl"))
    # Inject data with peak success at coherence ≈ 0.5
    for idx, coh in enumerate(np.linspace(0.1, 0.9, 200)):
        obs = PairedObservation(
            execution_id=f"exec-{idx}",
            timestamp=float(idx),
            operation_type="generate",
            coherence=coh,
            phi_score=coh,
            smoothness=coh,
            convergence=coh,
            trajectory_12d=np.zeros(12),
            task_completed=(1.0 - 4 * (coh - 0.5) ** 2 + random.gauss(0, 0.1)) > 0.5,
            test_pass_rate=None,
            output_quality=None,
            error_count=0,
            wall_time_seconds=1.0,
            control_loops_active=[],
            model_used="claude-opus-4-6",
            task_difficulty=None,
        )
        correlator.record(obs)
    result = correlator.test_hiho_hypothesis()
    assert result["hiho_supported"]
```
