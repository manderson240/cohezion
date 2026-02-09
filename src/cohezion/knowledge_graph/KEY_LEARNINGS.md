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
