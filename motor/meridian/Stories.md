---
title: "Meridian Concierge Agent - User Stories"
project: cohezion
type: stories
status: draft
created: 2026-03-06
tags: [meridian, concierge, stories, sprint-planning]
aspect: doer
neural:
  activation: 0.735
  stage: growing
  cluster: projects
---

# Meridian: User Stories

---

## Epic 1: Composite Router Facade

### E1-S1: Define Meridian Core Types

**As a** developer building Meridian,
**I want** well-defined data types for routing decisions, signals, and configurations,
**So that** all Meridian components share a consistent interface.

**Acceptance Criteria**:
- [ ] `MeridianRoutingDecision` dataclass with: model, score, confidence, signals, dialect, context_budget, cascade_threshold, skill, estimated_cost, estimated_latency
- [ ] `RoutingSignals` dataclass with: intent_fit, capability_fit, cost_efficiency, hw_feasibility, vault_experience (all float 0.0-1.0)
- [ ] `MeridianResult` dataclass with: response, model_used, quality_score, tokens_used, cost_usd, latency_ms, cascade_depth
- [ ] All types are Pydantic models for validation
- [ ] Types exported from `concierge/__init__.py`

**Technical Notes**:
- File: `src/cohezion/concierge/types.py`
- ~100 lines
- No dependencies on existing routers (pure data definitions)

**Story Points**: 1

---

### E1-S2: Implement Signal Normalization

**As a** developer building the CompositeRouter,
**I want** each existing router's output normalized to a 0.0-1.0 scale,
**So that** signals can be combined via weighted sum regardless of their native output format.

**Acceptance Criteria**:
- [ ] CostAwareRouter output normalized: `1.0 - (cost / max_budget)`
- [ ] SmartRouter output normalized: `capability_score / 100`
- [ ] DynamicModelRouter output normalized: `1.0 if feasible, tps/max_tps otherwise`
- [ ] RequestAlignmentAnalyzer coherence passed through (already 0.0-1.0)
- [ ] SkillSelector composite passed through (already 0.0-1.0)
- [ ] Each normalizer handles edge cases (division by zero, missing values)
- [ ] 5 unit tests covering normalization edge cases

**Technical Notes**:
- File: `src/cohezion/concierge/composite_router.py`
- Uses existing router APIs — no modifications to existing routers
- Mock routers in tests: `@patch("cohezion.swarm.cost_aware_router.CostAwareRouter")`

**Story Points**: 2

---

### E1-S3: Implement Composite Scoring Function

**As a** developer building the CompositeRouter,
**I want** a weighted sum function that combines all 5 normalized signals into a single composite score,
**So that** model selection considers all routing dimensions simultaneously.

**Acceptance Criteria**:
- [ ] `compute_composite_score(signals, weights)` returns float 0.0-1.0
- [ ] Default weights: intent 30%, capability 25%, cost 20%, hardware 15%, experience 10%
- [ ] Weights configurable via `config.py`
- [ ] Weights must sum to 1.0 (validated)
- [ ] Missing signals handled gracefully (redistribute weight to remaining signals)
- [ ] 5 unit tests covering scoring scenarios

**Technical Notes**:
- File: `src/cohezion/concierge/composite_router.py`
- Pure function, no side effects
- Consider: Should the scoring function be pluggable (strategy pattern)? Decision: No, KISS. Start with weighted sum, replace later if needed.

**Story Points**: 2

---

### E1-S4: Implement CompositeRouter Orchestration

**As a** developer building MeridianAgent,
**I want** a `CompositeRouter.route(query)` method that calls all existing routers, normalizes their outputs, computes composite scores for each candidate model, and returns the best model,
**So that** routing decisions are made holistically.

**Acceptance Criteria**:
- [ ] `CompositeRouter.route(query, constraints)` returns `MeridianRoutingDecision`
- [ ] Calls RequestAlignmentAnalyzer, SkillSelector, CostAwareRouter, SmartRouter, DynamicModelRouter
- [ ] Handles individual router failures gracefully (skip failed router, redistribute weight)
- [ ] Routing latency <50ms (measured in test)
- [ ] Returns top-3 candidates with scores (best selected, alternatives available for cascade)
- [ ] 5 integration tests with mocked routers

**Technical Notes**:
- File: `src/cohezion/concierge/composite_router.py`
- All router calls are synchronous (heuristic-based, no I/O)
- If a router raises, catch and log warning, continue with remaining signals

**Story Points**: 3

---

### E1-S5: Implement MeridianAgent Entry Point

**As a** user or calling code,
**I want** a single `MeridianAgent` class with `route()`, `execute()`, and `cascade()` methods,
**So that** I have one entry point for all Meridian functionality.

**Acceptance Criteria**:
- [ ] `MeridianAgent.route(query)` → `MeridianRoutingDecision` (route only, no execution)
- [ ] `MeridianAgent.execute(query)` → `MeridianResult` (route + execute via CompoundExecutor)
- [ ] `MeridianAgent.cascade(query)` → `MeridianResult` (route + cascading execution)
- [ ] Singleton pattern consistent with existing Cohezion singletons
- [ ] Configuration via `MeridianConfig` dataclass
- [ ] Exported from `concierge/__init__.py`
- [ ] 3 integration tests (route, execute, cascade paths)

**Technical Notes**:
- File: `src/cohezion/concierge/meridian.py`
- `execute()` and `cascade()` are async (I/O for model calls)
- `route()` is sync (heuristic-only)

**Story Points**: 3

---

## Epic 2: Prompt Dialect Registry

### E2-S1: Define Dialect Configuration Schema

**As a** developer building the PromptDialectRegistry,
**I want** a well-defined schema for dialect configurations,
**So that** new dialects can be added without code changes.

**Acceptance Criteria**:
- [ ] `DialectConfig` dataclass with: family, model_patterns, reasoning_style, preferred_verbs, context_format, system_prompt_style, max_preamble_tokens, strengths
- [ ] Model-to-dialect mapping via glob patterns (e.g., `claude-*` → claude dialect)
- [ ] 5 built-in dialects defined: claude, gemini, ollama_small, ollama_coder, ollama_reasoner
- [ ] Default dialect for unknown models: `ollama_small` (safest)
- [ ] 3 unit tests for model-to-dialect resolution

**Technical Notes**:
- File: `src/cohezion/concierge/prompt_dialect.py`
- ~80 lines for schema + registry
- Glob matching via `fnmatch` for model_patterns

**Story Points**: 2

---

### E2-S2: Implement Prompt Transformation Engine

**As a** developer building Meridian,
**I want** a function that transforms a prompt's phrasing based on the target dialect without changing its semantic intent,
**So that** each model receives prompts optimized for its strengths.

**Acceptance Criteria**:
- [ ] `transform_prompt(prompt, dialect, intent)` returns transformed prompt string
- [ ] Verb substitution: replaces generic verbs with dialect-preferred verbs
- [ ] Preamble adjustment: adds/removes system-level framing per dialect
- [ ] Context format: wraps context in dialect-appropriate format (XML tags for Claude, minimal for phi3)
- [ ] Semantic intent preserved (transformed prompt asks for the same thing)
- [ ] 5 unit tests covering each dialect family

**Technical Notes**:
- File: `src/cohezion/concierge/prompt_dialect.py`
- ~150 lines for transformation logic
- Uses regex for verb substitution, string templates for preamble/context formatting
- Does NOT call an LLM for transformation — all heuristic-based

**Story Points**: 3

---

### E2-S3: Integrate Dialects into MeridianAgent Pipeline

**As a** user making requests through Meridian,
**I want** my prompts automatically dialect-shaped before reaching the selected model,
**So that** I get better responses without manually tuning prompts.

**Acceptance Criteria**:
- [ ] MeridianAgent.execute() applies dialect transformation between routing and execution
- [ ] Dialect selection based on routed model (via model-to-dialect mapping)
- [ ] Original prompt preserved in logging (both original and transformed logged)
- [ ] Dialect bypass option via `MeridianConfig.disable_dialect_shaping`
- [ ] 3 integration tests: end-to-end with dialect shaping

**Technical Notes**:
- Modify: `src/cohezion/concierge/meridian.py`
- Add dialect step between composite_router.route() and executor.execute()

**Story Points**: 2

---

### E2-S4: Dialect Effectiveness Tracking

**As a** developer optimizing Meridian,
**I want** dialect effectiveness tracked in vault,
**So that** we can measure whether dialect shaping improves response quality and adjust over time.

**Acceptance Criteria**:
- [ ] After each execution, log: model, dialect_family, quality_score, query_hash
- [ ] Vault entry at: `sessions/{session}/dialect_metrics/{timestamp}.md`
- [ ] Aggregate query: "average quality by dialect family" possible via vault search
- [ ] Non-blocking logging (try/except wrapped)

**Technical Notes**:
- Add to: `src/cohezion/concierge/meridian.py` (logging step)
- Vault writes are async and non-blocking
- Future: use this data to auto-tune dialect configs

**Story Points**: 1

---

## Epic 3: Context Budgeter

### E3-S1: Implement Token Counting

**As a** developer building the ContextBudgeter,
**I want** accurate token counting for context pieces,
**So that** I can calculate how much context fits within a model's window.

**Acceptance Criteria**:
- [ ] `count_tokens(text)` returns approximate token count
- [ ] Uses word-based heuristic: `len(text.split()) * 1.3` (fast, ~90% accurate)
- [ ] Model-specific context windows defined in config
- [ ] Available budget = context_window - prompt_tokens - output_reserve
- [ ] 3 unit tests for token counting accuracy

**Technical Notes**:
- File: `src/cohezion/concierge/context_budget.py`
- Avoid importing tiktoken (heavy dependency) — use heuristic
- Output reserve default: 2048 tokens

**Story Points**: 1

---

### E3-S2: Implement Relevance Ranking

**As a** developer building the ContextBudgeter,
**I want** context pieces ranked by semantic relevance to the query,
**So that** the most important context is included when budget is limited.

**Acceptance Criteria**:
- [ ] `rank_by_relevance(pieces, query)` returns pieces sorted by relevance score
- [ ] Uses SemanticCache's embedding similarity for ranking
- [ ] Fallback to keyword overlap when embeddings unavailable
- [ ] 3 unit tests with mock embeddings

**Technical Notes**:
- File: `src/cohezion/concierge/context_budget.py`
- Import: `from cohezion.cache.semantic_cache import SemanticCache`
- Reuse existing 384D all-MiniLM-L6-v2 embeddings

**Story Points**: 2

---

### E3-S3: Implement Greedy Fill Algorithm

**As a** developer building the ContextBudgeter,
**I want** a greedy fill algorithm that selects top-ranked context pieces until the budget is exhausted,
**So that** context utilization is maximized within the model's capacity.

**Acceptance Criteria**:
- [ ] `budget(pieces, model_window, prompt_tokens, output_reserve)` returns selected pieces
- [ ] If all pieces fit, return all (no filtering)
- [ ] Greedy fill: iterate ranked pieces, add until budget exhausted
- [ ] Partial fit: compress last piece to fill remaining space
- [ ] Context utilization ratio = used_tokens / available_tokens (logged)
- [ ] 5 unit tests: all-fit, partial-fit, nothing-fits, compression, edge cases

**Technical Notes**:
- File: `src/cohezion/concierge/context_budget.py`
- Compression: truncate to first N sentences that fit (heuristic, not LLM)

**Story Points**: 2

---

### E3-S4: Integrate Context Budgeter into Meridian Pipeline

**As a** user making requests through Meridian,
**I want** context automatically budgeted for the selected model,
**So that** the model gets the right amount of context regardless of its capacity.

**Acceptance Criteria**:
- [ ] MeridianAgent.execute() applies context budgeting after model selection
- [ ] Context pieces sourced from: vault guidance, skill context, user-provided context
- [ ] Budget applied before prompt dialect shaping (budget first, then shape)
- [ ] Bypass option via `MeridianConfig.disable_context_budgeting`
- [ ] 3 integration tests with different model capacities

**Technical Notes**:
- Modify: `src/cohezion/concierge/meridian.py`
- Pipeline order: route → budget context → shape prompt → execute

**Story Points**: 2

---

## Epic 4: Cascade Executor

### E4-S1: Define Cascade Tier Configuration

**As a** developer building the CascadeExecutor,
**I want** configurable cascade tiers with model, cost ceiling, and quality threshold,
**So that** the cascade strategy can be tuned per deployment.

**Acceptance Criteria**:
- [ ] `CascadeTier` dataclass with: name, model, max_cost_usd, quality_threshold, timeout_seconds, best_for
- [ ] Default 4-tier config: local_fast, local_capable, cloud_standard, cloud_premium
- [ ] Config loadable from `concierge/config.py`
- [ ] Tiers ordered by cost (cheapest first)
- [ ] 2 unit tests for config validation

**Technical Notes**:
- File: `src/cohezion/concierge/cascade.py` + `config.py`
- Tiers are a list, not a hierarchy — can skip tiers based on initial routing

**Story Points**: 1

---

### E4-S2: Implement Quality Assessment Integration

**As a** developer building the CascadeExecutor,
**I want** output quality assessed after each tier's execution,
**So that** the cascade can decide whether to accept the result or escalate.

**Acceptance Criteria**:
- [ ] `assess_quality(result, success_criteria)` returns float 0.0-1.0
- [ ] Uses existing ModelQualityClassifier
- [ ] Assessment criteria: completeness, coherence, specificity, format compliance
- [ ] Quality score compared against tier's quality_threshold
- [ ] 3 unit tests with mocked classifier

**Technical Notes**:
- File: `src/cohezion/concierge/cascade.py`
- Import: `from cohezion.compound.model_quality_classifier import ModelQualityClassifier`
- If classifier unavailable, use heuristic: response length > 50 tokens = 0.6 quality

**Story Points**: 2

---

### E4-S3: Implement Cascade Execution Loop

**As a** developer building the CascadeExecutor,
**I want** an execution loop that tries each tier in order, escalating when quality is insufficient,
**So that** tasks are handled at the cheapest tier that produces acceptable quality.

**Acceptance Criteria**:
- [ ] `CascadeExecutor.execute(task, context, tiers)` returns `MeridianResult`
- [ ] Starts at tier 0 (cheapest), executes, assesses quality
- [ ] If quality >= threshold: accept and return
- [ ] If quality < threshold: escalate to next tier
- [ ] If all tiers exhausted: return best result with cascade_depth in metadata
- [ ] Budget enforcement: cumulative cascade cost cannot exceed per-query budget
- [ ] 5 unit tests: single-tier success, escalation, budget cutoff, all-tiers, timeout

**Technical Notes**:
- File: `src/cohezion/concierge/cascade.py`
- Each tier execution is async (model I/O)
- Context re-budgeted for each tier (different models have different windows)

**Story Points**: 3

---

### E4-S4: Implement Cascade Event Logging

**As a** developer optimizing Meridian routing,
**I want** cascade events logged to vault,
**So that** I can analyze escalation patterns and improve initial routing.

**Acceptance Criteria**:
- [ ] Each cascade event logged: tier, model, quality_score, cost, latency, escalation_reason
- [ ] Vault entry at: `sessions/{session}/cascade/{timestamp}.md`
- [ ] Summary metric: cascade_depth per request
- [ ] Non-blocking logging (try/except wrapped)
- [ ] 2 unit tests for log format

**Technical Notes**:
- File: `src/cohezion/concierge/cascade.py`
- Vault writes are async
- Future: analyze cascade logs to adjust initial routing weights

**Story Points**: 1

---

### E4-S5: Integrate Cascade into MeridianAgent

**As a** user calling `MeridianAgent.cascade(query)`,
**I want** cascading execution that transparently tries cheap models first,
**So that** I get the best quality/cost trade-off without manual model selection.

**Acceptance Criteria**:
- [ ] `MeridianAgent.cascade(query)` routes, then executes via CascadeExecutor
- [ ] Cascade tiers filtered by initial routing decision (skip tiers below router's recommendation)
- [ ] Smart cascade: if CompositeRouter is very confident (>0.9), skip cascade and use recommended model directly
- [ ] Result includes cascade_depth and total_cost in metadata
- [ ] 3 integration tests: no-cascade (high confidence), single-escalation, multi-escalation

**Technical Notes**:
- Modify: `src/cohezion/concierge/meridian.py`
- Optimization: if composite score confidence > 0.9, skip cascade overhead

**Story Points**: 2

---

## Epic 5: Meridian API & Integration

### E5-S1: FastAPI Route Endpoints

**As a** platform or API consumer,
**I want** HTTP endpoints for Meridian routing and execution,
**So that** I can call Meridian from any platform via REST API.

**Acceptance Criteria**:
- [ ] POST /meridian/route — accepts query, returns MeridianRoutingDecision (JSON)
- [ ] POST /meridian/execute — accepts query, returns MeridianResult (JSON)
- [ ] POST /meridian/cascade — accepts query + optional tier config, returns MeridianResult
- [ ] Request/response schemas defined via Pydantic
- [ ] OpenAPI docs auto-generated at /docs
- [ ] 3 endpoint tests via httpx TestClient

**Technical Notes**:
- File: `src/cohezion/api/meridian_routes.py`
- Register with existing FastAPI app in `src/cohezion/api/__init__.py`
- Follow existing API patterns (see other route files)

**Story Points**: 3

---

### E5-S2: BMAD Task Type Auto-Mapping

**As a** BMAD workflow user,
**I want** BMAD task types automatically mapped to Meridian routing decisions,
**So that** running "create architecture" or "quick dev" automatically selects the optimal model.

**Acceptance Criteria**:
- [ ] Mapping table: BMAD task type → intent + complexity + recommended model tier
- [ ] `create-architecture` → COMPLEX → deep reasoning model
- [ ] `quick-dev` → SIMPLE → fast local model
- [ ] `code-review` → MEDIUM → code-specialized model
- [ ] `create-prd` → COMPLEX → structured output model
- [ ] `sprint-status` → SIMPLE → retrieval model
- [ ] Mapping extensible via config
- [ ] 5 unit tests covering each BMAD task type

**Technical Notes**:
- File: `src/cohezion/concierge/config.py` (mapping table)
- Integrated via MeridianAgent: detect BMAD skill name in query → apply mapping

**Story Points**: 2

---

### E5-S3: Meridian Metrics Endpoint

**As a** developer monitoring Meridian,
**I want** a /meridian/metrics endpoint returning routing statistics,
**So that** I can monitor routing quality, cascade frequency, and cost savings.

**Acceptance Criteria**:
- [ ] GET /meridian/metrics returns JSON with:
  - avg_routing_latency_ms
  - total_requests_routed
  - cascade_depth_distribution
  - model_selection_distribution
  - cost_savings_pct (vs always-premium baseline)
  - avg_quality_score
- [ ] Data sourced from GlobalMetricsAggregator
- [ ] 5-minute rolling window
- [ ] 2 endpoint tests

**Technical Notes**:
- File: `src/cohezion/api/meridian_routes.py`
- Reuse existing GlobalMetricsAggregator infrastructure

**Story Points**: 2

---

### E5-S4: Meridian Dialect Listing Endpoint

**As a** developer or API consumer,
**I want** a /meridian/dialects endpoint listing available prompt dialects,
**So that** I can understand what model families Meridian supports and their characteristics.

**Acceptance Criteria**:
- [ ] GET /meridian/dialects returns JSON list of dialect configs
- [ ] Each dialect includes: family, model_patterns, reasoning_style, strengths
- [ ] 1 endpoint test

**Technical Notes**:
- File: `src/cohezion/api/meridian_routes.py`
- Read-only, returns dialect registry data

**Story Points**: 1

---

## Epic 6: Cross-Platform Session Bridge

### E6-S1: Session Export

**As a** user working in Claude Code,
**I want** to export my current session state,
**So that** I can continue the same task on another platform (Gemini CLI, Cursor, etc.).

**Acceptance Criteria**:
- [ ] `SessionBridge.export_session(session_id)` returns `SessionExport` dataclass
- [ ] Exports: intent_history, active_skill, context_pieces, model_usage, checkpoint, vault_refs
- [ ] Sensitive data sanitized (regex filter for SECRET|KEY|PASSWORD|TOKEN patterns)
- [ ] Export stored in vault at `sessions/{session_id}/exports/{timestamp}.md`
- [ ] 3 unit tests: export, sanitization, vault storage

**Technical Notes**:
- File: `src/cohezion/concierge/session_bridge.py`
- Reuses existing SessionManager for state access
- Sanitization is conservative — better to strip too much than leak secrets

**Story Points**: 2

---

### E6-S2: Session Import

**As a** user switching to a new platform,
**I want** to import a previously exported session,
**So that** I can resume work with full context preserved.

**Acceptance Criteria**:
- [ ] `SessionBridge.import_session(session_export)` returns reconstructed session_id
- [ ] Reconstructs: intent history, active skill, context, model usage
- [ ] Validates export version compatibility (v1.0)
- [ ] Logs import event to vault
- [ ] 3 unit tests: import, version validation, context reconstruction

**Technical Notes**:
- File: `src/cohezion/concierge/session_bridge.py`
- Import creates a new session that inherits the exported state

**Story Points**: 2

---

### E6-S3: Session Bridge API Endpoints

**As a** platform adapter,
**I want** HTTP endpoints for session export/import,
**So that** cross-platform handoff works via REST API.

**Acceptance Criteria**:
- [ ] POST /meridian/session/export — accepts session_id, returns SessionExport JSON
- [ ] POST /meridian/session/import — accepts SessionExport JSON, returns new session_id
- [ ] 2 endpoint tests: export + import round-trip

**Technical Notes**:
- File: `src/cohezion/api/meridian_routes.py`
- Add to existing Meridian route group

**Story Points**: 1

---

## Epic 7: Observability & Metrics

### E7-S1: Per-Request Routing Metrics

**As a** developer monitoring Meridian,
**I want** every routing decision to emit structured metrics,
**So that** I can track routing quality, latency, and cost over time.

**Acceptance Criteria**:
- [ ] After each route() call, emit to GlobalMetricsAggregator:
  - meridian_routing_latency_ms
  - meridian_composite_score
  - meridian_selected_model
  - meridian_dialect_family
  - meridian_context_utilization_ratio
  - meridian_cache_hit (boolean)
- [ ] Metrics are non-blocking (try/except wrapped)
- [ ] 3 unit tests verifying metric emission

**Technical Notes**:
- Modify: `src/cohezion/concierge/meridian.py`
- Import: `from cohezion.compound.global_metrics_aggregator import GlobalMetricsAggregator`

**Story Points**: 2

---

### E7-S2: Vault Decision Logging

**As a** developer analyzing Meridian's routing over time,
**I want** every routing decision logged to vault as a structured decision record,
**So that** historical routing patterns can be analyzed for optimization.

**Acceptance Criteria**:
- [ ] Each routing decision creates vault entry at `sessions/{session}/routing/{timestamp}.md`
- [ ] Entry includes: query_hash, intent, selected_model, composite_score, all signals, dialect, context_budget, cascade_depth, quality_score, latency
- [ ] Non-blocking vault writes (try/except)
- [ ] 2 unit tests for log format and content

**Technical Notes**:
- Modify: `src/cohezion/concierge/meridian.py`
- Uses existing vault_write infrastructure
- Query hash is SHA-256[:16] of the original query (for grouping without storing raw queries)

**Story Points**: 1

---

### E7-S3: JourneyTracker Integration

**As a** developer using Cohezion's 12D universe tracking,
**I want** Meridian routing decisions recorded as JourneyTracker trajectory points,
**So that** routing decisions are visible in the compound engineering observability layer.

**Acceptance Criteria**:
- [ ] Each Meridian routing decision records a trajectory point with:
  - agent_id: "meridian"
  - phase: "routing" or "execution"
  - coherence: composite_score
  - position: derived from routing signals (mapped to 12D coordinates)
- [ ] Non-blocking (try/except wrapped)
- [ ] 2 unit tests with mocked JourneyTracker

**Technical Notes**:
- Modify: `src/cohezion/concierge/meridian.py`
- Import: `from cohezion.compound.journey_tracker import JourneyTracker`
- 12D coordinate mapping: each routing signal maps to a dimension subset

**Story Points**: 2

---

## Story Summary

| Epic | Stories | Total Points |
|------|---------|-------------|
| E1: Composite Router Facade | 5 | 11 |
| E2: Prompt Dialect Registry | 4 | 8 |
| E3: Context Budgeter | 4 | 7 |
| E4: Cascade Executor | 5 | 9 |
| E5: API & Integration | 4 | 8 |
| E6: Session Bridge | 3 | 5 |
| E7: Observability | 3 | 5 |
| **Total** | **28** | **53** |

---

## Related Documents

- [[PRD]] — Full product requirements
- [[Architecture]] — Technical architecture
- [[Epics]] — Epic overview and dependency graph
