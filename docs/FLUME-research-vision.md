# FLUME Research Vision: Five Gaps Toward a Science of Semantic Reasoning Evaluation

**Authors**: Multi-Agent Research Team (Theorist, Practitioner, Skeptic, Vision Holder, Integrator)
**Date**: 2026-02-17
**Status**: Research Direction Document

---

## Executive Summary

FLUME (Fluid Latent Understanding through Manifold Encoding) compresses semantic reasoning into a 256D latent space, trained on 11K agent trajectories from 25M+ simulation cycles. It achieves MSE 0.1322, KL divergence 0.4329, and mean coherence 0.63 +/- 0.15. These results demonstrate that thought-space encoding is feasible. But five interconnected gaps stand between the current implementation and a rigorous science of semantic reasoning evaluation.

This document presents a structured investigation of each gap, conducted through multi-perspective dialogue among five specialist agents. Each gap section captures what we know, what we need to understand, our uncertainties, why it matters for agentic AI, and how it connects to the other gaps. Together, they form a coherent research program: validate the foundations (Gaps 1, 3, 5), build causal understanding (Gap 2), and characterize temporal robustness (Gap 4).

---

## Gap 1: LLM Grounding

**Challenge**: FLUME works on simulation agents. Does it work on real Claude reasoning?
**Core Question**: What would it mean to encode Claude's semantic reasoning into the same 256D thought-space?

### What We Know

We have two encoding pathways: the ThoughtEncoder (a Transformer that maps text to 256D via learned projection) and the ExperienceEncoder (a deterministic mapping: 12D trajectory + 12 scalar metrics + 5 operation one-hot + 227D SHA-256 fingerprint). The VAE was trained on ExperienceEncoder vectors. A DomainAlignmentMLP exists in `alignment.py` for cross-domain bridging. From Claude, we can observe output text, extended thinking traces, tool use sequences, and execution metrics -- but not internal activations. The existing JourneyTracker already projects observable metrics into 12D trajectory space, and the DegradationDetector monitors coherence thresholds in production.

### What We Need to Understand

Whether a structural homomorphism exists from Claude's observable reasoning traces to FLUME's latent manifold that preserves semantic distances. Specifically: whether the VAE's learned compression separates signal (dims 0:29) from fingerprint noise (dims 29:256) well enough that Claude-derived vectors produce meaningful latent neighborhoods. The test is mutual information in the post-mu_head latent space, with a minimum Cohen's d of 0.5 on matched-vs-random cosine similarity after stripping operation-type labels.

### Our Uncertainties

88% of the 256D input vector is SHA-256 hash expansion with no semantic structure. The HIHO coherence regularization (mu_mean - 0.5)^2 will force any input toward 0.5, making alignment claims potentially tautological. The training data distribution mismatch between simulation agents and LLM reasoning is severe. Most critically: the difference between a merely projective mapping (trivially achievable) and a structurally meaningful mapping (actually useful) may be impossible to establish from observable behavior alone.

### Why It Matters

As Claude takes on more autonomous agentic roles, we need monitoring infrastructure that detects reasoning drift before catastrophic output. FLUME's 12D trajectory space offers richer degradation detection than scalar thresholds -- trajectory smoothness and convergence across compound execution chains could provide early warning of alignment drift. Without grounding, the compound engineering loop optimizes against proxy metrics that may diverge from true reasoning quality.

### How It Connects

Gap 1 is foundational. If the 12D axiomatic dimensions are not validated for LLM reasoning, then Gap 2 (causal dynamics) studies causality in an ungrounded space, Gap 3 (performance validation) validates metrics against the wrong target, Gap 4 (temporal dynamics) characterizes recovery of a proxy signal, and Gap 5 (interpretability) interprets a space that may not mean what we think.

### Research Statement

The LLM Grounding gap reduces to a single empirical question: are FLUME's 12D axiomatic dimensions (novelty, logic, coherence, efficiency, convergence, smoothness, resonance, harmony, and the spatial/temporal/field/precipitation axes) meaningful measures of LLM reasoning quality, or are they artifacts of the simulation environment in which they were developed?

We propose a two-phase research program. Phase 1 validates the 12D ontology independently of the VAE: construct ground-truth ratings for each axiomatic dimension on 500 Claude execution traces across all five operation types, then test whether the dimensions correlate with downstream task quality and whether they provide richer degradation signals than scalar metrics alone. Phase 2, contingent on Phase 1 success, addresses the full 256D encoding: collect paired data (Claude and simulation agents on equivalent tasks), train the DomainAlignmentMLP to bridge distribution gaps, and evaluate whether VAE latent space neighborhoods are semantically coherent for Claude-derived vectors after label-stripped alignment.

The critical insight is that the 12D axiomatic space is the load-bearing structure. The 256D VAE is scaffolding. If the 12 dimensions are valid for LLM reasoning, FLUME grounding is an engineering problem. If they are not, it is a fundamental redesign.

---

## Gap 2: Causal Dynamics

**Challenge**: We can measure thought-space trajectories. Can we understand *why* they change?
**Core Question**: What input/decision patterns causally shape agent reasoning?

### What We Know

The trajectory encoding pipeline is fully deterministic and traceable: task_description -> SHA-256 -> 2048D -> chunk-mean -> 12D -> modulation -> final_12D. Three causal pathways exist by design: (1) operation type modulation profiles impose coarse trajectory structure, (2) execution quality (coherence, efficiency) modulates the blend between hash projection and operation profile via `quality_weight = 0.5 * coherence + 0.5 * efficiency`, (3) the LCSP predictor and BioelectricEngine define temporal dynamics via HIHO-constrained state transitions and voltage-driven gradients. The ExperienceEncoder's structured 256D layout provides a representation amenable to causal decomposition. 11K trajectories from 25M+ simulation cycles exist for retrospective analysis.

### What We Need to Understand

What fraction of trajectory variance is causally attributable to operation type versus task semantics versus execution quality? What is the Jacobian of the 12D trajectory with respect to coherence and efficiency -- which dimensions are causally sensitive to execution quality? Can a learned semantic encoder replace the SHA-256 hash to create a continuous causal pathway from task meaning to trajectory position? Can a trained LCSP predictor learn genuine causal dynamics rather than reflecting hardcoded attractors?

### Our Uncertainties

The SHA-256 hash's avalanche effect may have destroyed recoverable causal information about task semantics in existing trajectory data. The 12D axiomatic dimensions are an ontological choice, not a discovery. Causal relationships between these dimensions may be artifacts of our definitions rather than properties of the phenomena. The HIHO attractor dominates trajectory dynamics so strongly that genuine causal variation may be suppressed. We do not yet know whether 12 dimensions preserves causal structure, or whether causal signals exist only in the full 256D space.

### Why It Matters

Without causal understanding, safety mechanisms (DegradationDetector, RequestAlignmentAnalyzer) remain reactive: they detect problems after they occur but cannot predict or prevent them. The compound engineering loop's core value proposition -- that each execution improves future executions -- requires that the RetrospectionEngine identify causal factors in success and failure, not merely correlates. Predictive alignment monitoring (using causal sensitivity matrices to flag anomalous trajectory shifts before execution completes) would be a qualitative advance over post-hoc coherence threshold checking.

### How It Connects

Causal dynamics operate on the manifold. If the manifold geometry is poorly understood (Gap 5), causal pathways through it will be mischaracterized. Performance validation (Gap 3) provides the ground truth against which causal claims can be tested. The 256D-to-12D projection is a causal bottleneck whose information loss connects to interpretability (Gap 5). Temporal dynamics (Gap 4) require causal understanding to distinguish recovery from mere regression to the attractor.

### Research Statement

We can trace every deterministic step from input to trajectory in FLUME's 12D space, yet we cannot explain why one trajectory succeeds where another fails. This is the causal dynamics gap: transparency of mechanism without explanatory power over outcomes.

Three designed-in causal pathways exist -- operation type modulation, execution quality blending, and HIHO-constrained dynamics -- but none was learned from data. The SHA-256 encoding destroys semantic gradients, the axiomatic dimensions reflect ontological choices rather than discovered structure, and the LCSP predictor operates on random weights. Our system has causal architecture without causal content.

We propose a three-phase research program: (A) causal variance decomposition on existing trajectories to quantify what drives trajectory shape, (B) interventional sensitivity analysis to compute the Jacobian of trajectory dimensions with respect to execution quality, and (C) replacement of the hash-based encoder with a learned embedding to create continuous semantic causal pathways.

Success means the DegradationDetector can predict coherence collapse from early trajectory signals, the RetrospectionEngine can attribute failures to specific causal factors, and the compound loop can improve not by correlation but by genuine causal understanding of its own reasoning dynamics.

---

## Gap 3: Performance Validation

**Challenge**: We measure semantic coherence. Does it actually predict task success?
**Core Question**: Is there empirical evidence that coherent reasoning outperforms incoherent reasoning?

### What We Know

FLUME coherence is measured as the overlap between internal_state (test pass rate, code quality, dependency health) and external_alignment (research relevance, security, performance), yielding a mean of 0.63 +/- 0.15. The phi score compounds coherence (0.5), smoothness (0.3), and convergence (0.2) into a single trajectory quality metric. The GlobalMetricsAggregator records coherence and success rate as independent fields per instance and per skill. The DegradationDetector maintains moving-average baselines with the coherence threshold at 0.60 (CRITICAL severity). 3,300+ tests with 99.3% pass rate provide a substantial execution corpus. Topological persistence analysis exists as a coordinate-free alternative to point-wise metrics.

### What We Need to Understand

Whether coherence has predictive validity for task success when measured against outcomes independent of the coherence computation itself. Whether the phi score's component weights (0.5/0.3/0.2) reflect empirical reality or arbitrary design choices. Whether the smoothness component is tautological due to mechanical coupling between coherence and trajectory coordinates in `_step_to_axiomatic`. Whether the HIHO prediction (optimal at coherence ~0.5, not maximum coherence) holds empirically. Whether coherence-success relationships are operation-type-specific, which would invalidate the single 0.60 degradation threshold. Whether control loops create a thermostat effect masking the natural coherence-success relationship.

### Our Uncertainties

The 12D trajectory projections are derived from SHA-256 hash expansion, not learned representations. "Smoothness" in hash-space may have no relationship to semantic smoothness. The relationship between coherence and success may be confounded by task difficulty: hard tasks produce both low coherence and low success. The feedback loops (retry, model switching, degradation alerts) filter observable data: low-coherence executions that succeed may be systematically under-represented. The non-stationarity question: the coherence-success relationship may shift as the system accumulates knowledge through the compound loop.

### Why It Matters

Every autonomous decision in the system depends on metric thresholds: CostAwareRouter allocates models, ModelQualityClassifier triggers warnings, SkillRefiner updates skill definitions, BudgetEnforcer gates spending. If coherence does not correspond to real quality, these decisions are systematically miscalibrated. The compound engineering loop amplifies metric validity or invalidity over time. If coherence is noise, the loop converges toward a system increasingly confident in meaningless quantities -- epistemic corruption that compounds across sessions. The HIHO stability theory makes a specific, falsifiable prediction (optimal at 0.5, not at 1.0) that has never been tested.

### How It Connects

Validation tests whether the HIHO stability theory makes correct predictions, grounding the theoretical framework (connects to all gaps). If hash-derived projections fail validation, it directly motivates replacing them with learned semantic representations (Gap 5). Validated metrics enable confident scaling. The validation study should include topological persistence metrics as a structural alternative to point-wise coherence.

### Research Statement

FLUME's coherence metric (mean 0.63) and its derivative phi score govern every autonomous decision in the compound engineering loop -- from model routing to skill refinement to budget enforcement. Yet no empirical study has established whether these metrics predict task success as measured by independent outcome criteria. Three specific risks demand investigation. First, the smoothness component of phi score is mechanically coupled to coherence through the `_step_to_axiomatic` quality weighting, creating tautological inflation. Second, the system's control loops may create a thermostat effect that masks the natural coherence-success relationship. Third, operation-type-specific modulation profiles mean that "coherence" measures different constructs for different task types, potentially invalidating the single 0.60 degradation threshold. We propose a three-part validation program: (1) ablation studies with control loops disabled to observe natural coherence-outcome relationships, (2) phi score decomposition to test whether smoothness and convergence add predictive power beyond coherence alone, and (3) operation-stratified analysis to determine whether domain-specific thresholds are required. Without this validation, the compound loop risks compounding epistemic corruption rather than genuine learning.

---

## Gap 4: Temporal Dynamics

**Challenge**: Universes cares about agents handling interruptions. Can we measure coherence recovery?
**Core Question**: How do agents' semantic coherence degrade and recover under real operational stress?

### What We Know

FLUME coherence is governed by a nonlinear restoring force toward the HIHO attractor (0.5). The bioelectric engine implements `voltage = (coherence - 0.5) * 2` with velocity damping `magnitude = intensity * (1.0 - |voltage|)`, making recovery slower at extremes. The LCSP predictor adds additional damping: `prediction = 0.5 * prediction + 0.5 * previous_state`. The thermodynamic metrics framework computes entropy production rate, susceptibility, heat capacity, free energy landscape, and HIHO well depth analysis. Topological persistence can detect structural changes in trajectory shape (fragmentation into multiple behavioral modes) that scalar coherence cannot capture. The DegradationDetector monitors coherence with CRITICAL alerts at 0.60 threshold and 60-second cooldown. JourneyTracker records full 12D trajectories with a 20-point sliding window.

### What We Need to Understand

Per-dimension recovery timescales: do all 12 dimensions recover at the same rate? Nonlinear regime characterization: at what perturbation magnitude does recovery cease to be exponential? Free energy landscape under load: does the HIHO well remain deep under sustained operation, or does it flatten? Interruption recovery profiles: how many operations restore trajectory quality after context loss? Topological recovery signatures: does a "recovered" agent return to its original persistence diagram? Cross-agent variation: do agents with different operational histories recover differently?

### Our Uncertainties

Coherence may not correlate with actual task performance quality -- we are studying the dynamics of a proxy variable without validating the proxy (Gap 3). The system lacks true temporal awareness: it tracks ordered sequences of operations, not wall-clock time. "Recovery" may be nothing more than regression to a hardcoded attractor. The 20-point sliding window may be too small for long-horizon dynamics and too large for rapid perturbation detection. Phase transition detection via susceptibility scanning may be artifactual.

### Why It Matters

Temporal robustness is the difference between a laboratory demonstration and a deployed system. Characterizing recovery dynamics enables: recovery-aware task scheduling (assign easy tasks during recovery), predictive interruption management (estimate time-to-readiness), proactive degradation prevention (detect pre-critical states), agent fitness assessment (which agents handle stress better), and informed checkpoint/rollback decisions.

### How It Connects

Recovery trajectories trace paths through the 12D manifold, revealing geometric anisotropy and stability well shapes (Gap 5). Phase transitions under sustained load are emergent phenomena requiring causal understanding (Gap 2). Mutual information decay at increasing lag measures how quickly the agent "forgets" (Gap 2). If recovery rates vary across agents in multi-agent settings, task routing must account for individual readiness.

### Research Statement

FLUME agents operate in a 12D axiomatic space with a designed attractor at coherence 0.5 (HIHO), stabilized by bioelectric negative feedback and LCSP prediction damping. While mean-reversion toward HIHO is structurally guaranteed, the temporal dynamics of that reversion -- its characteristic timescale, its dependence on perturbation magnitude and direction, its variation across the 12 dimensions, and its behavior under sustained operational load -- remain uncharacterized.

We propose a three-phase empirical investigation: (1) controlled perturbation experiments measuring per-dimension recovery timescales and nonlinear regime boundaries, (2) interruption simulation measuring context-loss recovery as a function of preserved state, and (3) sustained load studies measuring free energy landscape evolution, entropy production trends, and topological trajectory stability over hundreds of operations.

The existing thermodynamic metrics, topological persistence, and degradation detection modules provide the measurement infrastructure. The gap is experimental, not theoretical. The deliverable is a calibrated recovery model enabling recovery-aware task scheduling: predicting when a perturbed agent will be ready for specific operation types, moving FLUME from a system that guarantees eventual stability to one that guarantees predictable stability with known timescales.

---

## Gap 5: Interpretability

**Challenge**: 256D thought-space is powerful but opaque. What does it mean?
**Core Question**: What semantic concepts live in the manifold? How do we ground it to language?

### What We Know

FLUME has two distinct 256D representation pathways. The ThoughtEncoder (autoencoder.py) is a genuine learned Transformer-based text encoder producing 256D latent vectors; standard interpretability methods (probing, traversals, CAVs, disentanglement metrics) are applicable. The ExperienceEncoder (experience_encoder.py) is a deterministic, hand-designed mapping where 227 of 256 dimensions are SHA-256 hash expansions -- semantically opaque.

The 12D axiomatic space has three incompatible label sets across the codebase: `journey_tracker.py` uses {novelty, logic, field, spatial, temporal, precipitation, coherence, efficiency, convergence, smoothness, resonance, harmony}; `universe_bridge.py` uses {spatial_x, spatial_y, spatial_z, physics, biology, field, logic, quantum, control, temporal, novelty, precipitation}; `surreal_server.py` uses {x, y, z, time, mass, sentiment, complexity, factuality, connectivity, stability, novelty, precipitation}. The JourneyTracker applies operation-specific modulation profiles creating systematic but unvalidated structure. The VAE trained on ExperienceEncoder outputs is dominated by hash noise reconstruction.

### What We Need to Understand

Whether the ThoughtEncoder's learned 256D space has discoverable semantic structure. Whether the ExperienceEncoder's [0:29] dimensions carry interpretable signal when hash noise is removed. Which 12D label set is canonical and whether dimensions encode what labels claim. Whether the VAE has learned meaningful latent structure or spent capacity modeling pseudorandom noise. How the ThoughtEncoder and ExperienceEncoder spaces relate.

### Our Uncertainties

We do not know whether the ThoughtEncoder has been trained on sufficient data for genuine semantic structure. The LCSP predictor's randomly-initialized weights may corrupt trajectory structure. "Semantic arithmetic" (interpolate, semantic_add) may not produce coherent results. We suspect but cannot prove the VAE's hash reconstruction is semantically meaningless. The relationship between 12D morphospace and 12D within the 256D vector is unclear.

### Why It Matters

If compound AI agents reason by navigating a thought-space, understanding what regions, trajectories, and directions mean is a prerequisite for meaningful human oversight. An uninterpretable manifold is an unauditable reasoning process. The three-way label inconsistency is not documentation debt -- it is a semantic integrity failure where data flows through wrong conceptual channels. The skill refinement loop depends on trajectory analysis; if trajectories are uninterpretable, refinement optimizes noise.

### How It Connects

Interpretability of the 12D space directly addresses whether axiomatic dimension labels are grounded (Gap 1). The ManifoldManager's domain-specific warps are only useful if the base manifold has interpretable structure (Gap 2). The ExperienceEncoder's hash fingerprint problem means training data quality is downstream of representation design (Gap 3). Until the 256D encoding scheme is fixed, more training data does not help.

### Research Statement

FLUME's interpretability challenge is bifurcated by its dual-pathway architecture. The ThoughtEncoder (Transformer-based autoencoder) produces genuinely learned 256D representations amenable to standard interpretability methods: probing classifiers, latent traversals, and disentanglement metrics. The ExperienceEncoder, however, fills 88% of its dimensions (227/256) with SHA-256 hash expansions that are deterministic but semantically opaque, meaning the VAE trained on these vectors likely devotes most capacity to reconstructing pseudorandom noise rather than learning semantic structure.

The immediate research priorities are: (1) canonicalize the 12D dimension labels, resolving three incompatible naming schemes across modules; (2) replace the [29:256] hash fingerprint with a learned embedding to give the VAE interpretable training signal; (3) run probing experiments on the [0:29] dimensions to validate whether operation-type modulation profiles create the semantic structure their labels promise; and (4) perform latent traversals on a trained ThoughtEncoder to discover what semantic concepts it actually encodes, independent of human-assigned dimension names.

---

## Connecting Narrative: How the Five Gaps Form One Research Vision

The five gaps are not independent problems -- they are facets of a single question: **Can we build a rigorous, empirically grounded science of semantic reasoning evaluation for autonomous AI agents?**

The gaps form a dependency structure. **Interpretability (Gap 5)** is the foundation: until we know what the 256D/12D spaces actually encode, every other analysis operates on potentially meaningless coordinates. The three-way label inconsistency and the hash-dominated encoding scheme are not minor issues -- they determine whether FLUME's "thought-space" is a genuine semantic manifold or a numerical projection dressed in aspirational labels.

**Performance Validation (Gap 3)** is the empirical anchor. The HIHO stability theory, the phi score formula, and every degradation threshold are hypotheses, not axioms. Validating them against independent outcome measures -- with control loops disabled to remove thermostat effects -- determines whether FLUME measures something real. If coherence predicts success, the entire framework is credible. If it does not, we need fundamental redesign before proceeding.

**LLM Grounding (Gap 1)** is the bridge from simulation to reality. FLUME's value depends on whether its evaluation framework transfers from controlled simulation agents to production LLMs like Claude. The 12D axiomatic dimensions may be universal properties of reasoning or artifacts of the simulation environment. This is an empirical question that Gap 1's validation experiments will answer.

**Causal Dynamics (Gap 2)** transforms FLUME from a descriptive tool to an explanatory one. Knowing that coherence dropped is less useful than knowing *why* it dropped. The three-phase causal program (variance decomposition, interventional sensitivity, learned semantic encoding) builds the explanatory power needed for proactive safety monitoring rather than reactive alerting.

**Temporal Dynamics (Gap 4)** is where theory meets deployment. Agents in the real world face interruptions, sustained load, and perturbations. Characterizing recovery dynamics -- per-dimension timescales, nonlinear regime boundaries, free energy landscape evolution -- transforms FLUME from a static evaluator into a dynamic monitoring system that can predict when agents are ready for specific tasks.

The research program has a natural sequencing: resolve interpretability and validate performance first (establishing that we are measuring something real), then ground in LLM behavior (establishing generality), then build causal understanding (establishing explanatory power), then characterize temporal dynamics (establishing operational utility). Each phase delivers value independently but compounds with the others.

---

## Why This Matters for Agentic AI

The fundamental challenge of agentic AI is not capability -- it is trustworthy autonomy. As AI agents take on more complex, longer-horizon tasks with real-world consequences, we need evaluation frameworks that go beyond outcome measurement to reasoning process evaluation.

Current approaches to agent evaluation focus on task completion: did the agent solve the problem? This is necessary but insufficient. Two agents can produce the same correct output through radically different reasoning processes -- one through careful, coherent analysis and another through lucky guessing. The second agent is a deployment risk that outcome metrics cannot detect.

FLUME's thought-space approach offers something different: a continuous manifold where the *process* of reasoning, not just its *product*, can be observed, measured, and monitored. If the five gaps are resolved, we gain the ability to:

1. **Detect reasoning drift in real-time** -- not waiting for a catastrophic output but observing trajectory deviations that precede failure (Gaps 1, 4)
2. **Explain why agents succeed or fail** -- not just what happened but what input features and decision patterns caused the outcome (Gap 2)
3. **Validate that our metrics track reality** -- ensuring that the compound engineering loop optimizes genuine quality rather than proxy metrics that diverge from truth (Gap 3)
4. **Interpret what agents are "thinking"** -- grounding abstract latent representations in human-comprehensible concepts (Gap 5)
5. **Predict recovery from perturbations** -- knowing when an interrupted agent will be ready for complex tasks again (Gap 4)

This is not about building a specific product. It is about establishing the scientific foundations for evaluating semantic reasoning in autonomous systems. The tools exist -- VAEs, trajectory tracking, thermodynamic analysis, topological persistence, causal inference. The gap is empirical validation and architectural coherence.

FLUME, with its five gaps resolved, would be a prototype for what rigorous agent evaluation could look like: not post-hoc scoring, but real-time, interpretable, causally grounded monitoring of the reasoning process itself. That is what safe agentic AI deployment requires.

---

## Appendix: Key Source Files

| File | Purpose |
|------|---------|
| `src/cohezion/flume/autoencoder.py` | ThoughtEncoder/FlumeEncoder -- learned text-to-256D pathway |
| `src/cohezion/flume/experience_encoder.py` | ExperienceEncoder -- deterministic 256D encoding |
| `src/cohezion/flume/training.py` | FlumeVAETrainer -- VAE training with HIHO regularization |
| `src/cohezion/flume/vae_encoder.py` | FlumeVAEEncoder -- production encoder |
| `src/cohezion/flume/bioelectric.py` | BioelectricEngine -- recovery dynamics via voltage feedback |
| `src/cohezion/flume/lcsp.py` | LCSP predictor -- state transition prediction |
| `src/cohezion/flume/morphospace.py` | MorphospaceMapper -- stability wells, navigation |
| `src/cohezion/flume/navigator.py` | FlumeNavigator -- trajectory prediction |
| `src/cohezion/compound/journey_tracker.py` | JourneyTracker -- 12D trajectory mapping |
| `src/cohezion/compound/degradation_detector.py` | DegradationDetector -- coherence monitoring |
| `src/cohezion/compound/global_metrics_aggregator.py` | Metrics collection and export |
| `src/cohezion/compound/request_alignment_analyzer.py` | Alignment scoring |
| `src/cohezion/compound/thermodynamic_metrics.py` | Free energy, phase transitions |
| `src/cohezion/compound/topological_persistence.py` | Persistent homology analysis |
| `src/cohezion/compound/model_quality_classifier.py` | Coherence forecasting |
| `src/cohezion/universe/engine.py` | AxiomaticState -- Smith's 12-Parameter Reality |
