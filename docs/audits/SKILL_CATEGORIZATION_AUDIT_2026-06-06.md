---
title: "Skill Categorization Audit — Anthropic 9-Type Taxonomy"
date: "2026-06-06"
auditor: "skill-quality-specialist"
scope: "245 .md files in src/cohezion/skills/, 242 registered in src/cohezion/registry/skill_registry.json"
status: "REPORT-ONLY — no skill files modified"
---

# Skill Categorization Audit — Anthropic 9-Type Taxonomy

Audit date: 2026-06-06
Reference: Anthropic post "Lessons from building Claude Code: how we use Skills"

---

## 1. Coverage

| Metric | Count |
|---|---|
| .md files read | 245 / 245 |
| Registry entries | 242 |
| Unregistered .md files (files not in registry) | 3 |
| Non-.md items in skills/ dir (excluded from audit) | 12 (2 subdirs, 7 .py files, skill_registry.json, kaggle/, mcp-builder/) |

**Coverage: 100% of .md skill files.** All 245 were read (frontmatter + first heading). No sampling.

Unregistered .md files (present in directory but absent from `src/cohezion/registry/skill_registry.json`):
- `EVO_ANALOGUE_ROUTING_PRIME.md`
- `TELEGRAM_HUB_ORCHESTRATION_PRIME.md`
- `TMUX_ORCHESTRATION_PRIME.md`

**Additional hygiene findings:**
- `BRANDING_OPS_PRIME` and `TENSOR_NETWORK_OPS_PRIME` are **directories** (not .md files), each containing `SKILL.md`. They are invisible to `.md`-glob tooling.
- `EXTRACTED_BLOCK_D41D8CD9.md` — filename suffix is the MD5 of the empty string; appears to be a junk artifact from an autonomous extraction that ran on an empty block.
- 67 .md files have no `name` field in YAML frontmatter; 68 have no `description` field (many are the same files). These are the lowercase/legacy skills.

---

## 2. Count Table: Skills per Type

Taxonomy source: Anthropic "Lessons from building Claude Code: how we use Skills" — 9 types.
Type 0 (Other/Out-of-Taxonomy) added because the taxonomy is software-engineering-focused and a significant portion of this library is physics, research, and theoretical/cosmological content.

| # | Type | Count | % |
|---|---|---|---|
| 0 | **Other / Out-of-Taxonomy** | 66 | 26.9% |
| 4 | **Business Process Automation** | 46 | 18.8% |
| 9 | **Infrastructure Operations** | 38 | 15.5% |
| 3 | **Data Fetching** | 19 | 7.8% |
| 5 | **Code Scaffolding** | 18 | 7.3% |
| 2 | **Product Verification** | 16 | 6.5% |
| 6 | **Code Quality Review** | 14 | 5.7% |
| 1 | **Library / API Reference** | 12 | 4.9% |
| 8 | **Runbooks** | 8 | 3.3% |
| 7 | **CI/CD** | 8 | 3.3% |
| | **TOTAL** | **245** | **100%** |

**Headline finding:** 26.9% of the library (66 skills) falls entirely outside the Anthropic 9-type taxonomy. These are physics simulation, theoretical cosmology, FLUME/HIHO research, ethics, and philosophy skills. The taxonomy was designed for software engineering workflows; it does not cover this corpus completely. Forcing these into the nearest SE type would produce misleading categorizations.

The Other bucket (all 66 files, programmatically verified):
`AGENTIC_DESIGN_PRIME.md`, `AGENT_SOVEREIGNTY_ETHICS_PRIME.md`, `AMBIENT_SONIFICATION_PRIME.md`, `ARC_INTERACTIVE_REASONING.md`, `ARC_TOPOLOGICAL_PIVOT_PRIME.md`, `ASCENSION_SKILL_PRIME.md`, `BEC_MHD_BRIDGE.md`, `BRAINSTORMING_PRIME.md`, `CITATIONS_PRIME.md`, `COLIBRE_BRIDGE.md`, `COMPUTATIONAL_RELATIVITY_PRIME.md`, `CONSTITUTION_PRIME.md`, `COSMIC_FIRE_PROTOCOL_PRIME.md`, `DISSIPATIVE_STRUCTURES_PRIME.md`, `DOC_TO_LORA_COMPRESSION_PRIME.md`, `DREAM_LOGIC_PRIME.md`, `EXPANSION_PRIME.md`, `EXPERIENCE_VAE_TRAINING_PRIME.md`, `EXTRACTED_BLOCK_D41D8CD9.md`, `FLUME_METHODOLOGY_PRIME.md`, `FLUME_WIKI_OUROBOROS_PRIME.md`, `GREEK_PARAMETERS_PRIME.md`, `GROUP_EVOLVING_AGENTS_PRIME.md`, `HARNESS_BENEFIT_ALIGNMENT_PRIME.md`, `HIHO_LM_PRIME.md`, `HIHO_STABILITY_PRIME.md`, `HOLOGRAPHIC_FLUME_PRIME.md`, `INTERPRETABILITY_PRIME.md`, `LATENT_SPACE_INTELLIGENCE_PRIME.md`, `MAMBA_STATE_TRACKING_PRIME.md`, `MANIFOLD_PHYSICS_OPTIMIZATION_PRIME.md`, `NOETHER_CONSERVATION_PRIME.md`, `PERSISTENT_UNIVERSE_PRIME.md`, `PHYSICS_LINEAGE_PRIME.md`, `QUADRATURE_PRIME.md`, `QUANTUM_HACKATHON_PRIME.md`, `QUANTUM_MPS_ROUTING_PRIME.md`, `R0_SIGMA_PRIME.md`, `REDUCER_PRIME.md`, `RESEARCH_PATTERNS_PRIME.md`, `SARFATTI_QGP_BRIDGE.md`, `SHOWREEL_GENERATION_PRIME.md`, `SPATIAL_PHONONS_PRIME.md`, `STEALTHSKATER_CORPUS.md`, `TENSOR_METRIC_ENGINEERING_PRIME.md`, `TRIUNE_SELF_PRIME.md`, `UNIVERSE_SIMULATION_PERSISTENCE_PRIME.md`, `VLIW_COG_BRIDGE_PRIME.md`, `advanced_physics_simulation.md`, `allostatica_prime.md`, `democratic_debate.md`, `enhanced_simulation.md`, `flume_comparison.md`, `high_d_physics_visualization.md`, `hiho_reality_sim.md`, `mass_simulation.md`, `matsumoto_hiho_synthesis.md`, `metaphysics.md`, `physics.md`, `physics_explainability.md`, `physics_informed_prediction.md`, `plasma_theosophy.md`, `research_synthesis.md`, `sandboxed_simulation.md`, `semantic_algebra.md`, `universe_physics.md`

---

## 3. Straddler List

A straddler genuinely drives two distinct use-cases requiring different agent trigger paths. The list below is the curated set of highest-impact straddlers — skills where both type assignments would independently cause an agent to invoke the skill for different, non-overlapping reasons. This is the "confuse the agent" hazard from the Anthropic post.

**True high-impact straddlers: 12** — skills where both types represent genuinely distinct, independent invocation reasons that would cause an agent to reach for the same skill from two different trigger paths.

Skills with any secondary type (broad definition, where secondary is consequential but one mode dominates): 131. See the Borderline section below.

### High-Impact Straddlers (split concern that materially routes incorrectly)

| File | Primary Type | Secondary Type | Why Confusing |
|---|---|---|---|
| `ADVERSARIAL_TDD_PRIME.md` | Product Verification | Code Quality Review | TDD cycle (write failing tests) and adversarial red-team review (critique existing code) are invoked for completely different reasons. |
| `AUTODQA_PRIME.md` | Product Verification | Code Quality Review | Simultaneously a QA execution system and an output quality guard. Two distinct agent invocation scenarios share this skill. |
| `AUTOHARNESS_PRIME.md` | Product Verification | CI/CD | Synthesizes verification harnesses AND wires them into CI pipelines. Test authoring vs. pipeline execution are separate concerns. |
| `COMPOUND_SELF_IMPROVEMENT_PRIME.md` | Business Process Automation | Code Quality Review | Runs the compound loop (BPA) while performing systematic code audits. Process orchestration vs. quality enforcement. |
| `KNOWLEDGE_GRAPH_INTEGRATION_PRIME.md` | Data Fetching | Library/API Reference | Bridges registry into a graph (data ops) AND documents the graph query API (reference). Two separate invocation motivations. |
| `META_HARNESS_TRACES_PRIME.md` | Product Verification | CI/CD | Manages execution traces (verification artifacts) AND optimizes the meta-harness pipeline structure (CI/CD). |
| `MODEL_ROUTING_PRIME.md` | Infrastructure Operations | Business Process Automation | Configures Ollama routing infra vs. orchestrating memory-aware task scheduling. Setup vs. runtime are distinct modes. |
| `OVERNIGHT_AUTONOMOUS_PRIME.md` | Business Process Automation | Runbooks | Orchestrates long sessions (BPA) while encoding the operational runbook for safe sustained execution (recovery, checkpointing). |
| `PLATFORM_COORDINATOR_PRIME.md` | Business Process Automation | Infrastructure Operations | Routes tasks across providers (BPA) vs. managing provider infrastructure (health, cost tiers, fallback). |
| `SURREALDB_MCP_PRIME.md` | Library/API Reference | Data Fetching | Documents the MCP tool schema (lib ref) AND describes live query / record fetch operations (data fetching). Both modes prominent. |
| `SYSTEMS_ENGINEERING_V_MODEL_PRIME.md` | Business Process Automation | Product Verification | V-Model process workflow (BPA) vs. the verification/validation methodology (product verification). Process vs. test strategy. |
| `VAULT_KEEPER_PRIME.md` | Data Fetching | Infrastructure Operations | Queries vault contents (data fetching) vs. maintaining vault infrastructure -- orphan detection, frontmatter enforcement (infra ops). |

### Borderline Straddlers (secondary type is consequential but weaker)

These 119 skills have a secondary type but one mode is clearly dominant. Listed by pair for awareness:

- **Product Verification + Code Quality Review (4 skills):** `ADVERSARIAL_TESTING_PRIME`, `AUTODQA_PRIME`, `MANIFOLD_INTEGRITY_PRIME`, `TDD_PRIME`
- **Business Process Automation + Infrastructure Operations (8 skills):** `EVO_ANALOGUE_ROUTING_PRIME`, `HOOKIFY_PRIME`, `HYBRID_SWARM_ORCHESTRATION_PRIME`, `PLATFORM_COORDINATOR_PRIME`, `QUARTER_ON_A_STRING_PRIME`, `REMOTE_ORCHESTRATION_PRIME`, `Symphony_Orchestration_PRIME`, `THROTTLED_SCOUT_PRIME`
- **Data Fetching + Infrastructure Operations (6 skills):** `MEMORY_MCP_PRIME`, `SEMANTIC_CACHING_PRIME`, `SURREALDB_OPERATIONS_PRIME`, `SURREALDB_OPTIMIZER_PRIME`, `SURREAL_DBA_PRIME`, `VAULT_KEEPER_PRIME`
- **Code Quality Review + Runbooks (3 skills):** `ANTI_PATTERN_DEFENSE_PRIME`, `SECURITY_GUARDRAILS_PRIME`, `SYSTEM_GUARDRAILS_PRIME`
- **CI/CD + Infrastructure Operations (2 skills):** `DEPENDENCY_AUTOMATION_PRIME`, `REPOSITORY_HEALTH_PRIME`

---

## 4. Description-Style Issues

Reference: Anthropic lesson #3 — "descriptions are for model triggering, not human reading." A description written as a noun-phrase summary or persona statement with no trigger conditions (no "use when...", no symptoms/error-strings/scenario language) is a description-style issue.

**Audited surface:** YAML frontmatter `description` field in each .md file. Registry descriptions were not separately audited; frontmatter is the triggering surface.

| Issue Category | Count |
|---|---|
| Missing description entirely (no frontmatter `description` field) | 68 |
| Persona-only (starts "You are..." or "Expert in..." with no trigger language) | 63 |
| Noun-phrase summary (human-readable but no trigger conditions) | 71 |
| **Total with description-style issues** | **202 / 245 (82%)** |

Note: 68 missing + 63 persona-only + 71 noun-phrase = 202. Some skills have both missing frontmatter name and description. The hygiene check found 67 files without a `name` field and 68 without a `description` field — one skill has a `description` but no `name`. Counts in the persona-only and noun-phrase rows are heuristic estimates: the extraction pass captured only the first line of multi-line descriptions, so skills with trigger language on line 2+ may be under-counted; the actual issue rate is likely lower than 82%.

**Representative persona-only offenders** (skills where the description says what the agent IS, not when to use it):

- `ADAPTIVE_TEMPLATE_PRIME.md`: `"You are a structural meta-engineer specializing in the evolution of codebase blueprints..."` — no trigger
- `ANTI_PATTERN_DEFENSE_PRIME.md`: `"You are a Staff Security and Reliability Engineer focused on preventing systemic illusions..."` — no trigger
- `AUTONOMIC_ANALYST_PRIME.md`: `"You are a real-time systems analyst specializing in cross-domain correlation..."` — no trigger
- `AUTORESEARCH_PRIME.md`: `"You are a specialist in Autonomous Experimentation Loops..."` — no trigger
- `CODEBASE_COHERENCE_PRIME.md`: `"You are a Codebase Coherence Engineer specializing in maintaining production-quality repositories..."` — no trigger
- `COMPOUND_TRAINING_CYCLE_PRIME.md`: `"You are a Compound Training Engineer who runs the closed-loop RL training cycle..."` — no trigger

**Representative noun-phrase offenders:**

- `AGENTIC_DESIGN_PRIME.md`: `"The art and science of 'Agentic Aesthetics'..."` — topic description, not a trigger
- `AMBIENT_SONIFICATION_PRIME.md`: `"Audible representation of complex system states. Mapping high-dimensional data..."` — what it does, not when to invoke
- `AMD_GEMM_MXFP4_PRIME.md`: `"MXFP4 GEMM kernel optimization for AMD MI355X..."` — capability summary, no trigger condition
- `BATCHING_PROTOCOL_PRIME.md`: `"Expert methodology for consolidating multiple independent, menial tasks..."` — methodology description, not a trigger
- `CITATIONS_PRIME.md`: `"Managing sovereign attribution and technical citations..."` — noun phrase, no scenario

---

## 5. Recommendations (Non-Destructive — Do Not Apply)

These are example fixes to illustrate the post's guidance. No files have been modified.

### REC-1: Split ADVERSARIAL_TDD_PRIME into two skills

Current: Single skill merges TDD test-authoring (Product Verification) with adversarial code critique (Code Quality Review).

Suggested split:
- `ADVERSARIAL_TDD_PRIME.md` (Product Verification) — trigger: "Use when writing tests for a new feature or when a test suite is missing coverage for a behavior."
- `ADVERSARIAL_REVIEW_PRIME.md` (Code Quality Review) — trigger: "Use when reviewing a completed implementation for logical fallacies, hallucinations, or unsafe assumptions."

### REC-2: Split SYSTEMS_ENGINEERING_V_MODEL_PRIME into process + verification skills

Current: Encodes V-Model process workflow (BPA) and verification/validation methodology (Product Verification) in one file.

Suggested split:
- `V_MODEL_PROCESS_PRIME.md` (Business Process Automation) — trigger: "Use when decomposing a multi-module feature request into sequenced implementation tasks with explicit verification gates."
- `V_MODEL_VERIFICATION_PRIME.md` (Product Verification) — trigger: "Use when validating that an implemented module satisfies its requirements specification."

### REC-3: Rewrite AUTODQA_PRIME description from persona to trigger

Current description: `"AUTODQA — Automated Design Quality Assurance for Cohezion compound engineering. Self-referential QA system that dogfoods the full inference stack..."` (capability summary, no trigger language)

Suggested: `"Use when an agent output needs to be evaluated for quality before being accepted: routes through task_classifier to NPU/iGPU/CPU, gates with HIHO score >= 0.45, blocks prompt injection and credential leaks. Triggered automatically after execute_task() in CompoundExecutor. Also use when building quality gates for new pipeline stages."`

### REC-4: Convert COMPOUND_SELF_IMPROVEMENT_PRIME to pure BPA, extract quality concern

Current: Orchestrates the compound loop (BPA) while simultaneously performing code quality reviews. Mixed concern confuses routing between "run improvement cycle" and "review this code."

Suggested: Move the code quality review checklist into `COMPOUND_QUALITY_GATES_PRIME.md` (Code Quality Review) with trigger: "Use when evaluating whether a PRIME skill update meets quality standards before commit." Keep `COMPOUND_SELF_IMPROVEMENT_PRIME` as pure BPA with trigger: "Use when Cohezion needs to self-improve a specific module using its own compound loop (Execute → Retrospect → Refine)."

### REC-5: Rewrite persona-only descriptions across the PRIME library

Pattern to fix (affects 63 skills): Replace `"You are a [role] specializing in [domain]..."` with `"Use when [concrete scenario]. Triggered by [symptoms/conditions]. Handles [specific cases]."`.

Example for `ADAPTIVE_TEMPLATE_PRIME.md`:

Current: `"You are a structural meta-engineer specializing in the evolution of codebase blueprints. You understand that static templates become technical debt..."`

Suggested: `"Use when a PRIME skill or workflow template has drifted from current system patterns, or when a retrospective identifies a structural inconsistency repeated across 3+ sessions. Triggered after retrospectives that surface template debt. Refines skill definitions, schema stubs, and workflow templates based on execution outcomes."`

### REC-6: Add a 10th type for Cohezion-specific out-of-taxonomy skills

The 66 Other/Out-of-Taxonomy skills are not software engineering but are valid within this library. Rather than abandoning the taxonomy for them, consider adding:

- **Type 10: Research / Theory** — covers physics bridges, FLUME research, HIHO theory, ARC reasoning experiments. Trigger language: "Use when investigating or simulating [physics/theoretical domain]."

This would make the taxonomy complete for this corpus and give agents a clear home for cosmological, physics, and theoretical skills.

### REC-7: Register the 3 unregistered skills

`EVO_ANALOGUE_ROUTING_PRIME.md`, `TELEGRAM_HUB_ORCHESTRATION_PRIME.md`, and `TMUX_ORCHESTRATION_PRIME.md` are absent from `src/cohezion/registry/skill_registry.json`. They are functional skills used in sessions but invisible to registry-based discovery.

### REC-8: Rename or resolve the two directory-style skills

`BRANDING_OPS_PRIME/` and `TENSOR_NETWORK_OPS_PRIME/` are directories (each with `SKILL.md` + `__init__.py`). This format works for Python-importable skills but breaks any tooling that globs `*.md` for discovery. Either rename the inner file to match the glob pattern or convert them to flat `.md` files.

---

## 6. Summary Statistics

| Metric | Value |
|---|---|
| Total .md skills audited | 245 / 245 (100%) |
| Registered in authoritative registry | 242 |
| Outside Anthropic 9-type taxonomy | 66 (26.9%) |
| Largest type: Business Process Automation | 46 (18.8%) |
| Second largest: Infrastructure Operations | 38 (15.5%) |
| High-impact straddlers (confuse agent routing) | 12 |
| Skills with any secondary type (broad, weaker signal) | 131 (53.5%) |
| Skills with description-style issues | 202 (82.4%) |
| -- Missing description entirely | 68 |
| -- Persona-only, no trigger language | 63 |
| -- Noun-phrase summary, no trigger | 71 |
| Junk artifact | 1 (EXTRACTED_BLOCK_D41D8CD9.md) |
| Directory-format skills (not .md) | 2 (BRANDING_OPS_PRIME, TENSOR_NETWORK_OPS_PRIME) |

---

*Report is read-only. No skill files were modified during this audit.*
