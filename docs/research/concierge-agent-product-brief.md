# Concierge Agent Product Brief

**Codename**: Meridian
**Status**: Research Spike → Product Brief
**Date**: 2026-03-06
**Author**: Claude (Session: concierge-agent-research)
**Replaces**: MCP Infrastructure PRD (transport-layer approach)

---

## Executive Summary

Cohezion has 7 routing/intent components (~3,600 lines) that each solve a piece of the model routing puzzle but don't coordinate. The **Concierge Agent** (codename: *Meridian*) unifies them into a single intelligent front door that makes any task work optimally regardless of which platform or model executes it.

The key insight: instead of building transport adapters for 5 platforms x 108 tools (the old MCP PRD approach), build ONE intelligence layer that understands intent, selects the right model, shapes the prompt for that model's strengths, and injects the right context — transparently.

Think "Ask Jeeves done right, 25 years later." Jeeves had the right idea (natural language intent understanding) but the wrong technology (keyword matching + human curation). We have the technology now.

---

## Problem Statement

### Current State: 7 Routers, No Conductor

| Component | Signal | File | Lines |
|-----------|--------|------|-------|
| CostAwareRouter | Cost/budget | `src/cohezion/swarm/cost_aware_router.py` | 713 |
| DynamicModelRouter | Hardware/memory | `src/cohezion/swarm/dynamic_model_router.py` | 528 |
| SmartRouter | Task capability | `src/cohezion/swarm/smart_router.py` | 490 |
| RequestAlignmentAnalyzer | Intent/constraints | `src/cohezion/compound/request_alignment_analyzer.py` | 1004 |
| SkillSelector | Vault experience | `src/cohezion/compound/skill_selector.py` | 431 |
| PromptOptimizer | Compression | `src/cohezion/compound/prompt_optimizer.py` | 229 |
| ModelPoolManager | Availability | `src/cohezion/swarm/model_pool_manager.py` | ~150 |

Each router independently makes decisions using a single signal. No component combines all signals into a unified routing decision. The result:

- CostAwareRouter picks the cheapest model, ignoring task fit
- SmartRouter picks the most capable model, ignoring cost
- DynamicModelRouter ensures hardware can handle it, but doesn't know if the task needs it
- RequestAlignmentAnalyzer extracts rich intent but hands it off to... nothing unified

### The MCP Infrastructure Approach (What We're Moving Away From)

The previous PRD proposed building platform adapters — transport plumbing to expose 108 tools across 5 platforms (Claude Code, Gemini CLI, Cursor, Windsurf, OpenCode). This is the wrong abstraction:

| MCP Infrastructure PRD | Concierge Agent |
|------------------------|-----------------|
| Transport layer (MCP plumbing) | Intelligence layer (intent routing) |
| Same prompt everywhere | Right prompt for each model |
| Same model everywhere | Right model for each task |
| Platform adapters | Platform-agnostic interpretation |
| 108 hardcoded tools | Dynamic task understanding |
| N platforms x M tools = N*M adapters | 1 intelligent front door |

---

## Product Vision

### One Sentence

Meridian is an intelligent front door that understands what you want, picks the best model to do it, shapes the request for that model's strengths, and gives you the right amount of context — all transparently, across any platform.

### Core Loop

```
User says something (any platform, any format)
    |
    v
[1. INTERPRET] What does the user actually want?
    |  RequestAlignmentAnalyzer: intent, constraints, success criteria
    |  SkillSelector: which skill(s) match this intent?
    |
    v
[2. ROUTE] Which model should handle this?
    |  CostAwareRouter: budget-optimal selection
    |  DynamicModelRouter: hardware-feasible selection
    |  SmartRouter: capability-optimal selection
    |  --> Unified composite score across all three
    |
    v
[3. SHAPE] How should we ask this model?
    |  Prompt dialect: Claude wants structured reasoning,
    |    Ollama wants concise directives, Gemini wants conversation
    |  Context budget: Opus gets 200K tokens, phi3 gets 4K
    |
    v
[4. EXECUTE] Run it
    |  ModelPoolManager: ensure model is loaded
    |  CompoundExecutor: vault-integrated execution
    |
    v
[5. EVALUATE] Was it good enough?
    |  Quality gate: if below threshold, cascade to better model
    |  Learn: log to vault for future routing decisions
    |
    v
Result (normalized for user's platform)
```

### What Makes This Different From "Just Another Router"

The concierge doesn't replace existing routers — it **orchestrates** them. Each router keeps its specialization. The concierge combines their signals into a single decision and adds capabilities none of them have:

1. **Prompt Dialects** — Same intent, different phrasing per model family
2. **Context Budgeting** — Right amount of context for each model's capacity
3. **Cascading Execution** — Start cheap, escalate only when needed
4. **Cross-Platform Memory** — Context follows the user across tools

---

## Existing Components (What's Already Built)

### Routing Infrastructure (~3,600 lines)

**CostAwareRouter** (`swarm/cost_aware_router.py`, 713 lines)
- Classifies query complexity via keyword heuristics: SIMPLE/MEDIUM/COMPLEX
- Maps complexity to model tiers: phi3:mini → qwen3-coder:30b → deepseek-r1:70b
- Budget enforcement with `BudgetEnforcer`, dynamic threshold tuning
- *Concierge role*: Cost signal in composite routing score

**DynamicModelRouter** (`swarm/dynamic_model_router.py`, 528 lines)
- Hardware-aware routing: memory bandwidth, quantization, context window analysis
- IDE priority integration (ANTIGRAVITY/ZED/OPENCODE)
- `AdaptiveTemplateManager`: message format detection (chatml/microsoft/llama3)
- *Concierge role*: Hardware feasibility gate + format adaptation

**SmartRouter** (`swarm/smart_router.py`, 490 lines)
- Task classification into 7 categories: ANALYSIS, SYNTHESIS, CREATIVE, CODING, FACTUAL, DEBATE, SUMMARY
- 18 local Ollama model profiles with capability/speed/quality tiers
- Strategy-based scoring (efficiency/quality/speed)
- *Concierge role*: Capability matching signal

**RequestAlignmentAnalyzer** (`compound/request_alignment_analyzer.py`, 1004 lines)
- Intent classification: GENERATE, ANALYZE, SEARCH, TRANSFORM, PERSIST
- Constraint extraction: tokens, latency, quality, scope
- Success criteria parsing, drift detection
- HIHO coherence threshold (0.5)
- *Concierge role*: Primary intent parser and coherence gate

**SkillSelector** (`compound/skill_selector.py`, 431 lines)
- Vault-guided skill selection with composite scoring
- Weights: coherence 50% + efficiency 30% + success rate 20%
- Historical performance tracking from vault
- *Concierge role*: Experience-based skill matching

**PromptOptimizer** (`compound/prompt_optimizer.py`, 229 lines)
- Filler word removal, redundancy cleanup, whitespace normalization
- Token savings: reduces prompt size without losing meaning
- *Concierge role*: Prompt compression (but NOT dialect shaping — that's new)

**ModelPoolManager** (`swarm/model_pool_manager.py`, ~150 lines)
- 3-tier model lifecycle: HOT (always loaded), WARM (evictable), COLD (on-demand)
- Health checks, dynamic eviction under memory pressure
- *Concierge role*: Availability gate before execution

### Supporting Infrastructure

| Component | Purpose | Concierge Leverage |
|-----------|---------|-------------------|
| IntakeSpecialist | 4-tier caching gateway (<10 tokens/request) | First contact point |
| CompoundExecutor | 11-step vault-integrated execution | Execution engine |
| SemanticCache | L1 hash + L2 cosine + L3 vault (95%+ hit rate) | Short-circuit on cache hit |
| 124 PRIME Skills | Task-specific definitions in registry | Skill catalog for matching |
| TeamOrchestrator | Multi-agent task decomposition | Complex task fan-out |
| ModelQualityClassifier | Proactive quality forecasting | Cascade quality gate |
| DegradationDetector | Thermal + coherence monitoring | Safety circuit breaker |
| JourneyTracker | 12D trajectory mapping | Observability layer |

### Elite Model Roster (from `core/routing/router.py`)

```python
role_map = {
    "elite-coding": "qwen3-coder-next:q8_0",     # 262K context
    "agentic-coding": "qwen3-coder-next:latest",  # 262K context
    "routing": "phi4-256k:latest",                 # 256K, fast
    "light-reasoning": "phi3:mini",                # <1GB RAM, fast
}
```

Model Pool Tiers:
- **HOT**: phi4-mini-reasoning, nomic-embed-text (always loaded)
- **WARM**: glm-4.7-flash, qwen3-coder:30b (startup, evictable)
- **COLD**: deepcoder:14b, nemotron-3-nano (on-demand)

---

## Gap Analysis: What Meridian Adds

### Gap 1: Unified Composite Scoring

**Problem**: Each router scores independently using different scales. CostAwareRouter returns a cost estimate, SmartRouter returns a capability score, DynamicModelRouter returns a hardware feasibility flag. There's no single function that combines these into "best model for this task right now."

**Solution**: Composite routing score

```python
@dataclass
class MeridianRoutingDecision:
    model: str
    score: float  # Composite 0.0-1.0
    signals: dict  # Individual router contributions
    confidence: float  # How certain is this routing?
    cascade_threshold: float  # Quality below this triggers escalation

def compute_composite_score(
    intent_fit: float,      # RequestAlignmentAnalyzer
    capability_fit: float,  # SmartRouter
    cost_efficiency: float, # CostAwareRouter
    hw_feasibility: float,  # DynamicModelRouter
    vault_success: float,   # SkillSelector (historical performance)
    weights: dict = None    # Configurable per-deployment
) -> float:
    w = weights or {
        "intent": 0.30,
        "capability": 0.25,
        "cost": 0.20,
        "hardware": 0.15,
        "experience": 0.10,
    }
    return sum(w[k] * v for k, v in {
        "intent": intent_fit,
        "capability": capability_fit,
        "cost": cost_efficiency,
        "hardware": hw_feasibility,
        "experience": vault_success,
    }.items())
```

### Gap 2: Prompt Dialect Shaping

**Problem**: `AdaptiveTemplateManager` handles message FORMAT (chatml vs llama3 vs microsoft) but not PHRASING. The same intent gets the same words regardless of which model processes it. But models have different strengths:

| Model Family | Prefers | Avoids |
|-------------|---------|--------|
| Claude (Opus/Sonnet) | Structured reasoning, explicit chains of thought, XML tags | Overly casual prompts |
| Gemini (Pro/Flash) | Conversational tone, broad context, examples | Rigid formatting |
| Ollama/phi3 | Concise directives, small context, direct questions | Long preambles |
| qwen3-coder | "implement" > "write", code-first, specific tech stack mentions | Vague descriptions |
| deepseek-r1 | Complex reasoning chains, mathematical precision | Simple lookups |

**Solution**: Prompt dialect registry

```python
class PromptDialect:
    """Adapts prompt phrasing (not just format) for target model."""

    dialects = {
        "claude": {
            "reasoning_style": "structured",
            "preferred_verbs": ["analyze", "reason through", "consider"],
            "context_format": "xml_tags",
            "max_preamble_tokens": 500,
        },
        "gemini": {
            "reasoning_style": "conversational",
            "preferred_verbs": ["help me", "explore", "think about"],
            "context_format": "markdown",
            "max_preamble_tokens": 300,
        },
        "ollama_small": {  # phi3, phi4-mini
            "reasoning_style": "direct",
            "preferred_verbs": ["do", "return", "output"],
            "context_format": "minimal",
            "max_preamble_tokens": 50,
        },
        "ollama_coder": {  # qwen3-coder
            "reasoning_style": "implementation",
            "preferred_verbs": ["implement", "write", "create"],
            "context_format": "code_first",
            "max_preamble_tokens": 100,
        },
        "ollama_reasoner": {  # deepseek-r1
            "reasoning_style": "chain_of_thought",
            "preferred_verbs": ["prove", "derive", "solve"],
            "context_format": "structured",
            "max_preamble_tokens": 200,
        },
    }
```

This is learnable — vault can track which phrasings produce better results per model and update the dialect registry over time.

### Gap 3: Context Budgeting

**Problem**: When vault guidance or task context is injected into prompts, the same amount goes to every model. Opus can handle 200K tokens of rich context; phi3:mini chokes on anything over 4K.

**Solution**: Context budgeter that compresses/selects based on target model capacity

```python
class ContextBudgeter:
    """Selects and compresses context to fit target model's window."""

    def budget(
        self,
        full_context: list[str],  # All available context pieces
        model_context_window: int,  # Target model's max tokens
        prompt_tokens: int,  # Tokens already used by prompt
        reserve_for_output: int = 2048,  # Leave room for response
    ) -> list[str]:
        available = model_context_window - prompt_tokens - reserve_for_output

        if available >= sum(len(c) for c in full_context):
            return full_context  # Everything fits

        # Rank by relevance (reuse SemanticCache's embedding similarity)
        ranked = self._rank_by_relevance(full_context, query_embedding)

        # Fill until budget exhausted
        selected = []
        tokens_used = 0
        for piece in ranked:
            piece_tokens = self._count_tokens(piece)
            if tokens_used + piece_tokens > available:
                # Try to compress this piece
                compressed = self._compress(piece, available - tokens_used)
                if compressed:
                    selected.append(compressed)
                break
            selected.append(piece)
            tokens_used += piece_tokens

        return selected
```

### Gap 4: Cascading Execution

**Problem**: No coordinated escalation strategy. SmartRouter has fallback chains but they're not cost-aware. If phi3:mini gives a low-quality answer, there's no mechanism to say "try again with qwen3-coder, and if that's still not good enough, hit cloud API."

**Solution**: Cascade executor with quality gates

```python
class CascadeExecutor:
    """Start cheap, escalate only when needed."""

    cascade_tiers = [
        {"model": "phi3:mini", "max_cost": 0.0, "quality_threshold": 0.7},
        {"model": "qwen3-coder:30b", "max_cost": 0.0, "quality_threshold": 0.8},
        {"model": "claude-sonnet-4-6", "max_cost": 0.01, "quality_threshold": 0.9},
        {"model": "claude-opus-4-6", "max_cost": 0.05, "quality_threshold": None},
    ]

    async def execute(self, task, context):
        for tier in self.cascade_tiers:
            result = await self._run(task, context, tier["model"])
            quality = self._assess_quality(result, task.success_criteria)

            if quality >= (tier["quality_threshold"] or 0):
                return result  # Good enough at this tier

            # Log cascade for vault learning
            self._log_cascade(task, tier["model"], quality)

        return result  # Best effort from highest tier
```

### Gap 5: Cross-Platform Session Memory

**Problem**: Vault provides persistent memory across sessions, but there's no mechanism for a user to start a task in Claude Code and continue it in Gemini CLI with full context.

**Solution**: Session state serialization via vault

```python
class CrossPlatformSession:
    """Serialize session state for platform handoff."""

    def export_session(self, session_id: str) -> dict:
        """Export current session state for another platform to import."""
        return {
            "session_id": session_id,
            "intent_history": self._get_intent_history(session_id),
            "active_skill": self._get_active_skill(session_id),
            "context_pieces": self._get_relevant_context(session_id),
            "model_usage": self._get_model_usage(session_id),
            "checkpoint": self._get_latest_checkpoint(session_id),
        }

    def import_session(self, state: dict) -> str:
        """Import a session from another platform."""
        # Vault stores the handoff, new platform picks it up
        vault_push_session_state(state)
        return state["session_id"]
```

This partially exists via `SessionManager` + vault, but needs a clean export/import API.

---

## Architecture

### Meridian Component Diagram

```
                    ┌─────────────────────────┐
                    │    Platform Adapters     │
                    │  (Claude Code, Gemini,   │
                    │   Cursor, Web UI, API)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────v────────────┐
                    │     MERIDIAN AGENT       │
                    │                         │
                    │  ┌──────────────────┐   │
                    │  │  IntakeSpecialist │   │  (existing)
                    │  │  Cache check      │   │
                    │  └────────┬─────────┘   │
                    │           │              │
                    │  ┌────────v─────────┐   │
                    │  │ RequestAlignment  │   │  (existing)
                    │  │ Analyzer          │   │
                    │  └────────┬─────────┘   │
                    │           │              │
                    │  ┌────────v─────────┐   │
                    │  │  SkillSelector    │   │  (existing)
                    │  └────────┬─────────┘   │
                    │           │              │
                    │  ┌────────v─────────┐   │
                    │  │ CompositeRouter   │   │  << NEW >>
                    │  │  (unified score)  │   │
                    │  │  Cost + HW +      │   │
                    │  │  Capability +     │   │
                    │  │  Experience       │   │
                    │  └────────┬─────────┘   │
                    │           │              │
                    │  ┌────────v─────────┐   │
                    │  │ PromptDialect     │   │  << NEW >>
                    │  │  + ContextBudget  │   │
                    │  └────────┬─────────┘   │
                    │           │              │
                    │  ┌────────v─────────┐   │
                    │  │ CascadeExecutor   │   │  << NEW >>
                    │  │  (try cheap →     │   │
                    │  │   escalate)       │   │
                    │  └────────┬─────────┘   │
                    │           │              │
                    │  ┌────────v─────────┐   │
                    │  │ Vault Logger      │   │  (existing)
                    │  │  (learn & refine) │   │
                    │  └──────────────────┘   │
                    └─────────────────────────┘
```

### New Files

```
src/cohezion/concierge/
    __init__.py
    meridian.py           # Main orchestrator (~300 lines)
    composite_router.py   # Unified scoring across all routers (~200 lines)
    prompt_dialect.py     # Model-specific prompt shaping (~300 lines)
    context_budget.py     # Context compression per model capacity (~200 lines)
    cascade.py            # Try cheap → escalate strategy (~400 lines)
    session_bridge.py     # Cross-platform session handoff (~150 lines)
```

Estimated new code: ~1,550 lines (phases 1-4). Builds on ~3,600 lines of existing routing infrastructure.

---

## Implementation Phases

### Phase 1: Composite Router Facade (~2 days)

**Goal**: Single entry point that orchestrates all existing routers.

**What**: `MeridianRouter` class that:
1. Calls `RequestAlignmentAnalyzer.analyze()` for intent
2. Calls `SkillSelector.select()` for skill matching
3. Calls `CostAwareRouter.select_model()` for cost signal
4. Calls `SmartRouter.route()` for capability signal
5. Calls `DynamicModelRouter.select()` for hardware signal
6. Computes composite score and returns `MeridianRoutingDecision`

**Validation**: Route 10 test queries through Meridian vs individual routers. Verify Meridian makes better decisions (measured by task completion quality).

**Files**: `src/cohezion/concierge/__init__.py`, `meridian.py`, `composite_router.py`

### Phase 2: Prompt Dialect Registry (~1 day)

**Goal**: Adapt prompt phrasing (not just format) based on target model.

**What**: Registry of model family → prompt style mappings. Transforms the same intent into model-optimal phrasing.

**Validation**: Same 10 queries, compare output quality when prompts are dialect-shaped vs generic.

**Files**: `prompt_dialect.py`

### Phase 3: Context Budgeter (~1 day)

**Goal**: Compress/select context to fit target model's token window.

**What**: Leverages SemanticCache embeddings to rank context pieces by relevance, then fills up to the model's available context budget.

**Validation**: Measure context utilization ratio (how much of available context window is used productively).

**Files**: `context_budget.py`

### Phase 4: Cascade Executor (~2 days)

**Goal**: Start with cheapest viable model, escalate only when quality is insufficient.

**What**: Try local model first. Assess output quality via `ModelQualityClassifier`. If below threshold, retry with next tier. Log cascade events to vault for future routing improvements.

**Validation**: Measure cost savings vs quality trade-off. Target: 50%+ of queries handled by cheapest tier with acceptable quality.

**Files**: `cascade.py`

### Phase 5: Cross-Platform Session Bridge (future)

**Goal**: Export/import session state across platforms.

**What**: Clean API for session serialization. Vault-backed persistence. Platform-specific import adapters.

**Deferred**: Depends on multi-platform deployment, which is future work.

**Files**: `session_bridge.py`

---

## Naming: Why "Meridian"

The concierge agent needs an identity. "Jeeves" is off-limits (IAC/InterActiveCorp holds the trademark from the 2005 acquisition of Ask Jeeves for ~$1.85B).

### Candidate Names

| Name | Meaning | Namespace | Vibe |
|------|---------|-----------|------|
| **Meridian** | The line where all paths converge; navigational precision | `meridian.route()`, `MeridianRouter` | Technical, authoritative, convergent |
| **Valet** | Personal assistant who anticipates needs | `valet.serve()`, `ValetAgent` | Service-oriented, warm, personal |
| **Conduit** | Channel through which everything flows | `conduit.flow()`, `ConduitRouter` | Infrastructure, neutral, pipeline |
| **Fulcrum** | The pivot point that enables leverage | `fulcrum.balance()`, `FulcrumAgent` | Mechanical, precise, amplifying |
| **Prism** | Separates white light into its components | `prism.refract()`, `PrismRouter` | Analytical, separating, elegant |

### Recommendation: Meridian

- **Convergence**: All routing signals (cost, capability, hardware, experience) converge at a single point — the meridian
- **Navigation**: Meridians guide you to the right destination, which is exactly what the concierge does
- **Precision**: Meridians are exact — no ambiguity about where you are
- **Domain fit**: Works in code (`MeridianRouter.route()`), in docs ("Meridian handles routing"), and in conversation ("Ask Meridian")
- **No IP risk**: "Meridian" is a generic term; no trademark concerns in the AI/software space for this usage

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| Routing decision quality | 85%+ optimal model selection | Compare Meridian choice vs oracle (best possible) on test set |
| Cost reduction | 30%+ savings vs always-use-best-model | Track actual spend per query with/without cascading |
| Latency overhead | <50ms routing decision time | Meridian decision time (not including model execution) |
| Cache leverage | 95%+ cache hit rate maintained | SemanticCache metrics (L1+L2+L3) |
| Cross-model quality | No quality degradation from dialect shaping | A/B test: generic prompt vs dialect-shaped prompt, measure output quality |
| Cascade efficiency | 50%+ queries resolved at cheapest tier | Track cascade depth distribution |

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Over-engineering (layer on layers) | Medium | High | Phase 1 is facade-only; measure before expanding |
| Routing latency | Low | Medium | All routing is heuristic-based, no LLM calls for routing itself |
| Prompt dialect brittleness | Medium | Low | Vault-backed learning; observe what works, auto-update |
| Cascade cost explosion | Low | Medium | Budget enforcer caps total spend per query |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| IP: "Jeeves" trademark | N/A | Avoided | Using "Meridian" codename instead |
| IP: Intent routing concept | None | N/A | Prior art everywhere; not patentable |
| Premature abstraction | Medium | High | Build only what's needed; validate with real queries |

---

## Relationship to Existing Cohezion Architecture

### What Meridian Replaces

- **Ad-hoc router selection**: Currently, calling code picks which router to use. Meridian makes that choice automatically.
- **MCP Infrastructure PRD**: The transport-layer approach of building platform adapters. Meridian replaces this with an intelligence-layer approach.

### What Meridian Preserves

- **All 7 existing routers**: They become signals feeding into Meridian's composite score.
- **CompoundExecutor**: Remains the execution engine.
- **SemanticCache**: Remains the caching layer.
- **Vault**: Remains the knowledge persistence layer.
- **PRIME Skills**: Remain the task-specific definitions.

### What Meridian Adds

- **CompositeRouter**: Unified scoring function across all routing signals.
- **PromptDialect**: Model-specific prompt phrasing.
- **ContextBudgeter**: Context compression per model capacity.
- **CascadeExecutor**: Try cheap → escalate strategy.
- **SessionBridge**: Cross-platform session handoff (future).

---

## BMAD Workflow Integration

Meridian naturally maps to BMAD task types:

| BMAD Task | Intent | Model Selection | Why |
|-----------|--------|----------------|-----|
| Create Architecture | GENERATE + COMPLEX | claude-opus-4-6 or deepseek-r1:70b | Needs deep reasoning, broad context |
| Quick Dev | GENERATE + SIMPLE | phi3:mini or qwen3-coder:30b | Speed matters, task is constrained |
| Code Review | ANALYZE + MEDIUM | qwen3-coder:30b | Code understanding + fast turnaround |
| Create PRD | GENERATE + COMPLEX | claude-opus-4-6 | Structured output, stakeholder language |
| Sprint Status | SEARCH + SIMPLE | phi3:mini | Data retrieval, minimal reasoning |
| Domain Research | ANALYZE + COMPLEX | claude-opus-4-6 + web search | Broad knowledge, synthesis |
| Quick Spec | GENERATE + MEDIUM | qwen3-coder:30b | Technical detail, moderate complexity |

The concierge makes these routing decisions automatically — the user just says "create the architecture" and Meridian handles the rest.

---

## Open Questions

1. **Should Meridian be a local service or part of the Cohezion API?**
   - Local service: Faster, works offline, no API dependency
   - API service: Centralized, easier to update, shared learning
   - Recommendation: Start as local (embedded in Cohezion), extract to service later if needed

2. **How aggressive should cascading be?**
   - Conservative: Only cascade on clear quality failures
   - Aggressive: Always start at cheapest tier
   - Recommendation: Configurable per-task, default to conservative

3. **Should prompt dialects be learned or hand-coded?**
   - Hand-coded: Predictable, fast to ship
   - Learned: Better long-term, requires data collection
   - Recommendation: Start hand-coded, add vault-based learning in Phase 2+

4. **How to handle cloud API models (Claude, Gemini) in the cascade?**
   - Always available (API call)
   - Cost is non-zero (unlike local Ollama)
   - Need clear budget policy for when to escalate to cloud
   - Recommendation: Cloud models are the last cascade tier, guarded by budget enforcer

---

## Next Steps

1. **Review this brief** — Does Meridian capture the concierge vision accurately?
2. **Phase 1 implementation** — CompositeRouter facade wrapping existing routers
3. **Test harness** — 10-50 representative queries across BMAD task types
4. **Measure** — Does unified routing actually make better decisions?
5. **Iterate** — Add prompt dialects, context budgeting, cascading based on measurement data
