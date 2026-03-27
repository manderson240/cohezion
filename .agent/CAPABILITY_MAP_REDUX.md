# Cohezion Capability Map (Redux)

A central registry of the swarm's **6-Dimensional Service Architecture**. Only "Prime" skills are listed here.

## 1. PROPRIOCEPTION (Ouroboros Service)
*The Nervous System: Health, Hygiene, and Self-Correction.*
- **Reflex**: [SELF_HEALING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SELF_HEALING_PRIME.md) (ReflexAgent).
- **Pruning**: [REPO_HYGIENE_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/REPO_HYGIENE_PRIME.md) (PrunerAgent).
- **Rescue**: [KNOWLEDGE_HARVESTING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/KNOWLEDGE_HARVESTING_PRIME.md) (Ghost Harvest).
- **Telemetry**: [SYSTEM_MONITORING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SYSTEM_MONITORING_PRIME.md).

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

## 6. INFRASTRUCTURE (VLIW Service)
*The Substrate: Hardware & Data.*
- **Database**: [DATABASE_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/DATABASE_PRIME.md) (SurrealDB).
- **Ops**: [IDE_OPTIMIZATION_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/IDE_OPTIMIZATION_PRIME.md).
- **Security**: [SECURITY_GUARDRAILS_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SECURITY_GUARDRAILS_PRIME.md).

## DORMANT PROTOCOLS
- **Mycelium**: [Proposed] Test Synthesis & Preservation (`ShadowScripter`).
- **Quantum MPS**: [Dormant] Matrix Product States for Q-Sim.
