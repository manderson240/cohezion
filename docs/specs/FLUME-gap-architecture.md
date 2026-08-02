# FLUME Gap Architecture: From Research Vision to Implementation

**Date**: 2026-02-18
**Status**: Specification
**Depends on**: `docs/FLUME-research-vision.md`, `docs/FLUME-next-experiments.md`

---

## Overview

This document specifies the architecture to close five research gaps identified in the FLUME Research Vision. It defines new components, their interfaces, data flows, and integration points with the existing codebase.

**Execution order follows the dependency chain:**

```
Gap 5 (Interpretability)      ← Foundation: fix the representation
    ↓
Gap 3 (Performance Validation) ← Empirical anchor: prove metrics work
    ↓
Gap 1 (LLM Grounding)         ← Bridge: transfer to real reasoning
    ↓
Gap 2 (Causal Dynamics)       ← Explanatory power: understand why
    ↓
Gap 4 (Temporal Dynamics)     ← Operational utility: predict recovery
```

Each gap produces artifacts consumed by subsequent gaps. Skipping order risks building on unvalidated foundations.

**Partial Parallelism Note (Gap 1 and Gap 3):**

The strict sequential ordering above is conservative. In practice, Gap 1 has two phases:

- **Phase 1A** — `ClaudeTraceEncoder` development and `GroundTruthRatingFramework` setup:
  Depends only on Gap 5 canonical labels. Can begin immediately after Gap 5 completes,
  *in parallel* with Gap 3 validation experiments.

- **Phase 1B** — `TransferValidationSuite` (specifically `test_coherence_correlation_transfer`):
  Depends on `CoherenceSuccessCorrelator.get_correlation()` from Gap 3. Must wait for Gap 3.

Teams with sufficient capacity may start Phase 1A alongside Gap 3 to compress the timeline.
The dependency arrow above reflects Phase 1B's requirement, not Phase 1A.

---

## System Context: What Exists Today

```
                  ┌─────────────────────────────────────────────────────┐
                  │              FLUME (Current State)                   │
                  │                                                     │
                  │  ExperienceEncoder ──────────► 256D vector          │
                  │    [0:12]  12D trajectory (JourneyTracker)          │
                  │    [12:24] 12 scalar metrics                        │
                  │    [24:29] 5 op-type one-hot                        │
                  │    [29:256] 227D SHA-256 hash ◄── THE PROBLEM       │
                  │                                                     │
                  │  ThoughtEncoder ─────────────► 256D vector          │
                  │    Transformer-based, learned, underutilized        │
                  │                                                     │
                  │  FlumeVAETrainer                                    │
                  │    256D → 512D hidden → mu/logvar → z → recon      │
                  │    Loss = MSE + 0.1·KL + 0.05·(mu_mean - 0.5)²    │
                  │                                                     │
                  │  12D Manifold Physics                               │
                  │    LCSP (random weights), BioelectricEngine,        │
                  │    MorphospaceMapper, FlumeNavigator                │
                  │                                                     │
                  │  Monitoring                                         │
                  │    DegradationDetector (0.60 threshold)             │
                  │    ModelQualityClassifier (linear forecasting)      │
                  │    ThermodynamicMetrics (entropy, free energy)      │
                  │    TopologicalPersistence (H0, H1)                  │
                  └─────────────────────────────────────────────────────┘
```

### Critical Issues in Current State

1. **88% of 256D input is SHA-256 noise** — VAE spends capacity reconstructing pseudorandom bytes
2. **Three incompatible 12D label sets** — JourneyTracker, UniverseBridge, SurrealMCP use different names
3. **LCSP uses random weights** — predictor has never learned from data
4. **No coherence-success validation** — the 0.60 degradation threshold is a guess
5. **No LLM-derived training data** — all trajectories come from simulation agents
6. **HIHO theory untested** — the prediction that 0.5 is optimal has never been empirically verified

---

## Architecture: New Components

### Component Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NEW COMPONENTS BY GAP                            │
│                                                                         │
│  GAP 5: INTERPRETABILITY (Foundation)                                   │
│  ├── CanonicalDimensionRegistry     12D label authority + mappings      │
│  ├── SemanticEmbedder               Replace SHA-256 with learned embs  │
│  ├── DimensionProbe                 Linear probes per 12D dimension    │
│  └── LatentTraversalTool            Walk/visualize 256D space          │
│                                                                         │
│  GAP 3: PERFORMANCE VALIDATION (Empirical Anchor)                       │
│  ├── AblationController             Disable control loops for study    │
│  ├── PhiScoreDecomposer             Test component independence        │
│  ├── CoherenceSuccessCorrelator     Paired metric-outcome collection   │
│  └── OperationStratifiedValidator   Per-op-type threshold analysis     │
│                                                                         │
│  GAP 1: LLM GROUNDING (Bridge)                                         │
│  ├── ClaudeTraceEncoder             Observable outputs → 12D/256D     │
│  ├── GroundTruthRatingFramework     Human+auto ratings on traces      │
│  ├── DomainAlignmentTrainer         Train existing alignment MLP      │
│  └── TransferValidationSuite        Cross-domain validation tests     │
│                                                                         │
│  GAP 2: CAUSAL DYNAMICS (Explanatory)                                   │
│  ├── VarianceDecomposer             ANOVA on trajectory variance      │
│  ├── JacobianAnalyzer               d(trajectory)/d(quality metrics)  │
│  ├── CausalAttributionEngine        Failure → specific causal factors │
│  └── InterventionalTestHarness      Controlled input perturbations    │
│                                                                         │
│  GAP 4: TEMPORAL DYNAMICS (Operational)                                 │
│  ├── PerturbationInjector           Controlled perturbation framework │
│  ├── RecoveryCurveAnalyzer          Per-dim recovery timescales       │
│  ├── FreeEnergyLandscapeMonitor     HIHO well depth under load        │
│  ├── InterruptionSimulator          Context-loss recovery measurement │
│  └── RecoveryAwareScheduler         Predict agent readiness           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: End-to-End

```
                    EXECUTION
                       │
            ┌──────────▼──────────┐
            │   JourneyTracker    │  Records 12D trajectory
            │   (existing)        │  Uses CanonicalDimensionRegistry (NEW)
            └──────────┬──────────┘
                       │
          ┌────────────▼────────────┐
          │   ExperienceEncoder     │  Produces 256D vector
          │   (MODIFIED: uses       │  [0:29] structured (unchanged)
          │    SemanticEmbedder     │  [29:256] learned embedding (NEW)
          │    for dims 29:256)     │
          └────────────┬────────────┘
                       │
              ┌────────▼────────┐
              │  FlumeVAETrainer│  Trains on semantically rich 256D
              │  (existing)     │  Now gets meaningful signal in all dims
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ┌───────────┐ ┌──────────┐ ┌──────────────┐
   │ Coherence │ │ Causal   │ │ Temporal     │
   │ Success   │ │ Analysis │ │ Recovery     │
   │ Correlator│ │ Pipeline │ │ Pipeline     │
   │ (Gap 3)   │ │ (Gap 2)  │ │ (Gap 4)     │
   └───────────┘ └──────────┘ └──────────────┘
         │             │             │
         ▼             ▼             ▼
   ┌─────────────────────────────────────┐
   │  Validated Metrics + Causal Model   │
   │  → DegradationDetector (improved)   │
   │  → RecoveryAwareScheduler (new)     │
   │  → SkillRefiner (causal insights)   │
   └─────────────────────────────────────┘
```

---

## File Layout: Where New Code Lives

```
src/cohezion/flume/
├── experience_encoder.py      # MODIFIED: SemanticEmbedder integration
├── semantic_embedder.py       # NEW (Gap 5): Learned embeddings for dims 29:256
├── dimension_registry.py      # NEW (Gap 5): Canonical 12D labels + mappings
├── dimension_probe.py         # NEW (Gap 5): Linear probing classifiers
├── latent_traversal.py        # NEW (Gap 5): Latent space exploration tools
├── claude_trace_encoder.py    # NEW (Gap 1): Claude output → 12D/256D
├── domain_alignment_trainer.py# NEW (Gap 1): Train DomainAlignmentMLP
├── alignment.py               # EXISTING: DomainAlignmentMLP (no changes)
├── autoencoder.py             # EXISTING: ThoughtEncoder (no changes)
├── training.py                # EXISTING: FlumeVAETrainer (no changes)
└── ...

src/cohezion/compound/
├── journey_tracker.py         # MODIFIED: Use CanonicalDimensionRegistry
├── degradation_detector.py    # MODIFIED: Per-op-type thresholds (Gap 3)
├── ablation_controller.py     # NEW (Gap 3): Control loop toggle
├── phi_score_decomposer.py    # NEW (Gap 3): Component analysis
├── coherence_success.py       # NEW (Gap 3): Paired metric-outcome store
├── variance_decomposer.py     # NEW (Gap 2): ANOVA on trajectories
├── jacobian_analyzer.py       # NEW (Gap 2): Sensitivity analysis
├── causal_attribution.py      # NEW (Gap 2): Factor attribution
├── perturbation_injector.py   # NEW (Gap 4): Controlled perturbations
├── recovery_curve_analyzer.py # NEW (Gap 4): Recovery timescale fitting
├── free_energy_monitor.py     # NEW (Gap 4): HIHO well depth tracking
├── interruption_simulator.py  # NEW (Gap 4): Context-loss experiments
├── recovery_scheduler.py      # NEW (Gap 4): Readiness prediction
└── ...

src/cohezion/validation/       # NEW directory
├── __init__.py
├── ground_truth_ratings.py    # NEW (Gap 1): Rating framework
├── transfer_validation.py     # NEW (Gap 1): Cross-domain tests
└── operation_stratified.py    # NEW (Gap 3): Per-op-type analysis

tests/flume/
├── test_semantic_embedder.py       # NEW
├── test_dimension_registry.py      # NEW
├── test_dimension_probe.py         # NEW
├── test_claude_trace_encoder.py    # NEW
└── ...

tests/compound/
├── test_ablation_controller.py     # NEW
├── test_coherence_success.py       # NEW
├── test_variance_decomposer.py     # NEW
├── test_perturbation_injector.py   # NEW
├── test_recovery_curve.py          # NEW
└── ...

tests/validation/
├── test_ground_truth_ratings.py    # NEW
├── test_transfer_validation.py     # NEW
└── ...
```

---

## Interface Contracts

### Cross-Gap Dependencies

| Producer (Gap) | Interface | Consumer (Gap) |
|----------------|-----------|----------------|
| 5 | `CanonicalDimensionRegistry.get_labels() → list[str]` | 1, 2, 3, 4 |
| 5 | `SemanticEmbedder.embed(text) → ndarray(227,)` | 3, 2 |
| 5 | `DimensionProbe.validate(dim_idx, data) → ProbeResult` | 1, 3 |
| 3 | `CoherenceSuccessCorrelator.get_correlation() → CorrelationResult` | 1, 2 |
| 3 | `AblationController.disable(loops) → context_manager` | 2, 4 |
| 3 | `OperationStratifiedValidator.get_thresholds() → dict[str, float]` | 1, 4 |
| 1 | `ClaudeTraceEncoder.encode(trace) → ndarray(256,)` | 2, 4 |
| 1 | `GroundTruthRatingFramework.rate(traces) → list[Rating]` | 2 |
| 2 | `VarianceDecomposer.decompose(trajectories) → VarianceReport` | 4 |
| 2 | `JacobianAnalyzer.compute(trajectory) → ndarray(12, N)` | 4 |
| 4 | `RecoveryAwareScheduler.predict_readiness(agent) → ReadinessState` | Compound Loop |

---

## Shared Data Schemas

### TrajectoryRecord (extended)

```python
@dataclass
class TrajectoryRecord:
    """Single point in a trajectory, used across all gaps."""

    timestamp: float
    agent_id: str
    operation_type: str  # One of OPERATION_TYPES
    trajectory_12d: np.ndarray  # (12,) canonical labels
    metrics: dict[str, float]  # METRIC_KEYS
    task_outcome: TaskOutcome | None  # Gap 3: independent success measure
    claude_trace: ClaudeTrace | None  # Gap 1: raw Claude observables
    causal_context: CausalContext | None  # Gap 2: what caused this point


@dataclass
class TaskOutcome:
    """Independent outcome measure, NOT derived from coherence."""

    test_pass_rate: float | None  # 0.0-1.0 if applicable
    output_quality_rating: float | None  # Human or auto-rated
    task_completed: bool
    error_count: int
    wall_time_seconds: float


@dataclass
class ClaudeTrace:
    """Observable outputs from Claude execution."""

    thinking_text: str | None  # Extended thinking
    tool_calls: list[dict]  # Tool invocations
    output_text: str  # Final output
    model_id: str  # Which Claude model
    input_tokens: int
    output_tokens: int


@dataclass
class CausalContext:
    """Causal factors for a trajectory point."""

    input_features: dict[str, float]  # What went in
    decision_points: list[str]  # Key routing decisions
    active_control_loops: list[str]  # What feedback was active
```

### ExperimentResult (shared across all gaps)

```python
@dataclass
class ExperimentResult:
    """Standard result format for any gap experiment."""

    experiment_id: str
    gap_number: int
    hypothesis: str
    method: str
    data_points: int
    result: dict[str, Any]  # Gap-specific metrics
    conclusion: str  # "supported", "refuted", "inconclusive"
    confidence: float  # 0.0-1.0
    artifacts: list[str]  # Paths to saved data/plots
    timestamp: float
```

---

## Migration Strategy

### Phase 1: Non-Breaking Foundation (Gap 5)

Changes are additive. No existing interfaces break.

1. Add `CanonicalDimensionRegistry` — new file, no existing imports change
2. Add `SemanticEmbedder` — new file, optional integration
3. Modify `ExperienceEncoder.encode()` to accept an optional `embedder` parameter
   - Default behavior unchanged (SHA-256)
   - Pass `SemanticEmbedder` to enable learned embeddings
4. Add probing and traversal tools — purely analytical, no production impact

### Phase 2: Validation Infrastructure (Gap 3)

Adds observability. Production behavior unchanged unless ablation explicitly enabled.

1. `AblationController` wraps existing control loops with toggle switches
2. `CoherenceSuccessCorrelator` is a passive collector — records data, changes nothing
3. `OperationStratifiedValidator` produces recommendations; `DegradationDetector` updated only after validation

### Phase 3: LLM Bridge (Gap 1)

New encoding pathway. Existing simulation pathway unchanged.

1. `ClaudeTraceEncoder` produces 256D vectors in the same space as `ExperienceEncoder`
2. `DomainAlignmentTrainer` trains the existing `DomainAlignmentMLP` on paired data
3. Both encoders remain available; selection is per-data-source

### Phase 4: Causal Analysis (Gap 2)

Purely analytical. No production execution paths change.

1. All components are offline analysis tools
2. Consume trajectory data already recorded by JourneyTracker
3. Output goes to experiment results, not production decision-making (yet)

### Phase 5: Temporal Operations (Gap 4)

First gap to change production behavior.

1. `RecoveryAwareScheduler` integrates into task routing
2. `DegradationDetector` thresholds updated based on Gap 3 findings
3. Only after Gaps 1-3 validate that metrics are meaningful

---

## Success Criteria

| Gap | Minimum Viable Result | Stretch Goal |
|-----|----------------------|--------------|
| 5 | Single canonical 12D label set enforced; probes show ≥3 dims encode claimed semantics | Learned embeddings replace SHA-256 in production |
| 3 | Coherence-success correlation measured; HIHO 0.5 optimality tested | Per-op-type thresholds deployed |
| 1 | 500+ Claude traces encoded; reconstruction quality comparable to simulation | Validated DomainAlignmentMLP bridges distributions |
| 2 | Variance decomposition quantifies op-type vs. semantics vs. quality | Jacobian-based predictive alerts |
| 4 | Per-dimension recovery timescales measured | Recovery-aware scheduling in production |

---

## Detailed Specs

Each gap has its own specification document:

- [Gap 5: Interpretability](gap5-interpretability-spec.md) — Foundation layer
- [Gap 3: Performance Validation](gap3-performance-validation-spec.md) — Empirical anchor
- [Gap 1: LLM Grounding](gap1-llm-grounding-spec.md) — Bridge to reality
- [Gap 2: Causal Dynamics](gap2-causal-dynamics-spec.md) — Explanatory power
- [Gap 4: Temporal Dynamics](gap4-temporal-dynamics-spec.md) — Operational utility
