# FLUME Next Experiments: Concrete Research Steps

**Date**: 2026-02-17
**Source**: Practitioner synthesis from multi-agent gap analysis
**Status**: Actionable experiment proposals

---

## Priority Ordering

The experiments are organized by dependency: foundational work first (interpretability, validation), then grounding and causal analysis, then temporal dynamics. Each experiment specifies what it tests, what infrastructure exists, what needs building, and the expected timeline.

---

## Phase 1: Foundations (Weeks 1-2)

These experiments establish whether we are measuring something real.

### Experiment 1.1: Label Reconciliation Audit

**Gap**: 5 (Interpretability)
**What it tests**: Whether the 12D axiomatic space has a consistent definition across the codebase.
**Infrastructure exists**: All three label sets are in code.
**What to build**: A reconciliation script that extracts and compares dimension names from `journey_tracker.py`, `universe_bridge.py`, `surreal_server.py`, and `engine.py`.
**Deliverable**: A reconciliation table mapping each dimension index to its name in each module. A decision on the canonical label set. A PR that aligns all modules to one naming scheme.
**Effort**: 1 day.
**Why first**: Every other experiment depends on knowing what the dimensions mean.

### Experiment 1.2: Operation-Type Probing on [0:12]

**Gap**: 5 (Interpretability) + 3 (Performance Validation)
**What it tests**: Whether JourneyTracker's modulation profiles create detectable structure in the 12D trajectory.
**Infrastructure exists**: JourneyTracker with modulation profiles, ExperienceCollector for data gathering.
**What to build**: A probing script that collects 1000+ trajectory points across all five operation types and trains a linear classifier (logistic regression) to predict operation type from the 12D vector alone.
**Expected result**: >70% accuracy if modulation profiles work, ~20% (random) if they do not.
**Deliverable**: Classification accuracy, confusion matrix, per-dimension feature importance scores.
**Effort**: 2-3 days.
**Why it matters**: If a linear probe cannot distinguish operation types, the 12D labels are noise.

### Experiment 1.3: Dimension Correlation Analysis

**Gap**: 5 (Interpretability)
**What it tests**: Whether the 12 dimensions are empirically independent (as the distinct labels imply) or highly correlated (suggesting a lower-dimensional effective space).
**Infrastructure exists**: Trajectory data in vault/parquet shards.
**What to build**: Compute the 12x12 empirical correlation matrix across a large corpus of trajectory points. Perform PCA to determine effective dimensionality.
**Expected result**: If effective dimensionality < 6, the 12D space is overparameterized.
**Deliverable**: Correlation matrix heatmap, scree plot, effective dimensionality estimate.
**Effort**: 1 day.

### Experiment 1.4: Coherence-Success Correlation (Observational)

**Gap**: 3 (Performance Validation)
**What it tests**: Whether coherence_score and success_rate show any statistical association in existing data.
**Infrastructure exists**: GlobalMetricsAggregator stores both fields independently. CSV export method exists.
**What to build**: Export metrics to CSV. Compute Spearman rank correlation between coherence_score and success_rate across instances. Stratify by operation type to check for domain-specific relationships.
**Expected result**: Positive correlation if coherence is informative; no correlation if it is a proxy metric.
**Deliverable**: Correlation coefficients (overall and per-operation-type), scatter plots, p-values.
**Effort**: 1 day.
**Caveat**: This is observational only. Confounding by task difficulty and thermostat effects limit causal interpretation.

---

## Phase 2: Validation (Weeks 2-3)

These experiments test whether coherence metrics predict real outcomes.

### Experiment 2.1: Ablation Study (Control Loops Disabled)

**Gap**: 3 (Performance Validation)
**What it tests**: The natural relationship between coherence and task success, without the thermostat effect of retries, model switching, and degradation alerts.
**Infrastructure exists**: CompoundExecutor, DegradationDetector, FeedbackLoop, test suite.
**What to build**: A `ValidationExecutor` wrapper that wraps CompoundExecutor with DegradationDetector and FeedbackLoop disabled. Run the existing test suite through it with seed=42. Record (coherence, binary_success) pairs.
**Analysis**: Logistic regression: P(success) = logistic(beta_0 + beta_1 * coherence). If beta_1 is significantly positive (p < 0.01), coherence has predictive validity independent of control loops.
**Deliverable**: Logistic regression coefficients, ROC curve, AUC score.
**Effort**: 3-4 days.

### Experiment 2.2: Phi Score Decomposition

**Gap**: 3 (Performance Validation)
**What it tests**: Whether the phi score's 0.5/0.3/0.2 weights for coherence/smoothness/convergence are empirically justified.
**What to build**: Regress binary task success on coherence, smoothness, and convergence *separately* (not as the composite phi score). Compare the full model (all three predictors) to coherence-only.
**Expected result**: If smoothness adds no predictive power beyond coherence, the phi score is a noisier version of coherence with decorative coefficients. If all three contribute independently, the composite is justified.
**Analysis**: Nested model comparison using likelihood ratio test. Compute individual beta coefficients and their significance.
**Deliverable**: Model comparison statistics, per-component predictive contribution.
**Effort**: 1-2 days (uses data from Experiment 2.1).

### Experiment 2.3: Smoothness Tautology Test

**Gap**: 3 (Performance Validation) + 5 (Interpretability)
**What it tests**: Whether the mechanical coupling between coherence and smoothness (via `quality_weight = 0.5 * coherence + 0.5 * efficiency` in `_step_to_axiomatic`) creates circular inflation.
**What to build**: Compute smoothness from the raw 2048D hash embeddings *before* quality-weighted modulation (bypassing the blending step). Compare this "raw smoothness" to the current "modulated smoothness."
**Expected result**: If raw smoothness and modulated smoothness correlate highly (r > 0.8), the tautology is mild. If they diverge (r < 0.4), the modulation step is dominating and smoothness is just repackaged coherence.
**Deliverable**: Correlation between raw and modulated smoothness; recommendation on whether to fix the coupling.
**Effort**: 2 days.

---

## Phase 3: Grounding & Causality (Weeks 3-5)

These experiments bridge simulation data to LLM behavior and build causal understanding.

### Experiment 3.1: Causal Variance Decomposition (ANOVA)

**Gap**: 2 (Causal Dynamics)
**What it tests**: What fraction of trajectory variance is explained by operation type vs. task content vs. execution quality.
**Infrastructure exists**: 11K trajectories with operation types and quality metrics.
**What to build**: Partition trajectories by operation type. Compute within-operation and between-operation variance for each of the 12 dimensions. Run one-way ANOVA per dimension.
**Expected result**: If between-operation variance >> within-operation variance, operation type is the dominant causal driver and the hash contribution is noise.
**Deliverable**: ANOVA table per dimension, variance explained (eta-squared) by operation type.
**Effort**: 2 days.

### Experiment 3.2: Interventional Sensitivity (Jacobian Computation)

**Gap**: 2 (Causal Dynamics)
**What it tests**: How sensitive each trajectory dimension is to changes in coherence and efficiency.
**What to build**: For 100 representative task descriptions across all operation types, sweep coherence from 0.0 to 1.0 in 0.1 increments while holding other inputs fixed. Record the 12D trajectory at each point. Compute the partial derivative of each trajectory dimension with respect to coherence.
**Deliverable**: 12x1 Jacobian vector (sensitivity of each dimension to coherence), plotted as a bar chart. Identify which dimensions are causally responsive vs. insensitive.
**Effort**: 2-3 days.

### Experiment 3.3: Cross-Domain Reconstruction Test (LLM Grounding)

**Gap**: 1 (LLM Grounding)
**What it tests**: Whether Claude-derived vectors and simulation-derived vectors occupy the same VAE latent neighborhoods.
**What to build**: Run Claude on 200 tasks matching existing simulation tasks. Construct ExperienceEncoder vectors for Claude executions. Pass both Claude and simulation vectors through the trained VAE encoder. Compare matched-pair cosine similarity vs. random-pair cosine similarity.
**Analysis**: Permutation test (p < 0.01). Cohen's d on cosine similarity difference. Include label-stripped variant (zero out dims [24:29]) to test beyond trivial operation-type matching.
**Deliverable**: Cosine similarity distributions, permutation test results, t-SNE visualization of latent neighborhoods.
**Effort**: 5-7 days (requires Claude API calls for data collection).

### Experiment 3.4: Learned Embedding Replacement

**Gap**: 2 (Causal Dynamics) + 5 (Interpretability)
**What it tests**: Whether replacing SHA-256 fingerprint [29:256] with a learned embedding creates meaningful semantic structure.
**What to build**: Use the existing ThoughtEncoder (or Ollama nomic-embed-text) to generate 227D embeddings for task descriptions. Replace `_sha256_expand()` in ExperienceEncoder with these learned embeddings. Retrain the VAE on the new vectors. Compare latent space structure (clustering, interpolation quality) between hash-based and learned-embedding VAEs.
**Deliverable**: Comparison of VAE reconstruction quality, latent space visualizations, interpolation examples.
**Effort**: 5-7 days.

---

## Phase 4: Temporal Dynamics (Weeks 5-7)

These experiments characterize recovery and robustness.

### Experiment 4.1: Controlled Perturbation Recovery Curves

**Gap**: 4 (Temporal Dynamics)
**What it tests**: Per-dimension recovery timescales and nonlinear regime boundaries.
**What to build**: Initialize agents at HIHO origin. Apply perturbations of varying magnitudes (delta = 0.1, 0.2, 0.3, 0.4) in each dimension independently. Run recovery for 200 steps via BioelectricEngine.simulate_morphogenesis(). Record all 12 dimensions at each step. Fit exponential decay per dimension.
**Expected result**: Dimension-specific tau values; nonlinear slowdown at high perturbation magnitudes.
**Deliverable**: Per-dimension recovery timescale table, recovery curve plots, nonlinearity analysis.
**Effort**: 3-4 days.

### Experiment 4.2: Interruption Simulation

**Gap**: 4 (Temporal Dynamics)
**What it tests**: How many post-interruption operations are needed to restore trajectory quality.
**What to build**: Run 20 sequential compound executions (baseline). Clear JourneyTracker's `_recent_points` buffer (simulates context loss). Resume with 20 more executions. Measure phi score recovery. Vary severity: partial clear (keep last 5 points) vs. total clear.
**Deliverable**: Recovery curves by interruption severity, operations-to-recovery estimates.
**Effort**: 3-4 days.

### Experiment 4.3: Sustained Load Free Energy Evolution

**Gap**: 4 (Temporal Dynamics)
**What it tests**: Whether the HIHO stability well remains deep under sustained operation.
**What to build**: Run 500 consecutive executions with ThermodynamicMetrics active. Track entropy production rate, susceptibility, heat capacity, and HIHO well depth at intervals of 50 executions.
**Expected result**: If well depth decreases monotonically, the system becomes fragile under load. If it remains stable, HIHO is robust.
**Deliverable**: Time series of thermodynamic quantities, well depth evolution plot.
**Effort**: 3-4 days.

---

## Phase 5: Integration (Weeks 7-8)

### Experiment 5.1: ThoughtEncoder Latent Traversals

**Gap**: 5 (Interpretability)
**What it tests**: What semantic concepts the ThoughtEncoder's learned space actually encodes.
**What to build**: Encode a diverse text corpus through ThoughtEncoder. Perform PCA. For top-k principal components, generate traversal sequences (move along each PC, decode at each point). Evaluate decoded texts for systematic semantic variation.
**Deliverable**: Traversal visualizations with decoded text examples, per-PC semantic interpretation.
**Effort**: 5-7 days.

### Experiment 5.2: End-to-End Validation Pipeline

**Gaps**: All
**What it tests**: Whether the complete pipeline (encode -> track -> evaluate -> predict) delivers actionable monitoring for a real compound execution chain.
**What to build**: Run Claude through a complete compound engineering loop (skill -> expand -> plan -> execute -> retrospect -> refine). Track the full 12D trajectory. Apply the validated coherence metric (from Phase 2). Compute causal sensitivity (from Phase 3). Monitor recovery dynamics (from Phase 4). Interpret trajectory using probing results (from Phase 1).
**Deliverable**: A demonstration showing FLUME monitoring a real agentic execution with interpretable, validated, causally grounded metrics.
**Effort**: 7-10 days.

---

## Summary Timeline

| Week | Phase | Key Experiments | Primary Gaps |
|------|-------|----------------|--------------|
| 1 | Foundations | Label audit, probing, correlation | 5, 3 |
| 2 | Foundations + Validation | Coherence-success, ablation study | 3, 5 |
| 3 | Validation | Phi decomposition, tautology test | 3 |
| 3-4 | Grounding & Causality | ANOVA, Jacobian, Claude data collection | 2, 1 |
| 4-5 | Grounding & Causality | Cross-domain test, learned embedding | 1, 2, 5 |
| 5-6 | Temporal | Perturbation recovery, interruption sim | 4 |
| 6-7 | Temporal | Sustained load, free energy evolution | 4 |
| 7-8 | Integration | Traversals, end-to-end validation | All |

---

## Resource Requirements

- **Compute**: All experiments run on local hardware (AMD Ryzen AI MAX+ 395, 128 GiB RAM). No cloud GPU required.
- **Claude API**: Experiment 3.3 requires ~200 Claude API calls for data collection (~$5-10 at current pricing).
- **Ollama**: Experiments using nomic-embed-text require local Ollama instance.
- **Data**: Existing 11K trajectories in vault/parquet. New data generated during experiments.
- **Dependencies**: numpy, scikit-learn, matplotlib for analysis. All available in current environment.
