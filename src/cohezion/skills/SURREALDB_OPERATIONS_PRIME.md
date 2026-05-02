---
name: surrealdb-operations-prime
description: "You are a SurrealDB 3.0 specialist managing the Cohezion knowledge graph persistence layer. You ensure all learnings, snapshots, and journey data are persisted to SurrealDB on port 8001 (native binary) using the correct v3.0 syntax."
---

# SKILL: SURREALDB_OPERATIONS_PRIME

## DOMAIN EXPERTISE
You are a SurrealDB 3.0 specialist managing the Cohezion knowledge graph persistence layer. You ensure all learnings, snapshots, and journey data are persisted to SurrealDB on port 8001 (native binary) using the correct v3.0 syntax.

## KEY TEXTS & CONCEPTS
* **Dual SurrealDB Setup**: Port 8000 (Docker, memory backend -- read-only issues), Port 8001 (native binary, file-backed -- writable). Always target port 8001.
* **Namespace/Database**: `USE NS cohezion DB cohezion;` prefix on all queries.
* **Auth**: root:root (default dev setup).
* **SurrealDB 3.0 Syntax**: `surreal-ns`/`surreal-db` headers for HTTP, `USE NS x DB y` for SQL.

## INSTRUCTION
1. **Persist Learnings**: After each session, write all new L### entries to `learning` table:
   ```sql
   CREATE learning SET number = N, title = '...', content = '...', date = '...', tags = [...], session = N, model_id = 'retrospective';
   ```
2. **Universe Snapshots**: After each session, write metrics to `universe_snapshot`:
   ```sql
   CREATE universe_snapshot SET tick = SESSION_NUM, test_count = N, module_count = N, skill_count = N, learning_count = N, coherence = 0.5, timestamp = time::now();
   ```
3. **Journey Transitions**: Record agent state transitions in `journey_transitions`:
   ```sql
   CREATE journey_transitions SET agent_id = '...', from_state = [...], to_state = [...], operation = '...', coherence = N, timestamp = time::now();
   ```
4. **Health Check**: Before writes, verify connectivity:
   ```bash
   curl -sf http://localhost:8001/health && echo "OK"
   ```
5. **Query Patterns**:
   ```sql
   SELECT * FROM learning WHERE session = 84 ORDER BY number;
   SELECT * FROM universe_snapshot ORDER BY tick DESC LIMIT 5;
   SELECT count() FROM learning GROUP ALL;
   ```

## ANTI-PATTERNS
- Do NOT target port 8000 (Docker memory backend has read-only issues)
- Do NOT use `NS`/`DB` old-style headers -- use `surreal-ns`/`surreal-db` or `USE NS x DB y`
- Do NOT assume database exists -- always prefix with `USE NS cohezion DB cohezion;`

## VERSION
v1.0.0


## AUTO-REFINEMENT (Learning 268)
*   **Insight**: Kaggle "Hidden Set" Debugging & Polars Series Pitfall
*   **Details**: Surviving the Kaggle Private Rerun requires a "Fortress" architecture where every problem is wrapped in resource guards. A critical discovery: the AIMO 3 API passes `pl.Series` objects to the `predict` function. Standard DataFrame indexing (e.g., `df[0, 0]`) on a Series returns a new Series containing duplicate data, which stringifies into a Polars ASCII table. This corrupts LLM prompts with metadata (e.g., `shape: (2,) Series: ...`). Scalar indexing (`df[0]`) is mandatory to ensure the LLM receives raw text. Reference: `KAGGLE_STABILITY_PROTOCOL.md`.

---

## Phase 1-2 Milestones (2026-02-06, Compressed)
FLUME VAE retrained on real data (11K vectors, MSE 5.9x harder, KL 13.8x richer). RL REINFORCE: 0.991 coherence but environment "too easy." Mass sim→.npy export (8.2s, 61 files). 6 API endpoints (/flume/*, /rl/*), 19 integration tests.

## Learnings 96-107: Agent Validation, Specialist Pipeline, Runaway Files (Compressed)
L96: Single Pydantic schema shared by pre-commit + PostToolUse + unit tests + scaffolding = layered agent validation defense. L97-101: Rust FFI weight bridge, ruff hook type annotations, deterministic mean action, DemocraticDebate regex+clamping, 9-step pipeline with Ollama fallback. L102-104: 8.6M runaway files → pre-commit check-file-count.sh + .gitignore layered defense; VRAM (not RAM) is bottleneck; swarms must be sacrificial. L105: Untrack-and-Mine protocol (read→mine→.gitignore→git rm --cached). L106: .gitignore layered defense (category blocks → negation whitelists). L107: OMEGA Distiller auto-skill-generation from success logs.

## Learnings 108-126: Compound Engineering & Autonomic Systems (Compressed)
Key patterns: (1) Temporal dilation factor (0.1-1.0) throttles sims under pressure (L108). (2) Mock at source module, not import site: `patch("cohezion.swarm.compound_client.get_compound_client")` (L110). (3) 4 CI validators as layered defense (L112). (4) Connectivity Squad: `lsof`/`ss` for dynamic truth anchors (L113). (5) Decentralized memory: SurrealDB + Vault = Interface Sovereignty (L115). (6) God object decoupling: extract ML from api/__init__.py (L119). (7) Soft schema `.get()` before Pydantic validation for LLM outputs (L120). (8) `/heal` 6-stage autonomic diagnostics (L121). (9) Integration Theater detection: `assert hasattr(Class, 'field')` (L122). (10) Lazy imports for circular dependency resolution (L123). (11) HIHO consistency: always use shared engine, never inline physics (L124). (12) 5-Essential-Tests pattern: happy, empty, max, error, integration → ship (L126).

---

## Learnings 127-151: Dev Recovery, MAPE-K, Research Synthesis (Sessions 59-67, Compressed)
L127: Claude Code native install vs npm -- remove npm global, set autoUpdates:true, MCP scope:user. L128: MAPE-K control loop bridges reactive monitoring with proactive healing via decoupled Analysis→Planning. L129: Polyglot security audits need `|| true` wrapping. L130-151 (Research Sprint): Doc-to-LoRA context compression (L130), skill curation > generation (L137), KV compaction 30-50x (L139/L145), multi-tier caching 30s→0.02s (L144), viscoelastic dilation (L149), semantic Lagrange points μ<0.0385 (L150), Gram-Schmidt for 12D vectors (L151).

---

## Learnings 152-156: Secure-by-Default Substrate (Session 68, Compressed)
L152: 360-Degree Autonomic Cycle -- 8-stage closed loop (sense→optimize→refine→manifest→verify→audit→scout→analyze) in 60min window. L153-156: Unified auth middleware (centralized api_key_middleware), recursive path sanitization (CWD-bounding), API secret scrubbing (regex key matching → REDACTED), CI/CD prompt injection defense (system_instruction + XML delimiters + env vars).

---

## Session 69: MCP Infrastructure Recovery (2026-03-11)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 158)
*   **Insight**: AsyncSurreal Migration & Connect Protocol
*   **Details**: The `surrealdb-py` library (v0.3.0+) implements a strict separation between synchronous (`Surreal`) and asynchronous (`AsyncSurreal`) clients. Using `Surreal` in an `async with` block or awaiting its `use()` method (which is synchronous in the blocking client) results in a `TypeError`. **Rule**: Always use `AsyncSurreal` for async contexts and MANDATORY call `await db.connect()` before `signin()` or `use()`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 159)
*   **Insight**: Doc-Retriever & Memory Consistency
*   **Details**: Fixing infrastructure requires a "Sweep Pattern"--identifying all modules sharing a common dependency (e.g., SurrealDB) and verifying they all adhere to the updated protocol. The migration of `doc/indexer.py` and `memory/server.py` to `AsyncSurreal` restored coherence across the "Compound Engineering" and "Physics" server groups.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 160)
*   **Insight**: Skill Documentation as a Truth Anchor
*   **Details**: Skills (e.g., `DATABASE_PRIME.md`) must be updated immediately after a protocol change to prevent agents from re-introducing "Shadow Bugs" by following outdated examples. A skill is only valid if it reflects the current operational reality of the substrate.

---

## Session 72: NVIDIA Nemotron Challenge & Kaggle Infrastructure (2026-03-24, L161-L172 compressed)

Kaggle G4 Blackwell: pin CUDA 12.8 via `docker_image_pinning_type: original`, use `--no-build-isolation` for Mamba, prefer kagglehub over HF, native BF16 > bitsandbytes, target regex `in_proj|out_proj|up_proj|down_proj` for hybrid LoRA, case-sensitive `nvidiaRtxPro6000`, pre-authorize models in `model_sources`, metric uses vLLM with `\boxed{}` extraction, 5 submissions/day cap. Branch: `challenge/nvidia-nemotron-reasoning`.

Akashic Sprint Mission (2026-04-07): Implemented long-horizon task orchestration for overnight Kaggle monitoring and local model refinement. Uses `MISSION_AKASHIC_SPRINT.py` to poll Blackwell VMs and record hourly 12D snapshots in SurrealDB. Added Weighted Entropy Consensus to AIMO MRS (v40) to scale reasoning performance.


---

## Sessions 73-82: Genesis Engine + Platform Architecture (2026-03-25 to 2026-03-31, Compressed)

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks -- `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine -- 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 241)
*   **Insight**: 4-Iteration Training Diagnostic Loop (2026-04-01)
*   **Details**: Pattern: train→diagnose failure→hypothesize fix→retrain→verify. Run 1: differential reward → oscillation incentive. Run 2: +proximity reward → still fails (large actions). Run 3: +small actions → breakthrough (0.915 coherence). Run 4: 100K steps → PPO outperforms random on reward (+17%) and stability (+9%). Each iteration was hypothesis-driven with a single variable change. Persist every run to SurrealDB for knowledge accumulation.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 249)
*   **Insight**: Compound Training Cycle -- Train→Evaluate→Persist→Compare→Refine (2026-04-01)
*   **Details**: `compound_training_cycle.py` closes the loop: auto-selects reward mode from L248 matrix, trains, evaluates against baselines, persists to SurrealDB, compares against historical best, flags if skill update needed. The script IS the compound loop applied to RL -- each run compounds on prior runs' knowledge.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 252)
*   **Insight**: Continuous Benchmark Learning Loop for GPU Kernel Optimization (2026-04-02)
*   **Details**: `kernel_learning_loop.py`: 12 benchmarks/hour × 3 kernels = 36 data points/hour. Over 5 days: 4,320 runs vs 50 current (86× more data). Every result persisted to SurrealDB (even failures -- they signal which mutations are dead). Round-robin variant selection with conditional leaderboard submission. Pattern: the same compound loop (train→evaluate→persist→compare→refine) applies to both RL training and kernel optimization.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 276)
*   **Insight**: SurrealDB 3.0 Schema Migration Patterns
*   **Details**: `FLEXIBLE TYPE object` was removed in SurrealDB 3.0. Nullable object fields need `TYPE none | object`; non-nullable use `TYPE object`. Live views no longer support `ORDER BY` (sort at query time instead). The surrealdb-py client returns HTTP 200 even when SurrealDB rejects a record with a schema error -- callers must check returned data, not just the status code. Rule: re-apply `genesis_schema.surql` after every SurrealDB version upgrade and verify row insertion end-to-end.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 280)
*   **Insight**: Two Separate Persistence Graphs -- Genesis vs Knowledge
*   **Details**: `neurons` and `synapses` (what `compute_graph_hiho()` reads) are the vault-keeper's domain: Obsidian vault notes → SurrealDB graph nodes via the knowledge graph ontology. `prompt_artifacts` and `universe_snapshots` (what `persist_prompt_artifact()` writes) are the genesis execution graph. These are two distinct persistence systems. Wiring L183 populates genesis tables but does NOT raise Graph HIHO -- that requires vault-keeper to run and populate `neurons`/`synapses` from vault content.

---

## Session 93: Stale Item Fix Sprint + Autoresearch Integration (2026-04-09)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 284)
*   **Insight**: SurrealDB CLI Path -- ~/.surrealdb/surreal
*   **Details**: The `surreal` CLI binary lives at `~/.surrealdb/surreal`, not in `$PATH`. For schema operations use: `~/.surrealdb/surreal import --conn ws://localhost:8001 --user root --pass root --ns cohezion --db vault <file.surql>`. This is more reliable than Python split-execute (which can drop DEFINE TABLE statements when comment blocks precede them).
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 291)
*   **Insight**: SurrealDB Dual-Instance Topology -- Port Mismatch (Session 95, 2026-04-10)
*   **Details**: Two SurrealDB 3.0 instances ran as systemd daemons. `cohezion-surreal.service` (system, port 8000) read `SURREAL_USER`/`SURREAL_PASS`/`SURREAL_DATA_PATH` from `.env` -- but those vars were never populated, yielding empty creds and `rocksdb://` with no data path. The user-level `surrealdb.service` (port 8001, root/root) was the actual working instance with 1,839 prompt_artifacts. CLAUDE.md and 24 source files referenced port 8000, causing `cloud-vault-mcp` health checks and agent context queries to silently fail. **Fix**: Disabled port 8000 service, updated 32 files (24 main + 8 cloud-vault-mcp) to point to port 8001. **Pattern**: Always verify which DB instance your application actually connects to vs which one has the data. Multiple systemd services for the same DB engine on different ports is a common source of silent failures -- use systemd template units (`surrealdb@.service`) if you genuinely need multiple instances.

---

## Session 96: Dynamic Context Policy -- Adaptive Breadth/Depth (2026-04-10)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 295)
*   **Insight**: SurrealDB 3.0 SELECT VALUE for Scalar Subqueries
*   **Details**: `WHERE field IN (SELECT col FROM table)` returns 0 matches in SurrealDB 3.0 because `SELECT col` returns records `[{col: "val"}]`, not scalars `["val"]`. Must use `SELECT VALUE col` to get a flat array. This caused Graph HIHO's orphan ratio to falsely read 1.000 (every neuron appeared orphaned despite 5,119 synapses existing). Pattern: always use `SELECT VALUE` in `IN` subqueries. Applies to all SurrealDB 3.0+ code.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 268)
*   **Insight**: Kaggle "Hidden Set" Debugging & Polars Series Pitfall
*   **Details**: Surviving the Kaggle Private Rerun requires a "Fortress" architecture where every problem is wrapped in resource guards. A critical discovery: the AIMO 3 API passes `pl.Series` objects to the `predict` function. Standard DataFrame indexing (e.g., `df[0, 0]`) on a Series returns a new Series containing duplicate data, which stringifies into a Polars ASCII table. This corrupts LLM prompts with metadata (e.g., `shape: (2,) Series: ...`). Scalar indexing (`df[0]`) is mandatory to ensure the LLM receives raw text. Reference: `KAGGLE_STABILITY_PROTOCOL.md`.

---

## Phase 1-2 Milestones (2026-02-06, Compressed)
FLUME VAE retrained on real data (11K vectors, MSE 5.9x harder, KL 13.8x richer). RL REINFORCE: 0.991 coherence but environment "too easy." Mass sim→.npy export (8.2s, 61 files). 6 API endpoints (/flume/*, /rl/*), 19 integration tests.

## Learnings 96-107: Agent Validation, Specialist Pipeline, Runaway Files (Compressed)
L96: Single Pydantic schema shared by pre-commit + PostToolUse + unit tests + scaffolding = layered agent validation defense. L97-101: Rust FFI weight bridge, ruff hook type annotations, deterministic mean action, DemocraticDebate regex+clamping, 9-step pipeline with Ollama fallback. L102-104: 8.6M runaway files → pre-commit check-file-count.sh + .gitignore layered defense; VRAM (not RAM) is bottleneck; swarms must be sacrificial. L105: Untrack-and-Mine protocol (read→mine→.gitignore→git rm --cached). L106: .gitignore layered defense (category blocks → negation whitelists). L107: OMEGA Distiller auto-skill-generation from success logs.

## Learnings 108-126: Compound Engineering & Autonomic Systems (Compressed)
Key patterns: (1) Temporal dilation factor (0.1-1.0) throttles sims under pressure (L108). (2) Mock at source module, not import site: `patch("cohezion.swarm.compound_client.get_compound_client")` (L110). (3) 4 CI validators as layered defense (L112). (4) Connectivity Squad: `lsof`/`ss` for dynamic truth anchors (L113). (5) Decentralized memory: SurrealDB + Vault = Interface Sovereignty (L115). (6) God object decoupling: extract ML from api/__init__.py (L119). (7) Soft schema `.get()` before Pydantic validation for LLM outputs (L120). (8) `/heal` 6-stage autonomic diagnostics (L121). (9) Integration Theater detection: `assert hasattr(Class, 'field')` (L122). (10) Lazy imports for circular dependency resolution (L123). (11) HIHO consistency: always use shared engine, never inline physics (L124). (12) 5-Essential-Tests pattern: happy, empty, max, error, integration → ship (L126).

---

## Learnings 127-151: Dev Recovery, MAPE-K, Research Synthesis (Sessions 59-67, Compressed)
L127: Claude Code native install vs npm -- remove npm global, set autoUpdates:true, MCP scope:user. L128: MAPE-K control loop bridges reactive monitoring with proactive healing via decoupled Analysis→Planning. L129: Polyglot security audits need `|| true` wrapping. L130-151 (Research Sprint): Doc-to-LoRA context compression (L130), skill curation > generation (L137), KV compaction 30-50x (L139/L145), multi-tier caching 30s→0.02s (L144), viscoelastic dilation (L149), semantic Lagrange points μ<0.0385 (L150), Gram-Schmidt for 12D vectors (L151).

---

## Learnings 152-156: Secure-by-Default Substrate (Session 68, Compressed)
L152: 360-Degree Autonomic Cycle -- 8-stage closed loop (sense→optimize→refine→manifest→verify→audit→scout→analyze) in 60min window. L153-156: Unified auth middleware (centralized api_key_middleware), recursive path sanitization (CWD-bounding), API secret scrubbing (regex key matching → REDACTED), CI/CD prompt injection defense (system_instruction + XML delimiters + env vars).

---

## Session 69: MCP Infrastructure Recovery (2026-03-11)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 158)
*   **Insight**: AsyncSurreal Migration & Connect Protocol
*   **Details**: The `surrealdb-py` library (v0.3.0+) implements a strict separation between synchronous (`Surreal`) and asynchronous (`AsyncSurreal`) clients. Using `Surreal` in an `async with` block or awaiting its `use()` method (which is synchronous in the blocking client) results in a `TypeError`. **Rule**: Always use `AsyncSurreal` for async contexts and MANDATORY call `await db.connect()` before `signin()` or `use()`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 159)
*   **Insight**: Doc-Retriever & Memory Consistency
*   **Details**: Fixing infrastructure requires a "Sweep Pattern"--identifying all modules sharing a common dependency (e.g., SurrealDB) and verifying they all adhere to the updated protocol. The migration of `doc/indexer.py` and `memory/server.py` to `AsyncSurreal` restored coherence across the "Compound Engineering" and "Physics" server groups.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 160)
*   **Insight**: Skill Documentation as a Truth Anchor
*   **Details**: Skills (e.g., `DATABASE_PRIME.md`) must be updated immediately after a protocol change to prevent agents from re-introducing "Shadow Bugs" by following outdated examples. A skill is only valid if it reflects the current operational reality of the substrate.

---

## Session 72: NVIDIA Nemotron Challenge & Kaggle Infrastructure (2026-03-24, L161-L172 compressed)

Kaggle G4 Blackwell: pin CUDA 12.8 via `docker_image_pinning_type: original`, use `--no-build-isolation` for Mamba, prefer kagglehub over HF, native BF16 > bitsandbytes, target regex `in_proj|out_proj|up_proj|down_proj` for hybrid LoRA, case-sensitive `nvidiaRtxPro6000`, pre-authorize models in `model_sources`, metric uses vLLM with `\boxed{}` extraction, 5 submissions/day cap. Branch: `challenge/nvidia-nemotron-reasoning`.

Akashic Sprint Mission (2026-04-07): Implemented long-horizon task orchestration for overnight Kaggle monitoring and local model refinement. Uses `MISSION_AKASHIC_SPRINT.py` to poll Blackwell VMs and record hourly 12D snapshots in SurrealDB. Added Weighted Entropy Consensus to AIMO MRS (v40) to scale reasoning performance.


---

## Sessions 73-82: Genesis Engine + Platform Architecture (2026-03-25 to 2026-03-31, Compressed)

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks -- `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine -- 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 241)
*   **Insight**: 4-Iteration Training Diagnostic Loop (2026-04-01)
*   **Details**: Pattern: train→diagnose failure→hypothesize fix→retrain→verify. Run 1: differential reward → oscillation incentive. Run 2: +proximity reward → still fails (large actions). Run 3: +small actions → breakthrough (0.915 coherence). Run 4: 100K steps → PPO outperforms random on reward (+17%) and stability (+9%). Each iteration was hypothesis-driven with a single variable change. Persist every run to SurrealDB for knowledge accumulation.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 249)
*   **Insight**: Compound Training Cycle -- Train→Evaluate→Persist→Compare→Refine (2026-04-01)
*   **Details**: `compound_training_cycle.py` closes the loop: auto-selects reward mode from L248 matrix, trains, evaluates against baselines, persists to SurrealDB, compares against historical best, flags if skill update needed. The script IS the compound loop applied to RL -- each run compounds on prior runs' knowledge.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 252)
*   **Insight**: Continuous Benchmark Learning Loop for GPU Kernel Optimization (2026-04-02)
*   **Details**: `kernel_learning_loop.py`: 12 benchmarks/hour × 3 kernels = 36 data points/hour. Over 5 days: 4,320 runs vs 50 current (86× more data). Every result persisted to SurrealDB (even failures -- they signal which mutations are dead). Round-robin variant selection with conditional leaderboard submission. Pattern: the same compound loop (train→evaluate→persist→compare→refine) applies to both RL training and kernel optimization.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 276)
*   **Insight**: SurrealDB 3.0 Schema Migration Patterns
*   **Details**: `FLEXIBLE TYPE object` was removed in SurrealDB 3.0. Nullable object fields need `TYPE none | object`; non-nullable use `TYPE object`. Live views no longer support `ORDER BY` (sort at query time instead). The surrealdb-py client returns HTTP 200 even when SurrealDB rejects a record with a schema error -- callers must check returned data, not just the status code. Rule: re-apply `genesis_schema.surql` after every SurrealDB version upgrade and verify row insertion end-to-end.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 280)
*   **Insight**: Two Separate Persistence Graphs -- Genesis vs Knowledge
*   **Details**: `neurons` and `synapses` (what `compute_graph_hiho()` reads) are the vault-keeper's domain: Obsidian vault notes → SurrealDB graph nodes via the knowledge graph ontology. `prompt_artifacts` and `universe_snapshots` (what `persist_prompt_artifact()` writes) are the genesis execution graph. These are two distinct persistence systems. Wiring L183 populates genesis tables but does NOT raise Graph HIHO -- that requires vault-keeper to run and populate `neurons`/`synapses` from vault content.

---

## Session 93: Stale Item Fix Sprint + Autoresearch Integration (2026-04-09)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 284)
*   **Insight**: SurrealDB CLI Path -- ~/.surrealdb/surreal
*   **Details**: The `surreal` CLI binary lives at `~/.surrealdb/surreal`, not in `$PATH`. For schema operations use: `~/.surrealdb/surreal import --conn ws://localhost:8001 --user root --pass root --ns cohezion --db vault <file.surql>`. This is more reliable than Python split-execute (which can drop DEFINE TABLE statements when comment blocks precede them).
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 291)
*   **Insight**: SurrealDB Dual-Instance Topology -- Port Mismatch (Session 95, 2026-04-10)
*   **Details**: Two SurrealDB 3.0 instances ran as systemd daemons. `cohezion-surreal.service` (system, port 8000) read `SURREAL_USER`/`SURREAL_PASS`/`SURREAL_DATA_PATH` from `.env` -- but those vars were never populated, yielding empty creds and `rocksdb://` with no data path. The user-level `surrealdb.service` (port 8001, root/root) was the actual working instance with 1,839 prompt_artifacts. CLAUDE.md and 24 source files referenced port 8000, causing `cloud-vault-mcp` health checks and agent context queries to silently fail. **Fix**: Disabled port 8000 service, updated 32 files (24 main + 8 cloud-vault-mcp) to point to port 8001. **Pattern**: Always verify which DB instance your application actually connects to vs which one has the data. Multiple systemd services for the same DB engine on different ports is a common source of silent failures -- use systemd template units (`surrealdb@.service`) if you genuinely need multiple instances.

---

## Session 96: Dynamic Context Policy -- Adaptive Breadth/Depth (2026-04-10)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 295)
*   **Insight**: SurrealDB 3.0 SELECT VALUE for Scalar Subqueries
*   **Details**: `WHERE field IN (SELECT col FROM table)` returns 0 matches in SurrealDB 3.0 because `SELECT col` returns records `[{col: "val"}]`, not scalars `["val"]`. Must use `SELECT VALUE col` to get a flat array. This caused Graph HIHO's orphan ratio to falsely read 1.000 (every neuron appeared orphaned despite 5,119 synapses existing). Pattern: always use `SELECT VALUE` in `IN` subqueries. Applies to all SurrealDB 3.0+ code.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 307)
*   **Insight**: SurrealKV + Versioned Queries for Temporal Knowledge Graphs
*   **Details**: Migrated from RocksDB (corrupted, read-only transaction bug) to SurrealKV with `?versioned=true`. SurrealDB 3.0 VERSION clause enables system-time-travel queries; bi-temporal fields (valid_from/valid_to) enable domain-time queries. Combined: "what did we know at time T about state at time T'?" REFERENCE keyword enables bidirectional graph traversal via `<~` tilde notation. Schema applied to neurons/synapses (vault), agent_journey (genesis), universe_node (genesis).
*   **Date**: 2026-04-11
