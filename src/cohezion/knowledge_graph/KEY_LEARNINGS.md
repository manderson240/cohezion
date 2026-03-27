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