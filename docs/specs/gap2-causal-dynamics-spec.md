# Gap 2 Spec: Causal Dynamics — Explanatory Power

**Priority**: Fourth (depends on Gap 5 learned embeddings, Gap 3 validated metrics, Gap 1 grounded traces)
**Timeline**: Weeks 5-7 of the research program
**Risk if skipped**: System detects problems but cannot explain or predict them

---

## Problem Statement

FLUME's trajectory encoding pipeline is fully transparent:

```
task_description → SHA-256 → 2048D → chunk-mean → 12D → quality_weight modulation → final_12D
```

Every step is deterministic and traceable. Yet we cannot explain why one trajectory succeeds where another fails. We have **causal architecture without causal content**:

1. **Operation type modulation** imposes coarse structure (5 profiles × 12 dimensions), but the profiles are hand-designed, not learned from outcomes.
2. **Quality weight blending** `quality_weight = 0.5 * coherence + 0.5 * efficiency` mixes hash-derived coordinates with operation profiles, but the 0.5/0.5 split is arbitrary.
3. **LCSP predictor** uses random weights — it predicts based on initialization noise, not learned dynamics.
4. **SHA-256 hash destroys semantic gradients** — the avalanche effect means tiny input changes produce completely different trajectory coordinates. No continuous causal pathway exists from task meaning to trajectory position.

The net result: the DegradationDetector can tell you coherence dropped below 0.60, but it cannot tell you that coherence dropped *because* the task complexity exceeded the model's capacity, or *because* the semantic domain shifted mid-execution.

---

## Component 1: VarianceDecomposer

**File**: `src/cohezion/compound/variance_decomposer.py`

### Purpose

Quantify what fraction of 12D trajectory variance is attributable to each causal factor: operation type, task semantics, and execution quality. This is ANOVA applied to trajectory space.

### Interface

```python
@dataclass
class VarianceComponent:
    """Variance attributable to one factor."""

    factor_name: str  # "operation_type", "task_semantics", "quality"
    variance_explained: float  # Sum of squares for this factor
    fraction_of_total: float  # η² (eta-squared)
    f_statistic: float
    p_value: float
    per_dimension: np.ndarray  # (12,) fraction per canonical dimension


@dataclass
class VarianceReport:
    """Full variance decomposition report."""

    components: list[VarianceComponent]
    residual_fraction: float  # Unexplained variance
    total_variance: float
    n_observations: int
    interaction_effects: dict[str, float]  # Pairwise interaction η²


class VarianceDecomposer:
    """ANOVA-based variance decomposition for 12D trajectories.

    Decomposes trajectory variance into:
    1. Operation type effect (5 categories)
    2. Task semantic cluster effect (from embeddings)
    3. Execution quality effect (coherence, efficiency)
    4. Residual (unexplained)
    """

    def __init__(self, n_semantic_clusters: int = 20):
        """
        Parameters
        ----------
        n_semantic_clusters : int
            Number of task semantic clusters for categorical decomposition.
            Tasks are clustered by SemanticEmbedder output.
        """

    def decompose(
        self,
        trajectories: np.ndarray,  # (N, 12) trajectory data
        operation_types: list[str],  # (N,) operation type labels
        task_embeddings: np.ndarray,  # (N, 227) from SemanticEmbedder
        quality_metrics: np.ndarray,  # (N, 2) coherence + efficiency
    ) -> VarianceReport:
        """Run full variance decomposition.

        Method: Two-way ANOVA with:
          Factor A: operation_type (5 levels)
          Factor B: semantic_cluster (k-means on task_embeddings, n_clusters levels)
          Covariate: quality_metrics (continuous)

        For each of the 12 canonical dimensions, compute:
          SS_operation / SS_total → fraction from operation type
          SS_semantic / SS_total → fraction from task semantics
          SS_quality / SS_total → fraction from execution quality
          SS_residual / SS_total → unexplained
        """

    def decompose_per_dimension(
        self,
        trajectories: np.ndarray,
        operation_types: list[str],
        task_embeddings: np.ndarray,
        quality_metrics: np.ndarray,
    ) -> dict[int, VarianceReport]:
        """Run decomposition separately for each of the 12 dimensions.

        Returns dim_index → VarianceReport mapping.
        Useful for identifying which dimensions are driven by which factors.
        """
```

### Expected Results

Based on the current architecture, we predict:

| Factor | Expected η² | Reasoning |
|--------|------------|-----------|
| Operation type | 0.30-0.50 | Modulation profiles impose strong structure |
| Task semantics | 0.05-0.15 | SHA-256 destroys most semantic signal |
| Execution quality | 0.10-0.25 | quality_weight directly modulates trajectory |
| Residual | 0.20-0.40 | Hash noise + random LCSP weights |

With SemanticEmbedder (Gap 5) replacing SHA-256, we expect task semantics η² to increase significantly (perhaps to 0.20-0.40) and residual to decrease.

---

## Component 2: JacobianAnalyzer

**File**: `src/cohezion/compound/jacobian_analyzer.py`

### Purpose

Compute the partial derivatives of the 12D trajectory with respect to execution quality metrics. This reveals which dimensions are causally sensitive to coherence and efficiency, and by how much.

### Interface

```python
@dataclass
class JacobianResult:
    """Jacobian matrix and derived sensitivity metrics."""

    jacobian: np.ndarray  # (12, N_metrics) partial derivatives
    metric_names: list[str]  # Names of the N input metrics
    dimension_labels: list[str]  # Canonical 12D labels

    # Derived metrics
    sensitivity_per_dim: np.ndarray  # (12,) Frobenius norm per row
    sensitivity_per_metric: np.ndarray  # (N,) Frobenius norm per column
    most_sensitive_dim: int  # Dimension with highest total sensitivity
    most_influential_metric: str  # Metric with highest total influence


@dataclass
class SensitivityProfile:
    """How a specific dimension responds to metric changes."""

    dimension_index: int
    dimension_label: str
    sensitivities: dict[str, float]  # metric_name → sensitivity magnitude
    direction: dict[str, str]  # metric_name → "positive" or "negative"
    is_robust: bool  # True if all sensitivities < threshold


class JacobianAnalyzer:
    """Compute sensitivity of 12D trajectory to execution quality metrics.

    Uses numerical differentiation (finite differences) on the deterministic
    encoding pipeline to compute ∂trajectory_i / ∂metric_j.
    """

    def __init__(self, encoder: ExperienceEncoder, epsilon: float = 1e-4):
        """
        Parameters
        ----------
        encoder : ExperienceEncoder
            The encoder whose Jacobian we compute.
        epsilon : float
            Step size for finite differences.
        """

    def compute_jacobian(
        self,
        experience: dict,
        metrics_to_perturb: list[str] | None = None,
    ) -> JacobianResult:
        """Compute Jacobian at a single experience point.

        For each metric m in metrics_to_perturb:
          1. Encode experience with metric m + epsilon → vec_plus
          2. Encode experience with metric m - epsilon → vec_minus
          3. ∂trajectory / ∂m = (vec_plus[:12] - vec_minus[:12]) / (2 * epsilon)

        Parameters
        ----------
        experience : dict
            Base experience to compute Jacobian at.
        metrics_to_perturb : list[str], optional
            Which METRIC_KEYS to perturb. Defaults to all 12.
        """

    def compute_average_jacobian(
        self,
        experiences: list[dict],
        metrics_to_perturb: list[str] | None = None,
    ) -> JacobianResult:
        """Average Jacobian across multiple experience points.

        More robust than single-point Jacobian; reveals general sensitivity
        patterns rather than local artifacts.
        """

    def sensitivity_profile(
        self,
        experiences: list[dict],
        dimension_index: int,
    ) -> SensitivityProfile:
        """Get detailed sensitivity profile for a single 12D dimension.

        Shows how this dimension responds to changes in each metric.
        """

    def find_causal_bottlenecks(
        self,
        experiences: list[dict],
    ) -> list[tuple[str, int, float]]:
        """Find (metric, dimension) pairs with unusually high sensitivity.

        These are causal bottlenecks: small changes in the metric cause
        large changes in the dimension. Useful for identifying fragile
        pathways in the encoding pipeline.

        Returns list of (metric_name, dim_index, sensitivity) sorted by sensitivity.
        """
```

### Jacobian Interpretation

```
            ∂coherence  ∂efficiency  ∂duration  ∂tokens  ...
           ┌──────────┬───────────┬──────────┬─────────┐
SPATIAL_X  │  0.00    │   0.00    │  0.00    │  0.00   │  ← Robust (hash-dominated)
SPATIAL_Y  │  0.00    │   0.00    │  0.00    │  0.00   │  ← Robust (hash-dominated)
SPATIAL_Z  │  0.00    │   0.00    │  0.00    │  0.00   │  ← Robust (hash-dominated)
TEMPORAL   │  0.00    │   0.00    │  0.00    │  0.00   │  ← Robust
COHERENCE  │  0.45    │   0.15    │  0.02    │  0.01   │  ← Sensitive to quality
EFFICIENCY │  0.15    │   0.40    │  0.05    │  0.03   │  ← Sensitive to quality
NOVELTY    │  0.02    │   0.01    │  0.00    │  0.00   │  ← Mostly hash-derived
LOGIC      │  0.03    │   0.02    │  0.00    │  0.00   │  ← Mostly hash-derived
CONVERGENCE│  0.20    │   0.10    │  0.01    │  0.01   │  ← Moderately sensitive
SMOOTHNESS │  0.35    │   0.12    │  0.01    │  0.00   │  ← Coupled to coherence!
FIELD      │  0.01    │   0.01    │  0.00    │  0.00   │  ← Robust
PRECIPITATN│  0.01    │   0.01    │  0.00    │  0.00   │  ← Robust
           └──────────┴───────────┴──────────┴─────────┘

Reading: SMOOTHNESS has high sensitivity to coherence (0.35) — confirms
the tautology flagged in Gap 3. COHERENCE and EFFICIENCY dimensions
are the primary quality-sensitive dimensions.
```

---

## Component 3: CausalAttributionEngine

**File**: `src/cohezion/compound/causal_attribution.py`

### Purpose

Given a trajectory outcome (success or failure), attribute it to specific causal factors. This is the component that answers "why did this execution fail?" instead of just "this execution failed."

### Interface

```python
@dataclass
class CausalFactor:
    """A single causal factor contributing to an outcome."""

    factor_name: str  # e.g., "task_complexity", "model_capacity_mismatch"
    linear_contribution: float  # Linear attribution score: Δmetric × sensitivity
    # NOTE: This is NOT a Shapley value. Shapley values require
    # combinatorial enumeration over feature subsets (see SHAP library).
    # This implements the simpler Δmetric × Jacobian_sensitivity method
    # (see Attribution Method section below). Rename to shap_contribution
    # if proper SHAP computation is added in a future iteration.
    direction: str  # "positive" (helped) or "negative" (hurt)
    evidence: str  # Human-readable evidence for this attribution
    confidence: float  # 0.0-1.0


@dataclass
class CausalAttribution:
    """Full causal attribution for a single execution."""

    execution_id: str
    outcome: str  # "success" or "failure"
    factors: list[CausalFactor]  # Sorted by |linear_contribution|, descending
    counterfactual: str | None  # "Would have succeeded if..." — FUTURE WORK:
    # Currently None. Counterfactual generation requires
    # identifying the minimum metric change that would flip
    # the predicted outcome. Implementation strategy:
    # find argmin_Δm ||Δm|| s.t. predict(m + Δm) = "success".
    # Track as a follow-on deliverable once attribution is validated.
    trajectory_anomalies: list[str]  # Detected anomalies in 12D path


class CausalAttributionEngine:
    """Attribute execution outcomes to specific causal factors.

    Uses the Jacobian (from JacobianAnalyzer) and variance decomposition
    (from VarianceDecomposer) to identify which factors caused the observed
    trajectory and outcome.
    """

    def __init__(
        self,
        jacobian_analyzer: JacobianAnalyzer,
        variance_decomposer: VarianceDecomposer,
        correlator: CoherenceSuccessCorrelator,
    ): ...

    def attribute(
        self,
        experience: dict,
        trajectory: np.ndarray,  # (T, 12) trajectory over time
        outcome: TaskOutcome,
    ) -> CausalAttribution:
        """Attribute outcome to causal factors.

        Method:
        1. Compute Jacobian at this experience point
        2. Identify which metrics deviated from baseline
        3. Multiply deviation × sensitivity → contribution
        4. Rank factors by |contribution|
        5. Generate counterfactual explanation
        """

    def attribute_batch(
        self,
        experiences: list[dict],
        trajectories: list[np.ndarray],
        outcomes: list[TaskOutcome],
    ) -> list[CausalAttribution]:
        """Attribute a batch of executions."""

    def find_common_failure_factors(
        self,
        attributions: list[CausalAttribution],
        min_frequency: float = 0.3,
    ) -> list[tuple[str, float, int]]:
        """Find factors that commonly appear in failures.

        Returns (factor_name, mean_contribution, frequency_count)
        for factors appearing in ≥ min_frequency of failure attributions.
        """

    def generate_predictive_alert(
        self,
        current_trajectory: np.ndarray,  # (T, 12) trajectory so far
        current_metrics: dict[str, float],
    ) -> str | None:
        """Check if current trajectory pattern matches known failure factors.

        If early trajectory signals match a common failure pattern,
        return a warning string. Otherwise return None.

        This is the key deliverable: predictive alerts based on causal
        understanding rather than threshold crossings.
        """
```

### Attribution Method: Deviation × Sensitivity

```
Step 1: Baseline metrics (from GlobalMetricsAggregator)
  coherence_baseline = 0.63
  efficiency_baseline = 0.75
  ...

Step 2: Current deviation
  Δcoherence = 0.45 - 0.63 = -0.18  (below baseline)
  Δefficiency = 0.80 - 0.75 = +0.05  (above baseline)
  ...

Step 3: Sensitivity (from Jacobian)
  ∂convergence/∂coherence = 0.20
  ∂convergence/∂efficiency = 0.10
  ...

Step 4: Contribution = Δmetric × sensitivity
  coherence_contribution = -0.18 × 0.20 = -0.036 (hurt convergence)
  efficiency_contribution = +0.05 × 0.10 = +0.005 (helped convergence)

Step 5: Rank and explain
  "Convergence was low primarily because coherence dropped 18% below
   baseline (contribution: -0.036). Efficiency was slightly above
   baseline but did not compensate."
```

---

## Component 4: InterventionalTestHarness

**File**: `src/cohezion/compound/interventional_harness.py`

### Purpose

Controlled input perturbations to test causal hypotheses. Instead of observing natural variation (which may be confounded), we deliberately modify specific inputs and measure trajectory changes.

### Interface

```python
@dataclass
class Intervention:
    """A single controlled intervention."""

    target_variable: str  # What to change
    original_value: Any  # Before intervention
    intervened_value: Any  # After intervention
    expected_effect: str  # Hypothesis


@dataclass
class InterventionResult:
    """Result of a controlled intervention."""

    intervention: Intervention
    trajectory_before: np.ndarray  # (12,) before intervention
    trajectory_after: np.ndarray  # (12,) after intervention
    delta: np.ndarray  # (12,) change per dimension
    outcome_before: TaskOutcome
    outcome_after: TaskOutcome
    hypothesis_supported: bool


class InterventionalTestHarness:
    """Run controlled interventions to test causal hypotheses."""

    def __init__(
        self,
        encoder: ExperienceEncoder,
        ablation_controller: AblationController,
    ): ...

    def intervene(
        self,
        base_experience: dict,
        intervention: Intervention,
    ) -> InterventionResult:
        """Apply a single intervention and measure the effect.

        1. Encode base_experience → trajectory_before
        2. Modify base_experience[target_variable] = intervened_value
        3. Encode modified experience → trajectory_after
        4. Compute delta = trajectory_after - trajectory_before
        5. If delta matches expected_effect direction → hypothesis supported
        """

    def run_experiment(
        self,
        base_experiences: list[dict],
        interventions: list[Intervention],
    ) -> list[InterventionResult]:
        """Run a full experiment: all interventions on all base experiences.

        Returns N_experiences × N_interventions results.
        """

    def average_treatment_effect(
        self,
        results: list[InterventionResult],
    ) -> np.ndarray:
        """Compute average treatment effect across all results.

        Returns (12,) average delta per canonical dimension.
        """
```

### Pre-Designed Interventions

| Intervention | Target | Hypothesis |
|-------------|--------|-----------|
| Flip operation type | operation_type | Changes dims matching modulation profile |
| Double token count | tokens_used | Decreases efficiency dim, others stable |
| Zero coherence | coherence metric | Collapses quality-sensitive dims |
| Change task domain | task_description | Changes semantic fingerprint dims |
| Swap model ID | model_used | Changes efficiency/latency dims |

---

## Validation Criteria (Gap 2 Complete When)

1. **Variance decomposition quantified**: η² for operation_type, task_semantics, and quality measured on ≥1000 trajectories, with total explained variance > 60%
2. **Jacobian computed**: Average Jacobian reveals which dimensions are quality-sensitive vs. hash-dominated, with ≥4 dimensions having sensitivity > 0.1 to at least one quality metric
3. **Causal attribution functional**: For ≥50 failure cases, the engine identifies the top causal factor with contribution > 0.02
4. **Predictive alerts validated**: On held-out data, causal-pattern-based alerts predict failure ≥2 steps before DegradationDetector threshold crossing in ≥30% of cases

---

## Tests

```python
# tests/compound/test_variance_decomposer.py
def test_operation_type_dominates():
    decomposer = VarianceDecomposer()
    # Create trajectories where operation type is the main factor
    np.random.seed(42)
    trajectories = np.zeros((100, 12))
    op_types = ["generate"] * 50 + ["analyze"] * 50
    # Generate profiles should differ from analyze profiles
    generate_profile = np.array([0.8, 0.2, 0.5, 0.5, 0.7, 0.6, 0.4, 0.8, 0.6, 0.7, 0.5, 0.5])
    analyze_profile = np.array([0.2, 0.8, 0.5, 0.5, 0.6, 0.7, 0.8, 0.4, 0.7, 0.6, 0.5, 0.5])
    for i, op in enumerate(op_types):
        noise = np.random.randn(12) * 0.05  # Small noise so op type dominates
        trajectories[i] = (generate_profile if op == "generate" else analyze_profile) + noise
    task_embeddings = np.random.randn(100, 227)  # Random semantic embeddings
    quality_metrics = np.random.rand(100, 2)  # Random coherence + efficiency
    report = decomposer.decompose(trajectories, op_types, task_embeddings, quality_metrics)
    op_component = [c for c in report.components if c.factor_name == "operation_type"][0]
    assert op_component.fraction_of_total > 0.5


# tests/compound/test_jacobian_analyzer.py
def test_coherence_sensitivity():
    analyzer = JacobianAnalyzer(ExperienceEncoder())
    experience = {
        "trajectory": [0.5] * 12,
        "coherence": 0.5,
        "efficiency": 0.5,
        "phi_score": 0.5,
        "anomaly_score": 0.0,
        "misalignment_score": 0.0,
        "task_description": "test task",
        "operation_type": "generate",
    }
    result = analyzer.compute_jacobian(experience, ["coherence"])
    # Coherence dimension (idx 4) should be sensitive to coherence metric
    assert abs(result.jacobian[4, 0]) > 0.01


def test_hash_dimensions_insensitive():
    analyzer = JacobianAnalyzer(ExperienceEncoder())
    experience = {
        "trajectory": [0.5] * 12,
        "coherence": 0.5,
        "efficiency": 0.5,
        "phi_score": 0.5,
        "anomaly_score": 0.0,
        "misalignment_score": 0.0,
        "task_description": "test task",
        "operation_type": "generate",
    }
    result = analyzer.compute_jacobian(experience, ["coherence"])
    # Spatial dims (0-2) should NOT be sensitive to coherence
    for i in range(3):
        assert abs(result.jacobian[i, 0]) < 0.001
```
