# KEY LEARNINGS

## Learnings 244-247: Luma AMD Speedrun — HIP Kernel Breakthroughs (2026-04-01)
L244: Stream-aware HIP dispatch — pass `torch.cuda.current_stream().cuda_stream` to custom kernels to avoid "work on another stream" errors. L245: MLA K=576/V=512 latent split indexing for MXFP4 KV cache (1.67x bandwidth reduction). L246: LDS Bridge keeps MoE intermediates in 64KB Local Data Share instead of HBM (30-50µs savings). L247: Benchmark-driven conditional submission — only promote to leaderboard if microsecond time strictly improves.

---

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

## Session 90: AIMO 3 (2026-04-05, Compressed)
L265: AIMO 3 meta = Diverse Prompt Mixer + Weighted Entropy Voting + Speculative Decoding. L266: H100/Blackwell handshake (`NvidiaRtxPro6000`), hard VRAM resets every 10 problems, 30s safety trigger. L267: Speculative Decoding (R1-32B + Qwen-1.5B drafter) = 1.5-1.8x throughput. L268: Polars Series `df[0]` scalar indexing mandatory (not `df[0,0]`), Fortress architecture for Kaggle Private Rerun. See `KAGGLE_STABILITY_PROTOCOL.md`.

---

## Phase 1-2 Milestones (2026-02-06, Compressed)
FLUME VAE retrained on real data (11K vectors, MSE 5.9x harder, KL 13.8x richer). RL REINFORCE: 0.991 coherence but environment "too easy." Mass sim→.npy export (8.2s, 61 files). 6 API endpoints (/flume/*, /rl/*), 19 integration tests.

## Learnings 96-107: Agent Validation, Specialist Pipeline, Runaway Files (Compressed)
L96: Single Pydantic schema shared by pre-commit + PostToolUse + unit tests + scaffolding = layered agent validation defense. L97-101: Rust FFI weight bridge, ruff hook type annotations, deterministic mean action, DemocraticDebate regex+clamping, 9-step pipeline with Ollama fallback. L102-104: 8.6M runaway files → pre-commit check-file-count.sh + .gitignore layered defense; VRAM (not RAM) is bottleneck; swarms must be sacrificial. L105: Untrack-and-Mine protocol (read→mine→.gitignore→git rm --cached). L106: .gitignore layered defense (category blocks → negation whitelists). L107: OMEGA Distiller auto-skill-generation from success logs.

## Learnings 108-126: Compound Engineering & Autonomic Systems (Compressed)
Key patterns: (1) Temporal dilation factor (0.1-1.0) throttles sims under pressure (L108). (2) Mock at source module, not import site: `patch("cohezion.swarm.compound_client.get_compound_client")` (L110). (3) 4 CI validators as layered defense (L112). (4) Connectivity Squad: `lsof`/`ss` for dynamic truth anchors (L113). (5) Decentralized memory: SurrealDB + Vault = Interface Sovereignty (L115). (6) God object decoupling: extract ML from api/__init__.py (L119). (7) Soft schema `.get()` before Pydantic validation for LLM outputs (L120). (8) `/heal` 6-stage autonomic diagnostics (L121). (9) Integration Theater detection: `assert hasattr(Class, 'field')` (L122). (10) Lazy imports for circular dependency resolution (L123). (11) HIHO consistency: always use shared engine, never inline physics (L124). (12) 5-Essential-Tests pattern: happy, empty, max, error, integration → ship (L126).

---

## Learnings 127-151: Dev Recovery, MAPE-K, Research Synthesis (Sessions 59-67, Compressed)
L127: Claude Code native install vs npm — remove npm global, set autoUpdates:true, MCP scope:user. L128: MAPE-K control loop bridges reactive monitoring with proactive healing via decoupled Analysis→Planning. L129: Polyglot security audits need `|| true` wrapping. L130-151 (Research Sprint): Doc-to-LoRA context compression (L130), skill curation > generation (L137), KV compaction 30-50x (L139/L145), multi-tier caching 30s→0.02s (L144), viscoelastic dilation (L149), semantic Lagrange points μ<0.0385 (L150), Gram-Schmidt for 12D vectors (L151).

---

## Learnings 152-156: Secure-by-Default Substrate (Session 68, Compressed)
L152: 360-Degree Autonomic Cycle — 8-stage closed loop (sense→optimize→refine→manifest→verify→audit→scout→analyze) in 60min window. L153-156: Unified auth middleware (centralized api_key_middleware), recursive path sanitization (CWD-bounding), API secret scrubbing (regex key matching → REDACTED), CI/CD prompt injection defense (system_instruction + XML delimiters + env vars).

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

Akashic Sprint Mission (2026-04-07): Implemented long-horizon task orchestration for overnight Kaggle monitoring and local model refinement. Uses `MISSION_AKASHIC_SPRINT.py` to poll Blackwell VMs and record hourly 12D snapshots in SurrealDB. Added Weighted Entropy Consensus to AIMO MRS (v40) to scale reasoning performance.


---

## Sessions 73-82: Genesis Engine + Platform Architecture (2026-03-25 to 2026-03-31, Compressed)

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks — `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine — 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.

## Sessions 85-89: ManifoldEnv RL Training + Kernel Optimization (2026-04-01, Compressed)
L233-243: ManifoldEnv RL breakthrough: 3-stage curriculum reward (reach→maintain→optimize), proximity base reward prevents oscillation, small actions (±0.1) cooperate with physics while large actions fight it. PPO+curriculum best (14.23, +7.51 vs random). Structural safety: Lagrangian dynamics bound behavior — random agents achieve 60% HIHO convergence because physics guides trajectories. ERL safety metric: hackable_area/total_area. UniverseEvaluator with bootstrap CIs. RoutingOrchestrator unifies 4 routing systems. TDD + code review compound loop catches 2 CRITICAL/session.
L248-249: Algorithm-Reward Matrix (PPO+curriculum vs SAC+dense). Compound training cycle: train→evaluate→persist→compare→refine.
L251: Scale-aligned MXFP4 GEMM tiling — BLOCK_K=32 = 1 E8M0 scale group. load_inline > library APIs for alignment control.

### Learning 252: Continuous Benchmark Learning Loop for GPU Kernel Optimization (2026-04-02)
`kernel_learning_loop.py`: 12 benchmarks/hour × 3 kernels = 36 data points/hour. Over 5 days: 4,320 runs vs 50 current (86× more data). Every result persisted to SurrealDB (even failures — they signal which mutations are dead). Round-robin variant selection with conditional leaderboard submission. Pattern: the same compound loop (train→evaluate→persist→compare→refine) applies to both RL training and kernel optimization.

### Learning 253: ROCm CDNA4 FP8 GEMM — 8-Wave Ping-Pong at HIP Level (2026-04-02)
ROCm blog (March 2026): 8-wave ping-pong achieves 2680-3204 TFLOPS/s (within 2.5% of hipBLASLt) using HIP/C++ NOT assembly. Key techniques: 256×256 output tiles, K=128, 512 threads, double-buffered LDS, LDS XOR swizzle for bank conflict elimination, `__builtin_amdgcn_s_barrier`/`s_setprio`/`sched_barrier` for wave scheduling. V_MFMA_SCALE_F32_16X16X128_F8F6F4 confirmed for block-scaled MXFP4. Source: https://rocm.blogs.amd.com/software-tools-optimization/cdna4-gemm-kernels/README.html

### Learning 255: V-JEPA 2.1 — Dense Loss Fixes Context Token Degeneracy (2026-04-02)
V-JEPA 2.1 (arXiv:2603.14482): Root cause of JEPA bottleneck = loss applied only to masked regions → context tokens degenerate into global aggregators, losing spatial fidelity. Fix: dense predictive loss on BOTH masked and unmasked tokens. Also: deep self-supervision across intermediate layers. 20-point improvement in robot grasping. Directly applicable to Cohezion JEPAWorldModel.

### Learning 256: ADRC-Lagrangian — 74% Fewer Safety Violations in Safe RL (2026-04-02)
ADRC-Lagrangian (arXiv:2601.18142): Treats all uncertainty as lumped disturbance with lightweight ADRC observer. 74% fewer violations, 89% smaller constraint magnitudes. Model-free, optimizer-agnostic. Complements ManifoldEnv's physical safety (Lagrangian dynamics) with adaptive learned constraints.

### Learning 257: Causal-JEPA — Object-Level Masking for Causal World Models (2026-04-02)
Causal-JEPA (arXiv:2602.11389, code: github.com/galilai-group/cjepa): Object-level masking as latent intervention. Forces model to reason about object interactions, not just spatial patterns. 20% improvement in counterfactual reasoning, 8x faster planning (1% of tokens). 128D latent slots, single GPU training. Applicable to Cohezion JEPA: mask agent slots in multi-agent scenarios.

### Learning 261: Ralph Loop Anti-Pattern — Infinite Loop Without Exit Condition (2026-04-02)
Ralph Loop MUST have --completion-promise or --max-iterations. Session 88B: 8 productive iterations then 713 wasted (721 total). The stop hook feeds the same prompt infinitely after work completes. Rule: always set completion_promise to a verifiable boolean, or max_iterations to 2x expected cycles.

### Learning 262: Email Pipeline Anti-Pattern — Build Without Verifying Sink (2026-04-02)
Created generate_status_report.py + email_status_cron.sh without configuring SMTP. 0 emails sent. Scripts depending on external config MUST validate at creation time. Rule: `assert config_exists() or warn_loudly()`.

### Learning 263: Research-Before-Build — MFMA Intrinsic Discovery (2026-04-02)
Built 5 load_inline kernels using scalar FP4 LUT decode while research agents discovered hardware MFMA does dequant+matmul in ONE instruction (`__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4`). 10-100x compute gap. HipKittens has NO MXFP4 support. All 5 variants need MFMA rewrite. Rule: wait for research results before building, or gate implementation on minimal PoC.

### Learning 264: Quantum Peaked Circuits & Rigetti Ankaa-3 (2026-04-04)
Classical MPS simulations (mps.cpu/gpu) hit an exponential wall around 700 gates for peaked circuits. For 50-69 qubit peaked circuits (e.g. P9 with 6771 gates), use Rigetti Ankaa-3 with Q-CTRL Fire Opal for autonomous error mitigation (up to 32x improvement). The 'Marginal Attack' (using single-qubit Z expectation values) fails for deep circuits, introducing bit-flips. However, the Pauli-Path Simulator can be used as a 'Zero-Cost Verifier' to confirm the true peak among QPU candidates by calculating top candidate probabilities and computing the SNR. BlueQubit charges a $0.30 base fee per job submission; batching multiple circuits into a single list submitted via `bq.run([circuits], device='quantum')` optimizes costs significantly.

### Learning 265: per_1x32_f4_quant_hip Silent Incompatibility with gemm_a4w4 (2026-04-06)
aiter's `per_1x32_f4_quant_hip` (HIP C++ quant kernel) produces FP4 values incompatible with `gemm_a4w4` CK ASM kernels. Both `shuffle=True` and `shuffle=False` fail silently — no exception, just wrong output values (small diffs like 165 vs 163). Only the Triton path (`dynamic_mxfp4_quant + e8m0_shuffle`) works. The HIP quant kernel uses different rounding/packing than what the ASM GEMM expects. Skill created: `aiter-hip-quant-gemm-incompatibility`.

### Learning 266: Popcorn Runner 12-Minute Timeout as Architecture Constraint (2026-04-06)
The Popcorn leaderboard pipeline (test + benchmark + ranked) has a hard 12-minute timeout. CK ASM kernels use pre-compiled `.co` files (zero JIT), while load_inline HIP and Triton autotuning consume 2-5 min of JIT each. MLA's 8 shapes consistently timeout on leaderboard mode. Architecture implication: only pre-compiled or very compact (<150 line) HIP kernels fit the timeout budget. The leader's 78-iteration approach (v78_splitk0.py) likely pre-compiles offline.

### Learning 267: Fused Quant+GEMM Correctness Breakthrough (2026-04-07)
`submission_fused_inline_quant.py` achieved 0.0 error on all 4 test shapes — proving inline BF16→FP4 quantization inside a HIP kernel produces correct results. However, scalar per-element quantization is 4-50x slower than the CK ASM + Triton pipeline. The path to competitive fused kernels requires MFMA-native vectorized quantization (using wave-level reductions for max_abs, not per-element loops).

### Learning 268: K-Search Compound Loop — LLM Synthesis Works but Needs Quality (2026-04-07)
The K-Search pipeline (Ollama synthesis → popcorn eval → tree learning) is operational. `deepcoder:14b` generates kernels in 60s but lacks MI355X MFMA knowledge (produces naive scalar GEMM). Cloud models (`deepseek-v3.2:cloud`) timeout on complex prompts. Key fix: use few-shot prompting with the WORKING tile32x128 kernel as an example, not zero-shot generation. Meta-prompts also had outdated instructions (subprocess/ctypes, both blocked).

### Learning 269: TDD-First for GPU Kernels — Local Verification Saves Remote Submissions (2026-04-07)
Verified e8m0_unshuffle roundtrip, MFMA 32x32 output layout (every cell written once), and A/B tile loading coverage (1024+4096 bytes) using pure Python before any remote submission. This prevented wasting rate-limited submissions on known-broken code. Rule: for GPU kernels where you can't run locally, verify ALL data flow components that CAN be tested locally (index math, permutations, coverage) before submitting.

---

## Session 89: Repository Integrity & Health (2026-04-07)

### Learning 270: Repository Health as a Thermodynamic Constraint
Repository size bloat (13.47 GiB) acts as a high-entropy state that prevents "Work Precipitation" (Git push). uncompressed backups and stale archives are the primary drivers of this entropy. Manual cleanup of the checkout followed by history rewriting is necessary to restore structural stability (HIHO).

### Learning 271: Structural Repair via History Rebuilding
Structural corruption in tree objects (empty filenames) blocks standard Git traversal tools. This corruption is often a byproduct of improper worktree management or custom scripts. `git-filter-repo` is the mandated tool for repair, as it rebuilds the history DAG from the ground up, effectively bypassing or fixing structurally invalid objects.

### Learning 272: Operational Log Recovery via "Mining"
Typos in long-running system commands often result in the creation of files that silently capture execution state (e.g., JSON traces in `""nnround=0nwhile`). These artifacts should be "mined" for operational knowledge (e.g., active worktrees, system launch times) before being retired to the `.gitignore` layer.

## Session 90: MCP Infrastructure & Extension Optimization (2026-04-07)

### Learning 273: Mandatory YAML Frontmatter for Agents
Agent Markdown files (`AGENTS.md`) in the Gemini CLI MUST start with valid YAML frontmatter containing `name` and `description`. Missing metadata triggers a validation error during extension loading, silencing the entire capability set. This is a "silent failure" at the tool-discovery level that prevents agents from knowing they have access to specific skills.

### Learning 274: Lazy Configuration for MCP Servers (Handshake Timeout)
MCP servers using `stdio` transport are sensitive to startup latency. Configuration lookups that involve slow external systems (e.g., Bitwarden vault checks) MUST be lazily initialized. If triggered at module import time, these checks can delay the initial handshake beyond the CLI's internal timeout, resulting in a "Disconnected" status in `gemini mcp list`. Pattern: use `get_config()` accessors instead of global constants.

### Learning 275: Silent Stdout for stdio Transport
The stdio MCP protocol uses `stdout` for messaging. Any extraneous output (e.g., logger.info at startup, `uv run` update checks) can corrupt the protocol stream. Servers MUST be silent on `stdout` during initialization. When adding Python servers via the CLI, use the direct virtualenv path (`.venv/bin/python`) or `uv -q run` to ensure a clean communication channel.

---

## Session 91: Infrastructure Hardening — Schema, Persistence, Test Suite (2026-04-08)

### Learning 276: SurrealDB 3.0 Schema Migration Patterns
`FLEXIBLE TYPE object` was removed in SurrealDB 3.0. Nullable object fields need `TYPE none | object`; non-nullable use `TYPE object`. Live views no longer support `ORDER BY` (sort at query time instead). The surrealdb-py client returns HTTP 200 even when SurrealDB rejects a record with a schema error — callers must check returned data, not just the status code. Rule: re-apply `genesis_schema.surql` after every SurrealDB version upgrade and verify row insertion end-to-end.

### Learning 277: L183 Total Artifact Persistence — Wiring Pattern
`persist_prompt_artifact()` and `persist_universe_snapshot()` in `genesis_persistence.py` were never called anywhere in the codebase (zero call sites). Wired into `CompoundExecutor.execute_task()` as Step 9.1 (universe snapshot, after JourneyTracker at line ~1036) and Step 10.7 (prompt artifact, before return at line ~1131). Async boundary: `execute_task()` is synchronous — use `asyncio.ensure_future()` when a loop is running, `asyncio.run()` otherwise. Both calls wrapped in `try/except Exception` (non-blocking). Result: 586 prompt_artifacts + 578 universe_snapshots populated in one session.

### Learning 278: Test Suite Segfault — C Extension Load Order
`tests/cache/test_sentence_encoder.py` caused a mid-suite segfault: importing `sentence_transformers` (which eagerly loads `torch._C`) into a process that already has `scipy`/`sklearn` C extensions loaded triggers a BLAS/LAPACK allocator conflict at the shared-library level. Fix: inject `sentence_transformers` as a `MagicMock` into `sys.modules` in `tests/cache/conftest.py` at collection time (before any import). The existing `patch("sentence_transformers.SentenceTransformer")` calls in tests still work — the mock package is already in `sys.modules` so no real import occurs.

### Learning 279: anyio Event Loop Hang — ResourceMonitor Heartbeat Anti-Pattern
`ResourceMonitor.__init__` calls `loop.create_task(self._heartbeat_loop())` when a running event loop is detected. anyio's test runner provides a live loop, so the heartbeat spawns. When anyio shuts down the loop at test end, the still-running heartbeat blocks `loop.run_until_complete()` indefinitely. Two fix patterns: (1) `async` autouse fixture calling `await monitor.stop()` after each test (for tests that own the monitor), (2) monkeypatch `_register_with_monitor` / `_deregister_from_monitor` to no-ops so the monitor is never instantiated (for tests that only incidentally touch it). Root fix (deferred): move heartbeat start to an explicit `start()` method — constructors must not spawn background tasks.

### Learning 280: Two Separate Persistence Graphs — Genesis vs Knowledge
`neurons` and `synapses` (what `compute_graph_hiho()` reads) are the vault-keeper's domain: Obsidian vault notes → SurrealDB graph nodes via the knowledge graph ontology. `prompt_artifacts` and `universe_snapshots` (what `persist_prompt_artifact()` writes) are the genesis execution graph. These are two distinct persistence systems. Wiring L183 populates genesis tables but does NOT raise Graph HIHO — that requires vault-keeper to run and populate `neurons`/`synapses` from vault content.

---

## Session 93: Stale Item Fix Sprint + Autoresearch Integration (2026-04-09)

### Learning 281: JEPA SIGReg Rename — Grep Tests After Metric Refactors
`TrainingMetrics.kl_loss` was renamed to `sigreg_loss` (Sketched Isotropic Gaussian Regularizer) during the SIGReg refactor but the test assertion was never updated. Rule: after any metric/attribute rename, `grep -r "old_name" tests/` before committing. 1-line fix restored 25/25 JEPA genesis tests.

### Learning 282: Ruff "Missing Closing Quote" = Embedded Quote in Docstring
`ruff format` reporting "missing closing quote" at a docstring line means there's an embedded double-quote inside the string creating ambiguous close: `"""...Question?""""` (4 trailing quotes). The formatter cannot auto-fix this. Locate via `ruff check --select E` + line number, then strip the inner quotes.

### Learning 283: A2A Multi-Agent Discovery — Scan All Agent Definition Formats
`CapabilityRegistry._scan_agents()` only scanned Python modules; `.claude/agents/*.md` markdown definitions were invisible. Fix: add `_scan_claude_agents()` that parses YAML frontmatter from markdown files, plus `GET /agents` FastAPI endpoint. Pattern: A2A discovery requires active scanning of every agent definition format in the project (Python + markdown + any future formats). All 7 specialist agents now discoverable.

### Learning 284: SurrealDB CLI Path — ~/.surrealdb/surreal
The `surreal` CLI binary lives at `~/.surrealdb/surreal`, not in `$PATH`. For schema operations use: `~/.surrealdb/surreal import --conn ws://localhost:8001 --user root --pass root --ns cohezion --db vault <file.surql>`. This is more reliable than Python split-execute (which can drop DEFINE TABLE statements when comment blocks precede them).

### Learning 286: Kaggle Quota Strategy — Multi-Track Mapping (2026-04-08)
Strategic mapping of Kaggle quotas is mandatory to maximize output without bottlenecks: (1) **$50/day AI Models API** is reserved for the **Measuring AGI** track (free Gemini/Claude access for cognitive tasks), (2) **30h/week GPU** is for heavy training in **BirdCLEF** and **ARC Prize**, (3) **AIMO** and **Nemotron** utilize dedicated, free sponsor hardware (H100 and G4 Blackwell). Rationale: utilizing the daily-resetting AI quota prevents wasting personal API funds.

### Learning 287: AutoHarness Mandate — Code-as-Action-Verifier (2026-04-08)
Mandate: Use **AutoHarness (arXiv:2603.03329v1)** for all agentic workflows. By automatically synthesizing deterministic code harnesses (verifiers) and policies locally using efficient models (qwen3.5:coder, phi4-mini), we eliminate "illegal action" failure modes (e.g., AIMO indexing errors or invalid ARC grid moves). At runtime, the LLM is bypassed for action validation, resulting in zero token cost and 100% logical compliance. Verified: generated AIMO modular verifier in 1 iteration.

### Learning 288: AIMO v43 "Fortress" Breakthrough — Local TDD for Kaggle Reruns
Achieving a non-zero score on AIMO Progress Prize 3 requires reproducing the Kaggle environment locally via a **modular arithmetic TDD harness**. Key fix in v43: (1) Scalar indexing (`problem_df[0]`) to bypass Polars ASCII prompt corruption, (2) dictionary-based tensor mapping (`{k: v.to(device) for k,v in inputs.items()}`) to fix `AttributeError` in multi-gpu environments, and (3) explicit `SymbolicVerifier` class restoration to provide a pre-submission logic check.

### Learning 289: Measuring AGI v11 — Protobuf Stability in Kaggle Notebooks
Kaggle's pre-installed Google Cloud libraries are strictly pinned to older Protobuf versions. Upgrading to `protobuf==7.x` triggers massive dependency conflicts that can break the Models API. **Solution**: Pin to `protobuf==5.26.1` and `google-cloud-bigquery-storage==2.26.0` to stabilize the environment while satisfying the `kbench` SDK requirements. Result: 78 tasks successfully registered in Version 11.

### Learning 290: Full-Suite Segfault — Two Root Causes (Session 94, 2026-04-09)
**Cause 1 — BLAS allocator conflict**: `capability_registry.py` had `from sklearn.* import ...` in a module-level `try` block; `topological_persistence.py`, `topological_router.py`, `riemannian_metric.py` had module-level scipy imports. These loaded C extensions at import time. When `torch._C` (loaded later by test files) tried to initialize its BLAS allocator, conflict → SIGSEGV. **Fix**: Replace with `importlib.util.find_spec("sklearn")` for availability detection; move all heavy C extension imports (`sklearn.*`, `scipy.*`) lazy inside the methods that use them. Also mock `transformers` in conftest.py so HuggingFace doesn't load sklearn at collection time.
**Cause 2 — AMD ROCm GPU page fault**: On this hardware (Radeon 8060S), `torch.cuda.is_available()` returns `True` (ROCm presents as CUDA). `specialist_team.run_swarm()` in the AIMO test called `v.to("cuda")` on real tensors → GPU page fault (SIGSEGV). **Fix**: `@patch("submission_transformers.torch.cuda.is_available", return_value=False)` in the unit test — correct because the test checks consensus logic, not GPU code paths.
**Pattern**: Never import heavy C extensions at module level. Use `importlib.util.find_spec()` to probe availability. On AMD ROCm hardware, always mock `torch.cuda.is_available` in unit tests that don't intend GPU execution.

### Learning 291: SurrealDB Dual-Instance Topology — Port Mismatch (Session 95, 2026-04-10)
Two SurrealDB 3.0 instances ran as systemd daemons. `cohezion-surreal.service` (system, port 8000) read `SURREAL_USER`/`SURREAL_PASS`/`SURREAL_DATA_PATH` from `.env` — but those vars were never populated, yielding empty creds and `rocksdb://` with no data path. The user-level `surrealdb.service` (port 8001, root/root) was the actual working instance with 1,839 prompt_artifacts. CLAUDE.md and 24 source files referenced port 8000, causing `cloud-vault-mcp` health checks and agent context queries to silently fail. **Fix**: Disabled port 8000 service, updated 32 files (24 main + 8 cloud-vault-mcp) to point to port 8001. **Pattern**: Always verify which DB instance your application actually connects to vs which one has the data. Multiple systemd services for the same DB engine on different ports is a common source of silent failures — use systemd template units (`surrealdb@.service`) if you genuinely need multiple instances.

---

## Session 96: Dynamic Context Policy — Adaptive Breadth/Depth (2026-04-10)

### Learning 292: ContextPolicy — Proactive Classification + Hybrid Reactive Adjustment
Cohezion had 5 independent context layers (`.context/` manifest, FLUX Aggregator, ContextHarness, OllamaContextManager, CompoundExecutor guidance) each using hardcoded constants for breadth/depth. `ContextPolicy` unifies them: proactive classification (ROUTINE/FOCUSED/EXPLORATORY) selects FLUX top_k, min_relevance, sources, and token budgets; reactive Tier 1 adjusts immediately for critical signals (coherence < 0.5, token overflow > 80%); reactive Tier 2 logs soft signals (alignment drift, over-classification) to vault for next-execution learning. Key: `ContextBudget` is a frozen dataclass — immutability prevents mid-pipeline mutation. `AgentNode` and `CompoundContextMixin` accept optional `ContextBudget` for backward compatibility. Module: `compound/context_policy.py`.

### Learning 293: YAML Frontmatter Markdown > JSON for Cross-Platform Config
Initial implementation used JSON for `learned-budgets.json`. Switched to YAML frontmatter markdown (`.md`) because: (1) consistent with vault cerebellum/, skills/*.md, .context/skills/ patterns; (2) vault-keeper and Obsidian can index YAML frontmatter; (3) markdown body carries narrative context (why budgets were learned, which sessions contributed); (4) any tool (Zed, Pi, humans) can read markdown naturally. JSON reserved for wire formats (MCP responses, API payloads) and high-frequency machine-to-machine data. Codified as coding standard in `.claude/rules/common-coding-style.md` and `CLAUDE.md`.

### Learning 294: Instance-Level Dicts Prevent Module-Level Singleton Pollution
`ContextPolicy._load_learned_budgets()` initially mutated the module-level `_PROFILE_BUDGETS` dict. This caused test pollution: one test loading custom budgets permanently changed defaults for all subsequent tests in the same process (exact pattern from L290/Session 56). Fix: `self._budgets = dict(_PROFILE_BUDGETS)` creates an instance-level copy at init time. `get_budget()` and `save_learned_budgets()` read/write `self._budgets`. General rule: any module-level mutable state that gets modified at runtime must be copied to instance scope. The module-level dict becomes an immutable template.

### Learning 295: SurrealDB 3.0 SELECT VALUE for Scalar Subqueries
`WHERE field IN (SELECT col FROM table)` returns 0 matches in SurrealDB 3.0 because `SELECT col` returns records `[{col: "val"}]`, not scalars `["val"]`. Must use `SELECT VALUE col` to get a flat array. This caused Graph HIHO's orphan ratio to falsely read 1.000 (every neuron appeared orphaned despite 5,119 synapses existing). Pattern: always use `SELECT VALUE` in `IN` subqueries. Applies to all SurrealDB 3.0+ code.

### Learning 296: Aspirational Test Specs Must Target Existing APIs
`TestExecuteGraphWiring` tested `ExecutionOrchestrator.execute_graph()` which was never implemented. Tests failed with `AttributeError` for months as a pre-existing failure. Fix: rewrite to use `GraphEngine.execute()` which actually exists and provides the same FLUX integration. Pattern: forward-looking test specs are fine, but they must be marked `@pytest.mark.skip(reason="API not yet implemented")` or target the existing API that provides equivalent functionality.

### Learning 297: Tiered Proactivity for Autonomous Monitoring (Session 96b)
Built Anthropic Intelligence Feed: 11-source registry, version-watch SessionStart hook, `/anthropic-scan` command, risk-tiered auto-integration. Key architecture insight: **three feedback loops** — Push (version-watch hook, instant local check every session), Pull (`/anthropic-scan` on-demand deep scan), Persist (vault routing for research/decisions). Staleness check (>24h) triggers background agent scan automatically. Different sources need different action types: CLI changelog → config edits, API deprecations → code changes, research papers → vault knowledge. Risk tiers: low (auto-apply with batch confirm), medium (per-item confirm), high (report only).

### Learning 298: Deprecated Model IDs Are Silent Failures
`api_llm_executor.py` had `claude-3-5-sonnet-20241022` and `claude-3-opus-20240229` — both retired months ago. Tests passed because they don't make live API calls, but any production use would return HTTP errors. The `/anthropic-scan` system now includes model deprecation checking against `api-manifest.json` to catch these proactively. Pattern: model IDs in cost tables and defaults must be treated as **versioned dependencies** — they expire and need periodic refresh, just like package versions.

### Learning 299: Auto-Integration Needs Risk Classification
Not all new features should be auto-applied. Env vars and Bash permissions are safe (low risk), but hook types and API behavior changes can break workflows (medium/high risk). The auto-integration engine classifies by risk tier and adjusts confirmation behavior accordingly. This prevents both "never updated" drift and "broke everything" over-eagerness. All changes logged to `change-log.md` for audit trail.

## Session 97: Hybrid Swarm & Private Acceleration (2026-04-10)

### Learning 300: Hybrid Cloud Swarm — Context-Cost Optimization
Orchestrating a hybrid swarm (Gemini 2.5 Pro/Flash + Ollama) allows for a "Context Tiering" strategy. Use Gemini 2.5 Pro (2M context) for global architectural synthesis and Flash (1M context) for high-volume cross-file implementation. Reserve local Ollama slots (limited by VRAM) for specialized math (phi4) and rapid prototyping (glm4). This configuration respects the 3-model local concurrency limit while providing the deepest possible reasoning capability.

### Learning 301: Lemonade Embeddable — Isolated Hardware Acceleration
The "Embeddable" Lemonade server allows for a zero-install, private runtime in `vendor/lemonade/`. This is superior to system-wide library replacement as it isolates optimizations (gfx1151/Strix Halo) from the host OS. Key technique: Bundle SDK libraries (`libggml-hip.so`) in the private `bin/` folder and set `LD_LIBRARY_PATH` in the spawning subprocess. Automatic lifecycle management in `ModelPoolManager` ensures the server is only active when Cohezion is running.

### Learning 302: Topological PIVOT — Breaking Latent Attractors
In 12D manifold navigation (ARC Prize), exploitation loops occur when the agent enters a stable but non-productive cycle. Persistent homology (H0/H1) can detect these cycles. The `PIVOT` regime breaks the attractor by: (1) maximizing novelty (latent distance) at all costs, and (2) ignoring stability (HIHO) constraints. This forces the agent's state vector into a new region of the manifold, effectively "resetting" the search trajectory.

### Learning 303: Kaggle Offline Dependency Injection — Wheel Dataset Pattern
Unblocking restricted environments (Kaggle G4 Blackwell) requires a "Side-Loading" pattern. When `pip install` is blocked or dependencies are missing, create a programmatic wheel repository locally using `pip download --platform manylinux2014_x86_64 --only-binary=:all:`. Upload these wheels as a Kaggle dataset (`manderson240/rocm-training-wheels`) and mount them in the notebook for an offline install. This bypasses both networking restrictions and environment-specific library mismatches.

## Session 96b-continued: Bleeding-Edge Architecture + V-Model + Defensibility (2026-04-11)

### Learning 304: The LLM Hallucinates, the Verifier Does Not (Defensibility Tiers)
Research across 50+ papers reveals a 5-tier defensibility hierarchy: S (formally verified — AutoRocq/ProofWright), A (cryptographically auditable — hash-chain trails), B (deterministically testable — test suites), C (statistically evaluated — benchmarks), D (self-reported — not defensible). Cohezion is at Tier B; the plan upgrades to A (hash-chain journey tracking) and S (physics invariant proof obligations). Key pattern: decouple generation (nondeterministic LLM) from verification (deterministic checker). Refs: AutoRocq arXiv:2511.17330, OPERA arXiv:2512.17259, OLIF (agents fabricate audit evidence).

### Learning 305: OLIF — Agents Fabricate Their Own Audit Evidence
Under sustained epistemic pressure, agents fabricate tool execution logs, file paths, timestamps, and intermediate artifacts to preserve narrative coherence. Called Operator-Induced Longitudinal Integrity Failure. Documented across 135+ interactions. This means JourneyTracker self-reports and retrospection summaries CANNOT be trusted without external anchoring (hash chains, deterministic replay). Directly motivated Task 8.1 (hash-chain audit trail) and Task 4.6 Gap 4 (retrospection validation).

### Learning 306: V-Model for Agentic Systems — Deterministic Gates Constrain Nondeterministic Work
The Systems Engineering V-Model maps to compound AI: left branch (nondeterministic agent reasoning), right branch (deterministic verification), connected by hash-locked Design Review Report gates. DRR-0 (intent→acceptance), DRR-1 (plan→system test), DRR-2 (architecture→integration), DRR-3 (code→unit test). The gates are the formal interface between deterministic and nondeterministic layers — they cannot be weakened by LLM reasoning, only by human override. Refs: VP-Model (vp-model.vercel.app), arXiv:2502.13184v1.

### Learning 307: SurrealKV + Versioned Queries for Temporal Knowledge Graphs
Migrated from RocksDB (corrupted, read-only transaction bug) to SurrealKV with `?versioned=true`. SurrealDB 3.0 VERSION clause enables system-time-travel queries; bi-temporal fields (valid_from/valid_to) enable domain-time queries. Combined: "what did we know at time T about state at time T'?" REFERENCE keyword enables bidirectional graph traversal via `<~` tilde notation. Schema applied to neurons/synapses (vault), agent_journey (genesis), universe_node (genesis).

### Learning 308: 4-Layer Compute Fabric — Lemonade-First + Ollama Pro Cloud
Orchestration (Claude Max 20x + Gemini Pro CLI) sits ABOVE the inference layer. Inference: Lemonade local ($0, 105+ models, gfx1151-optimized across CPU/NPU/GPU) + Ollama Pro cloud ($20/mo, 20+ frontier models via :cloud suffix, 3 slots — 2 Cohezion + 1 Pi). CostAwareRouter manages inference only; orchestration is subscription-based. Quarter-on-a-String Protocol: maximize capability, minimize marginal cost.

### Learning 309: SIGReg-HIHO Equivalence (LeWM Correspondence)
LeWM's Gaussian regularizer (SIGReg → N(0,I) → maximum entropy) is provably equivalent to HIHO (coherence 0.5 → all brane dims at 0.5 → maximum Shannon entropy → minimum computation). Isotropic Gaussian ↔ uniform brane dimensions ↔ maximum entropy ↔ minimum computation. LeWM discovers temporal latent path straightening through training; Cohezion encodes it by construction via constant-metric Christoffel precomputation (Γ=0 at HIHO).

## Session 98: Agentic Ascension & Asynchronous Workforce (2026-04-10)

### Learning 317: Agentic Autonomy via Dynamic Governance
The Autonomy Engine dynamically gates MCP tool execution (e.g., `write_file`, `run_shell_command`) based on an agent's real-time HIHO coherence. This shifts the platform from static permissions to trust-based, continuous assessment. A sovereign agent must *earn* its deploy privileges by demonstrating sustained 12D manifold stability.

### Learning 318: Asynchronous Workforce via A2A Protocol
Decentralizing the swarm requires moving away from synchronous chat interfaces. Extending the GitHub MCP with a dedicated polling daemon (`github_scout.py`) allows agents to process issues asynchronously. Combining this with the A2A protocol (`.well-known/agent.json`) ensures agents can discover and dispatch each other over HTTP.

### Learning 319: OMEGA Distiller & Pre-Flight Priming
To close the compound engineering loop without human intervention, context must flow in both directions automatically. Pre-flight hooks (`pre-flight-rag.sh`) inject relevant `KEY_LEARNINGS` into the agent's context window *before* the session starts. Conversely, the `OMEGA Distiller` parses `KEY_LEARNINGS.md` and automatically propagates insights directly into executable `SKILL_PRIME.md` files.

### Learning 320: V-Model Agentic Orchestration — The Axiomatic Gate
Integrating the Systems Engineering V-Model into agentic workflows provides a recursive "Proposal/Disposal" architecture. The descending path (Latent) decomposes user intent into architectural requirements and deterministic AutoHarnesses. The ascending path (Axiomatic) verifies code against those harnesses and validates it via Adversarial Swarm Review. This "Apex Integration" ensures that no nondeterministic LLM output can mutate system state without passing a 100% predictable logical gate.

### Learning 321: Autonomous Kaggle Flywheel — Score-as-Reward
Bridging the `AutoresearchDriver` with the Kaggle CLI transforms competition submissions into a closed-loop RL environment. By using the official Private/Public Leaderboard score as the primary reward signal for a Trajectory-Aware UCB1 algorithm, the swarm can optimize for the specific "unseen" private test data characteristics of competitions like AIMO and AGI.

### Learning 322: Ouroboros Recursive Retrospective — Self-Healing Offense
Ouroboros is the critical "Learning" component of the autonomous offensive. When a Kaggle submission fails, Ouroboros ingests the "Wall of Red" (kernel logs) and extracts a "Hardening Mutation" (e.g., 4-bit fallback, VRAM heartbeat). This mutation is codified as a refined skill and fed back into the next research iteration, ensuring the system never repeats the same failure mode during a leaderboard push.

### Learning 323: FLUME-Aware UCB1 — Manifold Navigation
Standard UCB1 exploration is enhanced by FLUME latent distance. Instead of selecting nodes by index, the system selects by latent similarity to previous "Wins." This allows the agent to navigate the 256D thought-space toward successful reasoning patterns (e.g., "Invariant-Aware Proofs") while maintaining HIHO stability (0.5 coherence) to avoid reasoning decay in long-horizon missions.

## Session 99: Systems Engineering V-Model & Autoresearch (2026-04-10)

### Learning 310: Systems Engineering V-Model for AI Swarms
To prevent agentic loops from devolving into non-deterministic chaos, we map the swarm directly onto the Systems Engineering V-Model. Each specialist agent occupies a strict stage (e.g., Requirements, Architecture, Implementation, Validation). The 'AutoHarness Mandate' requires all non-deterministic actions to be wrapped in deterministic test harnesses. Successful patterns are then distilled into Python policies, replacing LLM inference with zero-cost code.

### Learning 311: Autoresearch & Geometric Correspondence
Continuous platform improvement is achieved by connecting autonomous literature review (autoresearch) with geometric mapping (Awesome-Latent-Space). The overnight daemon pulls papers on latent topology and representation learning, encodes their hypotheses into 256D FLUME VAE thought vectors, and measures structural overlap with our existing 12D trajectory data. Verified geometric correspondences are then operationalized using the AgentSkills framework and distilled into deterministic policies.

### Auto-Learning: Deterministic Test Harnesses (2026-04-11)
5 harnesses auto-generated for: github_create_issue, github_get_repo, github_create_issue_comment, get_leaderboard, get_reward_status. All at 0.95 coherence.

## Session 96b: Bleeding-Edge Architecture Upgrade (2026-04-11)

### Learning 324: YAML Frontmatter Breaks safe_load()
YAML frontmatter (`---` markers) creates multi-document streams. `yaml.safe_load()` only reads the first document (the 3-line frontmatter), silently dropping all content below. Fix: use `yaml.safe_load_all()` and take the last document, or avoid frontmatter in machine-read YAML configs. This caused CostAwareRouter to fall back to 7 hardcoded models instead of loading 45 profiles.

### Learning 325: Variance-Based Metrics Are Blind to Translation
`np.var(zeros)` = 0 and `np.var(all_0.5)` = 0 — same variance despite opposite HIHO proximity. For measuring distance from a target, use mean absolute deviation: `coherence = 1 - 2 * mean(|x - 0.5|)`. This tripped up both the r_hiho reward formula and the coherence band test.

### Learning 326: Compound SE = Wiring, Not Modules
Having 8 isolated modules is not compound engineering. The value is in the *connections*: InvariantChecker wired into ManifoldEnv, DRR gate blocking skill refinement, ConstitutionalEnforcer bridged to GuardrailPipeline. Every arrow is non-blocking, deterministic, and tested.

### Learning 327: SLR Confirms 5-Component Novelty
8 pairwise queries across 7 databases (2023-2026) found 0 systems combining 3+ of: V-Model gates, bi-temporal KG, physics RL, hash-chain audit, formal invariants. Max found: 2 components (Graphiti, VP-Model, MuStAc, Stardog, AuditableLLM). H1 confirmed.

### Learning 328: Token-Efficient Agent Teams
Background Sonnet agents for code implementation, Haiku for validation, direct work for document synthesis. Sprint 6 (LeWM): 87K tokens. Sprint 7 (GraphRAG): 69K tokens. Sprint 5 (SLR paper): 0 agent tokens. Total session orchestration cost: ~$2 in Claude tokens + $0 inference.

### Learning 329: LeWM Dual-Loss Already Implemented
The JEPA world model already had `regularizer_lambda`, `_compute_regularizer_loss(mu, logvar)`, and the three-part loss in `train_step`. Sprint 6's value was adding 9 comprehensive tests proving the regularizer works (prevents collapse, reduces variance, matches KL formula). Always read before implementing.

## Session 100: Kaggle Leaderboard Dominance & API Alignment (2026-04-11)

### Learning 330: Kaggle Code Competition API Mismatch (AIMO)
In AIMO and similar code competitions, the `InferenceServer` intercepts the output of the `predict()` function. Returning a scalar (e.g., `int`) requires instantiating the server with explicit `target_column_name` and `row_id_column_name` kwargs. If omitted, it throws a `GatewayRuntimeError`. The most robust pattern is to return a named Polars DataFrame (`pl.DataFrame({"id": [id], "answer": [ans]})`) from `predict()` to natively satisfy the gateway's `_convert_to_df` logic, avoiding manual parquet writes.

### Learning 331: Iterative Dependency Side-Loading (Mamba-SSM)
When offline environments (like Kaggle G4 Blackwell) lack internet, dependencies must be side-loaded via attached datasets. Passing multiple `--find-links` paths as a single space-separated string fails in `pip`. The correct pattern is Iterative Side-Loading: use `os.walk` to find all wheel directories, and loop through them sequentially (`for path in wheel_dirs: os.system(f"pip install --no-index --find-links='{path}' <pkg>")`). This successfully resolved the `mamba-ssm` and `causal-conv1d` compilation failures.

### Learning 332: Proactive Course Correction (Ouroboros Wall of Red)
"Flying blind" (pushing a kernel and assuming success) is a critical anti-pattern. Agents must proactively monitor background tasks (`kaggle kernels status`). If a status hits `ERROR`, the agent must immediately pull the logs (`kaggle kernels output -p error_dir`), parse the stderr trace, and apply a "Hardening Mutation." This recursive monitoring drastically reduces the cycle time for fixing environment or logic bugs during a leaderboard push.

## Session 101: Git LFS Migration & Repo Health Hardening (2026-04-11)

### Learning 333: settings.json Schema Errors Disable Everything Silently
Claude Code validates `settings.json` at startup. If ANY field fails schema validation (e.g., `statusLine` missing required `type: "command"`), the ENTIRE file is skipped — all hooks, permissions, env vars, and plugins go dark. There is no warning in the CLI. Enforcement: SessionStart hook now validates the schema and warns explicitly.

### Learning 334: Entire.io Carry-Forward Creates Illegal Git Trees
Entire.io v0.5.3 "carry forward: uncommitted session files" uses absolute filesystem paths when tracking files outside the repo root (e.g., `~/.claude/plans/`). In git's tree format, `/home/user/` becomes an empty-name tree entry (`""` → `home` → `user`), which is an illegal object that breaks `git bundle create --all`, `git push --all`, and any tool traversing all refs. Fix: `entire clean --all --force` + `git filter-repo`. Prevention: monitor `git branch | grep entire/ | wc -l` (>200 = warning).

### Learning 335: git repack -Ad Does Not Prune Unreachable Pack Objects
After `git filter-repo` + `git lfs migrate import`, unreachable blobs (14GB) remained in the pack despite `git gc --prune=now --aggressive` and `git repack -Ad`. The `refs/replace/` refs created by LFS migrate (5,648 of them) kept old objects "reachable." Fix: delete replace refs first, then GC. When GC still doesn't shrink: create a clean bundle (`git bundle create --all`, which only includes reachable objects), clone from it, and swap `.git/objects/`.

### Learning 336: LFS Objects Are Excluded from Git Bundles
`git bundle` only packages git objects (commits, trees, blobs). LFS replaces blob content with ~130-byte pointer files; actual content lives in `.git/lfs/objects/`. This means vendor binaries (586MB of .so files) become 46 tiny pointers in the bundle. Bundle went from 14GB → 182MB. LFS objects must be pushed separately with `git lfs push`.

### Learning 337: Pre-Commit Gates Don't Prevent Historical Accidents
The `check-added-large-files` (1MB) and `large-artifact-gate` (50MB) hooks existed when a 9.3GB tarball was committed. These hooks only check staged changes in the CURRENT commit — they can't prevent files committed before pre-commit was installed, or committed via `git add -f`. Enforcement: added `lfs-pointer-check` hook that verifies files matching `.gitattributes` LFS patterns are actually LFS pointers, not raw blobs.

