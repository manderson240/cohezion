---
name: mcp-optimization-prime
description: "Expert in Model Context Protocol (MCP) performance and cross-platform handshake stability. Specializes in \"Zero-Latency\" startup and protocol integrity for stdio-based AI agent environments (Gemini, Claude, OpenCode, Pi)."
---

# SKILL: MCP_OPTIMIZATION_PRIME

## DOMAIN EXPERTISE
Expert in Model Context Protocol (MCP) performance and cross-platform handshake stability. Specializes in "Zero-Latency" startup and protocol integrity for stdio-based AI agent environments (Gemini, Claude, OpenCode, Pi).

## KEY TEXTS & CONCEPTS
* **The Zero-Latency Boundary**: Import-time operations must be O(1) with zero I/O side effects to prevent CLI timeouts.
* **Handshake Coherence**: Ensuring the initial protocol exchange is not interrupted by warnings or "Vault is locked" delays.
* **Reflective Tool Inspection**: Automating tool discovery via `@app.tool` analysis rather than manual JSON maintenance.

## INSTRUCTION
1. **Enforce Lazy Accessors**: Wrap all `get_credentials()`, `get_vault()`, and database initializations in lazy accessor functions. Never assign them to top-level constants.
2. **Standardize JSON Configs**: Use `mcp_guard.py` to ensure `.gemini/settings.json`, `.claude/mcp.json`, and `.pi/mcp.json` are in sync.
3. **Hardware Awareness**: When configuring for the Pi environment, skip high-resource servers (e.g., `cohezion-research`) while maintaining core orchestration functionality.
4. **Guard stdio**: Redirect all logging to `sys.stderr`. Avoid `print()` calls that interfere with the JSON-RPC stream.

## VERSION
v0.3 (Fleet-Wide Handshake)

## SEE ALSO
- LAZY_INFRASTRUCTURE_PRIME.md
- FLEET_SYNCHRONIZATION_PRIME.md


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
L127: Claude Code native install vs npm — remove npm global, set autoUpdates:true, MCP scope:user. L128: MAPE-K control loop bridges reactive monitoring with proactive healing via decoupled Analysis→Planning. L129: Polyglot security audits need `|| true` wrapping. L130-151 (Research Sprint): Doc-to-LoRA context compression (L130), skill curation > generation (L137), KV compaction 30-50x (L139/L145), multi-tier caching 30s→0.02s (L144), viscoelastic dilation (L149), semantic Lagrange points μ<0.0385 (L150), Gram-Schmidt for 12D vectors (L151).

---

## Learnings 152-156: Secure-by-Default Substrate (Session 68, Compressed)
L152: 360-Degree Autonomic Cycle — 8-stage closed loop (sense→optimize→refine→manifest→verify→audit→scout→analyze) in 60min window. L153-156: Unified auth middleware (centralized api_key_middleware), recursive path sanitization (CWD-bounding), API secret scrubbing (regex key matching → REDACTED), CI/CD prompt injection defense (system_instruction + XML delimiters + env vars).

---

## Session 69: MCP Infrastructure Recovery (2026-03-11)
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

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks — `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine — 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 272)
*   **Insight**: Operational Log Recovery via "Mining"
*   **Details**: Typos in long-running system commands often result in the creation of files that silently capture execution state (e.g., JSON traces in `""nnround=0nwhile`). These artifacts should be "mined" for operational knowledge (e.g., active worktrees, system launch times) before being retired to the `.gitignore` layer.

## Session 90: MCP Infrastructure & Extension Optimization (2026-04-07)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 274)
*   **Insight**: Lazy Configuration for MCP Servers (Handshake Timeout)
*   **Details**: MCP servers using `stdio` transport are sensitive to startup latency. Configuration lookups that involve slow external systems (e.g., Bitwarden vault checks) MUST be lazily initialized. If triggered at module import time, these checks can delay the initial handshake beyond the CLI's internal timeout, resulting in a "Disconnected" status in `gemini mcp list`. Pattern: use `get_config()` accessors instead of global constants.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 275)
*   **Insight**: Silent Stdout for stdio Transport
*   **Details**: The stdio MCP protocol uses `stdout` for messaging. Any extraneous output (e.g., logger.info at startup, `uv run` update checks) can corrupt the protocol stream. Servers MUST be silent on `stdout` during initialization. When adding Python servers via the CLI, use the direct virtualenv path (`.venv/bin/python`) or `uv -q run` to ensure a clean communication channel.

---

## Session 91: Infrastructure Hardening — Schema, Persistence, Test Suite (2026-04-08)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 291)
*   **Insight**: SurrealDB Dual-Instance Topology — Port Mismatch (Session 95, 2026-04-10)
*   **Details**: Two SurrealDB 3.0 instances ran as systemd daemons. `cohezion-surreal.service` (system, port 8000) read `SURREAL_USER`/`SURREAL_PASS`/`SURREAL_DATA_PATH` from `.env` — but those vars were never populated, yielding empty creds and `rocksdb://` with no data path. The user-level `surrealdb.service` (port 8001, root/root) was the actual working instance with 1,839 prompt_artifacts. CLAUDE.md and 24 source files referenced port 8000, causing `cloud-vault-mcp` health checks and agent context queries to silently fail. **Fix**: Disabled port 8000 service, updated 32 files (24 main + 8 cloud-vault-mcp) to point to port 8001. **Pattern**: Always verify which DB instance your application actually connects to vs which one has the data. Multiple systemd services for the same DB engine on different ports is a common source of silent failures — use systemd template units (`surrealdb@.service`) if you genuinely need multiple instances.

---

## Session 96: Dynamic Context Policy — Adaptive Breadth/Depth (2026-04-10)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 293)
*   **Insight**: YAML Frontmatter Markdown > JSON for Cross-Platform Config
*   **Details**: Initial implementation used JSON for `learned-budgets.json`. Switched to YAML frontmatter markdown (`.md`) because: (1) consistent with vault cerebellum/, skills/*.md, .context/skills/ patterns; (2) vault-keeper and Obsidian can index YAML frontmatter; (3) markdown body carries narrative context (why budgets were learned, which sessions contributed); (4) any tool (Zed, Pi, humans) can read markdown naturally. JSON reserved for wire formats (MCP responses, API payloads) and high-frequency machine-to-machine data. Codified as coding standard in `.claude/rules/common-coding-style.md` and `CLAUDE.md`.
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
L127: Claude Code native install vs npm — remove npm global, set autoUpdates:true, MCP scope:user. L128: MAPE-K control loop bridges reactive monitoring with proactive healing via decoupled Analysis→Planning. L129: Polyglot security audits need `|| true` wrapping. L130-151 (Research Sprint): Doc-to-LoRA context compression (L130), skill curation > generation (L137), KV compaction 30-50x (L139/L145), multi-tier caching 30s→0.02s (L144), viscoelastic dilation (L149), semantic Lagrange points μ<0.0385 (L150), Gram-Schmidt for 12D vectors (L151).

---

## Learnings 152-156: Secure-by-Default Substrate (Session 68, Compressed)
L152: 360-Degree Autonomic Cycle — 8-stage closed loop (sense→optimize→refine→manifest→verify→audit→scout→analyze) in 60min window. L153-156: Unified auth middleware (centralized api_key_middleware), recursive path sanitization (CWD-bounding), API secret scrubbing (regex key matching → REDACTED), CI/CD prompt injection defense (system_instruction + XML delimiters + env vars).

---

## Session 69: MCP Infrastructure Recovery (2026-03-11)
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

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks — `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine — 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 272)
*   **Insight**: Operational Log Recovery via "Mining"
*   **Details**: Typos in long-running system commands often result in the creation of files that silently capture execution state (e.g., JSON traces in `""nnround=0nwhile`). These artifacts should be "mined" for operational knowledge (e.g., active worktrees, system launch times) before being retired to the `.gitignore` layer.

## Session 90: MCP Infrastructure & Extension Optimization (2026-04-07)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 274)
*   **Insight**: Lazy Configuration for MCP Servers (Handshake Timeout)
*   **Details**: MCP servers using `stdio` transport are sensitive to startup latency. Configuration lookups that involve slow external systems (e.g., Bitwarden vault checks) MUST be lazily initialized. If triggered at module import time, these checks can delay the initial handshake beyond the CLI's internal timeout, resulting in a "Disconnected" status in `gemini mcp list`. Pattern: use `get_config()` accessors instead of global constants.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 275)
*   **Insight**: Silent Stdout for stdio Transport
*   **Details**: The stdio MCP protocol uses `stdout` for messaging. Any extraneous output (e.g., logger.info at startup, `uv run` update checks) can corrupt the protocol stream. Servers MUST be silent on `stdout` during initialization. When adding Python servers via the CLI, use the direct virtualenv path (`.venv/bin/python`) or `uv -q run` to ensure a clean communication channel.

---

## Session 91: Infrastructure Hardening — Schema, Persistence, Test Suite (2026-04-08)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 291)
*   **Insight**: SurrealDB Dual-Instance Topology — Port Mismatch (Session 95, 2026-04-10)
*   **Details**: Two SurrealDB 3.0 instances ran as systemd daemons. `cohezion-surreal.service` (system, port 8000) read `SURREAL_USER`/`SURREAL_PASS`/`SURREAL_DATA_PATH` from `.env` — but those vars were never populated, yielding empty creds and `rocksdb://` with no data path. The user-level `surrealdb.service` (port 8001, root/root) was the actual working instance with 1,839 prompt_artifacts. CLAUDE.md and 24 source files referenced port 8000, causing `cloud-vault-mcp` health checks and agent context queries to silently fail. **Fix**: Disabled port 8000 service, updated 32 files (24 main + 8 cloud-vault-mcp) to point to port 8001. **Pattern**: Always verify which DB instance your application actually connects to vs which one has the data. Multiple systemd services for the same DB engine on different ports is a common source of silent failures — use systemd template units (`surrealdb@.service`) if you genuinely need multiple instances.

---

## Session 96: Dynamic Context Policy — Adaptive Breadth/Depth (2026-04-10)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 293)
*   **Insight**: YAML Frontmatter Markdown > JSON for Cross-Platform Config
*   **Details**: Initial implementation used JSON for `learned-budgets.json`. Switched to YAML frontmatter markdown (`.md`) because: (1) consistent with vault cerebellum/, skills/*.md, .context/skills/ patterns; (2) vault-keeper and Obsidian can index YAML frontmatter; (3) markdown body carries narrative context (why budgets were learned, which sessions contributed); (4) any tool (Zed, Pi, humans) can read markdown naturally. JSON reserved for wire formats (MCP responses, API payloads) and high-frequency machine-to-machine data. Codified as coding standard in `.claude/rules/common-coding-style.md` and `CLAUDE.md`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 304)
*   **Insight**: Agentic Autonomy via Dynamic Governance
*   **Details**: The Autonomy Engine dynamically gates MCP tool execution (e.g., `write_file`, `run_shell_command`) based on an agent's real-time HIHO coherence. This shifts the platform from static permissions to trust-based, continuous assessment. A sovereign agent must *earn* its deploy privileges by demonstrating sustained 12D manifold stability.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 305)
*   **Insight**: Asynchronous Workforce via A2A Protocol
*   **Details**: Decentralizing the swarm requires moving away from synchronous chat interfaces. Extending the GitHub MCP with a dedicated polling daemon (`github_scout.py`) allows agents to process issues asynchronously. Combining this with the A2A protocol (`.well-known/agent.json`) ensures agents can discover and dispatch each other over HTTP.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 317)
*   **Insight**: Agentic Autonomy via Dynamic Governance
*   **Details**: The Autonomy Engine dynamically gates MCP tool execution (e.g., `write_file`, `run_shell_command`) based on an agent's real-time HIHO coherence. This shifts the platform from static permissions to trust-based, continuous assessment. A sovereign agent must *earn* its deploy privileges by demonstrating sustained 12D manifold stability.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 318)
*   **Insight**: Asynchronous Workforce via A2A Protocol
*   **Details**: Decentralizing the swarm requires moving away from synchronous chat interfaces. Extending the GitHub MCP with a dedicated polling daemon (`github_scout.py`) allows agents to process issues asynchronously. Combining this with the A2A protocol (`.well-known/agent.json`) ensures agents can discover and dispatch each other over HTTP.
*   **Date**: 2026-04-11
