---
title: "Product Brief: Cohezion"
status: "complete"
created: "2026-04-23"
updated: "2026-04-23"
inputs:
  - _bmad-output/project-context.md
  - docs/application/resume.md
  - docs/application/technical-summary.md
  - src/cohezion/competition/competition_portfolio.json
  - Obsidian vault (cerebellum/cortex/hippocampus architecture)
  - ~/dev/ ecosystem (OPH, GEAK, CAID, WarpX, AITER, le-wm, reference-kernels, A2UI)
---

# Product Brief: Cohezion

## Executive Summary

Cohezion is a physics-grounded environment for training and evaluating agentic AI — a 12D manifold-based universe engine where a single mathematical object, the Fisher information metric, simultaneously defines the environment's geometry, dynamics, thermodynamics, and dimensionality reduction. It produces Gymnasium-compatible RL environments, gauge-coupled multi-agent swarms, a trajectory-to-training pipeline for RLHF and DPO, and a surprise-driven JEPA world model. All built by one person: 2,684 commits, 5,919 tests, 37 conservation invariants, and competition-proven results including a 423× kernel speedup and 36-qubit quantum simulation.

The primary goal is to demonstrate the research engineering capability required to land a **Research Engineer, Universes role at a frontier AGI lab** — where building simulated environments for training and evaluating AI systems is the job description. Cohezion doesn't just prepare for that role; it IS that work. The core proposition layers this proof across three audiences: for **frontier AGI labs**, it's the most direct possible demonstration — a candidate who already built what they're hiring for. For **researchers**, it's an open framework where physics-grounded environments replace ad-hoc reward shaping with principled information geometry. For **competitions**, it's a self-funding engine that turns theoretical depth into prize money. These layers reinforce each other: competition wins validate the physics, the physics attracts researchers, and both prove the capability that opens doors.

The bar for the Universes role is explicit: build novel training environments where models navigate ambiguity, handle interruptions, maintain context over extended interactions, and exercise judgment in open-ended scenarios — with rigorous evaluations that measure real capability. Every component of Cohezion is oriented toward this specification.

## The Problem

Current agentic training environments are built on statistical heuristics, not physics. Reward functions are hand-crafted, environment dynamics are decoupled from representation learning, and evaluation metrics lack principled grounding. This creates three compounding failures:

1. **Reward hacking without physics guardrails.** Agents exploit reward loopholes because there's no conservation law or symplectic integrator constraining what's physically possible. The environment is arbitrary — so the agent learns to be arbitrary too.

2. **Representation-dynamics disconnect.** The latent space where agents "think" and the dynamics that govern how the world "moves" are designed by different people at different times. Changes to the world model don't propagate to the environment geometry. This gap is where most training instabilities originate.

3. **No one has proven a single person can do this.** Building a physics-grounded training environment with real differential geometry, gauge theory, and a complete trajectory-to-training pipeline is supposed to require a team. The absence of this proof is itself the bottleneck — it means frontier labs default to hiring teams that build fragmented systems, not individuals who build unified ones. And without alignment-relevant evaluation, physics-grounded environments remain academic demonstrations — the Interruption Recovery archetype (can an agent maintain context and recover coherence after mid-episode perturbation?) is exactly the kind of safety evaluation that matters.

## The Solution

Cohezion closes all three gaps with one architectural insight: **the Fisher information metric on FLUME VAE's latent space is a Rosetta Stone.** It simultaneously serves as:

- **Riemannian metric** → defines distances on the 12D manifold
- **Kinetic energy** → drives Lagrangian dynamics via Euler-Lagrange equations
- **Thermodynamic metric** → connects to Friston's free energy principle (HIHO reward = active inference)
- **Projection operator** → optimal 256D→12D submanifold via Fisher PCA (not variance PCA)

Changes to the VAE training automatically propagate to environment physics, reward landscape, and dimensionality reduction. The representation is the dynamics. The geometry is the thermodynamics. One object, four roles, zero gaps.

On this foundation, Cohezion wires together a living system — not a toolchain, but an organism:

**The Physics Stack:** 27 modules implementing the complete mathematical apparatus — `RiemannianMetric` (metric tensor, Christoffel symbols, geodesics), `LagrangianDynamics` (Euler-Lagrange equations with symplectic Störmer-Verlet integrator), `FisherInformationMetric` (the Rosetta Stone), `GaugeTheory` (SO(3) connections on four fabrics, Yang-Mills field strength), `FiberBundle` (principal bundle P(B⁴, SO(3)⁴) with base/fiber decomposition), `SpinorState` (SU(2) spinors on Bloch sphere with Fubini-Study metric), `ObserverPatch` (OPH bridge mapping holographic screen → SPIN coherence), `Cosmogony` (10-step symmetry-breaking cascade from ∅ to Reality Precipitates via Landau phase transitions).

**The FLUME Layer:** 46 modules — `FlumeVAE` (256D thought autoencoder, the CALM principle: compress text to continuous thought vectors for interpolation and trajectory prediction), `ExperienceEncoder` (trajectory → 256D latent), `GeometricLatentBridge` (256D → Mereon topological regimes, E6/E7/E8 symmetry classification), `TDA detector` (persistent homology for novelty detection), `TrajectoryCapture`, `MPSCompressor`, `TurboQuant`, `BioelectricEncoder`, `SpectralEncoder`, `DomainEncoder`, `GitEncoder`, `GridEncoder`.

**The Universe Engine:** `HIHOUnifiedEngine` orchestrating 12 sub-engines — CellularAutomata, ChaosTheory, Magnetohydrodynamics, HIHOStabilization, SacredGeometry, PenroseTwistor, QuantumEmergence, Bioelectrics, EsotericPhysics, KordylewskiSwarm, PlasmaMCP + `TriuneSimulationEngine` (Doer/Thinker/Knower state transitions with dual persistence to SurrealDB + Obsidian).

**Agents as Exotic Vacuum Objects:** `EVOAgent` — each agent IS an exotic vacuum object navigating the 12D/512D/2048D Triune Manifold. Internal state: `TriuneState(Doer=12D, Thinker=512D, Knower=2048D)`. Encodes intent through FLUME VAE, projects into the manifold, evolves via RewardCalculator (Gaussian coherence target at 0.5) + RatchetMechanism (locks high-performing states ≥ 0.85 into Root of Trust via Obsidian persistence). `EcoResilienceAgent` extends EVOAgent to synthesize Traditional Ecological Knowledge with Unified Physics.

**Biological Swarm Governance:** `QuadratureNexus` — 4-voice consensus (Architect/Engineer/Ethicist/Resource, mapping to Gemini/DeepSeek/Claude/ResourceMonitor). Action taken only when alignment > 0.85. `SwarmGovernor` manages mitosis (agent splits at 80% context) and apoptosis (agent dies at coherence < 0.3 for 3+ cycles) — stability through mortality. `DemocraticDebate` runs N-round multi-perspective deliberation. `TopologicalRouter` uses persistent homology + graph Laplacian spectra to classify agents into EXPLOIT/EXPLORE/PIVOT regimes.

**The Ouroboros Loop:** Self-healing cycle — `AnomalyDetector` monitors coherence degradation, `HealerAgent` synthesizes patches to restore HIHO equilibrium, `OuroborosBridge` maps healing to cosmogony phases (Detection→Diagnosis→Patching→Verification→Stable = Void→Symmetry Breaking→Gauge Correction→HIHO Restoration→Equilibrium). The system eats its own tail and regenerates.

**The Mycelium Network:** `ChangeObserver` detects modified files via git diff, `ShadowScripter` generates test synthesis, `CoverageLoop` iterates test generation until target coverage. The mycelial network grows tests like fungal hyphae — sensing changes, colonizing new code, ensuring no module remains untested.

**The Compound Engineering Loop:** 113 modules — `JourneyTracker` maps execution quality to 12D FLUME trajectories with operation-aware modulation (GENERATE/ANALYZE/SEARCH/TRANSFORM/PERSIST), `JourneyToTrainingBridge` converts trajectories to DPO preference pairs + RLHF rewards + judgment assessments, `EvolutionTrainingBridge` closes the loop (GroupEvolution → FLUME VAE → QLoRA fine-tuning → probe evaluation → next generation), `GroupEvolution` (Performance-Novelty selection from arXiv:2602.04837), `SkillConsensusVoter`, `DegradationDetector`, `RetrospectionEngine`, `CapabilityScorecard` (6 axes: Coherence Amplitude, Phase Locking, Exotic Charge Lifetime, Orbit Quality, TRIUNE Balance, Recovery Basin Radius).

**Autonomy as Phase Transition:** `AutonomyEngine` maps cosmogonic symmetry groups to agent permission tiers — VOID (∅, no autonomy), SO(12) (observe), SO(3)⁴ (low-risk), U(1)⁴ (medium), Z₂⁴ (high), HIHO (sovereign with kill switch). Agents EARN higher tiers by demonstrating sustained coherence. The attractor IS the safety — physics-grounded governance, not ad-hoc guardrails.

**Sandbox & Isolation:** `SandboxManager` (85GB memory budget, auto backend selection: ContainerizedUniverse/SystemdRunBackend/SubprocessBackend), `DivergenceDetector` per sandbox.

**MCP Server Fleet:** 96 modules — 15 MCP servers (BMAD, Journey, Memory, Plasma, Rewards, Security, Skills, Vault, Doc, GitHub, Git, HuggingFace, Sequential, Simulate, Traceability) with auth, session management, and protocol bridge.

Plus: `ManifoldEnv` + `SwarmEnv` (Gymnasium/PettingZoo), ARC-AGI-3 bridge, `JEPAWorldModel` with `SurpriseExplorer`, `SemanticCache` (L1 hash + L2 cosine + L3 vault, 95%+ hit rate), and the self-funding competition engine targeting $450K+ in active prizes.

## What Makes This Different

1. **Physics-grounded, not heuristic.** Every reward signal, evaluation metric, and dynamics equation traces back to a defined physics interpretation. HIHO coherence at 0.5 is the Brahmagupta zero — the restoring force vanishes at equilibrium, Yang-Mills curvatures go flat, free energy is minimized. This isn't metaphor; it's mathematics.

2. **Manifold unification.** No other platform derives environment, dynamics, reward, and projection from a single mathematical object. The Fisher metric is the moat — it makes the system parsimonious in a way that bolted-together alternatives can't match.

3. **Solo-built at this scale — Human-in-the-Loop Context Manager.** 2,684 commits, 5,919 tests, 37 conservation invariants, 1,068 source files, 7 specialist agents, 55 API endpoints, 160+ extracted learnings — one developer serving as the Human-in-the-Loop Context Manager of AI-developed code. The compound engineering loop, 5,919 tests, retrospection engine, and vault-coupled learning pipeline manage AI-generated output; the human provides context, direction, and quality gate. This isn't a bus-factor risk — it's a demonstration of how one person orchestrates AI engineering velocity while maintaining rigor. The execution velocity is the proof of capability.

4. **Self-funding through competition.** The engine pays for its own development: targeted entries into Arc Prize ($450K), Gemma Hackathon ($200K), and SEI Accelathon ($1M) with expected value of ~$5K across the active portfolio. Theory pays rent.

5. **Cross-domain synthesis as architecture.** The Obsidian vault's neuroanatomical structure (cerebellum → operational patterns, cortex → domain concepts, hippocampus → memory, thalamus → routing, prefrontal → planning) isn't naming convention — it's cognitive architecture that feeds back into agent design. 16 worldview traditions mapped to the cosmogony. TEK ↔ sacred geometry ↔ quantum physics ↔ ML, synthesized into code.

6. **Novel policy architecture.** The TRIUNE network (Knower → Thinker → Doer, 256D → 2048D → 512D → 12D) separates abstract feature extraction, structured reasoning, and action emission in a 3-tier hierarchy — a cognitively-grounded alternative to monolithic policies.

7. **Ecosystem, not monolith.** The `~/dev/` workspace reveals that Cohezion sits at the center of a broader research ecosystem: Observer Patch Holography (published theoretical physics papers deriving Standard Model from observer consistency, with a $10K disproval challenge), GEAK (agent-driven GPU kernel optimization framework benchmarked on AMD-AGI/AgentKernelArena), CAID (multi-agent workflow with asynchronous isolated delegation in git worktrees), active contributions to WarpX (Gordon Bell Prize-winning PIC code) and AITER (AMD's high-performance AI operators), LeWorldModel (LeCun group's JEPA reference implementation), and A2UI (open standard for safe agent-generated UIs). This isn't one project — it's a coherent research program where theory (OPH), infrastructure (GEAK/CAID), and application (Cohezion) reinforce each other.

8. **Agents as exotic vacuum objects.** Each agent in Cohezion IS an exotic vacuum object — a bound state navigating the Triune Manifold with internal structure (12D Doer, 512D Thinker, 2048D Knower), intent encoded through FLUME VAE, evolution governed by reward-ratchet mechanics, and lifecycle managed by biological governance (mitosis under load, apoptosis on decay). This isn't metaphor — the EVOAgent class implements the Shoulders (1991) exotic vacuum object model as a computational agent.

9. **The Ouroboros principle.** Self-healing mapped to cosmogony phases — anomaly detection = void fluctuation, diagnosis = symmetry breaking, patching = gauge field correction, verification = HIHO restoration, stable = manifold equilibrium. The system eats its failures and regenerates from them. The Mycelium network grows test coverage like fungal hyphae, sensing code changes and colonizing new modules.

10. **Autonomy earned through physics.** Agent permission tiers are cosmogonic symmetry groups — VOID → SO(12) → SO(3)⁴ → U(1)⁴ → Z₂⁴ → HIHO — with coherence thresholds from 0.0 to 0.50. The attractor IS the safety. Agents that converge to HIHO earn sovereign execution; agents that drift are demoted. Physics-grounded governance, not guardrails.

## Who This Serves

**Primary: Mike Anderson.** This is a personal research instrument first. Every design decision optimizes for one person's ability to push the frontier faster than a team. The vault, the competition engine, the compound loop — they all serve the question: what can one person build when the math is right?

**Secondary: Frontier AGI lab Universes teams.** The entire system is structured as living proof-of-capability for Research Engineer, Universes roles — specifically targeting teams that build novel training environments for capable and safe agentic AI. Competition wins, published benchmarks, and the coherence of the architecture itself are the application materials. Cohezion IS the portfolio.

**Tertiary: The RL research community.** Researchers who need physics-grounded environments, not toy problems. They find Cohezion through GitHub stars, competition entries, and the paper ("FLUME and the Genesis Engine," 27 citations). They stay because the Fisher metric approach actually works.

## Success Criteria

| Signal | Target | Timeline |
|---|---|---|
| **Frontier AGI lab — Research Engineer, Universes** | Secure the role | 2026 |
| **Published research** | Peer-reviewed paper on Fisher metric as Rosetta Stone + at least 2 benchmark results on the 5×4 archetype suite with bootstrap CIs | 2026 Q3 |
| **Competition income** | ≥$5,000 cumulative from active portfolio (3 aligned competitions) | 2026 |
| **GitHub engagement** | ≥500 stars (proof that researchers care) | 2026 Q4 |
| **Wiring completeness** | Zero orphan modules across all 1,068 source files (connected = participates in FLUME, compound loop, vault, or knowledge graph) | 2026 Q3 |
| **Pushing the limit** | At least one result that surprises the RL community (e.g., emergent gauge-coupled cooperation, HIHO convergence properties) | Ongoing |

## Wiring: What "Connected" Means

The goal of wiring everything together requires a concrete definition. A module is **connected** if it participates in at least one of:

1. **FLUME encode/decode contract** — the module transforms data through the 256D latent representation
2. **Compound engineering loop** — the module is invoked by or produces artifacts for the 11-step compound pipeline (including retrospection and skill refinement)
3. **Vault persistence** — the module's patterns, learnings, or operational data are persisted to the Obsidian vault's cerebellum/cortex structure
4. **Knowledge graph** — the module's state or outputs are tracked via SurrealDB bi-temporal records, neurons, or synapses

A module that touches none of these four is an **orphan** — it exists but isn't wired into the living system. The target: zero orphans.

## Scope

**In — the wired whole:**
- Complete 12D manifold physics stack (FLUME VAE → Fisher metric → Lagrangian dynamics → environments)
- `ManifoldEnv` and `SwarmEnv` as first-class Gymnasium/PettingZoo environments
- LLM Training Bridge (RLHF rewards, DPO pairs, judgment assessments)
- JEPA world model with surprise-driven exploration
- Competition engine (Arc Prize, Gemma, SEI + portfolio management)
- Compound engineering loop with retrospection and skill refinement
- Vault-coupled learning (cerebellum patterns, cortex concepts, learnings pipeline)
- 6-axis CapabilityScorecard with full statistical rigor
- Documentation and paper sufficient for external consumption
- **Ecosystem wiring**: OPH theoretical foundations → Cohezion physics engine; GEAK kernel optimization → compound loop; CAID multi-agent patterns → swarm architecture; WarpX/AITER contributions → hardware integration
- **~/dev/ consolidation**: every project in the development workspace mapped to its role in the Cohezion research program

**Out — for now:**
- Multi-user platform / SaaS — this is a single-developer research instrument, not a product
- Generic RL framework — Cohezion is opinionated (physics-grounded or nothing)
- Real-time 3D visualization as primary output (the Anima dashboard exists but is secondary)
- Commercial licensing — open-source research artifact, not a business

**Maybe:**
- External contributor onboarding (if GitHub traction warrants it)
- Additional competition tracks beyond the current 3 aligned entries
- Rust physics core production hardening (currently research-grade)
- Alignment/safety benchmark contributions (Interruption Recovery as a standard evaluation protocol)

## Vision

Cohezion is never finished — it evolves by looking inward (retrospection, learnings extraction, cosmogony cascade) and outward (competition results, community feedback, new physics). In 2–3 years, it becomes the definitive proof that a single researcher, armed with the right mathematics, can build a physics-grounded agentic universe that rivals team-built alternatives. The Fisher metric is the insight. The execution velocity is the evidence. The competitions are the scoreboard. And the system's own retrospection engine ensures it keeps learning — from every trajectory, every competition, every failure — looking inward at its own coherence and outward at the frontier it's trying to push.

If it succeeds, it doesn't just land a role — it establishes a new paradigm for how agentic training environments should be built: from the math up, not the heuristics down.