---
title: "Meridian Concierge Agent - Product Requirements Document"
project: cohezion
type: prd
status: draft
created: 2026-03-06
tags: [meridian, concierge, routing, compound-engineering, prd]
replaces: MCP Infrastructure PRD
aspect: doer
neural:
  activation: 0.96
  stage: growing
  synapse_in: 3
  synapse_out: 4
---

# Meridian: Concierge Agent PRD

## 1. Overview

### 1.1 Product Name
**Meridian** — The Cohezion Concierge Agent

### 1.2 Vision Statement
Meridian is a single intelligent front door that makes any task work optimally regardless of which platform or model executes it. It understands intent, selects the right model, shapes the prompt for that model's strengths, and injects the right context — all transparently.

### 1.3 Problem Statement
Cohezion has 7 separate routing/intent components (~3,600 lines) that each independently solve a piece of the routing puzzle:

| Component | Signal | Gap |
|-----------|--------|-----|
| CostAwareRouter | Cost/budget | Ignores task fit |
| DynamicModelRouter | Hardware/memory | Ignores semantics |
| SmartRouter | Task capability | Ignores cost |
| RequestAlignmentAnalyzer | Intent/constraints | Doesn't route |
| SkillSelector | Vault experience | No constraint filtering |
| PromptOptimizer | Compression | No dialect shaping |
| ModelPoolManager | Availability | No intelligence |

**No component combines all signals into a unified routing decision.** Users (and calling code) must manually pick which router to use, leading to suboptimal model selection, wasted tokens, and inconsistent results across platforms.

### 1.4 Target Users

1. **Cohezion CLI users** — Developers using Cohezion directly for compound engineering tasks
2. **Platform users** — Developers using Claude Code, Gemini CLI, Cursor, or other AI-assisted IDEs where Cohezion serves as the intelligence backend
3. **BMAD workflow users** — Teams running BMAD workflows (create architecture, quick dev, code review) who need automatic model selection
4. **API consumers** — Applications calling Cohezion's API endpoints for AI-assisted tasks

### 1.5 Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Routing quality | 85%+ optimal model selection | Compare vs oracle on test set |
| Cost reduction | 30%+ savings vs always-best-model | Track spend with/without cascading |
| Routing latency | <50ms decision time | Meridian overhead (excluding model execution) |
| Cache utilization | 95%+ hit rate maintained | SemanticCache L1+L2+L3 metrics |
| Cascade efficiency | 50%+ queries at cheapest tier | Track cascade depth distribution |
| Cross-model quality | No degradation from dialect shaping | A/B test generic vs shaped prompts |

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-1: Unified Composite Routing
- **FR-1.1**: Meridian SHALL accept any natural language task request and return a `MeridianRoutingDecision` containing: selected model, composite score, individual signal contributions, confidence level, and cascade threshold.
- **FR-1.2**: The composite score SHALL combine signals from: intent fit (RequestAlignmentAnalyzer), capability fit (SmartRouter), cost efficiency (CostAwareRouter), hardware feasibility (DynamicModelRouter), and vault experience (SkillSelector).
- **FR-1.3**: Signal weights SHALL be configurable per deployment, with defaults: intent 30%, capability 25%, cost 20%, hardware 15%, experience 10%.
- **FR-1.4**: Meridian SHALL respect HIHO coherence threshold (0.5) — requests below this threshold SHALL be decomposed or escalated.

#### FR-2: Prompt Dialect Shaping
- **FR-2.1**: Meridian SHALL maintain a prompt dialect registry mapping model families to preferred prompt styles.
- **FR-2.2**: Supported dialect families: `claude` (structured reasoning), `gemini` (conversational), `ollama_small` (concise directives), `ollama_coder` (implementation-focused), `ollama_reasoner` (chain-of-thought).
- **FR-2.3**: Dialect shaping SHALL transform prompt phrasing (verb choice, structure, preamble length) without altering semantic intent.
- **FR-2.4**: Dialect effectiveness SHALL be tracked in vault for continuous improvement.

#### FR-3: Context Budgeting
- **FR-3.1**: Meridian SHALL determine available context budget based on: target model's context window, prompt token count, and reserved output tokens (default 2048).
- **FR-3.2**: When full context exceeds budget, Meridian SHALL rank context pieces by semantic relevance (via SemanticCache embeddings) and select top-ranked pieces that fit.
- **FR-3.3**: Context compression SHALL be attempted for pieces that partially fit, using summarization heuristics.
- **FR-3.4**: Context budget utilization ratio SHALL be logged for optimization.

#### FR-4: Cascading Execution
- **FR-4.1**: Meridian SHALL support cascading execution tiers: local-small → local-large → cloud-standard → cloud-premium.
- **FR-4.2**: After each tier's execution, Meridian SHALL assess output quality using ModelQualityClassifier.
- **FR-4.3**: If quality is below the tier's threshold, Meridian SHALL automatically escalate to the next tier.
- **FR-4.4**: Cascade events SHALL be logged to vault for routing improvement.
- **FR-4.5**: Total cascade cost SHALL be bounded by BudgetEnforcer — no cascade SHALL exceed the per-query budget.

#### FR-5: Cross-Platform Session Memory
- **FR-5.1**: Meridian SHALL support session export — serializing current session state (intent history, active skill, context, model usage, checkpoint) to vault.
- **FR-5.2**: Meridian SHALL support session import — loading a previously exported session on any platform.
- **FR-5.3**: Session state SHALL be platform-agnostic (no platform-specific data in the serialized state).

#### FR-6: BMAD Integration
- **FR-6.1**: Meridian SHALL automatically map BMAD task types to routing decisions:
  - `create-architecture` → COMPLEX intent → deep reasoning model
  - `quick-dev` → SIMPLE intent → fast local model
  - `code-review` → MEDIUM intent → code-specialized model
  - `create-prd` → COMPLEX intent → structured output model
  - `sprint-status` → SIMPLE intent → retrieval model
- **FR-6.2**: BMAD task mapping SHALL be extensible via skill registry.

### 2.2 Non-Functional Requirements

#### NFR-1: Performance
- **NFR-1.1**: Routing decision latency SHALL be <50ms (P95) excluding model execution time.
- **NFR-1.2**: Meridian SHALL add no more than 5% overhead to total request latency.
- **NFR-1.3**: All routing logic SHALL be heuristic-based — no LLM calls for routing decisions.

#### NFR-2: Reliability
- **NFR-2.1**: If any individual router fails, Meridian SHALL gracefully degrade using remaining signals.
- **NFR-2.2**: If all routers fail, Meridian SHALL fall back to a default model (configurable).
- **NFR-2.3**: Vault logging SHALL be non-blocking — logging failures SHALL NOT affect routing or execution.

#### NFR-3: Observability
- **NFR-3.1**: Every routing decision SHALL be logged with: input query, selected model, composite score, individual signals, cascade depth, and execution time.
- **NFR-3.2**: Metrics SHALL be accessible via GlobalMetricsAggregator for dashboard integration.
- **NFR-3.3**: JourneyTracker SHALL record Meridian routing as a trajectory point.

#### NFR-4: Security
- **NFR-4.1**: Meridian SHALL NOT expose model selection logic to external callers.
- **NFR-4.2**: API keys and model credentials SHALL NOT be logged or exposed in routing decisions.
- **NFR-4.3**: Session export SHALL sanitize sensitive context before serialization.

#### NFR-5: Extensibility
- **NFR-5.1**: New model families SHALL be addable via dialect registry without code changes.
- **NFR-5.2**: New routing signals SHALL be pluggable via the composite scoring interface.
- **NFR-5.3**: Cascade tiers SHALL be configurable via settings, not hardcoded.

### 2.3 Constraints

- **C-1**: Must run on AMD Ryzen AI MAX+ 395 with 128GB RAM (no CUDA/RTX assumptions).
- **C-2**: Local models limited to 4 concurrent via Ollama.
- **C-3**: Cloud API usage must respect Free Tier limits (prefer local over cloud).
- **C-4**: Must integrate with existing CompoundExecutor execution pipeline.
- **C-5**: Must preserve backward compatibility — existing direct router usage continues to work.

---

## 3. User Flows

### 3.1 Simple Query Flow
```
User: "What does the calculate_total function do?"
    → Meridian classifies: SEARCH intent, SIMPLE complexity
    → Routes to: phi3:mini (fast, free, sufficient)
    → Dialect: direct/concise ("Explain the purpose of calculate_total")
    → Context: function source code only (~200 tokens)
    → Result: returned in <2 seconds
```

### 3.2 Complex Architecture Flow
```
User: "Design a microservices architecture for our payment system"
    → Meridian classifies: GENERATE intent, COMPLEX complexity
    → Routes to: claude-opus-4-6 (deep reasoning, large context)
    → Dialect: structured reasoning ("Analyze requirements, then design...")
    → Context: full project docs, existing architecture, constraints (~50K tokens)
    → Result: comprehensive architecture document
```

### 3.3 Cascade Flow
```
User: "Refactor this authentication module to use JWT"
    → Meridian classifies: TRANSFORM intent, MEDIUM complexity
    → Cascade tier 1: qwen3-coder:30b (local, code-focused)
    → Quality assessment: 0.65 (below 0.7 threshold)
    → Cascade tier 2: claude-sonnet-4-6 (cloud, better reasoning)
    → Quality assessment: 0.88 (above 0.8 threshold)
    → Result: high-quality refactored code, cost = $0.003 (not $0.02)
```

### 3.4 Cross-Platform Flow
```
Claude Code session:
    User: "Start designing the auth system"
    → Meridian creates session, begins architecture
    → User: "Save session, I'll continue in Gemini"
    → Meridian exports session state to vault

Gemini CLI session:
    User: "Resume my auth system design"
    → Meridian imports session from vault
    → Context, decisions, and progress all preserved
    → Continues with Gemini's strengths (broad knowledge)
```

---

## 4. Data Model

### 4.1 Core Types

```python
@dataclass
class MeridianRoutingDecision:
    model: str                      # Selected model ID
    score: float                    # Composite score 0.0-1.0
    confidence: float               # How certain is this routing?
    signals: RoutingSignals         # Individual router contributions
    dialect: str                    # Prompt dialect family
    context_budget: int             # Tokens available for context
    cascade_threshold: float        # Quality below this triggers escalation
    skill: str | None               # Matched PRIME skill
    estimated_cost_usd: float       # Projected cost
    estimated_latency_ms: float     # Projected latency

@dataclass
class RoutingSignals:
    intent_fit: float               # From RequestAlignmentAnalyzer
    capability_fit: float           # From SmartRouter
    cost_efficiency: float          # From CostAwareRouter
    hw_feasibility: float           # From DynamicModelRouter
    vault_experience: float         # From SkillSelector

@dataclass
class PromptDialectConfig:
    family: str                     # claude, gemini, ollama_small, etc.
    reasoning_style: str            # structured, conversational, direct, etc.
    preferred_verbs: list[str]      # Model-preferred action words
    context_format: str             # xml_tags, markdown, minimal, code_first
    max_preamble_tokens: int        # Max tokens for preamble/system prompt

@dataclass
class CascadeTier:
    model: str                      # Model to try at this tier
    max_cost_usd: float             # Cost ceiling for this tier
    quality_threshold: float | None # Minimum quality to accept (None = always accept)
    timeout_seconds: float          # Max execution time at this tier

@dataclass
class SessionExport:
    session_id: str
    timestamp: str
    intent_history: list[dict]
    active_skill: str | None
    context_pieces: list[str]
    model_usage: dict[str, int]
    checkpoint: dict | None
    platform_origin: str
```

---

## 5. API Surface

### 5.1 Primary Entry Point

```python
class MeridianAgent:
    """The concierge agent — single intelligent front door."""

    async def route(self, query: str, **kwargs) -> MeridianRoutingDecision:
        """Analyze query and determine optimal routing."""

    async def execute(self, query: str, **kwargs) -> MeridianResult:
        """Route AND execute in one call (convenience method)."""

    async def cascade(self, query: str, **kwargs) -> MeridianResult:
        """Execute with cascading — try cheap, escalate if needed."""

    def export_session(self, session_id: str) -> SessionExport:
        """Export session state for cross-platform handoff."""

    def import_session(self, state: SessionExport) -> str:
        """Import session state from another platform."""
```

### 5.2 FastAPI Endpoints

```
POST /meridian/route          → Route query, return decision (no execution)
POST /meridian/execute        → Route + execute in one call
POST /meridian/cascade        → Route + cascading execution
POST /meridian/session/export → Export session state
POST /meridian/session/import → Import session state
GET  /meridian/metrics        → Routing metrics dashboard
GET  /meridian/dialects       → List available prompt dialects
```

---

## 6. Relationship to Existing Systems

### 6.1 What Meridian Replaces
- **MCP Infrastructure PRD** — Transport-layer approach of platform adapters
- **Ad-hoc router selection** — Calling code manually picking which router to use

### 6.2 What Meridian Preserves
- All 7 existing routers (become signals feeding Meridian)
- CompoundExecutor (execution engine)
- SemanticCache (caching layer)
- Vault (knowledge persistence)
- PRIME Skills (task definitions)
- BMAD workflows (task types)

### 6.3 What Meridian Adds
- CompositeRouter (unified scoring)
- PromptDialect (model-specific phrasing)
- ContextBudgeter (capacity-aware context selection)
- CascadeExecutor (try cheap → escalate)
- SessionBridge (cross-platform handoff)

---

## 7. Out of Scope (v1)

- Multi-model ensemble execution (running same query on multiple models and merging)
- Real-time model fine-tuning based on routing feedback
- Visual/multimodal routing (image/audio input handling)
- Third-party model marketplace integration
- Billing/metering for external API consumers
- Automatic model downloading/installation

---

## 8. Dependencies

| Dependency | Type | Status |
|-----------|------|--------|
| RequestAlignmentAnalyzer | Internal | Existing (1004 lines) |
| CostAwareRouter | Internal | Existing (713 lines) |
| SmartRouter | Internal | Existing (490 lines) |
| DynamicModelRouter | Internal | Existing (528 lines) |
| SkillSelector | Internal | Existing (431 lines) |
| PromptOptimizer | Internal | Existing (229 lines) |
| ModelPoolManager | Internal | Existing (~150 lines) |
| CompoundExecutor | Internal | Existing |
| SemanticCache | Internal | Existing |
| ModelQualityClassifier | Internal | Existing |
| BudgetEnforcer | Internal | Existing |
| Vault (Obsidian) | External | Operational |
| Ollama | External | Operational (4 concurrent limit) |

---

## 9. Glossary

| Term | Definition |
|------|-----------|
| **Meridian** | Codename for the concierge agent; the line where all routing paths converge |
| **Composite Score** | Weighted combination of all routing signals into a single 0.0-1.0 score |
| **Prompt Dialect** | Model-specific prompt phrasing (not just format) that optimizes for each model's strengths |
| **Context Budgeting** | Selecting/compressing context to fit a target model's token capacity |
| **Cascading** | Trying the cheapest viable model first, then escalating to more capable/expensive models if quality is insufficient |
| **HIHO Threshold** | 0.5 coherence minimum — below this, tasks should be decomposed or escalated |
| **Session Bridge** | Mechanism for exporting/importing session state across platforms |

---

## Related Documents

- [[Architecture]] — Technical architecture and component design
- [[Epics]] — Epic breakdown for implementation
- [[Stories]] — Detailed user stories per epic
- [[2026-03-06-adopt-meridian-concierge-agent-over-mcp-infrastructure-prd]] — ADR for this decision
