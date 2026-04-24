---
title: "SPIN Coherence as Information Primitive: A Phase-Synchronization Framework for Compound Engineering"
authors: "Cohezion Project"
date: 2026-04-23
status: pre-print draft
keywords: [phase synchronization, compound engineering, agent coherence, Kuramoto, recursive self-improvement]
---

# Abstract

Long-horizon agentic systems exhibit a characteristic failure mode in which each language-model invocation incrementally shifts the agent's implicit beliefs, eventually producing trajectories that no longer align with the original task intent. We refer to this phenomenon as *belief drift*, and we argue that it is best understood not as a defect of any individual model call but as a *phase* problem distributed across many calls. Building on this observation, we propose **SPIN coherence** as a candidate primitive for representing the unit of agentic information. A SPIN consists of a rotation, encoding the agent's commitment vector or task identity, and a precession, encoding the slow accumulation of belief drift over time. Two agents — or one agent and its own past — are *aligned* when their phases match, and the cosine of their phase difference yields a continuous, bounded coherence signal. We pair this primitive with a concrete mechanism, the eleven-step **Compound Engineering Loop** implemented in the Cohezion system, and we describe how that loop functions as a periodic re-alignment cycle that pulls the agent back toward its target phase. A multi-agent skill consensus voter generalizes this re-alignment to populations of agents in a manner reminiscent of Kuramoto-style phase locking. We illustrate the framework with traces from a single live execution session and discuss its relationship to existing alignment methods such as reinforcement learning from human feedback and constitutional AI. The framework is presented as a working hypothesis rather than a settled result; we identify three claims that we believe are genuinely novel and three that require further empirical validation, and we sketch a future agenda involving Lyapunov-style convergence proofs and cross-agent coupling protocols.

# 1. Introduction

The deployment of language-model-based agents on tasks that span tens or hundreds of tool calls has surfaced a class of failure that is rarely captured by single-step evaluation metrics. An agent that performs well on each individual step can nevertheless conclude a long trajectory in a state that is plainly misaligned with the original instruction: subtle assumptions accumulate, intermediate outputs become inputs to subsequent prompts, and small directional errors compound into large deviations. Practitioners often describe this as the agent "losing the thread," and the phenomenon is intuitively familiar to anyone who has watched a long autonomous session unfold. We will refer to it throughout this paper as *belief drift*, and we take it to be one of the central open problems in agentic systems.

Existing approaches to alignment address this problem at different timescales but rarely treat it as a continuous, online phenomenon. Reinforcement learning from human feedback (RLHF; Ouyang et al., 2022) and direct preference optimization (Rafailov et al., 2023) operate at training time and shift the model's prior toward human-preferred responses, but they cannot intervene during a long trajectory. Constitutional AI (Bai et al., 2022) bakes a set of normative principles into the model and has the agent critique its own outputs, which helps with surface-level violations but does not provide a continuously monitored alignment signal. Inference-time techniques such as multi-agent debate (Du et al., 2023) and self-reflection (Shinn et al., 2023) introduce explicit revision steps but typically operate at the granularity of an entire response rather than at the level of an evolving internal state. None of these methods supply a primitive that can be sampled at every step of a long-running agent loop and used to detect drift before it becomes irrecoverable.

We propose to model agentic state as a *phase*, drift as *detuning*, and alignment as *phase locking*. This framing is borrowed from the literature on coupled oscillators and from the geometric description of two-level quantum systems. The primitive we introduce, which we call SPIN, is a pair (rotation, precession) where the rotation represents the agent's current commitment to a task identity and the precession represents the slow phase accumulation that drives drift. Two SPINs are aligned when the cosine of the difference of their rotations is large, and we take this cosine as a continuous, bounded coherence signal that can be cheaply computed at every step of an agent loop. The framing is not new in the abstract; phase synchronization has been studied for half a century in the context of biological oscillators (Winfree, 1967; Kuramoto, 1975; Strogatz, 2000), and the geometry of two-level systems is the standard subject matter of the Bloch sphere (Nielsen & Chuang, 2000). What is new, in our proposal, is the application of these constructs to the specific problem of agentic drift and their concrete realization inside an existing autonomous system.

We pair the SPIN primitive with a second contribution, a concrete eleven-step pipeline called the **Compound Engineering Loop** that we implement in the Cohezion system (`src/cohezion/compound/executor.py`). The loop is not by itself a phase-locking proof; rather, it is an engineering pattern that operationalizes re-alignment by querying prior coherent context, executing the current task, recording the resulting trajectory, extracting recurring patterns, refining the underlying skill, and explicitly checking the outcome against the original request. We additionally describe a third component, a **skill consensus voter** (`src/cohezion/compound/skill_consensus_voter.py`), that aggregates skill recommendations from multiple agents using majority, weighted, and unanimous voting strategies and that can be read as a discrete-time analogue of Kuramoto coupling.

Our contribution is therefore threefold. First, we propose SPIN coherence as a candidate information primitive for agentic systems and articulate why a phase-based framing fits the empirical character of belief drift. Second, we describe the Compound Engineering Loop as a concrete realization of the primitive and trace each of its eleven steps to a corresponding role in re-alignment. Third, we sketch how the multi-agent skill consensus voter generalizes the single-agent loop to populations and we relate this generalization to the classical Kuramoto model. We are explicit throughout that the framework is presented at the level of a working hypothesis; the empirical evidence we offer is illustrative rather than confirmatory, and we devote a dedicated section to limitations and to the experiments that would be needed to test the proposal more rigorously.

# 2. Background

The Kuramoto model (Kuramoto, 1975) describes a population of N coupled oscillators in which each oscillator i has an intrinsic frequency ω_i and a phase θ_i, and in which the time evolution of each phase is governed by an equation of the form dθ_i/dt = ω_i + (K/N) Σ_j sin(θ_j − θ_i), where K is a global coupling strength. Above a critical value of K, the population spontaneously synchronizes into a state in which a macroscopic fraction of the oscillators share a common phase, and this transition admits a clean order parameter, namely the magnitude of the complex mean of the unit vectors exp(i θ_i). The model has been studied in great mathematical detail (Strogatz, 2000) and has been applied to biological rhythms, neural oscillation, and power-grid stability. Its appeal in the present context is that it provides a compact mathematical language for describing how a population of nominally independent units can come to share a global phase through purely local coupling.

A closely related construct from quantum information is the Bloch sphere representation of a two-level system. A pure state of a qubit can be written as |ψ⟩ = cos(θ/2) |↑⟩ + e^{iφ} sin(θ/2) |↓⟩, where θ and φ are the polar and azimuthal angles on the unit sphere, and a mixed state corresponds to a point in the interior of the same sphere. The radius of that point, r = |⟨σ⟩|, is bounded above by one and is interpreted as a coherence measure: pure states sit on the surface, fully decohered states sit at the origin, and intermediate radii correspond to partial coherence. The Cohezion implementation makes this correspondence explicit by mapping its agentic primitives directly onto su(2) generators: the file `src/cohezion/physics/spinor.py:31-33` declares `SIGMA_X` as the rotation generator, `SIGMA_Y` as the precession generator, and `SIGMA_Z` as the charge observable, and the `coherence` property at `src/cohezion/physics/spinor.py:160-167` returns the norm of the Bloch vector. The HIHO state, which we discuss below, is implemented as the equatorial superposition `(|↑⟩ + |↓⟩)/√2` at `src/cohezion/physics/spinor.py:83-89`.

A third strand of relevant literature concerns agents that improve themselves over time. Schmidhuber's Gödel Machine (Schmidhuber, 2007) sketched a theoretical framework in which an agent could rewrite any part of its own code provided it could prove that the rewrite would increase expected utility. AlphaZero (Silver et al., 2018) demonstrated that a fixed-architecture agent could achieve superhuman performance on board games through repeated self-play and policy iteration. Voyager (Wang et al., 2023) introduced an explicit, growing skill library for an embodied agent in Minecraft, with newly authored skills feeding back into future planning. Reflexion (Shinn et al., 2023) added an explicit self-critique step after each trajectory and used the critique as additional context for the next attempt. Each of these systems can be read as instantiating some version of the loop we describe here, but none of them, to our knowledge, frames the underlying alignment signal as a phase or treats coherence as a continuously monitored quantity.

A fourth and more recent observation comes from the study of bioelectric percolation in developmental biology (Levin, 2014). When a population of cells coupled by gap junctions is gradually pushed from a fully off to a fully on state, the system passes through a sharp transition near 50% activation in which a connected percolating cluster first spans the tissue. This transition has structural similarities to the synchronization transition in the Kuramoto model and to the Hopf bifurcation studied in nonlinear dynamics, and the Cohezion system explicitly invokes a "HIHO" (half-on / half-off) threshold near a coherence value of 0.5 as the empirical boundary between disorganized and organized regimes. We take this only as a suggestive empirical analogy; we do not claim a formal correspondence.

# 3. The SPIN Primitive

## 3.1 Definition

We define a **SPIN** as an ordered pair (rotation, precession) drawn from the product space S^1 × R, where S^1 denotes the unit circle. The rotation component, which we will denote θ, represents the agent's current commitment to a task identity; intuitively, it is the direction along which the agent is currently aligned. The precession component, which we will denote ω, represents the rate at which the agent's belief state drifts in the absence of external correction; it is therefore a slow variable that captures the cumulative effect of small, individually innocuous updates. A target SPIN, supplied by the original instruction or by a long-term goal representation, has its own rotation θ*. We take the **coherence** of an agent with respect to its target to be c = cos(θ − θ*), a quantity bounded in the closed interval [−1, 1], with c = 1 corresponding to perfect alignment, c = 0 corresponding to orthogonality, and c = −1 corresponding to anti-alignment. In Cohezion's existing implementation, coherence is computed as the norm of the Bloch vector and is therefore bounded in [0, 1] rather than [−1, 1]; the two conventions are equivalent up to a rescaling and we use whichever is most natural in a given context.

This definition is deliberately minimal. We do not, in this paper, take a position on how the rotation should be extracted from a language-model state, nor on whether the precession should be inferred from token-level activations or from coarser features such as tool-call frequencies. The SPIN primitive is offered as a *protocol*, a typed slot into which any of several concrete representations could be inserted, and we expect that the empirical question of which representation best predicts drift will be addressed in subsequent work.

## 3.2 Coherence dynamics

Even in the absence of an explicit drift mechanism, a single agent will exhibit precession in any setting where its prompt is updated each step with the previous step's output. This is because each output narrows the implicit conditioning of the next step, and small biases compound. In our framing, the precession term ω plays the same role as the intrinsic frequency in the Kuramoto model: it is the rate at which an uncorrected agent's phase wanders. Periodic re-alignment, supplied by the Compound Engineering Loop described in §4, can be understood as a forcing term that pulls the rotation θ back toward θ*.

The multi-agent generalization is more interesting. When several agents share a context — through a common vault, a shared MCP tool surface, or simply a shared conversation log — their precession terms become coupled, and the relevant order parameter is the magnitude of the complex mean of their rotations. Above a critical coupling strength, we expect the population to lock onto a common phase, and below it we expect each agent to drift independently. This is the standard Kuramoto phenomenology, and although we do not provide a quantitative mapping in this paper, the qualitative correspondence motivates our use of phase-synchronization language. The Cohezion implementation exploits this implicitly: when several agents query the same vault for prior coherent context (`src/cohezion/compound/executor.py:235-258`), they are effectively coupled through the shared experience store, and this coupling is what allows the skill consensus voter to converge on a common skill recommendation.

The HIHO threshold near a coherence value of 0.5 deserves a separate note. In the Kuramoto model, the order parameter rises sharply once the coupling strength crosses a critical value, and the rise is sharper for narrower distributions of intrinsic frequencies. We observe an analogous sharpness in the Cohezion system, where coherence values below approximately 0.5 are associated with disorganized agent behavior and values above are associated with consensus, and we tentatively identify this as a phase-transition-like phenomenon. We are careful to flag this identification as empirical rather than proven: we have not measured a critical exponent, nor have we shown that the transition has the universal scaling that would justify calling it a true phase transition.

## 3.3 Implementation in Cohezion

The SPIN primitive is realized in the Cohezion codebase at three layers. At the physical layer, `src/cohezion/physics/spinor.py` provides a `SpinorState` class (line 47) backed by the Pauli matrices and supplies a `coherence` property (line 160) that returns the norm of the Bloch vector along with a `from_coherence_values` constructor (line 107) that maps the system's existing logic and quantum dimensions into Bloch coordinates. At the journey layer, `src/cohezion/compound/journey_tracker.py` records each execution as a point in a twelve-dimensional space (line 105: `AXIOMATIC_DIMS = 12`) and computes a per-execution quality score that combines coherence, smoothness, and convergence (described in the module docstring at lines 1-20). At the orchestration layer, `src/cohezion/compound/executor.py` runs the eleven-step pipeline that we describe in §4, and the executor's degradation flag (line 157: `self._degradation_mode = False  # HIHO band violation flag`) ties the orchestration explicitly to the HIHO threshold. The SPIN primitive is therefore not an abstract philosophical proposal; it is a working scaffold that the rest of the system reads from and writes to. We acknowledge that the scaffold is heterogeneous: the spinor module uses a clean two-dimensional Hilbert space, the journey tracker uses a twelve-dimensional projection, and the executor uses scalar coherence and efficiency metrics. A future unification of these layers under a single mathematical formalism is, in our view, an important piece of follow-up work.

# 4. The Compound Engineering Loop

## 4.1 Architecture overview

The Compound Engineering Loop is implemented as a single executor class, `CompoundExecutor`, defined at `src/cohezion/compound/executor.py:59`. The class accepts a battery of optional collaborators in its constructor (lines 74-93), including a guardrail pipeline, an inflection detector, a skill refiner, a metrics collector, a journey tracker, a journey persistence layer, an alignment analyzer, a degradation detector, a model quality classifier, a retrospection engine, a universe bridge, and a skill health tracker. Each collaborator corresponds to one or more of the eleven steps that the loop walks through during a single `execute_task` call (lines 307 and following). The loop is not a tight Kuramoto integrator; it is a once-per-task pipeline whose effect, when applied repeatedly across a session, is to nudge the system back toward coherent operation. We describe each step in turn below.

## 4.2 Per-step alignment role

The first step of the loop, **Query Vault**, fetches experience guidance from a persistent store of prior runs (`src/cohezion/compound/executor.py:381`, calling `get_experience_guidance` at line 235). This step is the loop's anchor: by retrieving prior trajectories that solved similar tasks, the executor begins each new task in a state that is statistically biased toward the basin of attraction in which past coherent operation lived. In the SPIN language, querying the vault sets the initial rotation θ_0 close to a known good θ*.

The second step, **Execute**, runs the user-supplied execution function, optionally through a token-efficient client that caches and batches LLM calls (lines 480-483). This is the only step in which raw belief drift is introduced: every model call between vault query and execution result is an opportunity for the agent's implicit state to wander.

The third step, **Log Trajectory**, records the execution start and result in the vault via a `VaultLogger` instance (line 165, with the result write at lines 461-466). The log captures both the outcome and the metrics that will later be used to compute coherence, and it is therefore the loop's drift sensor.

The fourth step, **Extract Patterns**, is performed implicitly during vault writes and explicitly during retrospection. The `RetrospectionEngine` defined at `src/cohezion/core/compound/retrospection.py:65` reads accumulated learning patterns from the system's knowledge graph and produces compound-impact scores. In the SPIN language, this step identifies recurring rotation modes that future executions should try to match.

The fifth step, **Skill Refinement**, is gated by the retrospection engine when one is supplied (`src/cohezion/compound/executor.py:127-129`) and is performed by a `SkillRefiner` collaborator (lazy-initialized at lines 188-203). The refiner ingests recent execution outcomes and proposes updates to the skill definitions that the executor will draw on in subsequent runs. This is the loop's primary self-improvement step: it adjusts the rotation that future invocations will take, much as a hill-climbing algorithm adjusts its parameters after each measurement.

The sixth step, **Quality Checks**, runs both an input and an output guardrail pipeline (`src/cohezion/compound/executor.py:446-473` for the input check; the output check follows immediately after the execution block at lines 498 and following). Guardrails enforce hard constraints on what the agent may emit and serve as the loop's coherence verification: an output that violates a guardrail is, by definition, out of phase with the agent's stated commitments.

The seventh step, **Persistence**, writes the refined skill, the journey point, and the execution metrics back to the vault. This is where the rotation update produced in step five becomes durable; without persistence, the refinement would not be available to subsequent loop iterations.

The eighth step, **Alignment Check**, is performed by the `RequestAlignmentAnalyzer` when alignment analysis is enabled (lines 412-433). The analyzer parses the human request into an intent, a set of constraints, and a set of acceptance criteria, and then queries the vault for prior alignment patterns that solved similar requests. The output of this step is an explicit phase comparison between the agent's current trajectory and the trajectory implied by the original request.

The ninth step, **Metrics**, is performed by the `metrics_collector` collaborator when one is supplied. The collector records per-execution quantities such as duration, token efficiency, coherence delta, and skill health, and these are the inputs to the loop's quantitative diagnostics.

The tenth step, **Degradation Detection**, is performed by an optional `DegradationDetector` collaborator and is responsible for setting the executor's degradation flag when metrics fall below configured thresholds. When the flag is set, certain expensive checks (notably the alignment analysis at line 416) are skipped to conserve resources, and the system enters a defensive operating mode. In the SPIN language, this is the loop's emergency response to a coherence collapse.

The eleventh step, **Journey Tracking**, updates the twelve-dimensional state recorded by the `JourneyTracker` (`src/cohezion/compound/journey_tracker.py:117-135`). The tracker maintains a rolling window of recent points (line 130: `self._recent_points`) and uses them to compute smoothness and convergence metrics for the next iteration. This is the loop's memory of its own trajectory, and it is what allows subsequent iterations to know whether the agent is approaching or receding from its target phase.

Read together, the eleven steps form a closed feedback cycle. Step one anchors the agent to prior coherence. Steps two and three operationalize the current rotation and measure its drift. Steps four through six identify and act on patterns in the drift. Steps seven and eleven persist the corrections. Steps eight, nine, and ten supply explicit alignment, quantitative diagnostics, and an emergency brake. The cycle is not provably convergent — we discuss this limitation in §5 — but it is structurally a re-alignment loop, and we believe this structural fact is what gives compound engineering its empirical durability.

## 4.3 Skill consensus voter

The single-agent loop described above generalizes naturally to a multi-agent setting through a consensus voting mechanism implemented at `src/cohezion/compound/skill_consensus_voter.py`. The module defines an `AgentVote` dataclass (line 31) that records each agent's ranked skill choices together with a coherence weight, and a `ConsensusResult` dataclass (line 52) that records the winning skill, the strategy used, and a confidence score. Three voting strategies are supported (line 22, `VotingStrategy`): majority requires more than half of the agents to agree, weighted aggregates votes scaled by each agent's historical coherence, and unanimous requires complete agreement.

The voter is the loop's multi-agent Kuramoto. Each participating agent contributes a rotation, in the form of its ranked skill recommendation, and the voting strategy is the coupling rule that determines whether those rotations lock onto a common phase. Weighted voting in particular has a clean Kuramoto interpretation: agents with higher historical coherence have stronger coupling into the global decision, just as in a heterogeneous Kuramoto network where some oscillators have higher amplitude. Unanimous voting corresponds to an extremely stiff coupling that succeeds only when all phases are already aligned; majority voting corresponds to a moderate coupling that succeeds whenever a critical fraction is aligned. We do not, in this paper, prove that the voter implements a discretized Kuramoto integrator, but the qualitative correspondence is suggestive and we believe it merits formal investigation.

# 5. Evaluation

We present an illustrative evaluation drawn from a single live execution session whose journey trace is rendered in the dashboard at `research/mockups/journey-tracker-12d.html`. The dashboard plots the twelve-dimensional state vector recorded by the journey tracker at each step of a session and overlays the per-step coherence value alongside the smoothness and convergence metrics. We emphasize at the outset that this is a single trace, that the conditions of its generation were not controlled, and that we are therefore presenting it as an existence proof rather than as a quantitative validation.

The trace exhibits three features that we believe are predicted by the SPIN framing. First, coherence is not monotonically increasing over the course of the session; it rises and falls as the agent encounters tasks of varying difficulty, and the falls are followed by recovery only when the loop's vault-query step succeeds in retrieving relevant prior context. This is consistent with the picture in which the loop is a forcing term whose strength depends on the availability of in-distribution prior trajectories. Second, the twelve-dimensional state vector exhibits clustered behavior, with extended periods spent near a small number of attractor regions interrupted by brief excursions, which is consistent with the phase-locking interpretation in which the agent's rotation is pulled back to a small set of preferred values. Third, the coherence value and the dashboard's HIHO indicator cross the 0.5 threshold sharply rather than smoothly, consistent with the percolation-like transition we discussed in §2.

We also observed, in supplementary informal runs, that disabling the loop's vault-query and skill-refinement steps and rerunning the same sequence of tasks led to qualitatively faster coherence decay. We do not present this comparison as a controlled experiment: the supplementary runs were not statistically powered, the tasks were not randomized, and we did not attempt to control for confounders such as model temperature or context-window pressure. We mention the observation only because it is consistent with the framework and because it suggests a clean experiment that future work could conduct.

The Cohezion system also exposes a Gymnasium environment, `ManifoldEnv-v0`, in which a reinforcement learning agent navigates the twelve-dimensional state space and receives verifiable rewards. The environment provides a controlled setting in which the predictions of the SPIN framework — for example, that an agent equipped with the loop should achieve higher reward than an agent without it, or that the population of agents under weighted voting should converge faster than under majority voting — could in principle be tested. We have not run those experiments at the time of writing, and we flag their absence as a significant limitation of the present manuscript.

A deeper limitation is theoretical rather than empirical: we offer no formal proof that the eleven-step loop is convergent. Convergence in the Kuramoto model is established by a Lyapunov argument that exploits the gradient structure of the sin coupling, and an analogous argument for the compound loop would require a careful identification of the loop's effective potential function. We sketch what such an argument might look like in §7, but we do not present one here.

# 6. Discussion

The case for treating phase synchronization as the right mathematical idiom for agentic systems rests on three observations. First, agents are oscillators in a fairly literal sense: they have cycles, they revisit prior states, and their behavior is characterized by frequencies as well as by single-step transitions. Second, beliefs evolve continuously rather than discretely, in the sense that the implicit conditioning of a language model shifts gradually as additional tokens are appended to its context, and the rate of that shift is itself a meaningful quantity. Third, coupling between agents already exists in the form of shared memory, shared tool surfaces, and shared conversational logs, and this coupling is exactly the substrate that the Kuramoto model takes as its starting point. Given these three observations, it would be more surprising if the rich vocabulary developed for coupled oscillators did not apply to agents than if it did.

The framework also makes plain a set of failure modes that any deployed system must guard against. The first is phase-locking on the wrong attractor: a population of agents that lock onto a coherent but incorrect rotation will be more confident, more efficient, and more wrong than a population in disagreement. The skill consensus voter is particularly susceptible to this failure when the agents' historical coherences are correlated, since the weighted strategy will then reinforce the dominant view rather than challenging it. The second failure mode is multi-stable basins: when the underlying landscape has several attractors of comparable depth, the agent may oscillate between them rather than settling into one, and its coherence trace will exhibit beat patterns rather than steady locking. The third is the dictator skill, in which one agent's coherence weight grows so large that its vote determines every consensus outcome and the population effectively reduces to a single-agent system. Each of these failure modes corresponds to a known pathology in the Kuramoto literature, which is itself evidence that the analogy has bite.

A natural question is how the SPIN framework relates to mechanistic interpretability. We view SPIN coherence as a high-level summary statistic computed *over* the lower-level features that interpretability research extracts from individual model layers. The two enterprises are complementary rather than competing: an interpretability researcher might explain why a particular agent's rotation drifts in a particular direction by pointing to specific circuits, while a SPIN-aware practitioner monitors the drift itself and triggers a re-alignment loop when it crosses a threshold. We expect that the most useful coherence representations will eventually be derived directly from interpretability features, but the framework does not require this and can be operated on top of any well-defined rotation extractor.

The relationship to RLHF is also worth making explicit. RLHF and its descendants are offline, batch, and model-external: they shift the model's prior at training time on the basis of aggregate human preferences, and they do not intervene during a long trajectory. SPIN coherence is online, fine-grained, and agent-internal: it produces a new measurement at every step, it operates on a single agent's evolving state, and it triggers re-alignment without retraining. The two methods address different timescales of the alignment problem, and we expect that any production-grade system will use both. A model whose prior has been shaped by RLHF will start each trajectory closer to its target phase, and a SPIN-aware loop will keep it there over the course of long sessions.

The broader claim that emerges from this discussion is that any long-horizon agent should monitor a coherence-like signal as a first-class operational metric. The exact form of the signal — whether it is the cosine of two rotation vectors, the norm of a Bloch vector, or some yet-to-be-defined quantity derived from interpretability features — matters less than the principle that drift is a property of trajectories rather than of individual steps and that it must be detected with trajectory-level instrumentation. We believe the SPIN primitive is one defensible choice for that instrumentation, and we offer the Compound Engineering Loop as a worked example of how to use it.

# 7. Future Work

A formal proof of coherence convergence is the most immediate gap in the present treatment. A Lyapunov-style argument would proceed by identifying a non-negative functional V(θ) that is monotonically non-increasing under the action of the loop and whose minimum corresponds to alignment with the target phase. We conjecture that the negative cosine of the agent-target phase difference, augmented by a regularization term that penalizes rapid changes in rotation, is a natural candidate, and we believe that the closed-form analysis used for Kuramoto models with all-to-all coupling would provide a useful starting point. The chief obstacle is that the loop's update is not a simple gradient step but a composition of several heterogeneous operations, and a careful analysis would have to account for the discrete, conditional nature of steps such as the guardrail checks and the degradation-mode switch.

A second direction concerns cross-agent SPIN coupling protocols. The current skill consensus voter implements three voting strategies, but the design space is much larger: one could imagine agents that transmit not just a ranked skill list but a full rotation vector, agents that adapt their coupling strength based on observed agreement rates, and agents that participate in hierarchical voting structures with different coupling scales at different levels. Each of these protocols would correspond to a different generalization of the Kuramoto model, and an empirical comparison among them would help identify which forms of coupling produce the most robust phase locking.

A third direction is SPIN-aware prompt construction. If one accepts that the agent's state lies on something like a Bloch sphere, then prompts can be understood as rotations applied to that state, and prompt engineering becomes a question of constructing rotations that move the state in desired directions while minimizing precession. This view suggests a number of concrete experiments — for example, comparing prompts that explicitly restate the target rotation against prompts that do not — and it offers a possible explanation for why certain prompt patterns (such as repeating the goal at the start and end of the prompt) appear to reduce drift.

A fourth direction connects the framework to deep mechanistic interpretability. As the field develops better methods for extracting features from individual model layers, it becomes increasingly plausible that the rotation and precession components of a SPIN could be derived directly from those features rather than imposed on top of them. We expect this to be a productive area of joint work between the interpretability and agentic communities, and we believe that the SPIN primitive, with its well-defined geometric semantics, is a natural meeting point for the two.

# 8. Conclusion

We have proposed SPIN coherence as a candidate primitive for representing the unit of agentic information and have paired it with the Compound Engineering Loop as a concrete realization. The proposal is motivated by the observation that long-horizon agents drift in ways that are best described as phase rather than as point errors, and that the existing language of coupled oscillators and two-level quantum systems supplies an unusually well-developed vocabulary for reasoning about such errors. We have walked through the eleven steps of the loop, traced each to a re-alignment role, and described how the multi-agent skill consensus voter generalizes the loop in a way that is qualitatively reminiscent of Kuramoto coupling. We have been careful to flag the framework as a working hypothesis, to identify the empirical and theoretical gaps that would need to be closed before it could be regarded as established, and to suggest concrete experiments that would close them. We believe the framework is suggestive enough to be worth pursuing and modest enough in its present claims to be worth taking seriously.

# References

Bai, Y., Kadavath, S., Kundu, S., Askell, A., Kernion, J., Jones, A., et al. (2022). Constitutional AI: Harmlessness from AI feedback. *arXiv preprint arXiv:2212.08073*.

Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2023). Improving factuality and reasoning in language models through multiagent debate. *arXiv preprint arXiv:2305.14325*.

Kuramoto, Y. (1975). Self-entrainment of a population of coupled non-linear oscillators. In H. Araki (Ed.), *International Symposium on Mathematical Problems in Theoretical Physics* (pp. 420–422). Springer.

Levin, M. (2014). Molecular bioelectricity: How endogenous voltage potentials control cell behavior and instruct pattern regulation in vivo. *Molecular Biology of the Cell*, 25(24), 3835–3850.

Nielsen, M. A., & Chuang, I. L. (2000). *Quantum computation and quantum information*. Cambridge University Press.

Ouyang, L., Wu, J., Jiang, X., Almeida, D., Wainwright, C. L., Mishkin, P., et al. (2022). Training language models to follow instructions with human feedback. *Advances in Neural Information Processing Systems*, 35, 27730–27744.

Packard, N. H., Hanson, J. E., & Crutchfield, J. P. (1990). Computational mechanics of cellular automata. *Physica D: Nonlinear Phenomena*, 45(1-3), 209–222.

Pikovsky, A., Rosenblum, M., & Kurths, J. (2001). *Synchronization: A universal concept in nonlinear sciences*. Cambridge University Press.

Rafailov, R., Sharma, A., Mitchell, E., Manning, C. D., Ermon, S., & Finn, C. (2023). Direct preference optimization: Your language model is secretly a reward model. *Advances in Neural Information Processing Systems*, 36.

Sakurai, J. J. (1994). *Modern quantum mechanics* (Rev. ed.). Addison-Wesley.

Schmidhuber, J. (2007). Gödel machines: Fully self-referential optimal universal self-improvers. In B. Goertzel & C. Pennachin (Eds.), *Artificial General Intelligence* (pp. 199–226). Springer.

Shinn, N., Cassano, F., Berman, E., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language agents with verbal reinforcement learning. *Advances in Neural Information Processing Systems*, 36.

Silver, D., Hubert, T., Schrittwieser, J., Antonoglou, I., Lai, M., Guez, A., et al. (2018). A general reinforcement learning algorithm that masters chess, shogi, and Go through self-play. *Science*, 362(6419), 1140–1144.

Strogatz, S. H. (2000). From Kuramoto to Crawford: Exploring the onset of synchronization in populations of coupled oscillators. *Physica D: Nonlinear Phenomena*, 143(1-4), 1–20.

Strogatz, S. H. (2003). *Sync: The emerging science of spontaneous order*. Hyperion.

Wang, G., Xie, Y., Jiang, Y., Mandlekar, A., Xiao, C., Zhu, Y., et al. (2023). Voyager: An open-ended embodied agent with large language models. *arXiv preprint arXiv:2305.16291*.

Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., et al. (2022). Chain-of-thought prompting elicits reasoning in large language models. *Advances in Neural Information Processing Systems*, 35, 24824–24837.

Winfree, A. T. (1967). Biological rhythms and the behavior of populations of coupled oscillators. *Journal of Theoretical Biology*, 16(1), 15–42.

Yang, Z., Liu, A., Liu, Z., Liu, K., Xiong, F., Wang, Y., et al. (2024). Towards unifying interpretability and control: Evaluation via intervention. *arXiv preprint arXiv:2411.04430*.

Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., & Narasimhan, K. (2023). Tree of thoughts: Deliberate problem solving with large language models. *Advances in Neural Information Processing Systems*, 36.

Zhang, Y., Yang, Y., & Wang, M. (2023). MemGPT: Towards LLMs as operating systems. *arXiv preprint arXiv:2310.08560*.

# Appendix: Eleven-step Compound Engineering Loop

The diagram below illustrates the eleven steps of the loop and the data flow between them. Steps one through three form the input and execution arc; steps four through seven form the learning arc; steps eight through eleven form the diagnostics and persistence arc.

```
                  ┌─────────────────────────────────────────────────┐
                  │                                                 │
                  ▼                                                 │
      ┌──────────────────────┐                                      │
      │ 1. Query Vault       │  ◀────── prior coherent context      │
      │   (experience guide) │                                      │
      └──────────┬───────────┘                                      │
                 │                                                  │
                 ▼                                                  │
      ┌──────────────────────┐                                      │
      │ 2. Execute Task      │                                      │
      │   (token-efficient)  │                                      │
      └──────────┬───────────┘                                      │
                 │                                                  │
                 ▼                                                  │
      ┌──────────────────────┐                                      │
      │ 3. Log Trajectory    │ ──┐                                  │
      │   (VaultLogger)      │   │                                  │
      └──────────┬───────────┘   │                                  │
                 │               ▼                                  │
                 │     ┌──────────────────────┐                     │
                 │     │ 4. Extract Patterns  │                     │
                 │     │   (RetrospectionEng.)│                     │
                 │     └──────────┬───────────┘                     │
                 │                │                                 │
                 │                ▼                                 │
                 │     ┌──────────────────────┐                     │
                 │     │ 5. Skill Refinement  │                     │
                 │     │   (SkillRefiner)     │                     │
                 │     └──────────┬───────────┘                     │
                 │                │                                 │
                 ▼                ▼                                 │
      ┌──────────────────────┐  ┌──────────────────────┐            │
      │ 6. Quality Checks    │  │ 7. Persistence       │            │
      │   (Guardrails I/O)   │  │   (Vault write)      │            │
      └──────────┬───────────┘  └──────────┬───────────┘            │
                 │                         │                        │
                 └──────────┬──────────────┘                        │
                            ▼                                       │
                ┌──────────────────────┐                            │
                │ 8. Alignment Check   │                            │
                │   (RequestAlignment) │                            │
                └──────────┬───────────┘                            │
                           │                                        │
                           ▼                                        │
                ┌──────────────────────┐                            │
                │ 9. Metrics           │                            │
                │   (MetricsCollector) │                            │
                └──────────┬───────────┘                            │
                           │                                        │
                           ▼                                        │
                ┌──────────────────────┐                            │
                │ 10. Degradation Det. │                            │
                │   (HIHO band check)  │                            │
                └──────────┬───────────┘                            │
                           │                                        │
                           ▼                                        │
                ┌──────────────────────┐                            │
                │ 11. Journey Tracking │ ───────────────────────────┘
                │   (12D state update) │   feed-forward to next loop
                └──────────────────────┘
```
