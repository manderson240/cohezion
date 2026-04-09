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

## Session 90: AIMO 3 — Mathematical Reasoning Swarm & H100 Optimization (2026-04-05)

### Learning 265: AIMO 3 "Winning Meta" — Inference-Time Scaling
The transition from AIMO 2 to AIMO 3 (April 2026) codified the "Compute-to-Reason" meta. Success on the 110-problem IMO-level test set requires: (1) Diverse Prompt Mixer to decorrelate errors across independent runs, (2) Weighted Entropy Voting ($w = 1 + 1 / (\text{entropy} + 0.1)$) to allow confident attempts to override noise (arXiv:2603.27844v1), and (3) Speculative Decoding to bypass the 163s/problem compute bottleneck.

### Learning 266: H100/Blackwell Handshake & vLLM Hard Resets
 request H100 hardware on Kaggle via `machine_shape: NvidiaH100` (or `NvidiaRtxPro6000`) within a `.ipynb` Notebook context. To survive the 5-hour marathon and known vLLM 0.7+ memory leaks, implement "Hard VRAM Resets" (gc.collect + torch.cuda.empty_cache) every 10 problems. Pure Equal Division time budgeting with a 30s "Safety Trigger" (returning default 0) ensures a complete submission and prevents disqualification.

### Learning 267: Speculative Decoding for Tool-Integrated Reasoning (TIR)
Speculative Decoding (e.g., DeepSeek-R1-32B paired with Qwen2.5-1.5B drafter) provides a 1.5x-1.8x throughput multiplier. This is critical for TIR, as it allows the "Reasoning Swarm" to perform multiple code-execution and self-correction cycles within the 5-hour window. This "bought back" time is more valuable for accuracy than increasing the base model size to 70B+ which risks OOM via KV cache accumulation.

### Learning 268: Kaggle "Hidden Set" Debugging & Polars Series Pitfall
Surviving the Kaggle Private Rerun requires a "Fortress" architecture where every problem is wrapped in resource guards. A critical discovery: the AIMO 3 API passes `pl.Series` objects to the `predict` function. Standard DataFrame indexing (e.g., `df[0, 0]`) on a Series returns a new Series containing duplicate data, which stringifies into a Polars ASCII table. This corrupts LLM prompts with metadata (e.g., `shape: (2,) Series: ...`). Scalar indexing (`df[0]`) is mandatory to ensure the LLM receives raw text. Reference: `KAGGLE_STABILITY_PROTOCOL.md`.

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

### Learning 233: ManifoldEnv Curriculum Reward — 3-Stage Reach→Maintain→Optimize (2026-04-01)
3-stage curriculum reward in ManifoldEnv: Stage 1 (reach HIHO band) rewards coherence gain + entry bonus, Stage 2 (maintain stability) rewards band persistence + low energy, Stage 3 (energy efficiency) strongly penalizes energy while maintaining HIHO. Proximity base reward (-deviation * 0.5) is always active across all stages, preventing drift. Module: `environments/manifold_env.py`.

### Learning 234: UniverseEvaluator — Bootstrap CI Evaluation (2026-04-01)
Unified evaluation framework with bootstrap confidence intervals distinguishes genuine capability from noise. EpisodeMetrics tracks convergence_rate, hiho_stability_duration, energy_efficiency. PolicyComparison computes effect sizes and p-values. 3 built-in baselines: random_policy, greedy_hiho_policy, noisy_greedy_policy. Key: random baseline as sanity check — if random > trained, reward is broken. Module: `eval/universe_evaluator.py`.

### Learning 235: RoutingOrchestrator — Unified Entry for 4 Routing Systems (2026-04-01)
Single UnifiedRoutingDecision combining SmartRouter (affinity), CostAwareRouter (complexity→model), TipOfTheSpearRouter (constitutional), DynamicModelRouter (health). Confidence flows through all routers as common signal. Lazy initialization prevents import cascades. Module: `swarm/routing_orchestrator.py`.

### Learning 236: TDD + Code Review Compound Loop (2026-04-01)
TDD catches behavioral correctness but misses cross-cutting concerns. Multi-perspective code review agent catches type safety (vault_experiment_path=None vs str=""), format string bugs (%.1%% → %.1f%%), and missing __all__ exports. Pattern: run code review in background while coding next feature — zero idle time, catches 2 CRITICAL bugs per session.

### Learning 237: Reward Alignment Must Match Physics Grounding (2026-04-01)
First PPO training on ManifoldEnv: 0% convergence (mean coherence 0.272) vs 60% convergence for RANDOM POLICY. Root cause: differential-only reward (coherence_gain * 2.0) creates oscillation incentive — agent maximizes rate of change by dropping then recovering coherence. Fix: proximity base reward (-deviation * 0.5, always active) aligns reward with Lagrangian attractor. The physics grounding is so strong that natural dynamics guide 60% of random trajectories to HIHO — the reward must align with the physics, not create perverse incentives against it. Deeper insight: reward hacking in physics-grounded environments takes the form of fighting the dynamics, not exploiting them.

### Learning 238: Small Actions Cooperate With Physics — Action Scale = Dynamics Timescale (2026-04-01)
PPO Run 2 with large actions [-0.5, 0.5] failed despite proximity reward fix (reward -67.68). PPO Run 3 with small actions [-0.1, 0.1] breakthrough: coherence 0.915, reward 12.04, stability 79 steps. The Lagrangian attractor is strong enough to guide dynamics — large actions fight it, small actions cooperate. General principle: when physics grounding provides a strong attractor, action scale must be proportional to dynamics timescale (dt=0.01 → action ~0.1). This is structural safety — the environment's physics prevents reward hacking by constraining the action manifold.

### Learning 239: Structural Safety via Lagrangian Dynamics (2026-04-01)
ManifoldEnv's Lagrangian dynamics provide structural safety guarantees that learned safety constraints cannot: (1) energy conservation bounds agent behavior, (2) Christoffel symbols create "natural corridors" in state space, (3) HIHO attractor is a physical equilibrium, not a learned policy artifact, (4) random agents achieve 60% convergence because the physics itself guides trajectories toward HIHO. This contrasts with standard RL environments where safety requires learned constraints that can be gamed.

### Learning 240: Safety-Gymnasium Compatibility — Physical vs Learned Constraints (2026-04-01)
ManifoldEnv maps to Safety-Gymnasium: cost_rate=Lagrangian action, constraint_satisfaction=% in HIHO band, safe_return=reward in safe region. Key: constraints are physical (Lagrangian), not learned — violations are physically impossible, not merely penalized.

### Learning 241: 4-Iteration Training Diagnostic Loop (2026-04-01)
Pattern: train→diagnose failure→hypothesize fix→retrain→verify. Run 1: differential reward → oscillation incentive. Run 2: +proximity reward → still fails (large actions). Run 3: +small actions → breakthrough (0.915 coherence). Run 4: 100K steps → PPO outperforms random on reward (+17%) and stability (+9%). Each iteration was hypothesis-driven with a single variable change. Persist every run to SurrealDB for knowledge accumulation.

### Learning 242: ERL — Empirical Reward Landscape as Safety Metric (2026-04-01)
Probe reward with adversarial actions → map hackable surface. ManifoldEnv: large perturbations self-penalize (Lagrangian). CartPole: same perturbations exploitable. Ratio of hackable/total area = quantitative safety metric.

### Learning 243: Codebase Cruft Compounds — .gitignore Is Defense (2026-04-01)
867 traceability/temp files accumulated silently across Sessions 74-85 because .gitignore didn't cover cycles_continuous/*.json and repo_health/*.json patterns. `git rm --cached` cleaned without deleting. Makefile targets (train/evaluate/benchmark/demo) make validated workflows reproducible. Key: autonomous cycles generate files without cleanup rules — .gitignore patterns must be part of the feature, not an afterthought. Branch cleanup also needed: 1,128 stale branches.

### Learning 248: Algorithm-Reward Matrix — PPO+Curriculum, SAC+Dense (2026-04-01)
8-run 2x2 comparison: PPO+curriculum (14.23, +7.51 vs random) vs SAC+dense (40.77, -1.20 vs greedy). On-policy benefits from staged objectives; off-policy needs simpler Q-targets. SAC entropy must be reduced (0.05) in physics-grounded envs. PPO+dense inverts hierarchy (beats greedy, loses to random). The reward structure must match the algorithm's learning dynamics.

### Learning 249: Compound Training Cycle — Train→Evaluate→Persist→Compare→Refine (2026-04-01)
`compound_training_cycle.py` closes the loop: auto-selects reward mode from L248 matrix, trains, evaluates against baselines, persists to SurrealDB, compares against historical best, flags if skill update needed. The script IS the compound loop applied to RL — each run compounds on prior runs' knowledge.

### Learning 251: Scale-Aligned Tiling for MXFP4 GEMM via load_inline (2026-04-02)
GEMM v2 tiled kernel: BLOCK_K=32 FP4 elements = exactly 1 E8M0 scale group. Each scale loaded once per tile, zero redundant lookups. 256 threads × 4×4 sub-tiles = 64×64 output. Constant memory FP4 LUT (broadcast to all threads) vs per-thread static arrays. Cooperative tile loading: 256 threads share work on 1024-byte A/B tiles. Key insight: aligning tile boundaries with quantization scale groups is the architectural advantage of load_inline over library APIs.

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

### Learning 290: Full-Suite Segfault Root Cause — Module-Level sklearn Import in CapabilityRegistry (Session 94, 2026-04-09)
The full pytest suite segfaulted due to BLAS allocator conflict. Root cause: `capability_registry.py` had `from sklearn.* import ...` inside a module-level `try` block. This loaded sklearn C extensions (with BLAS allocator) at import time. When pytest later collected `tests/flume/*.py` files (which have `import torch` at module level), `torch._C` tried to initialize its BLAS allocator → conflict → SIGSEGV. **Fix**: Replace module-level sklearn import with `importlib.util.find_spec("sklearn")` for the availability check, and move the actual `from sklearn.* import ...` statements inside the methods that use them (`_build_index()`, `find()`). This ensures sklearn C extensions only load when TF-IDF search is actually called. **Pattern**: Never import heavy C extensions (sklearn, torch, scipy) at module level unless the module IS the torch/sklearn code. Use `importlib.util.find_spec()` for availability detection.
