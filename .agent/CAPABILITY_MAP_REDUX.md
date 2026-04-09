# Cohezion Capability Map (Redux)

A central registry of the swarm's **6-Dimensional Service Architecture**. Only "Prime" skills are listed here.

**Last updated**: 2026-04-08 (Session 91 retrospective). **6,109 tests collected, 32 genesis physics modules, 11 frontend tsx components.**

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
- **Environments**: ManifoldEnv (gymnasium), SwarmEnv (multi-agent) (`environments/`).
- **World Model**: JEPA 86K-param predictor + surprise explorer (`world_model/`).
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
- **Specialist Agents (7)**: vault-keeper, surreal-dba, claude/gemini/ollama/mcp-specialist, platform-coordinator — A2A agent cards + PRIME skills.
- **Cost Tiers**: 70% simple (Ollama/Flash-Lite, free) → 20% medium (Sonnet, $3/M) → 10% hard (Opus, $15/M).

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
