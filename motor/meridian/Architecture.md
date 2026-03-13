---
title: "Meridian Concierge Agent - Architecture"
project: cohezion
type: architecture
status: draft
created: 2026-03-06
tags: [meridian, concierge, architecture, routing, compound-engineering]
aspect: doer
neural:
  activation: 0.9
  stage: growing
  synapse_in: 3
  synapse_out: 3
---

# Meridian: Architecture Document

## 1. System Context

Meridian is the intelligence layer that sits between user requests (from any platform) and Cohezion's execution engine. It orchestrates 7 existing routing components into a unified decision pipeline.

```
┌─────────────────────────────────────────────────┐
│                 EXTERNAL                         │
│                                                  │
│  Claude Code  │  Gemini CLI  │  Cursor  │  API   │
└───────┬───────┴──────┬───────┴────┬─────┴───┬───┘
        │              │            │          │
        └──────────────┴────────────┴──────────┘
                       │
              ┌────────v────────┐
              │  MERIDIAN AGENT │  ← This system
              └────────┬────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   ┌────v────┐                  ┌─────v─────┐
   │ Cohezion│                  │   Vault   │
   │ Engine  │                  │ (Obsidian)│
   └────┬────┘                  └───────────┘
        │
   ┌────v────┐
   │  Ollama │ / Cloud APIs
   └─────────┘
```

## 2. Component Architecture

### 2.1 Meridian Core Components

```
src/cohezion/concierge/
├── __init__.py               # Public API exports
├── meridian.py               # MeridianAgent orchestrator (~300 lines)
├── composite_router.py       # Unified scoring function (~200 lines)
├── prompt_dialect.py         # Model-specific prompt shaping (~300 lines)
├── context_budget.py         # Context compression/selection (~200 lines)
├── cascade.py                # Try cheap → escalate strategy (~400 lines)
├── session_bridge.py         # Cross-platform session handoff (~150 lines)
└── types.py                  # Shared data types (~100 lines)
```

**Total new code**: ~1,650 lines
**Existing code leveraged**: ~3,600 lines (7 routers + supporting infra)

### 2.2 Component Responsibilities

#### MeridianAgent (`meridian.py`)
The orchestrator. Single entry point for all routing decisions.

**Responsibilities**:
- Accept raw query from any platform
- Orchestrate the routing pipeline (parse → match → score → shape → execute)
- Manage cascade logic
- Handle session import/export
- Log all decisions to vault

**Dependencies**:
- CompositeRouter
- PromptDialectRegistry
- ContextBudgeter
- CascadeExecutor
- SessionBridge
- IntakeSpecialist (existing)
- CompoundExecutor (existing)

**Key Design Decision**: MeridianAgent is stateless per-request. Session state lives in vault, not in the agent.

#### CompositeRouter (`composite_router.py`)
Combines signals from all existing routers into a single score.

**Responsibilities**:
- Call each existing router and normalize their outputs to 0.0-1.0
- Apply configurable weights to each signal
- Return `MeridianRoutingDecision` with full signal breakdown
- Handle graceful degradation when individual routers fail

**Algorithm**:
```python
def route(query: str, constraints: dict) -> MeridianRoutingDecision:
    # 1. Parse intent
    alignment = RequestAlignmentAnalyzer.analyze(query)

    # 2. Match skills
    skills = SkillSelector.select(query, alignment.intent)

    # 3. Get candidate models from each router
    cost_candidates = CostAwareRouter.rank_models(query)
    capability_candidates = SmartRouter.classify_and_rank(query)
    hw_feasible = DynamicModelRouter.filter_feasible(cost_candidates + capability_candidates)

    # 4. Score each feasible model
    scored = []
    for model in hw_feasible:
        score = weighted_sum(
            intent_fit=alignment.coherence,
            capability_fit=capability_candidates.get(model, 0),
            cost_efficiency=cost_candidates.get(model, 0),
            hw_feasibility=1.0,  # Already filtered
            vault_experience=skills.get_model_score(model),
        )
        scored.append((model, score))

    # 5. Select best
    best_model, best_score = max(scored, key=lambda x: x[1])
    return MeridianRoutingDecision(model=best_model, score=best_score, ...)
```

**Normalization Strategy**:
| Router | Raw Output | Normalization |
|--------|-----------|---------------|
| CostAwareRouter | Cost estimate ($) | 1.0 - (cost / max_budget) |
| SmartRouter | Capability score (0-100) | score / 100 |
| DynamicModelRouter | Feasibility bool + metrics | 1.0 if feasible, TPS/max_TPS otherwise |
| RequestAlignmentAnalyzer | Coherence (0.0-1.0) | Already normalized |
| SkillSelector | Composite (0.0-1.0) | Already normalized |

#### PromptDialectRegistry (`prompt_dialect.py`)
Transforms prompt phrasing based on target model family.

**Responsibilities**:
- Map model IDs to dialect families
- Transform prompt verbs, structure, and preamble for target model
- Track dialect effectiveness in vault
- Support custom dialect definitions

**Dialect Families**:

```python
DIALECT_REGISTRY = {
    "claude": DialectConfig(
        model_patterns=["claude-*"],
        reasoning_style="structured",
        preferred_verbs=["analyze", "reason through", "evaluate", "consider"],
        context_format="xml_tags",
        system_prompt_style="detailed_persona",
        max_preamble_tokens=500,
        strengths=["nuanced reasoning", "safety", "structured output", "long context"],
    ),
    "gemini": DialectConfig(
        model_patterns=["gemini-*"],
        reasoning_style="conversational",
        preferred_verbs=["help me", "explore", "think about", "describe"],
        context_format="markdown",
        system_prompt_style="brief_role",
        max_preamble_tokens=300,
        strengths=["broad knowledge", "multimodal", "grounding", "speed"],
    ),
    "ollama_small": DialectConfig(
        model_patterns=["phi3:*", "phi4-mini-*", "nemotron-*"],
        reasoning_style="direct",
        preferred_verbs=["return", "output", "list", "answer"],
        context_format="minimal",
        system_prompt_style="one_line",
        max_preamble_tokens=50,
        strengths=["speed", "low memory", "simple tasks"],
    ),
    "ollama_coder": DialectConfig(
        model_patterns=["qwen3-coder*", "deepcoder*", "codellama*"],
        reasoning_style="implementation",
        preferred_verbs=["implement", "write", "create", "build", "refactor"],
        context_format="code_first",
        system_prompt_style="tech_stack",
        max_preamble_tokens=100,
        strengths=["code generation", "refactoring", "debugging", "large context"],
    ),
    "ollama_reasoner": DialectConfig(
        model_patterns=["deepseek-r1*", "qwq*"],
        reasoning_style="chain_of_thought",
        preferred_verbs=["prove", "derive", "solve", "reason step by step"],
        context_format="structured",
        system_prompt_style="problem_statement",
        max_preamble_tokens=200,
        strengths=["math", "logic", "complex reasoning", "chain of thought"],
    ),
}
```

**Transformation Pipeline**:
```
Original prompt: "Help me design an authentication system using JWT"
    ↓
Intent extraction: GENERATE + auth_system + JWT
    ↓
Claude dialect:   "Analyze the requirements for an authentication system.
                   Consider the trade-offs of JWT-based auth. Then design
                   a complete solution with: <requirements>...</requirements>"
    ↓
Ollama coder:     "Implement JWT authentication. Tech stack: Python/FastAPI.
                   Include: token generation, validation, refresh flow."
    ↓
Ollama small:     "Design JWT auth. Return: components, flow, code structure."
```

#### ContextBudgeter (`context_budget.py`)
Selects and compresses context to fit target model's capacity.

**Responsibilities**:
- Calculate available context tokens (model window - prompt - output reserve)
- Rank context pieces by semantic relevance using SemanticCache embeddings
- Select top-ranked pieces that fit within budget
- Compress partially-fitting pieces via heuristic summarization
- Log context utilization metrics

**Algorithm**:
```python
def budget(
    context_pieces: list[ContextPiece],
    model_context_window: int,
    prompt_tokens: int,
    output_reserve: int = 2048,
) -> list[ContextPiece]:
    available = model_context_window - prompt_tokens - output_reserve

    if sum(p.tokens for p in context_pieces) <= available:
        return context_pieces  # Everything fits

    # Rank by relevance to query
    ranked = sort_by_embedding_similarity(context_pieces, query_embedding)

    # Greedy fill
    selected = []
    used = 0
    for piece in ranked:
        if used + piece.tokens <= available:
            selected.append(piece)
            used += piece.tokens
        elif available - used > 100:  # Room for compressed version
            compressed = compress(piece, max_tokens=available - used)
            selected.append(compressed)
            break
        else:
            break

    return selected
```

**Model Context Windows** (reference):
| Model | Context Window | Effective Budget (after prompt + reserve) |
|-------|---------------|-------------------------------------------|
| claude-opus-4-6 | 200,000 | ~190,000 |
| claude-sonnet-4-6 | 200,000 | ~190,000 |
| gemini-3-1-pro | 2,000,000 | ~1,990,000 |
| qwen3-coder:30b | 262,144 | ~255,000 |
| deepseek-r1:70b | 128,000 | ~120,000 |
| phi3:mini | 4,096 | ~2,000 |
| phi4-mini-reasoning | 16,384 | ~12,000 |

#### CascadeExecutor (`cascade.py`)
Implements try-cheap-first, escalate-on-failure strategy.

**Responsibilities**:
- Define cascade tiers (configurable)
- Execute at cheapest viable tier
- Assess output quality via ModelQualityClassifier
- Escalate if quality below threshold
- Enforce total cascade budget
- Log cascade events for routing optimization

**Default Cascade Configuration**:
```python
DEFAULT_CASCADE = [
    CascadeTier(
        name="local_fast",
        model="phi3:mini",
        max_cost_usd=0.0,
        quality_threshold=0.7,
        timeout_seconds=30,
        best_for=["simple lookups", "formatting", "short answers"],
    ),
    CascadeTier(
        name="local_capable",
        model="qwen3-coder:30b",
        max_cost_usd=0.0,
        quality_threshold=0.8,
        timeout_seconds=120,
        best_for=["code generation", "analysis", "medium complexity"],
    ),
    CascadeTier(
        name="cloud_standard",
        model="claude-sonnet-4-6",
        max_cost_usd=0.01,
        quality_threshold=0.9,
        timeout_seconds=60,
        best_for=["nuanced reasoning", "complex tasks", "structured output"],
    ),
    CascadeTier(
        name="cloud_premium",
        model="claude-opus-4-6",
        max_cost_usd=0.05,
        quality_threshold=None,  # Always accept
        timeout_seconds=120,
        best_for=["deep research", "architecture", "critical decisions"],
    ),
]
```

**Quality Assessment Strategy**:
The cascade uses ModelQualityClassifier (existing) to evaluate output quality. Assessment criteria:
1. **Completeness**: Does the response address all parts of the query?
2. **Coherence**: Is the response internally consistent?
3. **Specificity**: Does the response contain actionable detail (not just platitudes)?
4. **Format compliance**: Does the response match expected output format?

Score 0.0-1.0 → compare against tier's quality_threshold.

#### SessionBridge (`session_bridge.py`)
Cross-platform session state serialization.

**Responsibilities**:
- Export current session state to vault-serializable format
- Import session state from vault
- Sanitize sensitive data before export
- Reconstruct execution context on import

**State Schema**:
```python
@dataclass
class SessionExport:
    version: str = "1.0"
    session_id: str
    exported_at: str                    # ISO timestamp
    platform_origin: str                # "claude-code", "gemini-cli", etc.
    intent_history: list[IntentRecord]  # Past routing decisions
    active_skill: str | None            # Currently matched PRIME skill
    context_pieces: list[str]           # Relevant context (sanitized)
    model_usage: dict[str, int]         # Tokens used per model
    cascade_history: list[CascadeEvent] # Past escalations
    checkpoint: dict | None             # CompoundExecutor checkpoint
    vault_refs: list[str]               # Vault note paths for full context
```

### 2.3 Integration Points

```
              Existing Components
              ┌─────────────────┐
              │RequestAlignment │◄─── Meridian calls .analyze()
              │Analyzer         │
              └────────┬────────┘
                       │ intent, constraints
              ┌────────v────────┐
              │  SkillSelector  │◄─── Meridian calls .select()
              └────────┬────────┘
                       │ matched skills
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────v────┐   ┌─────v─────┐  ┌────v────┐
   │CostAware│   │  Smart    │  │Dynamic  │
   │Router   │   │  Router   │  │Model    │
   │         │   │           │  │Router   │
   └────┬────┘   └─────┬─────┘  └────┬────┘
        │              │              │
        └──────────────┼──────────────┘
                       │ candidate models + scores
              ┌────────v────────┐
              │ CompositeRouter │◄─── NEW: unifies all scores
              └────────┬────────┘
                       │ MeridianRoutingDecision
              ┌────────v────────┐
              │ PromptDialect + │◄─── NEW: shapes prompt
              │ ContextBudgeter │
              └────────┬────────┘
                       │ shaped prompt + budgeted context
              ┌────────v────────┐
              │ModelPoolManager │◄─── Ensures model is loaded
              └────────┬────────┘
                       │
              ┌────────v────────┐
              │CompoundExecutor │◄─── Existing execution engine
              └────────┬────────┘
                       │ result
              ┌────────v────────┐
              │CascadeExecutor  │◄─── NEW: quality gate + escalation
              └────────┬────────┘
                       │ final result
              ┌────────v────────┐
              │  Vault Logger   │◄─── Existing: log for learning
              └─────────────────┘
```

## 3. Data Flow

### 3.1 Request Processing Pipeline

```
Step 1: INTAKE
  Input:  Raw query string + optional constraints
  Output: Parsed request with metadata
  Actor:  IntakeSpecialist (existing)
  Cache:  Check SemanticCache L1/L2/L3 — if hit, return immediately

Step 2: INTENT ANALYSIS
  Input:  Parsed request
  Output: Intent classification, constraints, success criteria, coherence score
  Actor:  RequestAlignmentAnalyzer (existing)
  Gate:   If coherence < 0.5 (HIHO), decompose or escalate

Step 3: SKILL MATCHING
  Input:  Intent + keywords
  Output: Ranked skills with composite scores
  Actor:  SkillSelector (existing, vault-guided)

Step 4: MODEL SCORING
  Input:  Intent + skill + constraints
  Output: Ranked models with composite scores
  Actor:  CompositeRouter (NEW)
  Calls:  CostAwareRouter, SmartRouter, DynamicModelRouter (all existing)

Step 5: PROMPT SHAPING
  Input:  Original prompt + selected model
  Output: Model-optimized prompt
  Actor:  PromptDialectRegistry (NEW) + PromptOptimizer (existing)

Step 6: CONTEXT BUDGETING
  Input:  Available context + model capacity
  Output: Selected/compressed context pieces
  Actor:  ContextBudgeter (NEW)

Step 7: EXECUTION
  Input:  Shaped prompt + budgeted context + model
  Output: Raw model response
  Actor:  ModelPoolManager (existing) → CompoundExecutor (existing)

Step 8: QUALITY ASSESSMENT
  Input:  Model response + success criteria
  Output: Quality score 0.0-1.0
  Actor:  ModelQualityClassifier (existing)
  Gate:   If quality < cascade_threshold, go to Step 4 with next tier

Step 9: LEARNING
  Input:  Full routing decision + result quality
  Output: Vault entries (decision log, routing metrics)
  Actor:  Vault Logger, GlobalMetricsAggregator (existing)
  Async:  Non-blocking, try/except wrapped
```

### 3.2 Cascade Data Flow

```
     ┌─────────────────┐
     │ Tier 1: phi3    │ cost: $0.00
     │ threshold: 0.7  │
     └────────┬────────┘
              │ quality = 0.55
              │ < 0.7 → ESCALATE
     ┌────────v────────┐
     │ Tier 2: qwen3   │ cost: $0.00
     │ threshold: 0.8  │
     └────────┬────────┘
              │ quality = 0.82
              │ ≥ 0.8 → ACCEPT
              v
         Return result
    Total cost: $0.00 (both tiers local)
    Cascade depth: 2
```

## 4. Technology Decisions

### 4.1 Architecture Decision Records

| Decision | Choice | Rationale | Alternatives Considered |
|----------|--------|-----------|------------------------|
| Routing algorithm | Heuristic (no LLM) | <50ms latency, deterministic, no additional cost | LLM-based routing (too slow, recursive cost) |
| State management | Stateless per-request | Simpler, vault handles persistence | In-memory state (doesn't survive restarts) |
| Composite scoring | Weighted linear sum | Interpretable, configurable, fast | Neural routing (opaque, requires training data) |
| Prompt dialect | Registry-based | Predictable, extensible, no training needed | Learned dialects (better long-term, but Phase 2+) |
| Context budgeting | Greedy fill by relevance | Fast, reasonable quality | Knapsack optimization (slower, marginal improvement) |
| Cascade quality gate | ModelQualityClassifier | Already exists, proven | LLM-as-judge (too expensive for cascade gate) |

### 4.2 File Layout

```
src/cohezion/concierge/
├── __init__.py              # Exports: MeridianAgent, route, execute, cascade
├── meridian.py              # MeridianAgent class
├── composite_router.py      # CompositeRouter + scoring
├── prompt_dialect.py        # PromptDialectRegistry + transformations
├── context_budget.py        # ContextBudgeter
├── cascade.py               # CascadeExecutor + tier config
├── session_bridge.py        # SessionBridge + import/export
├── types.py                 # Shared types (MeridianRoutingDecision, etc.)
└── config.py                # Default weights, tiers, dialect configs

tests/concierge/
├── __init__.py
├── test_composite_router.py
├── test_prompt_dialect.py
├── test_context_budget.py
├── test_cascade.py
├── test_session_bridge.py
├── test_meridian_integration.py
└── conftest.py              # Concierge-specific fixtures
```

### 4.3 Error Handling Strategy

```python
class MeridianError(Exception):
    """Base error for Meridian operations."""

class RoutingError(MeridianError):
    """All routers failed — no viable model found."""
    fallback_model: str  # Default model to use

class CascadeExhaustedError(MeridianError):
    """All cascade tiers exhausted without meeting quality threshold."""
    best_result: MeridianResult  # Return best-effort result
    cascade_log: list[CascadeEvent]  # Full cascade history

class BudgetExceededError(MeridianError):
    """Cascade would exceed budget — stopping early."""
    partial_result: MeridianResult | None
```

**Graceful Degradation Rules**:
1. If CostAwareRouter fails → route without cost signal (remaining 4 signals)
2. If SmartRouter fails → route without capability signal
3. If DynamicModelRouter fails → assume all models are hardware-feasible
4. If RequestAlignmentAnalyzer fails → use MEDIUM complexity as default
5. If SkillSelector fails → skip vault experience signal
6. If ALL routers fail → use configured default model
7. If vault logging fails → continue execution (non-blocking)

## 5. Performance Budget

| Operation | Target | Mechanism |
|-----------|--------|-----------|
| Intent analysis | <10ms | RequestAlignmentAnalyzer (heuristic regex) |
| Skill matching | <5ms | SkillSelector TF-IDF lookup |
| Model scoring (3 routers) | <15ms | Parallel calls, heuristic scoring |
| Composite score computation | <1ms | Weighted sum arithmetic |
| Prompt dialect transformation | <5ms | String operations |
| Context budgeting | <10ms | Embedding similarity + greedy fill |
| **Total routing overhead** | **<50ms** | All steps combined |

Model pool management (loading/evicting models) is excluded from the routing budget — it happens asynchronously.

## 6. Observability

### 6.1 Metrics Emitted

```python
# Per-request metrics (via GlobalMetricsAggregator)
meridian_routing_latency_ms         # Time to make routing decision
meridian_composite_score            # Final composite score
meridian_cascade_depth              # Number of cascade tiers used
meridian_context_utilization_ratio  # Context tokens used / available
meridian_cache_hit                  # Whether SemanticCache short-circuited
meridian_selected_model             # Which model was chosen
meridian_dialect_family             # Which prompt dialect was applied

# Aggregate metrics (5-min rolling window)
meridian_avg_cascade_depth          # Average escalation frequency
meridian_cost_savings_pct           # Savings vs always-use-premium
meridian_quality_by_tier            # Quality distribution per cascade tier
meridian_routing_signal_weights     # Current weight configuration
```

### 6.2 Vault Logging

Every routing decision creates a vault entry:
```yaml
path: sessions/{session_id}/routing/{timestamp}.md
content:
  query_hash: sha256[:16]
  intent: GENERATE
  selected_model: qwen3-coder:30b
  composite_score: 0.847
  signals:
    intent_fit: 0.92
    capability_fit: 0.85
    cost_efficiency: 0.95
    hw_feasibility: 1.0
    vault_experience: 0.78
  dialect: ollama_coder
  context_budget: 255000
  context_used: 12400
  cascade_depth: 1
  quality_score: 0.88
  latency_ms: 42
```

## 7. Security Considerations

1. **No model selection leakage**: API responses include result, not routing decision details (unless explicitly requested via debug mode)
2. **Credential isolation**: Model API keys accessed via environment variables, never logged
3. **Session sanitization**: `SessionBridge.export()` strips any context containing patterns matching `SECRET|KEY|PASSWORD|TOKEN` regex
4. **Input validation**: All Meridian inputs validated via Pydantic models
5. **Rate limiting**: Cascade execution respects per-model rate limits via ModelPoolManager

---

## Related Documents

- [[PRD]] — Product requirements and user flows
- [[Epics]] — Implementation epics
- [[Stories]] — Detailed user stories
