# Cohezion Capability Map (Redux)

A central registry of the swarm's **6-Dimensional Service Architecture**. Only "Prime" skills are listed here.

**Last updated**: 2026-04-18 (Session 103 retrospective). **6,369+ tests collected. Inference subsuite 45/45 (`tests/inference/`, new in S103). 35 genesis physics+world_model+env modules, 11 frontend tsx components. 398 genesis tests passing. SurrealDB on port 8001 (SurrealKV, 17 tables). 235 skill definitions (215 PRIME). 87 MCP tools. 92 API route handlers. Autoresearch (UCB1 K-Search + Step 5.91) wired. V-Model: 27 invariants across phases 1 (10), 2 (8), 6 (9) in `cohezion.inference`. A2A GET /agents returns 7 specialist agents. Claude Code v2.1.112 (native installer).**

## 1. PROPRIOCEPTION (Ouroboros Service)
*The Nervous System: Health, Hygiene, and Self-Correction.*
- **Reflex**: [SELF_HEALING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SELF_HEALING_PRIME.md) (ReflexAgent).
- **Pruning**: [REPO_HYGIENE_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/REPO_HYGIENE_PRIME.md) (PrunerAgent).
- **Rescue**: [KNOWLEDGE_HARVESTING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/KNOWLEDGE_HARVESTING_PRIME.md) (Ghost Harvest).
- **Telemetry**: [SYSTEM_MONITORING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SYSTEM_MONITORING_PRIME.md).
- **Maintenance MCP**: `cohezion-maintenance-mcp/` — 6 tools: graph_health, graph_prune_orphans, graph_compact, verify_graph_schema, vault_audit, surreal_table_stats.
- **Graph HIHO**: Weighted metric (connectivity 0.3, reciprocity 0.2, freshness 0.2, 1-orphan_ratio 0.3). Target: 0.5 +/- 0.15.

## 2. COGNITION (FLUME Service)
*The Mind: Latent Navigation & Logic.*
- **Manifold**: [FLUME_METHODOLOGY_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/FLUME_METHODOLOGY_PRIME.md).
- **Reasoning**: [SEQUENTIAL_THINKING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/sequential_thinking_prime.md) (MCP).
- **Compression**: [REDUCER_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/REDUCER_PRIME.md).

## 3. GOVERNANCE (Quadrature Nexus)
*The Will: Intent & Orchestration.*
- **Orchestration**: [SWARM_ORCHESTRATION_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SWARM_ORCHESTRATION_PRIME.md).
- **Ethics**: [CONSTITUTION_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/CONSTITUTION_PRIME.md).
- **Growth**: [ASCENSION_SKILL_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/ASCENSION_SKILL_PRIME.md).

## 4. PHYSICS (Genesis Engine — Grounded Simulation)
*The Body: 12D Riemannian Manifold with Real Mathematics.*
- **Spinor**: SU(2) algebra, Bloch sphere, HIHO = equatorial state (`physics/spinor.py`).
- **Geometry**: Riemannian metric, Christoffel symbols, geodesics (`physics/riemannian_metric.py`).
- **Dynamics**: Euler-Lagrange, symplectic Verlet integrator (`physics/lagrangian.py`).
- **Bundle**: Fiber bundle P(B⁴,SO(3)⁴), parallel transport (`physics/fiber_bundle.py`).
- **Gauge**: Yang-Mills SO(3), covariant Tempic field (`physics/gauge_theory.py`).
- **Fisher**: Information geometry, Rosetta Stone metric (`physics/information_geometry.py`).
- **Cosmogony**: Landau phase transitions ∅→HIHO, Brahmagupta's zero (`physics/cosmogony.py`).
- **MHD/HIHO**: HIHOUnifiedEngine with 11 sub-engines (`universe/hiho_unified_engine.py`).
- **Vis**: 8-tab webapp at `/genesis` (`web/anima_dashboard/`).
- **Audio**: PocketTTS narration + Tone.js sonification (`audio/narrator.py`).
- **Environments**: ManifoldEnv (gymnasium, verifiable rewards: r_hiho/r_conservation/r_unitarity/r_gauge), SwarmEnv (multi-agent) (`environments/`).
- **World Model**: JEPA 86K-param predictor + LeWM dual-loss (prediction + SIGReg + Gaussian KL) (`world_model/`).
- **Invariant Checker**: Runtime proof obligations after every physics step — 5 checks (`physics/invariant_checker.py`).
- **TDA Router**: TopologicalRouter — persistent homology drives swarm optimization (`swarm/topological_router.py`).
- **Research**: [Paper draft](docs/papers/genesis-engine-paper.md) | [Research doc](docs/genesis-engine-research.md) | [Tutorials](docs/tutorials/).

## 5. INTELLIGENCE (AI Lab Service)
*The Brain: Model Routing & Learning.*
- **Routing**: [MODEL_ROUTING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/MODEL_ROUTING_PRIME.md).
- **TDA Routing**: TopologicalRouter — H₀/H₁ → exploit/explore/pivot (`swarm/topological_router.py`).
- **Data**: [TRAINING_DATA_CAPTURE_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/TRAINING_DATA_CAPTURE_PRIME.md).
- **JEPA**: World model predicting manifold evolution (`world_model/jepa_world_model.py`).
- **Research**: [EXTERNAL_RESEARCH_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/EXTERNAL_RESEARCH_PRIME.md).
- **Intern-S1-mini**: 8B scientific reasoning model (pulled to Ollama). Part of 47-model local inventory.
- **GraphRAG**: Hybrid vector+graph+temporal queries in SurrealQL (`knowledge_graph/graphrag_engine.py`).
- **Lemonade Router**: CostAwareRouter with 45 YAML profiles, Lemonade-first tier routing ($0 inference).

## 5.4. LOCAL INFERENCE FLEET (Session 103, NEW)
*Unified router across NPU / iGPU / CPU / Cloud lanes — TTFT-optimized.*
- **Package**: `src/cohezion/inference/` — 7 modules, ~1,700 LOC
- **Route**: `route(prompt, task=..., stream=True, budget_usd=..., prefer=...)` — single entry point with task classification, health filter, budget filter, symmetry-axis injection, streaming TTFT measurement (`fleet.py`)
- **Registry**: 14 models × 7 lanes (NPU 13306 / iGPU ROCWMMA 13307 / iGPU Unified 13308 / CPU 13309 / Ollama 11434 / Claude CLI / Gemini CLI). AMD-optimal path ranking: NPU < iGPU < CPU < Cloud (`registry.py`)
- **Health**: 30s-cached `/v1/models` probes + live Claude CLI dispatch (`-p ping --bare --model haiku-4-5 --max-budget-usd 0.01`) + Omnibus gateway dashboard (`health.py`)
- **Orchestrator**: `TieredOrchestrator` — recursive `/advisor` pattern. Smarter tiers review less-smart tiers, escalate on QualityGate failure. Composable: a tier target can itself be a `TieredOrchestrator`. Nested budget pass-through via `run(budget_usd=...)` with `min(self_cap, parent_budget)` semantics (`orchestrator.py`)
- **ExtendClaude**: `extend_claude(prompt, claude_model=...)` — local-first, Claude fallback. Validates `claude_model ∈ registry.models` before local loop (fast-fail on typos)
- **HarnessPool**: 3-slot concurrent pi/opencode/hermes Ollama-cloud dispatch (`harnesses.py`)
- **GAIA adapter**: `GaiaAgentTier` + `amd_optimized_hierarchy()` (`gaia_adapter.py`)
- **V-Model gatekeepers**: Phase 1 (10 F-invariants, inference fleet structure), Phase 2 (8 I-invariants incl. I2b stderr sidecar), Phase 6 (9 O-invariants incl. O3b nested budget kwarg). `make vmodel-all` runs all three (`scripts/validation/vmodel/phase{1,2,6}_*_harness.py`)
- **Benchmark**: `scripts/benchmark_fleet.py` — 4-config comparison (Claude-only / local-only / hybrid-budget / hybrid-quality via extend_claude). Output path validation guards against CWD escape. Config A stderr sidecar preserves diagnostic trail (`benchmark_fleet.py`)
- **Launch**: `scripts/launch_fleet_safe.sh` — sequential staged lane launch; `/v1/models` body grep verifies expected model id per port (guards "wrong model on lane" misconfig)
- **Demos**: `demo/universes_demo.py` (2.7s end-to-end), `demo/orchestrate_demo.py` (tiered escalation)
- **Tests**: 45/45 in `tests/inference/` — regression tests lock in adversarial-review fixes (live-dispatch probe, nested budget, unknown-model rejection)
- **Commits**: `2cbc4d17f` (sprint + 3 P0 follow-ups), `00d1be0b8` (5 P1/P2 follow-ups) — on `isolated/session-oom-modularity`, landing via cherry-pick → `feat/inference-fleet` → PR to `main`

## 5.5. VERIFICATION (V-Model Lifecycle)
*The Immune System: Deterministic gates constraining nondeterministic work.*
- **DRR Generator**: Design Review Reports at V-Model gates (DRR-0 through DRR-3) (`compound/design_review_report.py`).
- **Constitutional Enforcer**: Deterministic hard constraint checker + GuardrailPipeline adapter (`security/constitutional_enforcer.py`).
- **Hash-Chain Audit**: SHA-256 tamper-evident chain in JourneyTracker (OLIF mitigation).
- **Skill Validator**: Blocks refinement mutations degrading metrics >5% (`compound/skill_refinement_validator.py`).
- **Retrospection Validator**: Cross-checks summaries against SurrealDB traces (`compound/retrospection_validator.py`).
- **Tape Logger**: JSONL deterministic replay (`compound/tape_logger.py`).
- **SLR Evidence**: 0/8 queries found 3+ component systems — 5-component novelty confirmed (`docs/papers/slr-synthesis.md`).
- **Specialist Agents (7)**: vault-keeper, surreal-dba, claude/gemini/ollama/mcp-specialist, platform-coordinator — A2A agent cards + PRIME skills.
- **Cost Tiers**: 70% simple (Ollama/Flash-Lite, free) → 20% medium (Sonnet, $3/M) → 10% hard (Opus, $15/M).
- **Autoresearch**: `AutoresearchDriver` (K-Search UCB1, subprocess eval, SurrealDB persist) at `research/autoresearch_driver.py`. Dispatched via Step 5.91 in `CompoundExecutor.execute_task()` on keywords: train/optimize/research/experiment/tune/improve loss. K-Search trees at `~/.cohezion-research/ksearch/{target}.json`. Targets: jepa/flume_vae/rl_ppo.
- **A2A Discovery**: `GET /agents` returns all registered specialist agents via `CapabilityRegistry._scan_claude_agents()` (scans `.claude/agents/*.md` YAML frontmatter).
- **Anthropic Intelligence Feed**: Autonomous monitoring of 11 Anthropic sources (CLI releases, API platform, research, alignment, system cards, deprecations, blog, help center, Glasswing, economic index). Components: `version-watch.sh` (SessionStart hook), `/anthropic-scan` (11-source scan command), `anthropic-intel-scan.md` (agentic background scan rule), risk-tiered auto-integration, `features-manifest.json` + `api-manifest.json` (feature registries), `change-log.md` (audit trail). Located at `~/.claude/anthropic-intel/`.
- **ContextPolicy**: Adaptive context breadth/depth control (`compound/context_policy.py`). ROUTINE/FOCUSED/EXPLORATORY profiles, hybrid reactive adjustment, YAML frontmatter persistence.

## 6. INFRASTRUCTURE (VLIW Service)
*The Substrate: Hardware & Data.*
- **Database**: [DATABASE_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/DATABASE_PRIME.md) (SurrealDB).
- **Ops**: [IDE_OPTIMIZATION_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/IDE_OPTIMIZATION_PRIME.md).
- **Security**: [SECURITY_GUARDRAILS_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SECURITY_GUARDRAILS_PRIME.md).

## 7. COMPETITION (Kaggle Arena)
*Competition archive + active tracks.*
- **AMD Speedrun** (CLOSED 2026-04-07): Final gaps — GEMM 3.1x (13.4µs vs 4.3µs), MLA 3.6x (69.7µs vs 19.5µs), MoE 2.2x (154µs vs 70.5µs). Fused quant+GEMM correctness proven (0.0 error). K-Search compound loop operational. Key constraint: 12-min runner timeout blocks JIT kernels. See `.claude/rules/luma-kernels.md`.
- **AIMO3**: H100 Blackwell handshake confirmed (`machine_shape: NvidiaRtxPro6000`). Diversity+Entropy Voting+Speculative Decoding framework built. Polars Series `.item()` indexing mandatory (not `[0,0]`). See `KAGGLE_STABILITY_PROTOCOL.md`.
- **Nemotron**: v20 adapter trained (LoRA r=32 on Mamba in_proj/out_proj); baseline complete.
- **Kaggle API**: Restored with KGAT_ token auth (`KAGGLE_API_TOKEN` env var).

## PREVIOUSLY DORMANT — NOW ACTIVE
- **Mycelium**: Implemented — `learning/mycelium_network.py`, `learning/mycelium_registry.py`, API at `/api/mycelium` (3 endpoints).
- **Quantum MPS**: Implemented — `physics/quantum/peaked_solver.py`, 36-qubit MPS (Bond 64), bit-exact. PRIME skill: `QUANTUM_MPS_ROUTING_PRIME`.
