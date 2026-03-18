---
title: "Meridian Concierge Agent - Epics"
project: cohezion
type: epics
status: draft
created: 2026-03-06
tags: [meridian, concierge, epics, planning]
aspect: doer
neural:
  activation: 0.79
  stage: growing
  synapse_in: 4
  synapse_out: 3
date: 2026-03-06
---

# Meridian: Epics

## Epic Overview

| Epic | Name | Priority | Estimated Stories | Dependencies |
|------|------|----------|-------------------|-------------|
| E1 | Composite Router Facade | P0 (Critical) | 5 | None |
| E2 | Prompt Dialect Registry | P1 (High) | 4 | E1 |
| E3 | Context Budgeter | P1 (High) | 3 | E1 |
| E4 | Cascade Executor | P1 (High) | 5 | E1, E3 |
| E5 | Cross-Platform Session Bridge | P2 (Medium) | 4 | E1 |
| E6 | FastAPI Integration | P2 (Medium) | 3 | E1-E4 |
| E7 | Observability & Metrics | P2 (Medium) | 3 | E1 |
| E8 | BMAD Task Mapping | P3 (Low) | 2 | E1, E2 |

---

## E1: Composite Router Facade

**Priority**: P0 (Critical)
**Estimated effort**: 5 stories
**Goal**: Create a single entry point (`MeridianAgent`) that orchestrates all existing routers into a unified routing decision.

### Description

This is the foundational epic. Without it, nothing else works. The composite router wraps CostAwareRouter, DynamicModelRouter, SmartRouter, RequestAlignmentAnalyzer, and SkillSelector into a single pipeline that produces a `MeridianRoutingDecision` with a composite score.

### Acceptance Criteria

- [ ] `MeridianAgent.route(query)` returns a `MeridianRoutingDecision`
- [ ] Composite score combines 5 signals with configurable weights
- [ ] Graceful degradation when individual routers fail
- [ ] Routing latency <50ms (P95)
- [ ] No LLM calls in the routing path
- [ ] All routing decisions logged to vault (non-blocking)
- [ ] Backward compatible — existing direct router usage unchanged

### Stories

- [[Stories#E1-S1]] Types and data models
- [[Stories#E1-S2]] CompositeRouter implementation
- [[Stories#E1-S3]] MeridianAgent orchestrator
- [[Stories#E1-S4]] Graceful degradation & fallbacks
- [[Stories#E1-S5]] Integration tests with real routers

---

## E2: Prompt Dialect Registry

**Priority**: P1 (High)
**Estimated effort**: 4 stories
**Goal**: Transform prompt phrasing (not just format) based on target model's strengths.

### Description

Different models respond better to different prompt styles. Claude wants structured reasoning with XML tags. qwen3-coder responds to "implement" better than "write." phi3:mini needs concise directives. The dialect registry maps model families to prompt styles and transforms prompts accordingly.

### Acceptance Criteria

- [ ] 5 dialect families defined: claude, gemini, ollama_small, ollama_coder, ollama_reasoner
- [ ] Prompt transformation preserves semantic intent while changing phrasing
- [ ] Model ID → dialect family mapping via pattern matching
- [ ] Dialect effectiveness tracked in vault
- [ ] New dialects addable via configuration (no code changes)
- [ ] A/B comparison shows no quality degradation vs generic prompts

### Stories

- [[Stories#E2-S1]] Dialect data model and registry
- [[Stories#E2-S2]] Prompt transformation engine
- [[Stories#E2-S3]] Vault-backed effectiveness tracking
- [[Stories#E2-S4]] Integration with MeridianAgent

---

## E3: Context Budgeter

**Priority**: P1 (High)
**Estimated effort**: 3 stories
**Goal**: Select and compress context to fit each model's token capacity.

### Description

Opus can handle 200K tokens. phi3:mini chokes above 4K. Currently, the same context goes to every model. The context budgeter ranks context pieces by relevance (using SemanticCache embeddings) and fills the target model's available window, compressing pieces when needed.

### Acceptance Criteria

- [ ] Calculate available budget: model_window - prompt_tokens - output_reserve
- [ ] Rank context by semantic relevance to query
- [ ] Greedy fill algorithm with compression fallback
- [ ] Context utilization ratio logged to metrics
- [ ] Handles edge case: zero available budget (no context injected)
- [ ] Compression preserves key information (heuristic summarization)

### Stories

- [[Stories#E3-S1]] Context budget calculator
- [[Stories#E3-S2]] Relevance ranking with SemanticCache
- [[Stories#E3-S3]] Integration with MeridianAgent + compression

---

## E4: Cascade Executor

**Priority**: P1 (High)
**Estimated effort**: 5 stories
**Goal**: Try cheapest viable model first, escalate only when quality is insufficient.

### Description

Most queries don't need Opus. The cascade executor tries local phi3:mini first. If quality is below threshold, it tries qwen3-coder. Only if that's still insufficient does it hit cloud API. This dramatically reduces cost while maintaining quality where it matters.

### Acceptance Criteria

- [ ] 4 cascade tiers: local_fast, local_capable, cloud_standard, cloud_premium
- [ ] Quality assessment via ModelQualityClassifier at each tier
- [ ] Escalation triggered when quality < tier.quality_threshold
- [ ] Total cascade cost bounded by BudgetEnforcer
- [ ] Cascade events logged to vault for routing optimization
- [ ] 50%+ of test queries resolved at cheapest tier
- [ ] Configurable cascade tiers (not hardcoded)

### Stories

- [[Stories#E4-S1]] Cascade tier configuration
- [[Stories#E4-S2]] Quality gate implementation
- [[Stories#E4-S3]] Budget-aware cascade execution
- [[Stories#E4-S4]] Cascade vault logging and learning
- [[Stories#E4-S5]] Integration tests with cascading

---

## E5: Cross-Platform Session Bridge

**Priority**: P2 (Medium)
**Estimated effort**: 4 stories
**Goal**: Export/import session state so users can continue work across platforms.

### Description

A user starts designing a system in Claude Code, then wants to continue in Gemini CLI. The session bridge exports session state (intent history, context, skill, checkpoint) to vault, and imports it on the target platform. Context follows the user.

### Acceptance Criteria

- [ ] `export_session()` serializes session state to vault
- [ ] `import_session()` reconstructs session on new platform
- [ ] Sensitive data sanitized before export (keys, tokens, passwords)
- [ ] Platform-agnostic schema (no platform-specific data)
- [ ] Session survives vault restart (persistent storage)
- [ ] Import on different platform preserves context fidelity

### Stories

- [[Stories#E5-S1]] Session export schema and serialization
- [[Stories#E5-S2]] Session import and context reconstruction
- [[Stories#E5-S3]] Sensitive data sanitization
- [[Stories#E5-S4]] Integration with vault persistence

---

## E6: FastAPI Integration

**Priority**: P2 (Medium)
**Estimated effort**: 3 stories
**Goal**: Expose Meridian capabilities via REST API endpoints.

### Description

Add `/meridian/*` endpoints to the existing FastAPI application. Enables external tools and platforms to use Meridian for intelligent routing.

### Acceptance Criteria

- [ ] `POST /meridian/route` — returns routing decision without execution
- [ ] `POST /meridian/execute` — routes and executes in one call
- [ ] `POST /meridian/cascade` — routes with cascading execution
- [ ] `GET /meridian/metrics` — returns routing metrics
- [ ] `GET /meridian/dialects` — lists available prompt dialects
- [ ] Session endpoints for export/import
- [ ] OpenAPI spec auto-generated

### Stories

- [[Stories#E6-S1]] Route and execute endpoints
- [[Stories#E6-S2]] Cascade and metrics endpoints
- [[Stories#E6-S3]] Session management endpoints

---

## E7: Observability & Metrics

**Priority**: P2 (Medium)
**Estimated effort**: 3 stories
**Goal**: Full observability into Meridian routing decisions and performance.

### Description

Every routing decision should be observable — which signals contributed, why a model was selected, cascade depth, cost savings. Integrates with existing GlobalMetricsAggregator and JourneyTracker.

### Acceptance Criteria

- [ ] Per-request metrics: routing latency, composite score, cascade depth, model selection
- [ ] Aggregate metrics: average cascade depth, cost savings %, quality by tier
- [ ] Vault decision logs with full signal breakdown
- [ ] JourneyTracker integration (routing as trajectory point)
- [ ] Dashboard-ready metric format (GlobalMetricsAggregator compatible)

### Stories

- [[Stories#E7-S1]] Per-request metric emission
- [[Stories#E7-S2]] Aggregate metrics and rolling windows
- [[Stories#E7-S3]] JourneyTracker and vault integration

---

## E8: BMAD Task Mapping

**Priority**: P3 (Low)
**Estimated effort**: 2 stories
**Goal**: Automatic mapping from BMAD task types to Meridian routing decisions.

### Description

BMAD workflows (create-architecture, quick-dev, code-review, create-prd, etc.) should automatically trigger optimal routing. When a user says "create the architecture," Meridian knows this is COMPLEX intent requiring a deep reasoning model.

### Acceptance Criteria

- [ ] BMAD task type → intent/complexity mapping defined
- [ ] At least 10 BMAD tasks mapped (architecture, dev, review, PRD, sprint, research, spec, story, retrospective, QA)
- [ ] Mapping extensible via skill registry
- [ ] Integration with BMAD workflow execution

### Stories

- [[Stories#E8-S1]] BMAD task type mapping
- [[Stories#E8-S2]] Skill registry integration

---

## Epic Dependency Graph

```
E1 (Composite Router) ──────────────────────────────────┐
    │                                                    │
    ├─── E2 (Prompt Dialect) ─── E8 (BMAD Mapping)      │
    │                                                    │
    ├─── E3 (Context Budget) ─── E4 (Cascade) ──────────┤
    │                                                    │
    ├─── E5 (Session Bridge)                             │
    │                                                    │
    ├─── E7 (Observability)                              │
    │                                                    │
    └─── E6 (FastAPI) ◄──────── E1-E4 complete ─────────┘
```

## Implementation Order

**Sprint 1**: E1 (Composite Router) — Foundation, everything depends on it
**Sprint 2**: E2 (Dialect) + E3 (Context Budget) — Parallel, both feed into E4
**Sprint 3**: E4 (Cascade) + E7 (Observability) — Cascade needs E3, observability needs E1
**Sprint 4**: E5 (Session Bridge) + E6 (FastAPI) — Polish and external access
**Sprint 5**: E8 (BMAD Mapping) — Final integration

---

## Related Documents

- [[PRD]] — Full product requirements
- [[Architecture]] — Technical architecture
- [[Stories]] — Detailed stories per epic
