# PHASE 5: Agentic Benchmark Metrics

## Overview

Phase 5 implements the **EVO Physics Metrics Engine** — a rigorous statistical framework for evaluating FLUME journey agents. Every EVO (Etheric Variant Oscillator) journey is scored across 6 physics-informed metric families with bootstrap confidence intervals, Mann-Whitney U significance testing, and Bonferroni correction for multiple comparisons.

## Metric Families

### 1. CoherenceMetric (HIHO Coherence)
**Concept**: Measures how close EVO coherence stays to the HIHO target of 0.5. HIHO (High-In/High-Out) is the stable coherence attractor. The metric computes mean coherence across episode steps, penalizing low coherence.

**Physics basis**: Coherence is derived from the 256D VAE latent space variance from the HIHO 0.5 target. A random walk would average ~0.5 coherence; a well-trained agent sustains >0.8.

**Null hypothesis (H0)**: Mean coherence = 0.5 (random walk).
**Metric**: Mean coherence across episode steps.
**Bootstrap**: 1000 resamples, 95% CI.

### 2. TRIUNEBalanceMetric
**Concept**: The TRIUNE SELF has three poles — Doer (action), Thinker (reasoning), Knower (intent). Balance means no single pole dominates. Measured as negative sum of |weight - 1/3| across all three poles.

**Physics basis**: TRIUNE states are updated each step and renormalized to sum to 1.0. Perfect balance = all three weights = 1/3 each.

**Null hypothesis (H0)**: TRIUNE weights are imbalanced (one pole dominates).
**Metric**: 0.0 = perfect balance, ~1.33 = maximum imbalance.

### 3. StabilityMetric
**Concept**: Inverse of the coefficient of variation (CV) of coherence plus HIHO distance. Measures how consistently the EVO maintains proximity to the HIHO attractor.

**Physics basis**: Stability is the absence of large deviations. CV = std/mean; a stable system has low CV.

**Null hypothesis (H0)**: EVO is unstable (high variance).
**Metric**: 1 / (1 + CV + mean_HIHO_distance). Range [0, 1].

### 4. ExoticChargeMetric
**Concept**: Measures how well the EVO sustains high exotic charge density without collapse. Exotic charge accumulates at +0.01/step in FlumeNavEnv, capped at 1.0. The EXOTIC_CHARGE archetype terminates when charge > 0.95.

**Physics basis**: Exotic vacuum objects accumulate charge from interactions with the vacuum. High sustained charge indicates the agent is exploiting vacuum structure effectively.

**Null hypothesis (H0)**: Charge accumulates slowly (mean < 0.3).
**Metric**: Mean exotic_charge_density across episode steps.

### 5. KordylewskiOrbitMetric
**Concept**: Kordylewski clouds are patterns of debris orbiting L4/L5 Lagrange points. EVOs assigned to L4 or L5 should maintain proximity to their Lagrange point.

**Physics basis**: The Kordylewski swarm provides gravitational scaffolding. Orbit stability indicates the agent is exploiting gravitational structure.

**Null hypothesis (H0)**: EVO drifts randomly (no orbit maintenance).
**Metric**: 1 / (1 + mean_lagrange_distance). Higher = better.

### 6. SPINPhaseMetric
**Concept**: SPIN phase accumulates 0.1 rad/step monotonically. Deviations indicate numerical instability.

**Physics basis**: Phase is a conserved quantity in the Hamiltonian dynamics. Monotonic accumulation with ~0.1 rad/step indicates correct integration.

**Null hypothesis (H0)**: Phase does not accumulate (mean increment ≈ 0).
**Metric**: Mean phase increment per step (expected ≈ 0.1 rad).

## Statistical Framework

### Bootstrap Resampling
- N_BOOTSTRAP = 1000 resamples per metric
- 95% confidence intervals via percentile method
- p-value computed against H0: mean = null_value

### Mann-Whitney U Test
- Non-parametric comparison between two episode populations
- H0: P(X > Y) = P(Y > X)
- Rank-biserial correlation as effect size
- Bonferroni correction for 6 simultaneous tests (α = 0.05/6 ≈ 0.0083)

### Power Analysis
- Estimated statistical power for given effect size and sample size
- Normal approximation to Mann-Whitney U distribution

## Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `CoherenceMetric` | agentic_metrics.py | HIHO coherence scoring |
| `TRIUNEBalanceMetric` | agentic_metrics.py | TRIUNE weight balance |
| `StabilityMetric` | agentic_metrics.py | Variance + HIHO proximity |
| `ExoticChargeMetric` | agentic_metrics.py | Charge accumulation rate |
| `KordylewskiOrbitMetric` | agentic_metrics.py | Lagrange orbit stability |
| `SPINPhaseMetric` | agentic_metrics.py | Phase monotonicity |
| `EVOPhysicsMetrics` | agentic_metrics.py | Aggregator for all 6 |
| `BootstrapResult` | agentic_metrics.py | Immutable CI + p-value result |
| `StatisticalComparison` | agentic_metrics.py | Mann-Whitney U result |
| `BonferroniCorrection` | agentic_metrics.py | Multiple comparison correction |

## Data Flow

```
EthericVariantOscillator.biology
         ↓
   Biography list (per-step dicts)
         ↓
   EVOPhysicsMetrics.compute_all()
         ↓
   6 × BootstrapResult
         ↓
   BONFERRONI CORRECTION (α/6)
         ↓
   Final significance calls
         ↓
   CapabilityScorecard.record_run()
         ↓
   Radar chart + longitudinal trends
```

## Tests

- 34 tests in `tests/benchmarks/test_agentic_metrics.py`
- Covers: bootstrap CI, Mann-Whitney U, Bonferroni, all 6 metrics, aggregator

## Integration Points

- **BenchmarkSuite**: Uses EVOPhysicsMetrics.compute_all() per episode
- **EvalPipeline**: Uses EVOPhysicsMetrics for per-episode and aggregate scoring
- **CapabilityScorecard**: Stores BootstrapResult per metric per run
- **LongitudinalTracker**: Tracks score trends across runs
