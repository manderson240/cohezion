---
title: Cohezion PRIME Skill Library — Capability & Skills Matrix Audit
date: 2026-06-02
auditor: skill-quality-specialist-agent
scope: src/cohezion/skills/ (primary), src/cohezion/registry/skill_registry.json (canonical)
---

# Cohezion PRIME Skill Library — Capability & Skills Matrix Audit

**Date:** 2026-06-02
**Worktree:** `/home/mike-anderson/dev/cohezion/.claude/worktrees/tingly-petting-zephyr`

---

## 1. Enumeration Summary

### File Counts

| Location | Count |
|----------|-------|
| `.md` files in `src/cohezion/skills/` | 240 |
| `.py` tool files in `src/cohezion/skills/` | 7 |
| Non-extension entries (dirs: `kaggle/`, `mcp-builder/`, files without ext: `BRANDING_OPS_PRIME`, `TENSOR_NETWORK_OPS_PRIME`) | 4 |
| **Total items in skills dir** | 251 |

### Registry Status

Two distinct registry files exist:

| Registry File | Entries | Nature |
|--------------|---------|--------|
| `src/cohezion/skills/skill_registry.json` | 82 | **Curated hand-maintained** — stores `version`, `concepts`, `see_also` metadata NOT in file frontmatter |
| `src/cohezion/registry/skill_registry.json` | 240 | **Auto-generated** — produced by `scripts/sync_skill_registry.py` / `src/cohezion/registry/populate_registry.py`; stores `name`, `description`, `keywords`, `path` from parsed frontmatter |

The curated registry (`skills/skill_registry.json`) is the authoritative skill metadata store. The auto-generated registry (`registry/skill_registry.json`) is a search/routing index. **Do not conflate them.**

---

## 2. Registry vs Filesystem Reconciliation (Mismatch Report)

### 2a. Curated Registry (`skills/skill_registry.json`) — 82 entries

**Registered but pointing to nonexistent/temp-path files (3 entries — test artifacts):**

| Registry Key | Recorded Source | Status |
|-------------|-----------------|--------|
| `SKILL_0_PRIME` | `/tmp/claude-1000/pytest-of-mike-anderson/pytest-435/test_factory_generate_top_skil0/skills/SKILL_0_PRIME.md` | STALE — temp pytest dir |
| `SKILL_1_PRIME` | `/tmp/claude-1000/pytest-of-mike-anderson/pytest-435/test_factory_generate_top_skil0/skills/SKILL_1_PRIME.md` | STALE — temp pytest dir |
| `TEST_SKILL_PRIME` | `/tmp/pytest-of-mike-anderson/pytest-35/test_version_header_in_generat0/skills/TEST_SKILL_PRIME.md` | STALE — temp pytest dir |

**Preserved verbatim for recoverability:**
```json
"SKILL_0_PRIME": {
  "version": "1.0",
  "concepts": [],
  "see_also": [],
  "source": "/tmp/claude-1000/pytest-of-mike-anderson/pytest-435/test_factory_generate_top_skil0/skills/SKILL_0_PRIME.md"
},
"SKILL_1_PRIME": {
  "version": "1.0",
  "concepts": [],
  "see_also": [],
  "source": "/tmp/claude-1000/pytest-of-mike-anderson/pytest-435/test_factory_generate_top_skil0/skills/SKILL_1_PRIME.md"
},
"TEST_SKILL_PRIME": {
  "version": "2.5",
  "concepts": [],
  "see_also": [],
  "source": "/tmp/pytest-of-mike-anderson/pytest-35/test_version_header_in_generat0/skills/TEST_SKILL_PRIME.md"
}
```

**ACTION APPLIED:** Removed these 3 test-artifact entries from `skills/skill_registry.json`. See section 7 (Refinements Log).

**Files in skills dir NOT in curated registry (161 unregistered):** This is a large and expected gap. The curated registry covers 79 high-quality hand-verified skills. The auto-generated registry covers all 240. The gap is a curation backlog, not a defect — the curated registry is selective by design. The highest-priority unregistered files to add to the curated registry are those that are already heavily referenced or architecturally central (see recommendations, section 5).

### 2b. Frontmatter Quality Audit (all 240 .md files)

| Status | Count |
|--------|-------|
| Has valid YAML frontmatter (starts with `---`) | 177 |
| No frontmatter at all | 63 |
| Has frontmatter, missing `name` field | 2 |
| Has frontmatter, missing `description` field | 2 |
| Has both `name` + `description` (fully compliant per CLAUDE.md L273) | 158 |

**Files missing `name` field (silent capability blackout risk):**
- `CAPABILITY_REGISTRY_PRIME.md` — has description but no name
- `project_management.md` — has description but no name

**Files missing `description` field:**
- `CI_INFRASTRUCTURE_FIXES_S104.md` — has all other fields but no description
- `COMPOUND_LOOP_CLOSURE_S104.md` — has all other fields but no description

**Files with NO frontmatter (63 total — highest blackout risk):** These files exist as raw markdown with no YAML header. They cannot be auto-discovered by the capability registry until they have frontmatter. Complete list:
```
3d_rendering.md, ARC_INTERACTIVE_REASONING.md, EXTRACTED_BLOCK_D41D8CD9.md,
RETROSPECTIVE_SKILL.md, SURREALDB_MOCK_PERSISTENCE_PRIME.md, SYNC_ASYNC_BRIDGE_PRIME.md,
adaptive_template_engine.md, advanced_physics_simulation.md, alignment_verification.md,
allostatica_prime.md, animations.md, api_patterns.md, async_workflow.md, bmad_workflow.md,
caching.md, code_simplification.md, code_standards.md, common_codebase_health.md,
compound_engineering.md, compound_prompt.md, controller_agent.md, democratic_debate.md,
embedding_strategy.md, enhanced_simulation.md, enterprise_ai_server_mastery.md,
flume_comparison.md, gateway_architecture.md, gmail_mcp.md, high_d_physics_visualization.md,
hiho_reality_sim.md, interactive_ui.md, knowledge_mining.md, learning.md,
marimo_development.md, marimo_notebooks.md, mass_simulation.md, matsumoto_hiho_synthesis.md,
meta_skill.md, metaphysics.md, multimodal_experience.md, multimodal_visualization.md,
observable_ai.md, ollama_management.md, parallel_orchestration.md, physics.md,
physics_explainability.md, physics_informed_prediction.md, plasma_theosophy.md,
pre_flight_validation.md, product_management.md, research_synthesis.md,
resource_management.md, sandboxed_simulation.md, self_evaluation.md, semantic_algebra.md,
semantic_analysis.md, skill_generator.md, smart_routing.md, swarm_orchestration.md,
swarm_synthesis.md, test_automation.md, universe_physics.md, visual_validation.md
```

Note: These files all have content parseable by the auto-generated registry (which reads H1 headings). They are dark only to capability-registry frontmatter lookups.

### 2c. see_also Cross-Reference Validation (Curated Registry)

15 dangling `see_also` references found — referenced skills that exist neither in the curated registry nor as any file on disk:

| Dangling Reference | Referenced By |
|-------------------|---------------|
| `COHEZION_BRIDGE_PRIME` | HALLUCINATION_RESOLVER_PRIME, LOCAL_OFFLOAD_PRIME |
| `COHEZION_VAULT_WORKFLOW_PRIME` | SURGICAL_COMMIT_UNDER_CHURN_PRIME |
| `FLUME_DYNAMICS_PRIME` | ASCENSION_SKILL_PRIME |
| `FLUME_ENCODER_PRIME` | QUANTUM_MPS_ROUTING_PRIME |
| `FLUME_NAVIGATOR_PRIME` | HIHO_STABILITY_PRIME |
| `METAPHYSICS_PRIME` | COMPOUND_ENGINEERING_PRIME |
| `PERSISTENT_QUALITY_PRIME` | HALLUCINATION_RESOLVER_PRIME, IDE_OPTIMIZATION_PRIME, LOCAL_OFFLOAD_PRIME, QUANTUM_MPS_ROUTING_PRIME |
| `PHYSICS_EXPLAINABILITY_PRIME` | CONSTITUTION_PRIME |
| `PHYSICS_INFORMED_PREDICTION_PRIME` | COMPUTATIONAL_RELATIVITY_PRIME |
| `PHYSICS_PRIME` | COMPOUND_ENGINEERING_PRIME |
| `RESOURCE_MANAGEMENT_PRIME` | TEMPORAL_PRECISION_PRIME |
| `REWARD_AND_RATCHET_PRIME` | ASCENSION_SKILL_PRIME |
| `SKILL_GENERATOR_PRIME` | ADAPTIVE_TEMPLATE_PRIME, ANTHROPIC_SKILL_BUILDER_PRIME |
| `SWARM_ORCHESTRATION_PRIME` | HIHO_STABILITY_PRIME, INTERPRETABILITY_PRIME, POLYGLOT_DELEGATION_PRIME, RECOVERY_PRIME, TEAM_ORCHESTRATION_PRIME |
| `SYSTEM_HARDENING_PRIME` | RIGOROUS_EVALUATION_PRIME |

Most of these appear to be skills that were renamed or never created. `SWARM_ORCHESTRATION_PRIME` has unregistered file equivalents (`swarm_orchestration.md`) but uses a different naming convention. `METAPHYSICS_PRIME` maps to `metaphysics.md`. These are naming drift issues, not missing capabilities.

---

## 3. Full Skill Enumeration (by capability domain)

The 240 skills are organized below by the capability domains defined in CLAUDE.md's architecture table.

### Domain taxonomy used:
1. Compound Loop / Self-improvement
2. Swarm / Multi-agent Orchestration
3. Semantic Cache / Memory
4. Cost-Routing / Local Inference Fleet
5. Persistence / SurrealDB
6. Physics / Genesis Engine
7. World-Model / JEPA / RL
8. Inference Hardware / AMD / NVIDIA
9. MCP / Tool Layer
10. A2UI / AG-UI / Frontend
11. Governance / Ethics / Constitution
12. Observability / Metrics / Debugging
13. Anomaly / Reliability / Self-Healing
14. Knowledge / Vault / Research
15. Data Mesh / API / Data Products
16. Security / Adversarial
17. Testing / Quality
18. Dev Infrastructure / CI / Git
19. Specialized Physics Bridges (stealthskater, cosmology)
20. Kaggle / Competition

---

## 4. Capability × Skill Coverage Matrix

| Capability Domain | Strong Skills (3+ solid) | Partial/Weak | Gap Level |
|------------------|--------------------------|--------------|-----------|
| **Compound Loop / Self-improvement** | COMPOUND_ENGINEERING_PRIME, COMPOUND_SELF_IMPROVEMENT_PRIME, AUTORESEARCH_PRIME, RALPH_LOOP_PRIME, AUTONOMIC_EVOLUTION_PRIME, ASCENSION_SKILL_PRIME, AGENTJET_PRIME, compound_engineering, EXPANSION_PRIME | COMPOUND_TRAINING_CYCLE_PRIME, COSMIC_FIRE_PROTOCOL_PRIME | NONE — well covered |
| **Swarm / Multi-agent Orchestration** | TEAM_ORCHESTRATION_PRIME, SWARM_PLANNER_PRIME, HYBRID_SWARM_ORCHESTRATION_PRIME, POLYGLOT_DELEGATION_PRIME, QUADRATURE_PRIME, Symphony_Orchestration_PRIME, MATH_REASONING_SWARM_PRIME, parallel_orchestration, swarm_orchestration, RESEARCH_SQUAD_PRIME | controller_agent, GROUP_EVOLVING_AGENTS_PRIME | NONE — heavily covered; see merge candidates |
| **Semantic Cache / Memory** | SEMANTIC_CACHING_PRIME, caching, MEMORY_MCP_PRIME, VECTOR_STORE_PRIME, embedding_strategy, LANGCHAIN_RAG_TIER_PRIME | REDUCER_PRIME, REDUNDANCY_SUPPRESSION_PRIME | NONE |
| **Cost-Routing / Local Inference Fleet** | MODEL_ROUTING_PRIME, LOCAL_OFFLOAD_PRIME, TOKEN_EFFICIENCY_PRIME, BATCHING_PROTOCOL_PRIME, QUARTER_ON_A_STRING_PRIME, LOCAL_INFERENCE_ROUTING, PLATFORM_COORDINATOR_PRIME, smart_routing, SMALL_MODEL_SPECIALIST_PRIME, Symphony_Orchestration_PRIME | TRIUNE_SELF_PRIME | NONE — possibly over-covered (merge candidates exist) |
| **Persistence / SurrealDB** | SURREALDB_MCP_PRIME, SURREALDB_OPTIMIZER_PRIME, SURREAL_DBA_PRIME, SURREALDB_OPERATIONS_PRIME, DATABASE_PRIME, UNIVERSE_SIMULATION_PERSISTENCE_PRIME, PERSISTENT_UNIVERSE_PRIME, PROACTIVE_PERSISTENCE_PRIME | SURREALDB_MOCK_PERSISTENCE_PRIME | NONE — 5 SurrealDB-specific skills; see merge candidates |
| **Physics / Genesis Engine** | HIHO_STABILITY_PRIME, COMPUTATIONAL_RELATIVITY_PRIME, FLUME_METHODOLOGY_PRIME, MANIFOLD_INTEGRITY_PRIME, MANIFOLD_PHYSICS_OPTIMIZATION_PRIME, HOLOGRAPHIC_FLUME_PRIME, EXPERIENCE_VAE_TRAINING_PRIME, FLUME_WIKI_OUROBOROS_PRIME, NOETHER_CONSERVATION_PRIME, DISSIPATIVE_STRUCTURES_PRIME, PHYSICS_LINEAGE_PRIME, physics, metaphysics, universe_physics, advanced_physics_simulation | TENSOR_METRIC_ENGINEERING_PRIME, GREEK_PARAMETERS_PRIME | NONE — extensive coverage |
| **World-Model / JEPA / RL** | RL_ENVIRONMENT_DESIGN_PRIME, MAMBA_STATE_TRACKING_PRIME, LATENT_SPACE_INTELLIGENCE_PRIME, TRAINING_DIAGNOSTIC_LOOP_PRIME, COMPOUND_TRAINING_CYCLE_PRIME, DREAM_LOGIC_PRIME, learning | TOPOLOGICAL_VERIFICATION_PRIME | **WEAK** — JEPA-specific skill missing; world model training/evaluation pattern absent |
| **Inference Hardware / AMD** | AMD_GEMM_MXFP4_PRIME, AMD_MLA_DECODE_PRIME, AMD_MOE_MXFP4_PRIME, KERNEL_OPTIMIZATION_PRIME, TURBO_QUANT_PRIME, LEMONADE_EMBEDDABLE_INTEGRATION_PRIME, VLIW_COG_BRIDGE_PRIME, TEMPORAL_PRECISION_PRIME | TURBOQUANT_PHASE_RECOVERY_S104 | NONE — AMD well-covered |
| **Inference Hardware / NVIDIA** | BLACKWELL_HARDWARE_OPTIMIZATION_PRIME, NVIDIA_HARDWARE_OPTIMIZATION_PRIME, TRANSFORMER_ENGINE_FP4_OPTIMIZATION_PRIME, MOE_HYBRID_ENGINEERING_PRIME | KAGGLE_BLACKWELL_RUNNER_PRIME | NONE |
| **MCP / Tool Layer** | MCP_SPECIALIST_PRIME, MCP_OPTIMIZATION_PRIME, SURREALDB_MCP_PRIME, HOOKIFY_PRIME, DATA_MESH_ARCHITECT_PRIME, CAPABILITY_REGISTRY_PRIME, LAZY_INFRASTRUCTURE_PRIME, gmail_mcp, MEMORY_MCP_PRIME | QUANTUM_LINK_PRIME | NONE |
| **A2UI / AG-UI / Frontend** | FRONTEND_DESIGN_PRIME, TYPESCRIPT_ADVANCED_TYPES_PRIME, VISUALIZATION_PRIME, AMBIENT_SONIFICATION_PRIME, SHOWREEL_GENERATION_PRIME, JOURNEY_DASHBOARD_PRIME, multimodal_visualization, interactive_ui, animations | high_d_physics_visualization | **WEAK** — No skill specifically for AG-UI event streaming (SSE/typed events per `agui_events.py`) or A2UI declarative component authoring. The existing frontend skills cover general UI but not the Cohezion-specific A2UI/AG-UI protocol |
| **Governance / Ethics / Constitution** | CONSTITUTION_PRIME, AGENT_SOVEREIGNTY_ETHICS_PRIME, SYSTEM_GUARDRAILS_PRIME, QUADRATURE_PRIME | CROSS_PLATFORM_SKILL_FORMAT_PRIME | NONE |
| **Observability / Metrics / Debugging** | SYSTEM_MONITORING_PRIME, JOURNEY_TRACKING_PRIME, USAGE_ANALYTICS_PRIME, META_HARNESS_TRACES_PRIME, observable_ai, AUTONOMIC_ANALYST_PRIME, AUTONOMIC_QUALITY_GUARD_PRIME, TRAINING_DATA_CAPTURE_PRIME, INTERPRETABILITY_PRIME | TEMPORAL_PRECISION_PRIME | NONE |
| **Anomaly / Reliability / Self-Healing** | RELIABILITY_PRIME, RELIABILITY_FALLBACK_PRIME, ANTI_PATTERN_DEFENSE_PRIME, ANTI_PATTERN_GUARDIAN_PRIME, API_ERROR_RESILIENCE_PRIME, AUTONOMOUS_RESILIENCE_PRIME, SELF_HEALING_PRIME, CONNECTIVITY_MANAGEMENT_PRIME, FAIL_FAST_PRIME | AUTONOMIC_HEALING_PRIME | NONE — 4 reliability/resilience skills; see merge candidates |
| **Knowledge / Vault / Research** | VAULT_KEEPER_PRIME, KNOWLEDGE_HARVESTING_PRIME, KNOWLEDGE_GRAPH_INTEGRATION_PRIME, LLM_WIKI_PRIME, EXTERNAL_RESEARCH_PRIME, RESEARCH_PATTERNS_PRIME, AUTONOMIC_RESEARCH_PRIME, knowledge_mining, research_synthesis, HALLUCINATION_RESOLVER_PRIME | THROTTLED_SCOUT_PRIME | NONE |
| **Data Mesh / API / Data Products** | DATA_MESH_ARCHITECT_PRIME, DATABASE_PRIME, api_patterns, SYSTEM_DEFINITION_PRIME, FLEET_SYNCHRONIZATION_PRIME, gateway_architecture | product_management | **WEAK** — No skill covering the `DataProduct` typed SLA pattern or `get_cohezion_data_products()` API specifically |
| **Security / Adversarial** | ADVERSARIAL_TESTING_PRIME, ADVERSARIAL_TDD_PRIME, SECURITY_GUARDRAILS_PRIME, SANDBOX_ISOLATION_PRIME, SIMULATION_PROFILES_PRIME, RIGOROUS_EVALUATION_PRIME, DEPENDENCY_AUTOMATION_PRIME | MULTI_PERSPECTIVE_REVIEW_PRIME | NONE |
| **Testing / Quality** | TESTING_PRIME, TDD_PRIME, MYCELIUM_PRIME, AUTOHARNESS_PRIME, AUTODQA_PRIME, SYSTEMS_ENGINEERING_V_MODEL_PRIME, ADVERSARIAL_TDD_PRIME, test_automation, visual_validation, self_evaluation, pre_flight_validation | alignment_verification | NONE — extensively covered |
| **Dev Infrastructure / CI / Git** | REPO_HYGIENE_PRIME, REPOSITORY_HEALTH_PRIME, SURGICAL_COMMIT_UNDER_CHURN_PRIME, CI_INFRASTRUCTURE_FIXES_S104, CODEBASE_COHERENCE_PRIME, ELEGANT_SIMPLICITY_PRIME, ORPHAN_MODULE_INTEGRATION_PRIME, WRITING_PLANS_PRIME, BRAINSTORMING_PRIME, code_standards, code_simplification | root-archaeology | NONE |
| **Specialized Physics Bridges** | BEC_MHD_BRIDGE, COLIBRE_BRIDGE, SARFATTI_QGP_BRIDGE, SPATIAL_PHONONS_PRIME, STEALTHSKATER_CORPUS, matsumoto_hiho_synthesis, plasma_theosophy, HIHO_LM_PRIME, ARC_TOPOLOGICAL_PIVOT_PRIME | NOETHER_CONSERVATION_PRIME | NONE (specialty domain) |
| **Kaggle / Competition** | KAGGLE_COMPOUND_PRIME, KAGGLE_BLACKWELL_RUNNER_PRIME, QUANTUM_HACKATHON_PRIME, MATH_REASONING_SWARM_PRIME | ARC_INTERACTIVE_REASONING | NONE |
| **Skill Management / Meta** | ADAPTIVE_TEMPLATE_PRIME, TEMPLATE_DRIVEN_DEVELOPMENT_PRIME, RETROSPECTIVE_SKILL, CROSS_PLATFORM_SKILL_FORMAT_PRIME, ANTHROPIC_SKILL_BUILDER_PRIME, skill_generator, meta_skill, CITATIONS_PRIME | CAPABILITY_REGISTRY_PRIME | NONE |
| **Remote / Async Orchestration** | REMOTE_ORCHESTRATION_PRIME, OVERNIGHT_AUTONOMOUS_PRIME, async_workflow, LONG_RUNNING_INFERENCE_PRIME, THROTTLED_SCOUT_PRIME, RECOVERY_PRIME | QUANTUM_LINK_PRIME | NONE |
| **Platform Coordination (multi-agent fleet)** | PLATFORM_COORDINATOR_PRIME, CLAUDE_SPECIALIST_PRIME, GEMINI_SPECIALIST_PRIME, OLLAMA_SPECIALIST_PRIME, MCP_SPECIALIST_PRIME, FLEET_SYNCHRONIZATION_PRIME, PI_INTEGRATION_PRIME | SMALL_MODEL_SPECIALIST_PRIME | NONE |

---

## 5. Capability Gaps (domains with no or weak coverage)

### GAP-1: JEPA World-Model Operations (Weak)

**Domain:** World-Model / JEPA
**Situation:** `src/cohezion/world_model/jepa_world_model.py` implements a ~2M param causal JEPA predictor. `SurpriseExplorer` and `SIGReg` are production components. No dedicated skill covers how to train, evaluate, fine-tune, or checkpoint this model — only generic RL/training skills exist.

**Stub:**
```yaml
---
name: jepa-world-model-prime
description: >
  Expert in the Cohezion JEPA (Joint Embedding Predictive Architecture) world model
  (~2M params, causal masking). Use when: training or fine-tuning the JEPA predictor,
  diagnosing SurpriseExplorer anomalies, adjusting SIGReg regularization, or
  interpreting JEPAWorldModel latent predictions. Skip when: general RL environment
  design (use RL_ENVIRONMENT_DESIGN_PRIME) or generic PyTorch training (use
  TRAINING_DIAGNOSTIC_LOOP_PRIME).
version: v0.1-stub
tier: PRIME
domain: World-Model
---

# JEPA World Model Prime

## TODO
- Document JEPAWorldModel.train() / predict() API
- SurpriseExplorer trigger conditions and thresholds
- SIGReg hyperparameter guidance (regularization budget)
- Checkpoint/restore pattern via SessionPersistence
- Integration with JourneyTracker (record surprise events)
- CPU-trainable constraint: no GPU assumptions
```

### GAP-2: AG-UI Event Streaming (Weak)

**Domain:** A2UI / AG-UI
**Situation:** `src/cohezion/api/agui_events.py` defines 15+ typed SSE event types and `/api/agui/stream` endpoint. No skill covers authoring AG-UI producer code, subscribing from the React client, or the CopilotKit AG-UI typed event taxonomy.

**Stub:**
```yaml
---
name: agui-event-streaming-prime
description: >
  Expert in Cohezion AG-UI typed Server-Sent Events protocol. Use when: implementing
  new AG-UI event producers in FastAPI, adding React SSE consumers in anima_dashboard,
  extending the 15+ typed event catalog (agui_events.py), or debugging stream disconnects.
  Skip when: general frontend work (use FRONTEND_DESIGN_PRIME) or A2UI declarative
  component authoring.
version: v0.1-stub
tier: PRIME
domain: A2UI/AG-UI
see_also: [A2UI_COMPONENT_CATALOG_PRIME, FRONTEND_DESIGN_PRIME]
---

# AG-UI Event Streaming Prime

## TODO
- Enumerate the 15+ typed event types from agui_events.py
- FastAPI SSE producer pattern (StreamingResponse + asyncio.Queue)
- React useEventSource hook pattern in anima_dashboard
- Error recovery / reconnect protocol
- Testing SSE streams (mock EventSource)
```

### GAP-3: Data Product SLA Pattern (Weak)

**Domain:** Data Mesh
**Situation:** `src/cohezion/data_mesh/data_product.py` implements typed `DataProduct` with SLAs (latency, availability, quality contracts). `get_cohezion_data_products()` is the entry point for 17+ MCP servers. No skill covers authoring new data products, defining SLAs, or debugging MCP tier access control.

**Stub:**
```yaml
---
name: data-product-sla-prime
description: >
  Expert in Cohezion Data Mesh typed data products with SLA contracts. Use when:
  creating a new DataProduct definition, wiring an MCP server to the data mesh,
  setting latency/availability/quality SLAs, or debugging tier access control.
  Skip when: general database queries (use DATABASE_PRIME) or SurrealDB administration
  (use SURREAL_DBA_PRIME).
version: v0.1-stub
tier: PRIME
domain: Data Mesh
see_also: [DATA_MESH_ARCHITECT_PRIME, DATABASE_PRIME, MCP_SPECIALIST_PRIME]
---

# Data Product SLA Prime

## TODO
- DataProduct class signature and required fields
- SLA definition: latency_ms, availability_ssd, quality_threshold
- MCP tier access control mapping (tier 1/2/3)
- How to register a new product via get_cohezion_data_products()
- Failure modes: SLA breach alerts, degraded-mode fallback
```

---

## 6. Overlap / Merge Candidates (RECOMMENDATIONS — not applied)

### MERGE-1: SurrealDB Skills (5 skills — high overlap)

**Skills:** `SURREALDB_MCP_PRIME`, `SURREALDB_OPTIMIZER_PRIME`, `SURREAL_DBA_PRIME`, `SURREALDB_OPERATIONS_PRIME`, `SURREALDB_MOCK_PERSISTENCE_PRIME`

**Rationale:** All 5 skills cover SurrealDB usage. `SURREALDB_OPERATIONS_PRIME` and `SURREAL_DBA_PRIME` describe nearly identical roles (v3.0 specialist vs DBA specialist). `SURREALDB_MCP_PRIME` covers the MCP interface specifically. `SURREALDB_OPTIMIZER_PRIME` covers performance tuning. These could consolidate into 2 skills: `SURREALDB_CORE_PRIME` (operations + DBA) and `SURREALDB_ADVANCED_PRIME` (MCP + optimizer + mock patterns). Risk: moderately referenced across codebase. **Recommend human confirmation before merging.**

### MERGE-2: Reliability / Resilience Skills (4 skills — partial overlap)

**Skills:** `RELIABILITY_PRIME`, `RELIABILITY_FALLBACK_PRIME`, `ANTI_PATTERN_DEFENSE_PRIME`, `API_ERROR_RESILIENCE_PRIME`

**Rationale:** `RELIABILITY_PRIME` (circuit breakers, connection pooling) and `RELIABILITY_FALLBACK_PRIME` (primary-buffer duality, reconciliation) cover the same failure-handling space from slightly different angles. `API_ERROR_RESILIENCE_PRIME` is more specific (multi-provider fallback). These could consolidate to `RELIABILITY_PRIME` (general) + `API_ERROR_RESILIENCE_PRIME` (API-specific). **Recommend human confirmation — `ANTI_PATTERN_DEFENSE_PRIME` has distinct sudo/GTT scope, keep separate.**

### MERGE-3: Cost/Routing Local-Inference Skills (partial overlap)

**Skills:** `MODEL_ROUTING_PRIME`, `LOCAL_OFFLOAD_PRIME`, `LOCAL_INFERENCE_ROUTING`, `SMALL_MODEL_SPECIALIST_PRIME`, `QUARTER_ON_A_STRING_PRIME`

**Rationale:** All five describe routing tasks to smaller/local models to reduce cost. `MODEL_ROUTING_PRIME` (Ollama catalog) and `LOCAL_INFERENCE_ROUTING` (NPU/iGPU/CPU/cloud tiers) are the most distinct — different scope (Ollama vs Lemonade/triune). `QUARTER_ON_A_STRING_PRIME` and `LOCAL_OFFLOAD_PRIME` both describe "use SLM for menial tasks" with slightly different framing. **Recommend merging `QUARTER_ON_A_STRING_PRIME` into `LOCAL_OFFLOAD_PRIME` (both describe the same pattern), and `SMALL_MODEL_SPECIALIST_PRIME` into `MODEL_ROUTING_PRIME`. Keep `LOCAL_INFERENCE_ROUTING` separate (triune orchestrator specific).**

### MERGE-4: Orchestration Skill Cluster (6 skills — significant overlap in "how to orchestrate a team")

**Skills:** `TEAM_ORCHESTRATION_PRIME`, `SWARM_PLANNER_PRIME`, `HYBRID_SWARM_ORCHESTRATION_PRIME`, `Symphony_Orchestration_PRIME`, `swarm_orchestration`, `parallel_orchestration`

**Rationale:** `TEAM_ORCHESTRATION_PRIME` and `SWARM_PLANNER_PRIME` both describe multi-agent planning with model routing — nearly identical scope. `HYBRID_SWARM_ORCHESTRATION_PRIME` adds the Gemini+Ollama specific aspect. `Symphony_Orchestration_PRIME` covers the "la-phase" routing protocol. Suggest consolidating `SWARM_PLANNER_PRIME` into `TEAM_ORCHESTRATION_PRIME` (the PRIME is more complete), keeping `HYBRID_SWARM_ORCHESTRATION_PRIME` and `Symphony_Orchestration_PRIME` as specialized extensions. **Recommend human confirmation — widely referenced.**

---

## 7. Split Candidates (RECOMMENDATIONS — not applied)

### SPLIT-1: `COMPOUND_ENGINEERING_PRIME` — Too broad

**File:** `COMPOUND_ENGINEERING_PRIME.md` + `compound_engineering.md` (note: two files exist for this skill)

**Issue:** The compound engineering concept covers: (a) the 11-step execution pipeline, (b) skill synthesis methodology, (c) self-improvement loops, (d) cross-platform format standards. The description triggers on too many distinct requests.

**Recommendation:** Keep `COMPOUND_ENGINEERING_PRIME` for the core 11-step loop and execution patterns. Separate out the "skill synthesis/creation" aspect into a dedicated `SKILL_SYNTHESIS_PRIME`. The format-standards aspect already has `CROSS_PLATFORM_SKILL_FORMAT_PRIME`.

### SPLIT-2: `DATABASE_PRIME` — Too generic

**Issue:** Covers SurrealDB, SQLite, PostgreSQL, Redis, and vector stores — 5 distinct database paradigms. Given that Cohezion has 4+ SurrealDB-specific skills and a `VECTOR_STORE_PRIME`, the `DATABASE_PRIME` should narrow its scope to relational/SQL patterns only and explicitly defer to domain-specific skills.

**Recommendation:** Trim `DATABASE_PRIME` description to: "SQL/relational database patterns (SQLite, PostgreSQL, connection pooling, migrations). Use for traditional RDBMS work. For SurrealDB, use SURREAL_DBA_PRIME. For vector databases, use VECTOR_STORE_PRIME." — This is a definition refinement, not a structural split.

### SPLIT-3: `SYSTEM_DEFINITION_PRIME` — Conflates CLAUDE.md authoring with AI system design

**Issue:** Covers CLAUDE.md authoring, GEMINI.md authoring, pattern extraction, and anti-pattern cataloging. The Claude/Gemini config authoring is very different from general system design.

**Recommendation:** Separate into `AGENT_CONFIG_PRIME` (CLAUDE.md/GEMINI.md optimization) and preserve `SYSTEM_DEFINITION_PRIME` for architecture. Low urgency — consider at next major skill audit.

---

## 8. Definitions Refined / Fixes Applied

### Applied (low-risk fixes executed directly)

**8a. Removed 3 stale test-artifact entries from `skills/skill_registry.json`:**
- `SKILL_0_PRIME` (temp pytest path)
- `SKILL_1_PRIME` (temp pytest path)
- `TEST_SKILL_PRIME` (temp pytest path)
Original entries preserved verbatim in section 2a above.

**8b. Added `name` field to `CAPABILITY_REGISTRY_PRIME.md`:**
- Added: `name: capability-registry-prime`

**8c. Added `name` field to `project_management.md`:**
- Added: `name: project-management-prime`

**8d. Added `description` field to `CI_INFRASTRUCTURE_FIXES_S104.md`:**
- Added description summarizing the skill's content

**8e. Added `description` field to `COMPOUND_LOOP_CLOSURE_S104.md`:**
- Added description summarizing the skill's content

**8f. Sharpened `description` fields for 6 high-trigger-accuracy improvements:**
- `COMPOUND_ENGINEERING_PRIME` (curated registry entry)
- `DATABASE_PRIME` (added explicit skip conditions for SurrealDB/vector)
- `RETROSPECTIVE_SKILL.md` (added frontmatter — was completely missing)
- `RELIABILITY_PRIME` (added explicit skip: "For persistence fallback, use RELIABILITY_FALLBACK_PRIME")
- `MODEL_ROUTING_PRIME` (narrowed to Ollama-specific; added skip for Lemonade/triune)
- `LOCAL_OFFLOAD_PRIME` (sharpened trigger conditions)

### Deferred (requires frontmatter authoring for 63+ files — batched TODO)

Adding frontmatter to the 63 no-frontmatter files would require reading and summarizing each file body. The auto-generated registry at `registry/skill_registry.json` already has descriptions for most of them. The highest-priority batch (skills referenced in see_also danglers or CLAUDE.md architecture) is:

**Priority batch 1 (directly referenced in CLAUDE.md architecture or see_also from curated registry):**
```
swarm_orchestration.md, resource_management.md, physics_explainability.md,
physics_informed_prediction.md, skill_generator.md, metaphysics.md,
compound_engineering.md (already in registry as COMPOUND_ENGINEERING_PRIME)
```

**TODO for next session:** Run `populate_registry.py` to sync the auto-generated registry first, then add frontmatter to the priority batch.

---

## 9. Non-Standard / Notable Files

| File | Issue | Recommendation |
|------|-------|----------------|
| `EXTRACTED_BLOCK_D41D8CD9.md` | MD5-hash name, empty content pattern | Archive to `.archive/` |
| `BRANDING_OPS_PRIME` (no extension) | Missing `.md` extension | Rename to `BRANDING_OPS_PRIME.md` |
| `TENSOR_NETWORK_OPS_PRIME` (no extension) | Missing `.md` extension | Rename to `TENSOR_NETWORK_OPS_PRIME.md` |
| `kaggle/` (directory) | Skill stored as directory, not file | Check if it contains `SKILL.md`; restructure or convert |
| `mcp-builder/` (directory) | Skill stored as directory | Same — check for `SKILL.md` |
| `TURBOQUANT_PHASE_RECOVERY_S104.md` | Session-specific incident record, not a reusable skill | Annotate as `type: incident-record`; consider archiving to `docs/sessions/` |
| `CI_INFRASTRUCTURE_FIXES_S104.md` | Same pattern | Same recommendation |
| `COMPOUND_LOOP_CLOSURE_S104.md` | Same pattern | Same recommendation |

---

## 10. Top 5 Highest-Impact Actions

### Summary of APPLIED vs NEEDS HUMAN CONFIRMATION

**APPLIED (safe, low-risk):**
1. Removed 3 stale `/tmp` test-artifact entries from `skills/skill_registry.json`
2. Fixed 4 incomplete frontmatter fields (`name`/`description` missing in 4 files)
3. Sharpened 6 skill `description` fields for triggering accuracy

**NEEDS HUMAN CONFIRMATION (structural/merge/split):**
4. Merge SurrealDB skill cluster (5 → 2): reduces confusion about which to invoke for a given SurrealDB task
5. Run `python3 src/cohezion/registry/populate_registry.py` to sync auto-generated registry — it is 240 entries vs the actual 240 files; ensure it catches any new files

### Detailed Priority Ranking

| Rank | Action | Impact | Risk | Status |
|------|--------|--------|------|--------|
| 1 | **Fix 15 dangling `see_also` refs** in curated registry — update to correct names (e.g., `SWARM_ORCHESTRATION_PRIME` → `swarm_orchestration`, `METAPHYSICS_PRIME` → `metaphysics`) | High — broken cross-refs silently orphan skills from discovery | Low — registry edits only | NEEDS CONFIRMATION — updating 15 entries |
| 2 | **Merge RELIABILITY_PRIME + RELIABILITY_FALLBACK_PRIME** — different framing, same pattern space; currently causes ambiguous routing | High — routing ambiguity resolved | Medium | NEEDS HUMAN CONFIRMATION |
| 3 | **Merge QUARTER_ON_A_STRING_PRIME into LOCAL_OFFLOAD_PRIME** — near-duplicate "use small local model for menial tasks" | Medium-High | Low | NEEDS HUMAN CONFIRMATION |
| 4 | **Add frontmatter to priority batch of 10 no-frontmatter skills** (swarm_orchestration, resource_management, physics, etc.) — currently dark to capability registry | High | Low — additive only | DEFERRED — 63 total files, batch approach recommended |
| 5 | **Draft + create 3 gap stubs** (JEPA world model, AG-UI streaming, data-product SLA) — genuine missing documentation for production components | Medium-High | Low — new files | STUB DRAFTS in section 5 above; APPLY requires creating files |

---

## 11. Counts Summary

| Metric | Count |
|--------|-------|
| Total .md skill files in `src/cohezion/skills/` | 240 |
| Files with valid frontmatter | 177 |
| Files missing frontmatter entirely | 63 |
| Files with incomplete frontmatter (missing name or description) | 4 |
| Entries in curated registry (`skills/skill_registry.json`) | 82 → **79** after cleanup |
| Entries in auto-generated registry (`registry/skill_registry.json`) | 240 |
| Stale test-artifact entries removed from curated registry | **3** |
| Dangling see_also cross-references | 15 |
| Capability gaps found | **3** (weak coverage) |
| Gap stubs drafted | **3** |
| Merge candidates recommended | **4** |
| Split candidates recommended | **3** |
| Definitions directly refined/fixed | **13** (3 registry removals + 4 frontmatter fixes + 6 description sharpens) |
