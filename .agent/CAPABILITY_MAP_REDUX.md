# Cohezion Capability Map (Redux)

A central registry of the swarm's **6-Dimensional Service Architecture**. Only "Prime" skills are listed here.

**Last updated**: 2026-04-10 (Session 96b retrospective). **6,184 tests collected (full suite runs to completion), 35 genesis physics+world_model+env modules, 11 frontend tsx components. 348 genesis tests passing (0 failing). 1,839 prompt_artifacts + 1,822 universe_snapshots in SurrealDB (port 8001, consolidated). 206 skill definitions (151 PRIME). Autoresearch (UCB1 K-Search + Step 5.91) wired. A2A GET /agents returns 7 specialist agents. Anthropic Intelligence Feed: 11-source monitoring + auto-integration.**

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
