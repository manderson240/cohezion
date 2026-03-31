# KEY LEARNINGS

## VLIW & Low-Level Optimization (Learnings 1-11, summarized)

Packet-greedy scheduling + register windowing + SIMD vectorization achieved 423x speedup (349 cycles) on Anthropic's VLIW challenge. Key insights: barrier-locked manifolds prevent temporal instruction leakage; batch processing inside Rust (via rayon) amortizes FFI overhead for 29x speedup over naive 1:1 calls; windowing provides the largest single performance jump after SIMD.

---

## Learnings 12-18: Manifold Physics & Agent Architecture (Compressed)
12D manifold must be grounded in physical substrate (CPU/VRAM/RAM), not purely semantic. VLIW→cognition parallel: 2048D vectors as "instruction packets." Peaked quantum circuits compress to low-rank MPS (Bond 64-256) → 100x throughput. Barrier-locked manifolds ensure hardware cache coherence. Hierarchical agent topology (Scout/Strategist) outperforms monolithic models. Stability through mortality (apoptosis/mitosis) forces HIHO dynamic equilibrium.

## Learnings 19-22: Swarm & Operations (Compressed)
Cognitive specialization > parameters — routed domain experts outperform generic 7B. Never rely on `sudo` for automated recovery (use Ollama API + AMD `/sys` telemetry). Agentic reasoning = state-machine planning with recursive verification, not next-token prediction.

## Learnings 26-30: Performance & Self-Healing (Compressed)
GIL limits autoregressive decoding to ~10Hz — inference loops must move to compiled languages. PyO3+maturin+uv = seamless Rust-Python bridge, but batch inside Rust (rayon 29.1x) not 1:1 FFI calls (0.2x regression). Semantic proprioception: project system state into 12D manifold to detect "Logic Drift" that simple thresholding misses. 3-Beat Actuation Law: require 3 consecutive low-coherence beats before repair — single-point anomalies are noise.

## Learnings 41-95: Infrastructure & Hardware (Compressed)
Key patterns: (1) Filesystem entropy limit at >1M files — use `.archive/` + SurrealDB (L41,81). (2) ZFS: ZVOL swap + arc_max cap at 12.5% RAM (L42-43). (3) Strix Halo: monitor GTT not VRAM, vendor 0x1002 = AMD, GTT ≈ system RAM = UMA (L60,89,91,92). (4) HIHO convergence at 25M cycles: C(t) = 0.5 + A·e^(-kt)·sin(ωt) (L63). (5) Context Guard: novelty-prioritized 20k-char limit (L77). (6) Hermetic: micro-stability → macro-coherence (L78). (7) Connection pooling + circuit breaker prevents cascade (L88). (8) Lazy imports as dependency firewall (L94). (9) End-to-end pipeline: 4-subsystem chain needs 5-stage integration tests (L95).

---

## Phase 1-2 Milestones (2026-02-06, Compressed)
FLUME VAE retrained on real data (11K vectors, MSE 5.9x harder, KL 13.8x richer). RL REINFORCE: 0.991 coherence but environment "too easy." Mass sim→.npy export (8.2s, 61 files). 6 API endpoints (/flume/*, /rl/*), 19 integration tests.

## Learning 96: Agent File Validation as Compound Defense (2026-02-06)
Missing YAML frontmatter in `.claude/agents/*.md` files was only caught by `claude doctor` after the fact. Fix: single Pydantic schema (`validation/agent_schema.py`) shared by pre-commit hook, PostToolUse hook, unit tests, and `/new-agent` scaffolding command. Layered defense = catch at commit time, warn in real-time, scaffold valid by default. Compound engineering: each layer reuses the same schema.

---

## Learnings 97-101: Specialist Pipeline (Compressed)
Weight bridge collapse via matrix multiply for Rust FFI (L97). Ruff hook fights: use type annotation to keep conditional imports (L98). Deterministic mean action for stable mass sim (L99). DemocraticDebate regex extraction + bounds clamping for LLM params (L100). 9-step pipeline with graceful Ollama fallback (L101).

---

## Learnings 102-104: Runaway Files Incident (Compressed)
Autonomous overnight sims generated 8.6M files — IDE froze, git bloated to 50MB. Fix: pre-commit `check-file-count.sh` blocks >1000 untracked, .gitignore all output dirs. Cleanup is never one-pass — budget 2-3 passes. GPU hang pattern: kill -9 + AMDGPU reset.
Total system freeze during concurrent web apps + LLM swarm. Root cause chain: (1) VRAM saturation from unthrottled concurrent model loads, (2) `amdgpu` ring reset failure, (3) kernel coredump stall under resource pressure. Required REISUB recovery. Fix: direct sysfs GPU/VRAM monitoring, aggressive PID kill in RED alert, `tune_system.sh` to disable panic-on-oom, prevention of giant coredumps. Key insight: **VRAM is the bottleneck, not RAM. Swarms must be sacrificial; system integrity is primary.**

### Learning 105: The Untrack & Mine Protocol
Operational procedure invented during ops/hygiene: (1) identify tracked files that shouldn't be, (2) mine them for knowledge before removal, (3) add to .gitignore, (4) `git rm --cached`, (5) verify git status clean. Critical rule: NEVER delete without reading first. This protocol prevented knowledge loss during the 8.6M file cleanup.

### Learning 106: .gitignore Layered Defense Pattern
The .gitignore evolved through 4 iterations across these branches, each adding a new defense layer: (1) output directories (`data/`, `results/`, `renders/`), (2) build artifacts (`assets/`, `*.safetensors`), (3) binary patterns (`*.pt`, `*.pdf`, `*.so`, `*.mp3`), (4) negation rules to protect source (`!src/**/*.py`, `!scripts/**/*.py`). The final pattern: block everything risky at category level, then whitelist specific safe patterns. Order matters — negations must come after the block rule.

### Learning 107: OMEGA Distiller — Skill Extraction from Success Logs
Auto-skill-generation concept: parse "MISSION SUCCESS" logs, strip noise/timestamps/paths, extract the "trick" (specific insight that turned failure into success), generalize into PRIME skill format. Template: domain expertise → key concepts → step-by-step instruction → patterns/antipatterns table. Never hardcode variable names from specific missions.

## Learnings 108-126: Compound Engineering & Autonomic Systems (Compressed)
Key patterns: (1) Temporal dilation factor (0.1-1.0) throttles sims under pressure (L108). (2) Mock at source module, not import site: `patch("cohezion.swarm.compound_client.get_compound_client")` (L110). (3) 4 CI validators as layered defense (L112). (4) Connectivity Squad: `lsof`/`ss` for dynamic truth anchors (L113). (5) Decentralized memory: SurrealDB + Vault = Interface Sovereignty (L115). (6) God object decoupling: extract ML from api/__init__.py (L119). (7) Soft schema `.get()` before Pydantic validation for LLM outputs (L120). (8) `/heal` 6-stage autonomic diagnostics (L121). (9) Integration Theater detection: `assert hasattr(Class, 'field')` (L122). (10) Lazy imports for circular dependency resolution (L123). (11) HIHO consistency: always use shared engine, never inline physics (L124). (12) 5-Essential-Tests pattern: happy, empty, max, error, integration → ship (L126).

---

## Session 59: Dev Environment Recovery (2026-02-20)

### Learning 127: Claude Code Native Install vs npm Conflict Resolution
When `claude update` warns "Running native installation but config install method is 'npm'": (1) remove leftover npm global: `npm -g uninstall @anthropic-ai/claude-code`, (2) re-run `claude update` which self-corrects `installMethod` in `~/.claude.json`. Root cause of lost auto-updates: `"autoUpdates": false` in `~/.claude.json` — fix by setting `true`. For user-scope MCP servers (e.g., context7): use `claude mcp add --scope user --transport stdio name -- command` which writes to `~/.claude.json` under `mcpServers`. Do NOT edit `~/.claude/mcp.json` for Claude Code MCP — that file is Pilot's config and serves a different system. The two files must not be conflated.

### Learning 128: Autonomic MAPE-K Control Loop Bridge
Implemented in Session 60 (2026-03-08). A semantic control loop (Monitor-Analyze-Plan-Execute) successfully bridges reactive hardware monitoring (ResourceMonitor) with proactive healing strategies (ModelSwap, ContextReduction). By decoupling the **Analysis** (interpreting vitals into severity tiers) from the **Planning** (selecting the strategy), the system gains the ability to make hardware-optimized decisions (e.g., AMD-specific memory rebalancing) without hardcoding logic into the monitoring layer.

### Learning 129: Polyglot Dependency Automation (2026-03-08)
Automating security audits across multiple ecosystems requires leveraging native tooling (`uv audit`, `npm audit`) within a fail-safe Bash wrapper (`set -uo pipefail`). Wrapping these commands with `|| true` is critical; otherwise, the presence of a vulnerability causes the tool to return a non-zero exit code, crashing the entire cron job before all ecosystems are scanned. Reports must be saved as Markdown artifacts to allow subsequent ingestion by LLM agents.

---

## Research Synthesis Sessions 61-67 (2026-03-08, summarized)

Key theoretical insights from deep research sprint: Doc-to-LoRA context compression shifts context entropy from token-limit to weight-loading optimization (L130). Self-generated skills often provide zero benefit — curation over generation (L137, arXiv:2602.12670). KV cache compaction achieves 30-50x memory reduction via task-aware pruning (L139/L145). Multi-tier caching: Tier 1 semantic (>95%) + Tier 2 retrieval (>70%) reduces latency from 30s to 0.02s (L144). Viscoelastic control loop (Maxwell relaxation) enables proactive dilation before lockups (L149). Semantic Lagrange Points: L4/L5 stable memory parking at $\mu < 0.0385$ (L150). Gram-Schmidt orthogonalization required for 12D manifold vectors — 2D rotation collapses in high dimensions (L151).

---

## Session 68: Secure-by-Default Substrate & The 360-Degree Autonomic Cycle (2026-03-10)

### Learning 152: The 360-Degree Autonomic Cycle
A complete architectural evolution loop has been achieved within a single 60-minute window: **Sensing (:00) -> Optimization (:15) -> Refinement (:30) -> Manifestation (:35) -> Verification (:40) -> Auditing (:45) -> Scouting (:50) -> Analysis (:55).** This closed loop ensures that the platform is a self-optimizing engine of growth.

### Learning 153: Unified Authentication Middleware
Platform-wide security is best enforced via a centralized middleware layer rather than per-server logic. By injecting `api_key_middleware` into the `aiohttp.Application` of all MCP servers, we establish a consistent security perimeter that rejects all unauthenticated traffic while allowing internal health checks via a shared `MCP_API_KEY`.

### Learning 154: Recursive Path Sanitization (CWD-Bounding)
Path traversal vulnerabilities in multi-agent systems are critically dangerous as agents often have broad filesystem access. The `sanitize_path` utility must be used with a strict `base_dir=Path.cwd()` bound for all tool-exposed file operations (indexing, scanning, reading). This prevents agents (or attackers hijacking them) from escaping the project workspace.

### Learning 155: API Response Redaction (Secret Scrubbing)
Management endpoints that return system status must recursively scrub environment variables. Identifying keys matching `["token", "key", "secret", "password"]` and replacing them with `***REDACTED***` prevents the accidental leakage of high-privilege credentials (e.g., `HF_TOKEN`, `GITHUB_TOKEN`) through administrative APIs.

### Learning 156: CI/CD Prompt Injection Defense (HITL + Isolation)
GitHub Action workflows that grant LLMs write access to the repository are high-value targets. Effective defense requires a multi-layered approach: 1) Explicit `system_instruction` warning the agent about injection, 2) XML-style delimiters (`<USER_INPUT>`) to segregate untrusted metadata from instructions, and 3) Environment variable passing for inputs to prevent shell command injection.

---

## Session 69: MCP Infrastructure Recovery (2026-03-11)

### Learning 157: Syntax-Valid Marimo Templates
When generating Marimo notebooks via f-strings in Python, triple-quoted strings within the template must be meticulously terminated and indented. An extra `'''` at the end of a return block will cause a `SyntaxError` that prevents the entire server from importing. Correct pattern: `return f'''...'''` followed immediately by the next method definition, with no trailing quotes in the module scope.

### Learning 158: AsyncSurreal Migration & Connect Protocol
The `surrealdb-py` library (v0.3.0+) implements a strict separation between synchronous (`Surreal`) and asynchronous (`AsyncSurreal`) clients. Using `Surreal` in an `async with` block or awaiting its `use()` method (which is synchronous in the blocking client) results in a `TypeError`. **Rule**: Always use `AsyncSurreal` for async contexts and MANDATORY call `await db.connect()` before `signin()` or `use()`.

### Learning 159: Doc-Retriever & Memory Consistency
Fixing infrastructure requires a "Sweep Pattern"—identifying all modules sharing a common dependency (e.g., SurrealDB) and verifying they all adhere to the updated protocol. The migration of `doc/indexer.py` and `memory/server.py` to `AsyncSurreal` restored coherence across the "Compound Engineering" and "Physics" server groups.

### Learning 160: Skill Documentation as a Truth Anchor
Skills (e.g., `DATABASE_PRIME.md`) must be updated immediately after a protocol change to prevent agents from re-introducing "Shadow Bugs" by following outdated examples. A skill is only valid if it reflects the current operational reality of the substrate.

---

## Session 72: NVIDIA Nemotron Challenge & Kaggle Infrastructure (2026-03-24, L161-L172 compressed)

Kaggle G4 Blackwell: pin CUDA 12.8 via `docker_image_pinning_type: original`, use `--no-build-isolation` for Mamba, prefer kagglehub over HF, native BF16 > bitsandbytes, target regex `in_proj|out_proj|up_proj|down_proj` for hybrid LoRA, case-sensitive `nvidiaRtxPro6000`, pre-authorize models in `model_sources`, metric uses vLLM with `\boxed{}` extraction, 5 submissions/day cap. Branch: `challenge/nvidia-nemotron-reasoning`.

---

## Session 73: Insights-Driven Enforcement Upgrade (2026-03-25)

### Learning 173: Declarative-to-Procedural Enforcement
Rules in markdown files (CLAUDE.md, workflow-enforcement.md) are suggestions Claude can drift from — 20 "wrong approach" incidents proved this despite strong anti-drift rules. Converting rules to hooks (code that fires automatically) creates a layered enforcement system: drift-detection.sh warns on new src/ files (PreToolUse), test-on-edit.sh runs matching tests after edits (PostToolUse), check-bash-output.sh catches exit-0-with-errors (PostToolUse). Key principle: hooks don't block (always exit 0) but surface information at the moment it's most actionable. Combined with the Drift Escalation Protocol (1st=note, 2nd=STOP, 3rd=ask user), this converts passive advice into active intervention.

### Learning 174: StrategyTracker for Autonomous Pivot Detection
The compound engineering loop (430-cycle autonomous runs) lacked programmatic pivot detection — it could run indefinitely on a plateau. Adding `StrategyTracker` to `RetrospectionEngine` tracks consecutive failures and improvement deltas per skill, emitting "PIVOT RECOMMENDED" when 3+ attempts show <5% improvement. This is the programmatic counterpart to the declarative Strategy Pivot Protocol in systematic-debugging.md. Together they enforce pivots at both the human-readable (rules) and machine-readable (code) levels.

---

## Session 74: Genesis Engine — Grounding Cosmology in Unified Physics (2026-03-26)

### Learning 175: SU(2) Spinor Algebra Replaces Binary SPIN
The ad-hoc `spin_coherence` (binary 1.0 or 0.0) and `charge_polarity = rot_offset + 0.3 * prec_offset` are replaced with proper SU(2) spinor states on the Bloch sphere. Coherence = |Bloch vector|, charge = ⟨σ_z⟩, HIHO state = equatorial (|↑⟩+|↓⟩)/√2. The Pauli commutation relations [σ_i, σ_j] = 2iε_ijk σ_k are verified by 33 tests. Module: `physics/spinor.py`.

### Learning 176: Brahmagupta's Zero IS HIHO
HIHO at 0.5 coherence is Brahmagupta's zero (628 CE) on the deviation scale: δ = coherence - 0.5 = 0. The four rules (a+0=a, a×0=0, a-a=0, 0/0=0) map to void-state operations. This grounds the cosmogony in a 1,400-year-old mathematical insight — zero is not absence, it is the generative equilibrium from which all structure emerges. Module: `physics/cosmogony.py` (ZeroAlgebra class).

### Learning 177: Symmetry Breaking Chain with Landau Theory
The cosmogony ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO follows real Landau phase transition theory: F(φ,T) = a(T-Tc)φ² + bφ⁴ with order parameter φ = √(a(Tc-T)/2b). Five critical temperatures T_c = [100, 10, 1, 0.1, 0.01]. Susceptibility diverges at each T_c. 34 tests verify all identities. Module: `physics/cosmogony.py`.

### Learning 178: Fisher Information Metric = Rosetta Stone
The Fisher metric simultaneously defines: (1) natural geometry of FLUME 256D latent space, (2) Riemannian metric for Lagrangian dynamics, (3) thermodynamic metric (entropy/free energy/heat capacity), (4) optimal 256D→12D projection. For diagonal Gaussian: g_ii = 2/σ². The natural gradient g⁻¹∇L is coordinate-invariant. Module: `physics/information_geometry.py`.

### Learning 179: Lagrangian Dynamics Replace Ad-Hoc Evolution
The `_toward_target()` linear interpolation in engine.py is replaced by Euler-Lagrange equations: g_ij q̈ʲ + Γⁱ_jk q̇ʲ q̇ᵏ = -gⁱʲ ∂V/∂qʲ. Symplectic Störmer-Verlet integrator ensures bounded energy drift (no secular growth). The fabric-block metric g = diag(1.0, 1.0, 1.0, 0.7, 0.7, 0.7, 0.5, 0.5, 0.5, 0.3, 0.3, 0.3) encodes gauge coupling constants. Module: `physics/lagrangian.py`.

### Learning 180: Yang-Mills Gauge Theory for Fabric Curvature
Each fabric carries an SO(3) gauge connection with field strength F = dA + [A,A]. At HIHO, all curvatures vanish (flat connection = vacuum). Yang-Mills energy density L = -Tr(F∧*F)/4g². The covariant Tempic field (gauge-corrected rate of change) replaces Euclidean displacement. Module: `physics/gauge_theory.py`.

### Learning 181: JEPA World Model from Lagrangian Trajectories
A ~86K parameter JEPA (Joint Embedding Predictive Architecture) learns to predict manifold evolution from (state, action, next_state) tuples. Two losses only: next-embedding prediction (MSE) + Gaussian regularizer (KL). Surprise score detects physically implausible transitions. Training data generated from Lagrangian dynamics produces physically plausible trajectories. Module: `world_model/jepa_world_model.py`.

### Learning 182: Vertical-Slice Milestones > Horizontal-Layer Plans
Planning by vertical slices (math + API + UI in each milestone) delivers working demos faster than horizontal layers (all math → all API → all UI). Each milestone has a "Done when" criterion. This session delivered 11 commits of runnable code vs. the alternative of having complete math with no visualization. Captured as skill: `exemplary-deep-planning`.

### Learning 183: Total Artifact Persistence in SurrealDB
Design principle: ALL artifacts (prompts, responses, internal states, model checkpoints, audio, video, simulation runs) stored in SurrealDB. Nothing is ephemeral. 6 new tables: journey_transitions, universe_snapshots, prompt_artifacts, model_artifacts, simulation_artifacts, internal_state_snapshots. Schema: `knowledge_graph/genesis_schema.surql`.

---

## Session 74 Phase 2: Genesis Engine Observatory + Environments (2026-03-26)

### Learning 184: Gymnasium-Compatible Physics Environment
The ManifoldEnv wraps the 12D Riemannian manifold as an OpenAI Gymnasium environment: reset/step/render with 19D observations (12D state + 3D Bloch + 4D fiber), 12D continuous actions, HIHO convergence reward, and Lagrangian dynamics. Registered as `Cohezion/ManifoldEnv-v0`. Any RL framework trains in our physics — this transforms Cohezion from demo to infrastructure. Module: `environments/manifold_env.py`.

### Learning 185: Multi-Agent Gauge Coupling
SwarmEnv extends ManifoldEnv to N agents interacting through gauge field coupling — each agent's deviation from HIHO generates curvature that affects all others. Cooperative reward = 50% individual + 50% collective coherence. Agents coordinate through physics, not explicit communication. Inspired by [2512.08296]. Module: `environments/swarm_env.py`.

### Learning 186: TDA as Optimization Signal, Not Just Visualization
The TopologicalRouter computes persistent homology on agent trajectory clouds and uses H₀ (clusters) and H₁ (loops) to DRIVE task routing: exploit agents get familiar tasks, explore agents get novel tasks, pivot agents (stuck in loops) get strategy changes. Goes beyond the position paper [2505.22467] which only proposed topology-aware MAS. Validated by [2603.06964] showing 9-18% improvement from PH in RL. Module: `swarm/topological_router.py`.

### Learning 187: SurrealDB 3.0 Syntax Changes
SurrealDB 3.0 moved from `FLEXIBLE TYPE object` to `TYPE object FLEXIBLE`, and `NS x DB y` to `USE NS x; USE DB y`. The `surreal-ns`/`surreal-db` headers replace the old `NS`/`DB` headers. View tables with `ORDER BY` are not supported in DEFINE TABLE AS. Port is 8001 (not 8000) on this system.

### Learning 188: Active Inference = HIHO (Friston Connection)
Friston's Free Energy Principle (F = E - TS minimization) is mathematically identical to HIHO (coherence → 0.5). Our `ThermodynamicMetrics.free_energy` IS Friston's variational free energy. The Fisher metric on FLUME DEFINES the natural gradient of F minimization. This connects Cohezion to 20+ years of neuroscience theory.

### Learning 189: 24-Commit Long-Horizon Session
A single Claude Code session delivered 24 commits, 192 tests, ~14,000 lines across 8 physics modules, 2 RL environments, 1 world model, 1 TDA router, 1 persistence layer, 12 frontend components, 4 tutorials, and 1 paper draft — all on an isolated worktree branch. The exemplary-deep-planning skill + vertical-slice milestones enabled this sustained output without drift.

---

## Session 75: Genesis Engine Phase 2 + Ralph Loop (2026-03-27)

### Learning 190: 10-Step Cosmogony Chain Completion
Completed the full cosmogony chain with 4 new steps: Quadrature (phase alignment), Phase (coherence locking), COHESION (gauge field unification), and Precipitate (manifestation from equilibrium). The 10-step chain ∅→Void→Symmetry→Field→Charge→Quadrature→Phase→COHESION→Precipitate→HIHO now mirrors physical cosmology's symmetry breaking cascade with mathematical precision.

### Learning 191: Levin Bioelectric Network Model
Gap junction percolation IS a HIHO phase transition. Bioelectric networks (Levin 2019, 2022) control morphogenesis via local connectivity — when gap junction probability crosses a percolation threshold, global coherence emerges. This maps directly to the HIHO attractor: local agent coupling → global manifold coherence. Module: `world_model/bioelectric_model.py`.

### Learning 192: InVEST Natural Capital — HIHO Proximity IS Habitat Quality
Stanford's InVEST model (Sharp et al., 2020) computes habitat quality from threat proximity. Reinterpreting: HIHO proximity IS habitat quality on the semantic manifold. Agents near equilibrium inhabit high-quality landscape; those far from HIHO are in degraded habitat. This grounds ecological economics in manifold geometry. Module: `world_model/natural_capital.py`.

### Learning 193: Causal-JEPA Upgrade
Causal masking (Nam et al., 2026, arXiv:2602.11389) added to JEPA world model enables 8x faster planning by enforcing temporal causality in predictive embeddings. The masked attention prevents future-leaking in trajectory prediction — critical for physically plausible world models.

### Learning 194: Worldview Explorer — Indigenous Cosmogonies
16 indigenous traditions (Lakota, Maori, Yoruba, Hindu, Norse, Aboriginal, Maya, etc.) mapped to the 10 cosmogony steps. Each tradition provides a unique lens on the same symmetry-breaking cascade. The Explorer enables cross-cultural validation of the mathematical framework — if 16 independent cosmogonies converge on the same phase transition structure, the mathematics is capturing something real. Module: `worldviews/`.

### Learning 195: Ouroboros + Mycelium Wired into Genesis
The Ouroboros bridge (self-referential loop closure) and Mycelium network (distributed information transport) are now first-class Genesis components. Ouroboros ensures the cosmogony chain is cyclic (HIHO → new Void), while Mycelium provides the substrate for bioelectric signal propagation across the agent swarm. Module: `ouroboros/`.

### Learning 196: Agents-as-EVOs Physics Model
Agents modeled as Evolutionary Viable Organisms (EVOs) with fitness landscapes defined by manifold curvature. Evolutionary dynamics (selection, mutation, crossover) operate on manifold coordinates, producing adaptation through geometric optimization rather than arbitrary fitness functions. Module: `world_model/evo_model.py`.

### Learning 197: Ralph Loop — Multi-Model Specialist Orchestration
5 specialist teams with multi-model orchestration executed 10+ commits and 364+ genesis tests in a single session. The Ralph Loop pattern (research → implement → verify → document) scales to parallel specialist teams working on independent vertical slices, then merging via worktree sync. Key: each team owns a complete slice (code + tests + docs), preventing integration theater.

---

## Session 76: Retrospective + Knowledge Architecture (2026-03-27)

### Learning 198: The Three Feedback Loops (Compound Architecture)
The Charter mandates three interlocking feedback loops: Inner (execution: CompoundExecutor → SkillRefiner), Middle (knowledge: retrospect → vault → SurrealDB graph → skill refinement → governance), Outer (coordination: platform specialists → cost routing → cross-session transfer). Only the inner loop partially works. The retrospect command is a text processor, not a compound orchestrator — it never calls `vault_log_decision()`, `SkillRefiner.refine()`, `BidirectionalLinker`, or `JourneyAnalyzer` (949 lines of unused analysis infrastructure). Closing the middle loop is the highest-impact gap.

### Learning 199: 6-Protocol Agent Stack (MCP/A2A/UCP/AP2/A2UI/AG-UI)
Google's Developer Guide (March 2026) identifies 6 complementary protocols: MCP (tool connectivity), A2A (agent discovery/coordination), UCP (commerce), AP2 (payment auth), A2UI (UI composition), AG-UI (event streaming). Cohezion has strong MCP (41+ tools) but zero A2A. The missing A2A layer prevents agents from discovering each other's capabilities and delegating without central orchestration. Agent cards (`.well-known/agent.json`) enable protocol-compliant discovery.

### Learning 200: Graph HIHO — Knowledge Coherence Metric
The knowledge graph needs its own HIHO-like health metric: connectivity coherence (connected/total nodes, target >0.8), link reciprocity (bidirectional paths, target >0.6), freshness (updated in 30 days, target >0.3), orphan ratio (disconnected/total, target <0.1). Weighted average = Graph HIHO (target 0.5±0.15). This grounds graph maintenance in the same mathematical framework as agent coherence.

### Learning 201: Dual-Format Agent Definitions (Agent + PRIME Skill)
Platform specialist agents need both a Claude Code agent definition (`.claude/agents/*.md`) for interactive subagent use AND a matching PRIME skill definition (`src/cohezion/skills/*.md`) for cross-platform + compound loop compatibility. The agent file defines tools/model/permissions; the PRIME skill defines domain knowledge/patterns/anti-patterns. Together they enable the same specialist to operate in Claude Code, Gemini CLI, or any MCP-compatible framework.

### Learning 202: MCP Specialist as Meta-Agent
The MCP layer is the nervous system connecting all agents to tools. Without a specialist who manages server lifecycle, tool schemas, health monitoring, and inter-server data flow, the coordination layer is fragile. The `mcp-health-check.sh` hook (3-service ping at session start) is the embryo; the MCP specialist agent graduates it to an active operational capability. Scope: all servers (cloud-vault-mcp, cohezion-compound, bmad, cohezion-maintenance-mcp), settings management, permission orchestration.

### Learning 203: Intern-S1 SAGE Framework = Expert Domain Lattice
InternLM's Intern-S1 (arxiv 2603.25040) uses the SAGE framework: Foundation→Fusion→Evolution with Grouped Routing and STE gradient estimation across 512 experts. This maps to Cohezion's Expert Domain Lattice (Charter §8) — both route through specialists but maintain general capabilities. Intern-S1-mini (8B, GGUF Q8=8.7GB) runs on Ollama and could replace phi3:mini for scientific reasoning tasks.

### Learning 204: s1 Budget Forcing = Test-Time Compute Without RL
Stanford's s1 paper (arxiv 2501.19393) achieves 57% AIME 2024 (vs o1-preview's 44%) using only 1K training examples + "budget forcing" (append "Wait" tokens to extend reasoning). No RL, no PRM, no special infrastructure — just SFT on Qwen2.5-32B. This is the most practical test-time scaling technique for Cohezion's competitions (AIMO3, Nemotron). Directly implementable with FLUME domain encoder for trajectory capture.

### Learning 205: AIMO3 Three-Pillar Approach (NemoSkills Winner)
AIMO2 winner (Nvidia NemoSkills) used: (1) 540K problems + 3.2M long-reasoning solutions dataset, (2) Tool-Integrated Reasoning (TIR) — code execution interleaved with CoT, (3) GenSelect — train a model to pick the best solution from N candidates, significantly beating majority voting. Score: 34/50 on private leaderboard. AIMO3 has H100 GPUs and harder problems.

### Learning 206: Test-Time Interaction (TTI) > Test-Time Compute (TTC)
Traditional test-time scaling generates long reasoning traces. TTI adds a new dimension: instead of thinking more, *interact more* — explore, backtrack, re-plan with environment feedback. Gemma 3 12B achieves SOTA open-source web agents via TTI. This maps directly to Cohezion's JourneyTracker + surprise explorer: agents don't just think harder, they explore the manifold dynamically.

### Learning 207: Background Agent Permission Isolation
Background agents (spawned via Agent tool with `run_in_background=true`) inherit more restrictive permissions than the main session. The platform-specialist-creator had content prepared for 9 files but Write was consistently denied. Pattern: use background agents for research/generation, execute file writes from main session. This compounds with the existing hook system — hooks may also behave differently for subagents.

### Learning 208: Hidden Multi-Platform Infrastructure (Claude + Gemini + OpenCode)
Cohezion operates across 3 AI platforms simultaneously: `.claude/` (41+ MCP tools, hooks, skills), `.gemini/` (6 MCP servers: skills, research, surreal, swarm, knowledge, bmad), `.opencode/` (113 BMAD commands, provider fallback chains, 4-tier cost routing). `TipOfTheSpearRouter` already implements HOT→WARM→COLD→CLOUD routing and `config/providers.yaml` defines fallback chains. `AGENTS.md` (366 lines) is the cross-platform Rosetta Stone. The platform-coordinator should CONSUME these existing configs, not rebuild them.

### Learning 209: Competition Licensing Conflict (CC BY 4.0 vs MIT-0)
ARC Prize requires CC0/MIT-0 (public domain). AIMO/Nemotron require CC BY 4.0 (attribution). These conflict — CC BY 4.0 disqualifies from ARC ($-2M). Solution: MIT-0 for all (most permissive, accepted everywhere) or dual licensing per competition. Must decide before first AIMO submission.

### Learnings 210-214: AMD Kernel Competition Results (Compressed)
GEMM/MoE/MLA kernel optimization on MI355X hit API ceiling. Key findings: (1) standalone MXFP4 quant at ~24µs is the Python-dispatch floor, leader's 9.7µs needs custom fused kernel; (2) aiter 0.1.11 has 26 MoE functions, only 5 were previously known; (3) GenSelect beats majority voting +8-15% for math (arXiv:2504.16891); (4) V-JEPA 2.1 (2B params, Mar 2026) is the upgrade path for Cohezion's 86K JEPA; (5) fmoe_g1u1_a16 requires bf16 weights, not fp4.

### Learning 215: FLUME-First Principle (2026-03-31)
All new modules MUST encode/decode through FLUME. The `flume_bridge.py` retrofit pattern (build module → add FLUME bridge later) wastes compound value. Start with `encode()` → latent reasoning → `decode()`. Currently only 3 of 10 core systems use FLUME despite 13 encoders being available.

### Learning 216: Concierge Agent Pattern (2026-03-31)
7-source state synthesis (continuations, worktrees, plans, git, SurrealDB, vault, MEMORY.md) + JSONL-based learning eliminates cold starts. Confidence scoring via HIHO threshold: >0.8 suggest, ~0.5 ask, <0.3 fresh start. Routing history persists across sessions.

### Learning 217: Cosmogonic Autonomy Tiers (2026-03-31)
Maps symmetry breaking chain to agent autonomy levels: ∅(none)→SO(12)(observe)→SO(3)⁴(edit)→U(1)⁴(commit)→Z₂⁴(deploy)→HIHO(sovereign with kill switch). Agents earn higher tiers by demonstrating sustained HIHO coherence. Novel governance model grounded in physics.

### Learning 218: OPH Overlap = HIL Mechanism (2026-03-31)
Observer Patch Holography's Axiom 2 (overlap consistency) is the mathematical foundation for human-in-the-loop governance. The human is an observer patch on the same holographic screen as the agent. Where they overlap, they must agree. High overlap → defer to human. Zero overlap → agent is sovereign in its domain.

### Learning 219: Data Mesh × MCP Registry (2026-03-31)
17+ MCP servers = 17 data domains. DataProduct type with schema, SLA, lineage, and ownership turns tools into governed data products. Factory pattern (get_cohezion_data_products()) prevents shared mutable state. MCP Registry is the self-serve platform layer of Data Mesh.

### Learning 220: A2UI Makes Agent Testing Structural (2026-03-31)
Component catalog (JSON) + experience scripts replace opaque WebGL testing. Agent validates the data structure, not the pixels. 9 Playwright e2e tests + 26 pytest tests. Data-attribute selectors (data-a2ui-component) are the most reliable Playwright selectors for dynamic UIs.
### Learning 221: LeWM — Missing JEPA World Model Upgrade (2026-03-31)
lucas-maes/le-wm is the first stable end-to-end JEPA from raw pixels using only 2 loss terms (next-embedding prediction + Gaussian regularizer). 15M params, single GPU, trains in hours, plans 48x faster than foundation models. Latent space encodes physical structure and detects implausible events. Direct upgrade path for Cohezion's 86K-param JEPAWorldModel. Connection: FLUME encode → LeWM predict → prediction error = free energy gradient. See: [[cerebellum/2026-03-31-session-wiring-retrospective]]

### Learning 222: GeminiProvider + Multi-Tier Cloud Routing (2026-03-31)
ModelProvider ABC + auto-registration pattern makes adding new cloud providers a single-file operation (~200 lines). GeminiProvider implements generate/list_models/health_check/close. Cost tiers in CostAwareRouter: Flash-Lite ($0.075/M, 70% simple), Flash ($0.30/M, 20% medium), Pro ($2.00/M, 10% hard). TipOfTheSpearRouter CLOUD tier now routes to Gemini Pro (code) / Flash (general) instead of placeholder. The 70/20/10 split from CLAUDE.md is now concretely wired.

### Learning 223: TurboQuant — Extreme Compression for FLUME + Semantic Cache (2026-03-31)
Google's TurboQuant (Mar 2026): PolarQuant (Cartesian→polar, fixed circular grid) + QJL (1-bit sign encoding via Johnson-Lindenstrauss). 6x KV memory reduction, 3-bit KV cache without training, 8x attention speedup. Direct Cohezion paths: (1) PolarQuant for FLUME 256D embeddings — manifold vectors are geometrically structured, polar quantization preserves structure; (2) QJL 1-bit for SemanticCache L2 cosine — 32x storage reduction; (3) Ollama KV cache — 6x memory means larger effective context on 128GB Strix Halo. QJL's sign-only quantization IS HIHO: half positive, half negative.

### Learning 224: Compound Token Efficiency Pipeline (C1-C5) (2026-03-31)
Five wired optimizations: (C1) ExecutorFactory auto-selects TokenEfficientCompoundExecutor for API prompt caching when token_client provided — 40-60% savings. (C2) Context-window guard in CostAwareRouter prevents overflow via auto-escalation chain (phi3→qwen→deepseek→smollm3→gemini). (C3) Cache hit rate→routing feedback — >90% hits downgrades to cheap models, <30% upgrades to better models. (C4) Template matching before execution — CacheWarmer.find_template_match() skips LLM entirely for >85% similar tasks (87-98% savings). (C5) Batch-aware concierge groups tasks by target for BatchableExecutor dedup.

### Learning 225: Meta-Harness Pattern — Filesystem > Prompt for Execution History (2026-03-31)
Stanford arXiv:2603.28052 shows exposing execution traces as browsable files (grep/cat) outperforms cramming into prompts. +7.7 points text classification, 4x fewer tokens. CompoundExecutor IS a harness. Integration: `execution_traces/` alongside vault — SkillRefiner browses traces instead of reading summaries. Validates vault-first approach.

### Learning 226: LatentMAS — Agents Communicate via KV Cache, Not Text (2026-03-31)
arXiv:2511.20639 shows training-free multi-agent collaboration via latent space KV cache transfer. 24x latency reduction vs text communication. FLUME 256D embeddings ARE the communication channel. Integration: agent-to-agent routing via FLUME vectors instead of serialized text. Interlat (arXiv:2511.09149) confirms pattern. DeepMind KV alignment (arXiv:2601.06123) provides multi-model coherence foundation.

### Learning 227: Build-Then-Forget Anti-Pattern — 41 Orphaned Modules (2026-03-31)
Internal sweep revealed 8 completely orphaned modules + 33 partially connected across Sessions 74-80. Root cause: modules built without wiring targets. Fix: every new module MUST have a Hookify rule or CompoundExecutor integration point at creation time. DegradationDetector is the natural bridge — healing/ and resilience/ now flow through it. CapabilityMatrix is the assessment bridge — eval/ and evaluation/ flow through it.

### Learning 228: IsoQuant — SO(4) Quaternion KV Compression Connects to SPIN (2026-03-31)
arXiv:2603.28430 (Mar 30, 2026): 4.5-4.7x mean kernel speedups over RotorQuant using isoclinic rotations via quaternion algebra. The SO(4)/quaternion math has a natural connection to Cohezion's SPIN coherence model (Rotation + Precession). Could unify KV cache compression with FLUME's latent space representation. Combined with TurboQuant (L223), IsoQuant provides the geometric compression while PolarQuant provides the coordinate-space compression. Also: VQKV achieves 82.8% compression training-free, applicable to Ollama models immediately.

### Learning 229: Layered Governance Architecture — L1-L4 Maps to Constitution (2026-03-31)
arXiv:2603.07191: 4-layer framework — L1 execution sandboxing, L2 intent verification (intercepts 93-98.5% malicious tool calls), L3 zero-trust inter-agent authorization, L4 immutable audit logging. Maps directly to Cohezion: L1=sandbox isolation, L2=RequestAlignmentAnalyzer, L3=TeamOrchestrator auth, L4=JourneyTracker audit trail. Also: AGENTSAFE (arXiv:2512.03180) adds semantic telemetry + anomaly detection patterns for DegradationDetector. OI-MAS (arXiv:2601.04861) provides joint role+scale routing — upgrade path for CostAwareRouter+DynamicModelRouter.
