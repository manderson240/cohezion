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
