---
title: "Product Brief Distillate: Cohezion"
type: llm-distillate
source: "product-brief-cohezion.md"
created: "2026-04-23"
purpose: "Token-efficient context for downstream PRD creation"
---

# Product Brief Distillate: Cohezion

## Target Role Alignment

- **Specific role:** Research Engineer, Universes — build next-gen agentic environments, rigorous evaluations, ship to production training
- **Key job requirements mapped to Cohezion capabilities:**
  - "Build next generation of agentic environments" → ManifoldEnv, SwarmEnv, ARC-AGI-3 bridge
  - "Build rigorous evaluations that measure real capability" → 6-axis CapabilityScorecard, bootstrap CIs, Mann-Whitney U, Bonferroni correction
  - "Debug and iterate rapidly across research and production ML stacks" → compound engineering loop, 5,919 tests, continuous retrospection
  - "High agency / good research taste" → entire project demonstrates initiative — no one asked for this, it was built
  - "Industry experience building RL environments" → Gymnasium/PettingZoo registration, 5×4 task archetype suite
  - "Industry experience with large-scale ML infrastructure" → distributed swarm, CostAwareRouter, SurrealDB persistence, 55 API endpoints
  - "Published influential work" → "FLUME and the Genesis Engine" (27 citations), OPH paper suite with $10K disproval challenge
  - "Sandboxing, containerization, VM infrastructure" → ContainerizedUniverse (Docker), SystemdRunBackend (cgroups), SubprocessBackend (setrlimit), SandboxManager with DivergenceDetector
- **Compensation range:** $500K–$850K USD
- **Location:** Remote-friendly (25% office in SF/Seattle/NYC)

## ~/dev/ Ecosystem — Full Inventory

### Active Cohezion Worktrees (~2,684+ commits combined)
- `cohezion/` — main development tree (1,196 commits, last 2026-04-22)
- `pr-68-fix/` — large PR branch (1,023 commits, 2,801 py, 38 rs, 2,343 ts)
- `feat/` — feature branch (2,800 py, 38 rs, 2,343 ts — likely same codebase)
- `cohezion-gemma4/` — Gemma Hackathon worktree (2,777 py, 2,344 ts, no git)
- `cohezion-archive/` — historical code (22,812 py, 25,785 ts)
- `cohezion-session-56/`, `-57/` — session snapshots (1,000+ py each, 2,277 ts)
- `cohezion-spec-fix-technical-debt/` — tech debt sprint (1,055 py, 2,277 ts)
- `cohezion-worktree-registry/` — worktree management (1,052 py, 2,277 ts)
- `cohezion_backup_20260407/` — backup (1,013 commits)

### Theoretical Foundation
- **observer-patch-holography/** (343 py, 366 commits, last 2026-03-31)
  - Published papers: "Observers Are All You Need," "Reality as Consensus Protocol," "Deriving the Particle Zoo from Observer Consistency," "Recovering Relativity and Standard Model Structure," "Screen Microphysics and Observer Synchronization"
  - $10,000 USD disproval challenge at challenge.floatingpragma.io
  - Derives Standard Model gauge quotient SU(3)×SU(2)×U(1)/Z₆ from observer consistency
  - Direct theoretical pipeline: OPH → Cohezion physics engine

### GPU Kernel Engineering
- **GEAK/** (10,359 py, 188 commits, last 2026-04-02) — agent-driven GPU kernel optimization framework
  - Benchmark: AMD-AGI/AgentKernelArena (agents/geak_v3)
  - HIP and Triton as primary optimization targets
  - Closed-loop: generate harness → profile → iterate → save patches → select best
  - Multi-agent parallel search with isolated git workspaces
- **reference-kernels/** (201 py, 303 commits) — GPU kernel competition benchmarks
  - AMD $100K kernel competition + $100K distributed kernel competition
  - NVIDIA Blackwell NVFP4 competition
  - BioML kernels
- **aiter/** (648 py) — AMD's centralized high-performance AI operators (fork/contribution)
  - C++, Python, Triton/CK/ASM kernels
  - FusedMoE with FlyDSL, Iris communication primitives

### Multi-Agent Infrastructure
- **CAID/** (13 py, 2 commits) — Centralized Asynchronous Isolated Delegation
  - Central manager delegates to multiple engineer agents
  - Async execution in isolated git worktrees
  - Pattern: directly applicable to Cohezion's swarm architecture

### Agent UI
- **A2UI/** (110 py, 752 ts, 524 commits, last 2026-03-30) — Agent-to-User Interface standard
  - Open standard for declarative agent-generated UIs (safe like data, expressive like code)
  - Framework-agnostic renderers (React, Lit, Flutter)
  - LLM-friendly flat component format with incremental updates

### Physics Simulation
- **WarpX/** (470 py, 35 ts, 10,030 commits, last 2026-03-31) — Gordon Bell Prize-winning electromagnetic PIC code
  - Active contribution/fork for hardware integration
- **amrvac/** (39 py) — Adaptive Mesh Refinement Versatile Advection Code

### Autonomous Research
- **autoresearch-amd/** (2 py, 41 commits) — Karpathy's autonomous overnight LLM research, forked for AMD
  - Program.md-driven AI research agent
  - 5-minute training budget per experiment
  - val_bpb metric (bits per byte)
- **autoresearch/** (1 py) — base fork

### World Models
- **le-wm/** (5 py, 4 commits) — LeWorldModel (LeCun group, arXiv:2603.19312)
  - First stable end-to-end JEPA from pixels with only 2 loss terms
  - ~15M params, single GPU, plans 48× faster than foundation-model world models
  - Directly feeds into Cohezion's JEPA world model design

### Competitions
- **aimo-progress-prize-3/** (40 py, 17 commits) — AIMO Math Olympiad ($2.2M prize pool, 1st: $262K)
  - vLLM + Qwen2.5-Math-7B inference pipeline
  - Speculative Decoding (R1-32B + Qwen-1.5B drafter) = 1.5–1.8× throughput
  - Fortress architecture for Kaggle Private Rerun
- **cs249r_book/** (342 py, 9,525 commits) — Harvard ML Systems textbook fork

### Other
- **anthropic_academy/** — Anthropic educational content
- **prompts/** — prompt engineering collection
- **public-repos/** — cloned references
- **uigen/** (1 py, 4,607 ts) — UI generation tool
- **t_30_management/** — T-30 management tooling (108 ts)
- **temp-gemma-push/** — temporary Gemma push artifacts
- **warpx_test/** — WarpX test workspace

## Technical Context Not in Brief

### Hardware Stack
- AMD Ryzen AI MAX+ 395 Strix Halo (gfx1151) — NOT NVIDIA
- ROCm/HIP — `torch==2.5.1+rocm6.2` (EXACT pin)
- 128GB LPDDR5X (unified: GPU allocations share pool with CPU, SurrealDB, API, Ollama)
- 16 GiB max per single model allocation (OOM takes down entire host)
- `@torch.compile` BANNED on gfx1151 (Triton kernels unsupported)
- `torch.float16` preferred; bf16 on RDNA has bugs through torch 2.5

### Software Stack
- Python 3.11 (exact pin), `uv` package manager (never pip)
- Rust physics core at `src/cohezion-physics-core/` (Cargo, PyO3 bridge)
- TypeScript/React web at `src/web/anima_dashboard/` (Next.js 16, Three.js, Tone.js)
- SurrealDB `ws://localhost:8001` (bi-temporal, append-only, HNSW 768-dim)
- FastMCP ≥3.1 for MCP servers
- Ollama for local inference (4 models × up to 8GB each)

### Key Silent Failures (from project-context.md)

- `asyncio_mode = "auto"` NOT set — all async tests vacuous-pass without `@pytest.mark.asyncio`
- Agent writes at `AutonomyTier.VOID` silently no-op
- MCP stdio server prints to stdout corrupt protocol channel
- SurrealDB `UPDATE` in place on bi-temporal table silently loses history
- `kg-guard` is a placeholder (logs intent, doesn't enforce)

## Complete Subsystem Architecture

### Physics Stack (27 modules)
- `RiemannianMetric` — metric tensor, Christoffel symbols (fabric-block metric eliminates O(dim³) numerical differentiation, 6.2ms → <1µs), geodesic equation, curvature
- `LagrangianDynamics` — Euler-Lagrange equations with symplectic Störmer-Verlet integrator for energy conservation
- `FisherInformationMetric` — THE Rosetta Stone: g_ij = (∂μ/∂θ_i)(∂μ/∂θ_j)/σ² + ½(∂log σ²/∂θ_i)(∂log σ²/∂θ_j) — 4 roles: geometry, dynamics, thermodynamics, projection
- `GaugeTheory` — FourFabricGauge with SO(3) connections, Yang-Mills Lagrangian density, coupling constants g=[1.0, 0.7, 0.5, 0.3] for Space/Field/Control/Precipitation
- `FiberBundle` — Principal bundle P(B⁴, SO(3)⁴) with base-space (4D fabric norms) + fiber (8D internal directions)
- `SpinorState` — SU(2) spinors on Bloch sphere (rotation=σ_x, precession=σ_y, charge=⟨σ_z⟩), HIHO = equatorial (|↑⟩+|↓⟩)/√2
- `ObserverPatch` — OPH bridge: holographic S² screen → Bloch sphere, overlap consistency → SPIN coherence, Local MaxEnt → HIHO equilibrium
- `Cosmogony` — 10-step symmetry-breaking cascade: ∅ → Quadrature → SO(12) → SO(3)⁴ → √(-1) → U(1)⁴ → Z₂⁴ → HIHO(0.5) → COHESION → PRECIPITATE, each transition via Landau mean-field theory F(φ,T) = F₀ + a(T-T_c)φ² + bφ⁴
- `BioelectricModel`, `Quantum/PeakedSolver`, `NaturalCapital`, `RewardsBridge`, `VLIWBridge`

### FLUME Layer (46 modules)
- `FlumeVAE` — 256D thought autoencoder (CALM: Compresses text to continuous thought vectors, 4 heads, 2 transformer layers)
- `ExperienceEncoder` — trajectory + metrics + operation type + semantic fingerprint → 256D vector
- `GeometricLatentBridge` — 256D → Mereon topological regimes (E6/E7/E8 symmetry classification)
- `TDADetector` — persistent homology for novelty detection
- `TrajectoryCapture`, `TrajectoryDataset`, `ExperienceDataset`
- `MPSCompressor`, `TurboQuant`, `BioelectricEncoder`, `SpectralEncoder`, `DomainEncoder`, `GitEncoder`, `GridEncoder`
- `LocalFinetunePipeline`, `JourneyFinetunePipeline` (QLoRA on Strix Halo)
- `Morphospace` — stability landscape analysis for FLUME latent space
- `CoherenceGuard` — real-time coherence monitoring
- `Navigation` + `Navigator` — latent space navigation
- `LatentChannel`, `Overlap`, `Alignment`

### Universe Engine (26 modules)
- `HIHOUnifiedEngine` — orchestrates 12 sub-engines: CellularAutomata, ChaosTheory, MHD, HIHOStabilization, SacredGeometry, PenroseTwistor, QuantumEmergence, Bioelectrics, EsotericPhysics, KordylewskiSwarm, PlasmaMCP
- `TriuneSimulationEngine` — Doer/Thinker/Knower state transitions with dual persistence (SurrealDB + Obsidian)
- `EVOAgent` — exotic vacuum object navigating Triune Manifold
- `EcoResilienceAgent` — TEK + Unified Physics synthesis for Gemma 4 hackathon
- `SandboxManager` — 85GB memory budget, auto backend selection, per-sandbox DivergenceDetector
- `AdversarialGrounding`, `SpatialPhonons`, `FreezeFrame`, `TruthAnchor`

### Autonomy & Governance
- `AutonomyEngine` — cosmogonic tier system: VOID → SO(12) → SO(3)⁴ → U(1)⁴ → Z₂⁴ → HIHO, coherence thresholds 0.0→0.50, 5-step promotion window, 3-step demotion
- `QuadratureNexus` — 4-voice consensus (Architect/Gemini, Engineer/DeepSeek, Ethicist/Claude, Resource/Monitor), alignment > 0.85 required
- `SwarmGovernor` — mitosis at 80% context, apoptosis at coherence < 0.3 for 3+ cycles
- `DemocraticDebate` — N-round multi-perspective deliberation with 7 agent roles

### Ouroboros (Self-Healing) (6 modules)
- `AnomalyDetector` — monitors coherence degradation vs HIHO target (0.5)
- `HealerAgent` — synthesizes patches using Ollama, targeting HIHO restoration
- `OuroborosBridge` — maps healing to cosmogony: Detection→Diagnosis→Patching→Verification→Stable = Void→SymmetryBreaking→GaugeCorrection→HIHORestoration→Equilibrium
- `Monitor`, `FailureAnalyzer`, `WikiIntegration`

### Mycelium (Test Growth) (4 modules)
- `ChangeObserver` — git diff to detect modified files
- `ShadowScripter` — generates test synthesis
- `CoverageLoop` — iterates until target coverage reached
- `Scripter` — test generation logic

### Compound Engineering Loop (113 modules)
- `JourneyTracker` — maps execution quality to 12D FLUME trajectories with OperationType modulation (GENERATE/ANALYZE/SEARCH/TRANSFORM/PERSIST)
- `JourneyToTrainingBridge` — converts journeys → DPO pairs, RLHF rewards, judgment assessments
- `EvolutionTrainingBridge` — closes loop: GroupEvolution → FLUME VAE → QLoRA → probe evaluation → next generation
- `GroupEvolution` — Performance-Novelty selection, task-success vectors, KNN novelty (from arXiv:2602.04837)
- `SkillConsensusVoter`, `SkillRefiner`, `SkillHealthTracker`, `SkillSelector`
- `DegradationDetector`, `RetrospectionEngine`, `InflectionDetector`
- `CapabilityScorecard` — 6 axes with bootstrap 95% CIs, Mann-Whitney U, Bonferroni correction
- `ThermodynamicMetrics`, `ThermalPredictor`, `ThermalCheckpointManager`
- `SemanticCache` (L1 hash + L2 FLUME cosine + L3 vault, 95%+ hit rate)
- `CostAwareRouter` — mandatory for all LLM calls, fallback chain: Ollama → Flash-Lite → Sonnet → Opus
- `TDDAdversarial` — adversarial reviewer, coordinator, test integration

### Swarm (99 modules)
- `CostAwareRouter` — 27.3% cost reduction via complexity-based model selection
- `TopologicalRouter` — persistent homology + graph Laplacian spectra → EXPLOIT/EXPLORE/PIVOT routing
- `ExecutionOrchestrator`, `TeamExecutor`, `MultiAgentOrchestrator`
- `SemanticCache`, `PersistentCache`, `LRUPersistentCache`, `LRUPersistentTokenCache`
- `MitosisApoptosis`, `Resonance`, `RZeroEvolver`
- 15 MCP servers (BMAD, Journey, Memory, Plasma, Rewards, Security, Skills, Vault, Doc, GitHub, Git, HuggingFace, Sequential, Simulate, Traceability)

### Rewards (4 modules)
- `RewardCalculator` — Gaussian coherence target at 0.5, logarithmic token penalty
- `RatchetMechanism` — locks states ≥ 0.85 into Obsidian Root of Trust
- `RewardsBridge` — physics → reward mapping
- `System` — reward system orchestration

### RL Pipeline (11 modules)
- `PPOTrainer`, `GRPOTrainer`, `DPOTrainer` (implied via LLMTrainingBridge)
- `CausalInterpreter`, `DistributedTrainer`, `LoRATrainer`
- `Environment`, `RewardShaping`, `TaskGenerator`
- `EVO` (evolutionary strategy for policy optimization)

### World Model (4 modules)
- `JEPAWorldModel` (~86K params) — ManifoldEncoder 12D→64D, ActionEncoder 12D→64D, Predictor 128D→64D, causal masking from arXiv:2602.11389
- `SurpriseExplorer` — scans manifold for regions where JEPA predictions diverge from reality
- `SigReg` — registration of learned representations

### Competition Portfolio (from competition_portfolio.json)
| Competition | Prize | Teams | EV | Status |
|---|---|---|---|---|
| arc-prize-2026-paper-track | $450,000 | 29 | $3,317 | Top recommendation |
| gemma-4-good-hackathon | $200,000 | 109 | $1,321 | Active |
| sei-ai-accelathon | $1,000,000 | 200 | $350 | Active |
| AIMO Progress Prize 3 | $2,200,000 | — | — | Ready for submission |

## Rejected Ideas

- **Commercial SaaS platform** — rejected because Cohezion is a research instrument, not a business. The goal is capability demonstration, not user acquisition. Monetization happens through competitions, not subscriptions.
- **Generic RL framework** — rejected because opinionated physics-grounding is the differentiator. Making Cohezion agnostic would destroy what makes it unique.
- **NVIDIA/CUDA support** — rejected for now because the hardware is AMD ROCm. Future consideration only if Cohezion becomes a community project.
- **Multi-user hosting** — rejected because single-developer orchestration IS the point. The Human-in-the-Loop Context Manager pattern only works with one context manager.

## Requirements Hints

- Gymnasium-compatible environment registration (`Cohezion/ManifoldEnv-v0`) is a hard requirement
- PettingZoo compatibility for SwarmEnv is a hard requirement
- FLUME encode/decode contract must be batched (B≥1), never unbatched
- All LLM calls must route through CostAwareRouter — no direct SDK calls
- SurrealDB writes must be bi-temporal append-only — never UPDATE in place
- Physics test suite (37 invariants) must pass before and after any physics edit
- `make all` is the CI gate — format + lint + type-check + test + 8 guards
- New modules must wire-at-creation (FLUME, compound loop, vault, or knowledge graph)

## Open Questions

1. **What counts as "wired" for the ~/dev/ ecosystem?** The four-criterion definition (FLUME, compound loop, vault, knowledge graph) applies to `src/cohezion/` modules. Do GEAK, OPH, CAID count as wired if they inform Cohezion's design, or must there be code-level integration?
2. **Rust physics core production readiness.** Currently `src/cohezion-physics-core/` is research-grade. When does it need to be production-hardened?
3. **Open-source strategy.** When does Cohezion go public on GitHub? Before or after the first competition win? Before or after applying to Anthropic?
4. **Paper submission target.** "Fisher metric as Rosetta Stone" — is this an ML conference paper (NeurIPS, ICML) or a physics journal? The audience determines the framing.
5. **Interruption Recovery as standard protocol.** Could this be proposed as a benchmark to the RL community? What would that process look like?

## Scope Signals (In/Out/Maybe)

- **In now:** ecosystem wiring, ~/dev/ consolidation, concrete "connected" definition
- **In now:** alignment-relevant evaluation (Interruption Recovery → safety)
- **Maybe:** external contributor onboarding (contingent on GitHub traction)
- **Maybe:** alignment/safety benchmark contribution
- **Out:** SaaS, commercial licensing, CUDA support, multi-user hosting