# Phase 5: Agentic Benchmark Metrics

## Overview

This module implements **6 EVO physics-based metrics** with full statistical rigor for evaluating agentic systems operating in the HIHO (High-Induction High-Order) manifold.

## Metric Families

### 1. EVO Coherence Amplitude

**Purpose**: Measures peak coherence over journey trajectory (HIHO stability).

**Formula**: `max(coherence_values)` from journey trajectory

**Interpretation**:
- 1.0 = Perfect HIHO stability (always at ideal coherence)
- 0.0 = No stability (always at extreme coherence)

**Physics basis**: EVO coherence amplitude represents the maximum "height" reached by the agent's coherence field in the 12D manifold during its journey.

### 2. Phase Locking Rate

**Purpose**: Percentage of steps where SPIN rotation aligns with precession.

**Formula**: `count(|spin - precession| <= threshold) / total_steps`

**Threshold**: 0.2 radians (configurable via `PHASE_LOCKING_THRESHOLD`)

**Interpretation**:
- 1.0 = Perfect phase locking (SPIN always aligns with precession)
- 0.0 = No phase locking (SPIN always misaligned with precession)

**Physics basis**: Phase locking is a fundamental phenomenon in oscillatory systems where two frequencies synchronize.

### 3. Exotic Charge Lifetime

**Purpose**: Steps before exotic charge density exceeds threshold (survival analysis).

**Formula**: `first_index_where(exotic_charge_density > 0.95)` or `trajectory_length`

**Threshold**: 0.95 (configurable via `EXOTIC_CHARGE_THRESHOLD`)

**Interpretation**:
- Longer lifetime = more stable exotic charge preservation
- Normalized to [0, 1] in composite score via `MAX_EXOTIC_CHARGE_LIFETIME=200`

**Physics basis**: Exotic charge is a hypothetical conserved quantity in the HIHO manifold; its decay rate indicates thermodynamic instability.

### 4. Kordylewski Orbit Quality

**Purpose**: Orbit stability relative to baseline variance.

**Formula**: `1 - (orbit_radius_variance / baseline_variance)`

**Interpretation**:
- 1.0 = Perfectly stable orbit (no radius variance)
- 0.0 = Unstable orbit (variance equals baseline)
- < 0.0 = Highly unstable (variance exceeds baseline)

**Physics basis**: Named after Kordylewski dust clouds (stable orbital configurations in gravitational fields).

### 5. TRIUNE Balance Index

**Purpose**: Balance of TRIUNE brain activation modes (doer/thinker/knower).

**Formula**: `1 - mean(std([doer, thinker, knower]))` per step, averaged across trajectory

**Interpretation**:
- 1.0 = Perfect balance (all activations equal)
- 0.0 = Maximum imbalance (one activation dominates)

**Physics basis**: TRIUNE refers to the three-mode architecture of biological motivation systems.

### 6. Recovery Basin Radius

**Purpose**: Maximum HIHO distance with successful recovery.

**Formula**: `max(hiho_distance where recovered == True)` until first failed recovery

**Interpretation**:
- 1.0 = Full basin (can recover from maximum distance)
- 0.0 = No recovery basin (cannot recover from any perturbation)

**Physics basis**: Recovery basin is the region in phase space where the system returns to the attractor.

---

## Statistical Rigor

### Bootstrap Confidence Intervals

All metrics include **95% bootstrap confidence intervals** using the percentile method.

**Parameters**:
- `n_bootstrap`: 1000 samples (default)
- `ci`: 0.95 (95% CI)

**Implementation**: Non-parametric resampling with replacement, computing the mean of bootstrap sample means.

### Mann-Whitney U Test

Non-parametric test for comparing two groups without assuming normality.

**Use case**: Comparing metrics across task archetypes.

**Output**:
```python
{
    "u_stat": float,  # Mann-Whitney U statistic
    "p_value": float,  # Two-sided p-value
}
```

### Bonferroni Correction

Controls family-wise error rate for multiple comparisons.

**Formula**: `adjusted_alpha = original_alpha / n_comparisons`

**Application**: For 6 metrics × N archetypes, the adjusted significance threshold is `0.05 / (6 * N)`.

### Power Analysis

**Minimum Detectable Effect (MDE)**: Smallest effect size detectable with given power.

**Formula** (Cohen's d for two independent groups):
```
MDE = (z_alpha + z_beta) / sqrt(n_harmonic)
where:
    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(power)
    n_harmonic = 2 / (1/n1 + 1/n2)
```

**Default parameters**:
- alpha = 0.05 (before Bonferroni)
- power = 0.8
- n1 = n2 = 30

---

## API Reference

### AgenticResults Dataclass

```python
@dataclass
class AgenticResults:
    evo_coherence_amplitude: float
    phase_locking_rate: float
    exotic_charge_lifetime: float
    kordylewski_orbit_quality: float
    triune_balance_index: float
    recovery_basin_radius: float
    composite_score: float
    confidence_intervals: dict[str, tuple[float, float]]
    statistical_tests: dict[str, dict]
```

### AgenticMetrics Class

```python
class AgenticMetrics:
    def compute_all_metrics(
        self,
        journeys: list[dict[str, Any]],
        n_bootstrap: int = 1000,
    ) -> AgenticResults:
        """Compute all 6 EVO metrics with bootstrap CIs."""
        
    def compare_task_archetypes(
        self,
        journeys: list[dict[str, Any]],
        archetype_key: str = "task_archetype",
    ) -> dict[str, Any]:
        """Compare metrics grouped by task archetype."""
```

---

## Composite Score

The composite score combines all 6 metrics using weighted averaging:

| Metric | Weight |
|--------|--------|
| EVO Coherence Amplitude | 0.20 |
| Phase Locking Rate | 0.15 |
| Exotic Charge Lifetime | 0.20 |
| Kordylewski Orbit Quality | 0.15 |
| TRIUNE Balance Index | 0.15 |
| Recovery Basin Radius | 0.15 |

**Exotic charge lifetime normalization**: `min(lifetime / 200, 1.0)`

---

## Usage Example

```python
from cohezion.benchmarks.agentic_metrics import AgenticMetrics

# Initialize metrics calculator
metrics = AgenticMetrics(random_state=42)

# Define journeys (agent trajectories through HIHO manifold)
journeys = [
    {
        "task_archetype": "exploration",
        "trajectory": [
            {
                "coherence": 0.5,
                "hiho_distance": 0.1,
                "spin": 0.5,
                "precession": 0.5,
                "exotic_charge_density": 0.3,
                "orbit_radius": 1.0,
                "doer_activation": 0.8,
                "thinker_activation": 0.7,
                "knower_activation": 0.75,
                "recovered": True,
            },
        ],
        "baseline_orbit_variance": 0.5,
    }
]

# Compute all metrics with 95% bootstrap CIs
results = metrics.compute_all_metrics(journeys, n_bootstrap=1000)

print(f"EVO Coherence: {results.evo_coherence_amplitude:.3f}")
print(f"95% CI: {results.confidence_intervals['evo_coherence_amplitude']}")
print(f"Composite Score: {results.composite_score:.3f}")

# Compare across task archetypes
archetype_metrics = metrics.compare_task_archetypes(journeys)
print(f"Mann-Whitney p-value: {archetype_metrics['mann_whitney']['p_value']:.4f}")
print(f"Bonferroni adjusted alpha: {archetype_metrics['bonferroni']['adjusted_alpha']:.6f}")
```

---

## Journey Schema

Expected fields in journey dictionaries:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trajectory` | list[dict] | Yes | List of trajectory steps |
| `task_archetype` | str | No | Classification of task type |
| `baseline_orbit_variance` | float | No | Baseline for orbit quality |

**Trajectory step fields**:

| Field | Type | Metric | Description |
|-------|------|--------|-------------|
| `coherence` | float | EVO Amplitude | Coherence value [0, 1] |
| `hiho_distance` | float | Recovery Basin | Distance from HIHO attractor |
| `spin` | float | Phase Locking | SPIN rotation angle |
| `precession` | float | Phase Locking | Precession angle |
| `exotic_charge_density` | float | Exotic Charge | Exotic charge density |
| `orbit_radius` | float | Kordylewski | Orbital radius |
| `doer_activation` | float | TRIUNE | Doer mode activation |
| `thinker_activation` | float | TRIUNE | Thinker mode activation |
| `knower_activation` | float | TRIUNE | Knower mode activation |
| `recovered` | bool | Recovery Basin | Whether recovery succeeded |

---

## Validation Thresholds

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| EVO Coherence Amplitude | > 0.8 | 0.6-0.8 | < 0.6 |
| Phase Locking Rate | > 0.7 | 0.4-0.7 | < 0.4 |
| Exotic Charge Lifetime | > 100 steps | 50-100 | < 50 |
| Kordylewski Orbit Quality | > 0.7 | 0.4-0.7 | < 0.4 |
| TRIUNE Balance Index | > 0.8 | 0.5-0.8 | < 0.5 |
| Recovery Basin Radius | > 0.6 | 0.3-0.6 | < 0.3 |
| Composite Score | > 0.7 | 0.4-0.7 | < 0.4 |

---

## Dependencies

- `numpy`: Array operations, variance, percentile
- `scipy`: Statistical functions (norm.ppf, mannwhitneyu)

No external dependencies beyond numpy/scipy for statistical rigor.
