# KEY LEARNINGS

## VLIW & Low-Level Optimization (Learnings 1-11, summarized)

Packet-greedy scheduling + register windowing + SIMD vectorization achieved 423x speedup (349 cycles) on Anthropic's VLIW challenge. Key insights: barrier-locked manifolds prevent temporal instruction leakage; batch processing inside Rust (via rayon) amortizes FFI overhead for 29x speedup over naive 1:1 calls; windowing provides the largest single performance jump after SIMD.

---

## Learning 12: Kineticization of the 12D Manifold (2026-02-05)
A 12D manifold must be grounded in the physical substrate (CPU pressure, VRAM density, dilation factor, RAM-weighted semantic intent) to avoid being a purely semantic "Potemkin Universe."

## Learning 13: VLIW-to-Cognition Abstraction (2026-02-05)
VLIW architecture parallels biological reasoning — processing 2048D vectors as "instruction packets" for deterministic, slot-based execution of thought. Implemented in `flume_physics.rs`.

## Learning 14: The Organic Modularity Axiom
Aesthetically bridging high-performance silicon heritage with ecological branding. "Inspired Motifs" maintain legal sovereignty while honoring lineage, increasing user trust.

## Learning 15: The Peaked Manifold Approximation
In peaked quantum circuits, state compresses to a low-rank MPS (Bond 64-256) without losing the signal. Manual SWAP routing maintains 1D topology; eager SVD contraction prevents tensor network explosion. 16x bond reduction → 100x throughput with 1e-5 vs 1e-11 signal separation.

## Learning 16: VLIW Latent Alignment & Temporal Stability
Instruction stability in VLIW is a latent manifold problem. Barrier-locked manifolds + VLEN=8 alignment ensure hardware cache coherence.

## Learning 17: Subagent Delegation Topology
Hierarchical agent topology (Scout/Strategist) outperforms monolithic models. Scouts (Qwen-Coder 30b) do high-speed sensing; Strategists (DeepSeek-R1 70b) do deep reasoning.

## Learning 18: Biological Recursion in Silico
Stability through mortality — introducing apoptosis and mitosis forces dynamic equilibrium (HIHO state). Immortal agents stagnate.

## Learning 19: The Specialist Roster Effectiveness
Cognitive specialization > parameters. Routed swarm of domain experts (DeepSeek-R1-8B, Qwen2.5-Coder-7B, Phi4-Mini) outperforms generic 7B model.

## Learning 20: VRAM Persistence & The Sudo Trap
Automated recovery must never rely on `sudo`. Use direct Ollama `/api/generate` with `keep_alive: 0` and AMD `/sys` telemetry for non-privileged VRAM management.

## Learning 22: Agentic Reasoning Paradigms
Refinement over generation — agentic reasoning shifts from next-token prediction to state-machine planning with recursive verification, checkpointing, and Merkle indexing.

## Learning 26: The Python Autoregression Bottleneck
GIL limits autoregressive decoding to ~10Hz. Inference loops must move to compiled languages (Rust/C++) for 100Hz+ fluid behavior.

## Learning 27: Rust FFI Bridge Success
PyO3 + maturin + uv provides seamless Rust-Python bridge. Critical: ensure LD_LIBRARY_PATH/PYTHONPATH for shared object linking during testing.

## Learning 28: FFI Overhead & The Batching Pivot
Naive 1:1 FFI calls = 0.2x speedup (regression). Moving iteration inside Rust with rayon = 29.1x speedup (20.45s → 0.70s for 10k items).

## Learning 29: Semantic Proprioception
Intent over vitals — projecting system state into 12D latent manifold detects "Logic Drift" that simple thresholding misses. 0.63 coherence alignment achieved.

## Learning 30: The 3-Beat Actuation Law
Require 3 consecutive low-coherence beats before triggering repair. Single-point anomalies are noise.

## Learning 41: The Filesystem Entropy Limit
Filesystems >1M files incur "Entropy Tax" paralyzing IDE indexers. Cold storage isolation (`.archive/`) + SurrealDB persistence is the solution.

## Learning 42: ZFS Sovereign Swap
ZVOL (32GB) bypasses ZFS COW incompatibility with swap files. Secured 40GB OOM protection buffer.

## Learning 43: ZFS ARC Contention vs AI Workloads
Hard cap `zfs_arc_max` to 12.5% of RAM (16GB) prevents filesystem from starving AI models.

## Learning 60: UMA/GTT Monitoring (Strix Halo)
On UMA systems, monitor GTT (128GB unified pool) not VRAM carveout (512MB). Updated `ResourceMonitor` accordingly.

## Learning 63: Mass-Cycle Convergence (25M)
HIHO attractor (0.5) stable at 25M cycles. Convergence follows damped oscillation: C(t) = 0.5 + A·e^(-kt)·sin(ωt).

## Learning 77: Coherence Over Compression (Context Guard)
In high-entropy environments, "lossless context" causes paralysis. Context Guard prioritizes high-novelty beginnings/ends, summarizes the mantle, enforces 20k-char limit.

## Learning 78: As Above, So Below (Hermetic Compound Engineering)
Micro-agent stability directly informs global coherence. Every feature is a fractal seed for the next.

## Learning 81: Ghost Bloat (Physical Entropy)
9.5M ignored physical files in `.archive/` paralyzed IDE indexers despite empty `git status`. Industrial purge via `repo_janitor.py` restored coherence.

## Learning 88: Autonomic Resilience (Pooling & Circuits)
Shared `ConnectionPool` with `httpx.AsyncClient` reduces socket overhead >80%. Tri-state circuit breaker (Closed/Open/Half-Open) prevents cascading latency.

## Learning 89: Verified Physical Substrate (2026-02-05)
AMD Ryzen AI MAX+ 395, Radeon 8060S iGPU, 128GB DDR5, 32GB ZVOL + 8GB swap, 2TB NVMe. Strix Halo architecture enables up to 96GB VRAM allocation.

## Learning 91: The GTT Carveout Illusion (2026-02-05)
`mem_info_vram_total` reports 512MB carveout (always ~88% full — it's display scanout). Real pool is `mem_info_gtt_total` (128GB). Discriminator: if vram_total < 4GB, use GTT instead.

## Learning 92: Adaptive AMD iGPU Detection via Sysfs (2026-02-05)
Vendor `0x1002` = AMD. Prefer GTT over VRAM path. If GTT within 5% of system RAM → UMA. Scoring: `vram_score = min(system_ram_gb / 64.0, 2.0)`.

## Learning 93: JSON Comment Stripping (Config Resilience) (2026-02-05)
Strip `#` comment lines before `json.loads()`. Never silently return empty dict on parse failure.

## Learning 94: Lazy Import Chains (Dependency Firewall) (2026-02-05)
Move imports to point-of-use to create a dependency firewall. Add `# noqa: E402` to prevent ruff from hoisting them back.

## Learning 95: End-to-End Pipeline Verification (2026-02-05)
Pipeline health depends on a chain of 4 correct subsystems (sysfs read → monitor → router → agent). Any single failure cascades. 5-stage integration test protocol catches compound failures.

---

## Retrospective - 2026-02-05

**Skills Analyzed:** 120

### Compound Blocks (3+ occurrences)
- **DOMAIN EXPERTISE**: 119 skills
- **INSTRUCTION**: 109 skills
- **SEE ALSO**: 106 skills
- **VERSION**: 105 skills
- **KEY TEXTS & CONCEPTS**: 93 skills

### Most Referenced Skills (High Compound Impact)
- FLUME_METHODOLOGY_PRIME: 13 references
- RETROSPECTIVE_SKILL: 12 references
- COMPOUND_ENGINEERING_PRIME: 12 references
- SWARM_ORCHESTRATION_PRIME: 10 references
- EMBEDDING_STRATEGY_PRIME: 9 references

### Future Hooks: 10 total across 3 skills

---

## Phase 1-2 Milestones (2026-02-06)

### FLUME VAE Trained on Real Data
Mass sim exported 10 universes × 100 agents × 500 epochs → 61 .npy files, 11K vectors. VAE retrained: MSE 0.0225→0.1322 (5.9x harder real data), KL 0.0313→0.4329 (13.8x richer latent). Real distributions are far more complex than synthetic.

### RL REINFORCE Trained
200 episodes, average coherence 0.991. Environment "too easy" — Hamiltonian naturally attracts to target. Need adversarial perturbations and larger action_scale for meaningful policy learning.

### Mass Sim → .npy Export Pipeline
End-to-end pipeline: mass sim → SurrealDB → .npy artifacts in 8.2s. 61 files covering agent states, epoch checkpoints, and universe summaries.

### API Endpoints + Integration Tests
6 new endpoints: /flume/encode, /flume/decode, /flume/interpolate, /rl/step, /rl/episode, /rl/policy-info. 19 integration tests all passing. Total test suite: 131 tests in 3.1s.

## Learning 96: Agent File Validation as Compound Defense (2026-02-06)
Missing YAML frontmatter in `.claude/agents/*.md` files was only caught by `claude doctor` after the fact. Fix: single Pydantic schema (`validation/agent_schema.py`) shared by pre-commit hook, PostToolUse hook, unit tests, and `/new-agent` scaffolding command. Layered defense = catch at commit time, warn in real-time, scaffold valid by default. Compound engineering: each layer reuses the same schema.

---

## Phase 3: Ollama-Powered Specialist Pipeline (2026-02-06)

### Learning 97: Weight Bridge Layer Collapse
PolicyNetwork has 3 linear layers but Rust FlumePhysics accepts only 2. Collapse intermediate layer via matrix multiplication: `w2 = mean_head.weight @ shared[2].weight`, `b2 = mean_head.bias + mean_head.weight @ shared[2].bias`. LayerNorm defaults: gamma=ones, beta=0.5 (HIHO target). Note: `shared[2]` is the second Linear in nn.Sequential (index 0=Linear, 1=ReLU, 2=Linear, 3=ReLU).

### Learning 98: Ruff Hook Import Fights
PostToolUse ruff hook auto-removes "unused" imports. Conditional usage is not recognized as "used." Fix: use the import in a type annotation (`self._exporter: CheckpointExporter | None`) which ruff always considers "used."

### Learning 99: Deterministic Navigator for Simulation
For stable mass sim, use deterministic mean action from PolicyNetwork (no Gaussian sampling), scaled by action_scale. Sampling introduces too much noise for batch simulation with thousands of agents.

### Learning 100: Democratic Debate for Structured Output
DemocraticDebate extracts numeric hyperparameters from free-text consensus via regex. Bounds enforcement (clamping + rounding to powers of 2 for hidden_dim) prevents debate hallucination from producing invalid params.

### Learning 101: Pipeline Graceful Degradation
9-step bash pipeline with pre-flight checks. If Ollama unavailable, skip analysis/debate/synthesis (4 of 9 steps) but still run training. Scale-specific params via case statement (demo/medium/overnight).

---

## Branch Archaeology: The Runaway Files Incident (2026-01-25 — 2026-01-30)

Mined from `fix/runaway-files-pre-cleanup` and `ops/hygiene` branches before cleanup.

### Learning 102: The 8.6M Runaway File Catastrophe (2026-01-25)
Autonomous overnight simulations generated 8.6 million files under `data/overnight/`, `results/`, `renders/`, and `src/cohezion/knowledge_graph/universe_nodes/`. Root cause: agents writing simulation artifacts to tracked directories with no guardrails. IDE indexers froze, git status took minutes, and the git index bloated past 50MB. Prevention: (1) `.gitignore` must cover ALL output directories before any simulation runs, (2) `check-file-count.sh` pre-commit hook blocks commits when untracked files > 1000, (3) never track directories where agents write output.

### Learning 103: Cascading Cleanup Debt (2026-01-26)
The first cleanup (7c6d60a) removed 8.6M files but missed ~1000 build artifacts from `apps/dashboard/assets/` (fonts, JS bundles, CodeMirror language files) and a 325MB PDF. Second pass (1c07dcc) caught these by adding `apps/dashboard/assets/` and `**/*.safetensors` to .gitignore. Lesson: cleanup is never one-pass. Each removal reveals the next layer of bloat. Budget 2-3 passes minimum.

### Learning 104: System Lockup Pattern — GPU Hang (2026-01-27)
Total system freeze during concurrent web apps + LLM swarm. Root cause chain: (1) VRAM saturation from unthrottled concurrent model loads, (2) `amdgpu` ring reset failure, (3) kernel coredump stall under resource pressure. Required REISUB recovery. Fix: direct sysfs GPU/VRAM monitoring, aggressive PID kill in RED alert, `tune_system.sh` to disable panic-on-oom, prevention of giant coredumps. Key insight: **VRAM is the bottleneck, not RAM. Swarms must be sacrificial; system integrity is primary.**

### Learning 105: The Untrack & Mine Protocol
Operational procedure invented during ops/hygiene: (1) identify tracked files that shouldn't be, (2) mine them for knowledge before removal, (3) add to .gitignore, (4) `git rm --cached`, (5) verify git status clean. Critical rule: NEVER delete without reading first. This protocol prevented knowledge loss during the 8.6M file cleanup.

### Learning 106: .gitignore Layered Defense Pattern
The .gitignore evolved through 4 iterations across these branches, each adding a new defense layer: (1) output directories (`data/`, `results/`, `renders/`), (2) build artifacts (`assets/`, `*.safetensors`), (3) binary patterns (`*.pt`, `*.pdf`, `*.so`, `*.mp3`), (4) negation rules to protect source (`!src/**/*.py`, `!scripts/**/*.py`). The final pattern: block everything risky at category level, then whitelist specific safe patterns. Order matters — negations must come after the block rule.

### Learning 107: OMEGA Distiller — Skill Extraction from Success Logs
Auto-skill-generation concept: parse "MISSION SUCCESS" logs, strip noise/timestamps/paths, extract the "trick" (specific insight that turned failure into success), generalize into PRIME skill format. Template: domain expertise → key concepts → step-by-step instruction → patterns/antipatterns table. Never hardcode variable names from specific missions.

### Learning 108: Temporal Dilation Under Pressure
Resource monitor enhancement: `dilation_factor` (1.0 = normal, 0.1 = severe) dynamically slows simulations when system pressure exceeds thresholds. Coordinated with "Desperation Mode" that throttles all non-essential containers at 90% CPU. Swarm operations observe the dilation factor before scheduling new work.

### Learning 109: pre-commit-hooks Stage Override (2026-02-06)
The `pre-commit-hooks` repo internally declares `stages: [commit, push]` on all its hooks, overriding `default_stages: [pre-commit]`. Must add explicit `stages: [pre-commit]` to each hook (trailing-whitespace, end-of-file-fixer, check-yaml, check-json) to prevent them from running during push. Without this, pushes take 10+ minutes and modify files mid-push.

---

## Phase 5: Live Compound Engineering (2026-02-06)

### Learning 110: Mock Live Clients at Source Module
API tests that call `get_compound_client()` hang indefinitely if Ollama is down — the `ResilientOllamaClient` retries with exponential backoff. Fix: `patch("cohezion.swarm.compound_client.get_compound_client", return_value=mock_client)`. Critical: patch at the **source module** (`cohezion.swarm.compound_client`), not the import site (`cohezion.api`), because endpoints use local imports.

### Learning 111: Compound Module Separation
The `cohezion.compound` package (`executor`, `feedback_loop`, `metrics`, `persistence`, `config`, `models`, `health`) is distinct from `cohezion.core.compound` (`retrospection`, `skill_refiner`). The former is the live execution runtime; the latter is the analysis/refinement engine. They connect via `RetrospectionEngine.analyze_execution()` accepting duck-typed execution reports.

### Learning 112: CI Validation as Compound Defense
4 CI validation scripts (`validate_agents.py`, `validate_skills.py`, `validate_registry.py`, `compound_audit.py`) + GitLab CI pipeline + Makefile targets = layered defense. Each validates a different invariant: agent frontmatter, skill structure, registry consistency, compound loop health. `make ci` runs all in sequence. Pattern: each validation script returns exit code 0/1 for CI compatibility.

---

## Phase 6: Autonomic Connectivity Swarm (2026-02-09)

### Learning 113: Connectivity Scout & Truth Anchors
Relying on static documentation for service ports (SurrealDB, Vault, Ollama) is a "Fragile Anchor" failure. The 'Connectivity Squad' pattern uses `lsof`/`ss` commands as autonomic diagnostics to establish dynamic "Truth Anchors" in real-time.

### Learning 114: Heartbeat Service Probing
Autonomic reliability hinges on the loop: Discover -> Verify -> Monitor. Integrated service heartbeat checks into `ResourceMonitor` using lightweight `curl` probes (`http_code` verification) to detect "Connectivity Drift" without adding library overhead. Dilation logic can now react to service downtime as well as hardware pressure.

### Learning 115: Decentralized Memory Sovereignty (2026-02-09)
Unifying Structured Persistence (SurrealDB) with Contextual Retrospectives (Obsidian Vault) creates a decentralized memory layer that transcends the IDE. By using an MCP-backed Vault for machine-readable checkpoints and human-readable mission retrospectives, agents achieve "Interface Sovereignty"—their state is available and identical whether running in a CLI, an API, or a swarm orchestrator. Circular dependency resolution in the `exp_persistence` package was the final barrier to this architectural stability.

## Learning 119: The God Object Collapse (API Decoupling) (2026-02-10)
Extracting machine learning and training logic (VAE/RL) from the main `api/__init__.py` entry point into dedicated service modules reduces monolithic sprawl and prevents architectural contagion. Delegating to services allows for independent scaling and safer unit testing of complex logic.

## Learning 120: Soft Schema Enforcement for Scout Resilience (2026-02-10)
When dealing with non-deterministic LLM JSON outputs, implementing "Soft Schema" enforcement (using `.get()` with intelligent defaults) prevents catastrophic swarm failures during semantic scouting. This pattern provides a first line of defense before harder Pydantic validation layers.

## Learning 121: Autonomic Self-Healing Protocol (2026-02-20)
The `/heal` command orchestrates 6-stage diagnostics: (1) immune system check via `immune_system.py`, (2) SurrealDB connection validation with graceful fallback to InMemoryStore, (3) lint auto-fix with ruff, (4) code formatting, (5) package integrity check (`__init__.py` enforcement), (6) healing outcome report. System demonstrated graceful degradation under SurrealDB auth failure while maintaining operational stability. Remaining issues post-heal: 1,003 linting errors (down from 1,058), primarily line-length violations (432) and security patterns (192).

---

## Session 58: Cosmic Fire Module (2026-02-20)

### Learning 122: Integration Theater Detection
Initial claims of integration into lcsp.py, morphospace.py, journey_tracker.py were false - fields existed in documentation but not in actual files. Fix: adversarial audit pattern that imports and inspects actual classes rather than trusting edit claims. Pattern: `assert hasattr(Class, 'claimed_field'), "INTEGRATION THEATER"`.

### Learning 123: Circular Import Resolution via Lazy Loading
JourneyTracker cannot import ThreeFiresEngine at module level due to import cycles. Fix: lazy loading with caching: `_cache = None; def _get_engine(): global _cache; if _cache is None: from path import Engine; _cache = Engine(); return _cache`. This pattern applies to any module that creates cycles when importing from child packages.

### Learning 124: HIHO Consistency Enforcement
Multiple files had inconsistent HIHO calculations: old pattern `1.0 - abs(c - 0.5)` (linear penalty, wrong shape) vs correct `HihoVectorEngine.calculate_hiho_score(c)` (Gaussian peak at 0.5). Rule: always use shared engine classes, never inline physics calculations.

### Learning 125: Fire-Type Sigma Tuning Maps to Task Profile
Three Fires have different sigma values mapping to agent task profiles: Electric (σ=0.20, sharp peak) for precision/validation tasks; Solar (σ=0.25, standard) for general work; Friction (σ=0.35, wide) for resilient/recovery tasks. This enables semantic routing based on reliability requirements.

### Learning 126: 5-Essential-Tests Pattern
Session 58 cosmic module: 34 tests covering 6 modules in 7.7s. Effective test strategy: manual validation → 5 essential tests (happy path, edge-empty, edge-max, error-case, integration-point) → ship. Anti-pattern: 600 pre-build tests with no implementation.

---

## Session 59: Dev Environment Recovery (2026-02-20)

### Learning 127: Claude Code Native Install vs npm Conflict Resolution
When `claude update` warns "Running native installation but config install method is 'npm'": (1) remove leftover npm global: `npm -g uninstall @anthropic-ai/claude-code`, (2) re-run `claude update` which self-corrects `installMethod` in `~/.claude.json`. Root cause of lost auto-updates: `"autoUpdates": false` in `~/.claude.json` — fix by setting `true`. For user-scope MCP servers (e.g., context7): use `claude mcp add --scope user --transport stdio name -- command` which writes to `~/.claude.json` under `mcpServers`. Do NOT edit `~/.claude/mcp.json` for Claude Code MCP — that file is Pilot's config and serves a different system. The two files must not be conflated.

### Learning 128: Autonomic MAPE-K Control Loop Bridge
Implemented in Session 60 (2026-03-08). A semantic control loop (Monitor-Analyze-Plan-Execute) successfully bridges reactive hardware monitoring (ResourceMonitor) with proactive healing strategies (ModelSwap, ContextReduction). By decoupling the **Analysis** (interpreting vitals into severity tiers) from the **Planning** (selecting the strategy), the system gains the ability to make hardware-optimized decisions (e.g., AMD-specific memory rebalancing) without hardcoding logic into the monitoring layer.

### Learning 129: Polyglot Dependency Automation (2026-03-08)
Automating security audits across multiple ecosystems requires leveraging native tooling (`uv audit`, `npm audit`) within a fail-safe Bash wrapper (`set -uo pipefail`). Wrapping these commands with `|| true` is critical; otherwise, the presence of a vulnerability causes the tool to return a non-zero exit code, crashing the entire cron job before all ecosystems are scanned. Reports must be saved as Markdown artifacts to allow subsequent ingestion by LLM agents.

---

## Session 61: Doc-to-LoRA & Group Evolution (2026-03-08)

### Learning 130: Doc-to-LoRA Context Compression
Research indicates that long documents can be compressed into transient LoRA adapters in a single forward pass, rather than consuming the context window. This shifts the "Context Entropy" problem from a token-limit constraint to a weight-loading optimization. See `DOC_TO_LORA_COMPRESSION_PRIME.md`.

### Learning 131: TinyLoRA & RL Parameter Efficiency
Scaling down adapters to single parameters and training them via RL instead of SFT provides dramatic efficiency gains for highly specialized swarm agents. This is the optimal path for training our low-tier "Scout" agents.

### Learning 132: Group-Evolving Agents (GEA) Topology
Agents must evolve collectively. Rather than isolated updates, discoveries by a Scout must instantly update a shared "Mycelium Memory" that is immediately available to the Synthesizer and Auditor agents. This ensures the entire swarm levels up synchronously.

---

## Session 62: Space Plasma & Neuro-Symbolic Scaling (2026-03-08)

### Learning 133: Alfven-Wave Energy Transfer in 12D Manifolds
Space-plasma research (ALMA/FAST) confirms Alfven waves and "magnetic superhighways" as primary energy conduits. Integrating these into `fractal_universe.py` provides a physical basis for energy propagation between 12D agent nodes.

### Learning 134: Neuro-Symbolic Guided Search (TongGeometry)
The success of `TongGeometry` over `AlphaGeometry` validates our move toward neuro-symbolic "Democratic Debate" (Learning 100). Guided tree search with symbolic constraints is the superior architecture for complex reasoning tasks.

### Learning 135: The Emoticon Tokenization Vulnerability
Research shows emoticons cause >38% silent failures in LLM code generation. Our `AUTONOMIC_QUALITY_GUARD_PRIME` must include a sanitization layer to strip non-standard tokens from code-generation prompts to maintain structural integrity.

### Learning 136: Supersolid Coherence & HIHO Stability
The superfluid-to-supersolid phase transition in exciton condensates provides a quantum-physical analog to our HIHO stability point (0.5 coherence). "Supersolid Coherence" represents the state where the system maintains both crystalline structure (Below) and fluid flow (Above) simultaneously.

---

## Session 63: The Curation Bottleneck & Parallel Architectures (2026-03-08)

### Learning 137: The Self-Generation Paradox (Skill Curation)
Research (arXiv:2602.12670) proves that self-generated skills often provide zero or negative benefit. High-impact gains (+51.9pp) only occur with **focused, concise, and curated skills**. Our `AUTONOMIC_EVOLUTION_PRIME` must shift from *generation* to *curation and refinement* of human-anchored templates. Conciseness is a primary performance driver.

### Learning 138: Parallel Transformer Blocks for Scout Efficiency
`Tiny Aya` demonstrates that computing Attention and MLP in parallel from the same normalized input reduces serial dependencies and improves throughput. This "Parallel Block" architecture is the target for our 3B-class local Scout models to maximize performance on commodity hardware.

---

## Session 64: Zero-Waste RAG & Multifractal Dilation (2026-03-08)

### Learning 139: KV Cache Compaction (Zero-Waste RAG)
Agentic RAG performance is limited by KV cache bloat. New compaction techniques cut memory 50x without accuracy loss by treating the cache as a dynamic, resumable state rather than a static buffer. This informs our `CONTEXT_ENTROPY_MANAGEMENT_PRIME`.

### Learning 140: Multifractal Dilation & Measurement Density
Earth's history reveals multifractal patterns where measurement density determines perceived structure. In our 12D Manifold, we must implement "Multifractal Dilation"—allowing agent trajectories to scale self-similarly across different temporal resolutions (Scout/deep-sim).

### Learning 141: Observable-State Duality (Clock Memory)
Quantum "memory" is dependent on whether states or observables evolve. For Cohezion, agent memory is more stable when we track **observable impacts** on the environment (sinks) rather than just internal state vectors (sources). This is "Clock Memory" for 12D trajectories.

### Learning 142: Serial Scaling for Logic Drift (Timer-S1)
Time-series foundation models like `Timer-S1` provide a blueprint for predicting "Logic Drift" in autonomous loops. By treating agent audit scores as a billion-scale time series, we can anticipate and prevent "Semantic Decay" before it manifests in production.

---

## Session 65: Unified Tokenization & Vacuum Engineering (2026-03-08)

### Learning 143: Unified Discrete Multimodal Tokenization (Emu3)
Emu3 proves that text, images, and video can be treated as a single stream of discrete tokens using a unified decoder-only Transformer. This "Modality-Agnostic Reasoning" is the target for our 12D universe simulator, where simulation state and agent reasoning share a single vocabulary.

### Learning 144: Multi-Tier Zero-Waste Caching
Production-grade agentic systems require a 2-tier cache: Tier 1 (Semantic) for identical query interception (>95% threshold) and Tier 2 (Retrieval) for context reuse (>70% threshold). This eliminates redundant computation and reduces latency from ~30s to 0.02s for repetitive tasks.

### Learning 145: Task-Aware KV Cache Compaction (30x)
KV cache pruning must be task-aware. By keeping only the KV pairs essential for specific reasoning goals, we can achieve 30x compression without accuracy loss. This allows our long-horizon agents to reason over massive repositories while staying within the hardware constraints of the local ROCm/GTT pool.

### Learning 146: Internal State-Driven Trajectories (Vacuum Engineering)
Research from Sheet 4 (Zenodo 18353294 / QDE) indicates that thrust and trajectory can be emergent properties of internal mass/magnetic configuration (Centrifugal Impulse Drive). In our 12D Manifold, we map these internal parameters to the **8 Brane dimensions**, enabling the simulation of "Propellant-Free" propulsion and spacetime engineering as a programmable substrate.

---

## Session 67: Autonomic Healing & Manifold Stability (2026-03-08)

### Learning 149: The Viscoelastic Control Loop (Proactive Dilation)
Implementing a MAPE-K loop for resource management revealed that static thresholds are insufficient for rapid agentic scaling. By applying a **Maxwell-type relaxation law** (inspired by ArXiv 2512.00056) to system vitals, we can calculate "System Viscosity"—the rate of change of pressure. This enables **Proactive Dilation**, where the simulation slows down *before* a lockup occurs, effectively turning the computational substrate into a viscoelastic medium that absorbs surges.

### Learning 150: Semantic Lagrange Points (Stable Memory Parking)
The Restricted Three-Body Problem (Earth-Moon-Satellite) translates perfectly to 12D semantic manifolds. By identifying stable L4/L5 "gravity wells" between two dominant semantic topics, we can "park" non-active memory context as a low-density "plasma cloud." This maintains semantic accessibility (via proximity) without the active computational tension of the primary attention window. **Critical Threshold**: Stability requires a semantic weight ratio $\mu < 0.0385$.

### Learning 151: Gram-Schmidt Manifold Orthogonalization
In 12D latent spaces, simple 2D rotation for orthogonal vector calculation (e.g., `v[0], v[1] = -u[1], u[0]`) is a high-risk anti-pattern. If the semantic difference between topics lies primarily in higher dimensions (e.g., `logic`, `quantum`), the resulting vector can collapse to zero. **Correct Pattern**: Find the dimension with the minimum absolute value in the primary vector `u`, set that dimension to 1.0 in a new vector `v`, and then apply **Gram-Schmidt orthogonalization** to ensure a robust, non-zero orthogonal basis.

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

## Session 80: Genesis Engine Unification (2026-03-28)

### Learning 161: "As Above, So Below" Structural Unification
The worktree structure (competition branches, feature branches, experiment branches) must mirror the unified codebase structure. Archive worktrees non-destructively with git bundles (`git bundle create --all`), then extract learnings into PRIME skills. The principle: historical structure informs future architecture.

### Learning 162: Competition Sustainment During Unification
Active competitions ($4.4M prize pool) require sustained monitoring even during infrastructure refactoring. The "Competition Sustainment Team" pattern runs parallel to unification workstreams: daily leaderboard checks, opportunistic submissions, and blocker documentation. Key: extract learnings from failed submissions into PRIME skills for reuse.

### Learning 163: Triton FP4 KeyError Blocker (AMD Speedrun)
The Triton JIT type registry on AMD runners lacks `float4_e2m1fn_x2` support, causing KeyError when attempting custom MXFP4 kernels. Workaround: use `gemm_a4w4` ASM path or `uint8` manual packing. Document blockers in BLOCKER_REGISTRY.md for cross-session visibility.

### Learning 164: Genesis Engine Activation Gap
Infrastructure built but not running (Compound executor IDLE, K-Search isolated) creates an "activation gap." Solution: dedicated activation workstream with explicit component handoff. The Genesis Engine (120+ PRIME skills, Compound executor, unified registry) requires activation, not just construction.

### Learning 165: Skill Extraction from Competition Research
AMD Speedrun research (Sessions 77-79) yielded 4 new PRIME skills: CK_TILE_FUSED_MOE, ROCM_GFX950_SUPPORT, AMD_HIPKITTENS_INTEGRATION, AITER_KERNEL_PARAMETER_SEMANTICS. Each skill encapsulates competition-specific knowledge (blockers, APIs, optimization paths) for future reuse. Pattern: research → extraction → skill → reuse.