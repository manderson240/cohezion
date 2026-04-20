---
title: "SurrealDB Agent Context Schema Design"
date: 2026-02-11
status: proposed
tags: [pattern, architecture, surrealdb, graph, agent-context, knowledge-graph]
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 33
  synapse_out: 19
---

# SurrealDB Agent Context Schema

Comprehensive schema for tracking agent sessions, decisions, reasoning, and outcomes in SurrealDB to create research lineage and enable strategic learning from agent work.

## Problem

Current knowledge graph (84 papers + 21 concepts + 148 relationships) lacks context for agent decision-making. We need to:
- Trace which research informed architectural decisions
- Validate (or challenge) lessons learned from agent work
- Detect misalignment between agent reasoning and established research
- Understand decision cascades and dependencies
- Feed agent context into 12D graph (Dimension 12: Agent Affinity)

## Solution

Five node types + eight relationship types create a comprehensive agent context model that integrates seamlessly with existing vault structure.

---

## Architecture

### Node Types (5 Core Entities)

#### 1. agent_session
**Purpose**: Wrapper for entire agent work session (task, goal, resource tracking)

```yaml
agent_id: string              # Unique agent identifier
session_id: string            # UUID with timestamp
start_time: datetime
end_time: datetime, nullable
model_used: string            # e.g., "claude-haiku-4-5", "gpt-4"
total_tokens: int
cost_usd: float
phase: string                 # "research", "decision", "implementation", "validation"
status: enum                  # "in_progress", "completed", "failed"
goals: array<string>          # Initial goals for session
outcome_summary: string, nullable  # Final summary if completed
```

**Rationale**: Captures agent work boundary + resource metrics for efficiency tracking and cost analysis.

**Example**:
```
agent_session:s001_2026_02_11_143000
├── agent_id: "data-graph-specialist"
├── start_time: 2026-02-11T14:30:00Z
├── model_used: "claude-haiku-4-5"
├── total_tokens: 42000
├── cost_usd: 0.21
├── goals: ["design-agent-context-schema", "integrate-with-12d-graph"]
├── status: "in_progress"
```

---

#### 2. agent_decision
**Purpose**: Records specific architectural/feature/refactor decision with reasoning + outcome

```yaml
decision_id: string
session_id: relation -> agent_session
decision_type: enum           # "architecture", "feature", "refactor", "bugfix", "data"
timestamp: datetime
reasoning: string             # Full explanation of decision
confidence_score: float       # 0-1, how confident was agent
validation_status: enum       # "pending", "validated", "invalidated"
implementation_status: enum   # "proposed", "in_progress", "completed", "abandoned"
metadata: object              # Tool-specific: {files_modified: [], tests_added: 3, ...}
```

**Rationale**: Traces every architectural decision to its reasoning, confidence level, and eventual validation.

**Example**:
```
agent_decision:d001
├── session_id: agent_session:s001
├── decision_type: "architecture"
├── timestamp: 2026-02-11T15:30:00Z
├── reasoning: "Use SurrealDB for graph storage because it supports..."
├── confidence_score: 0.92
├── validation_status: "pending"
```

---

#### 3. agent_reasoning
**Purpose**: Breaks down HOW a decision was made (research vs intuition vs convention)

```yaml
reasoning_id: string
decision_id: relation -> agent_decision
reasoning_type: enum         # "research_based", "pattern_based", "intuition", "convention"
source_notes: array<string>  # Paper/concept IDs that influenced reasoning
chain_of_thought: string     # Step-by-step reasoning breakdown
assumptions: array<string>   # Stated assumptions for decision
timestamp: datetime
```

**Rationale**: Enables detection of misalignment (agent reasoning vs established research) and understanding of decision dependencies.

**Example**:
```
agent_reasoning:r001
├── decision_id: agent_decision:d001
├── reasoning_type: "research_based"
├── source_notes: [
│    "paper:2023-surrealdb-benchmarks",
│    "concept:graph-database-tradeoffs"
│   ]
├── assumptions: [
│    "SurrealDB performance meets 100ms query latency",
│    "Real-time subscriptions needed for graph updates"
│   ]
```

---

#### 4. agent_context
**Purpose**: Tracks evolving agent state during session for "what was agent thinking at time T" queries

```yaml
context_id: string
session_id: relation -> agent_session
active_concepts: array<string>     # Concept IDs in focus
active_domains: array<string>      # Research domains being explored
current_goals: array<string>       # Active goals at this timestamp
token_budget_remaining: int
decision_history: array<string>    # Prior decision IDs in session
timestamp: datetime
relevance_snapshot: object         # 12D dimension values for papers at moment
```

**Rationale**: Enables retrospective analysis and context-aware recommendations based on what agent was thinking.

**Example**:
```
agent_context:c001
├── session_id: agent_session:s001
├── timestamp: 2026-02-11T15:15:00Z
├── active_concepts: ["graph-databases", "surrealdb", "knowledge-graphs"]
├── active_domains: ["databases", "ai-ml", "architecture"]
├── token_budget_remaining: 58000
├── relevance_snapshot: {
│    "dim_temporal": 2026-02-11,
│    "dim_domain": ["databases", "architecture"],
│    "dim_connectivity": 3.2,
│    "dim_agent_affinity": 1.0
│   }
```

---

#### 5. agent_outcome
**Purpose**: Closure node - captures learnings + validation for feedback loop

```yaml
outcome_id: string
session_id: relation -> agent_session
outcome_type: enum              # "success", "partial", "failed"
lessons_learned: array<string>  # Lesson node IDs extracted from session
metrics: object                 # {session_duration_min, token_efficiency_ratio, features_delivered}
validated_by: string, nullable  # Who validated the outcome (human/agent ID)
timestamp: datetime
next_recommendations: array<string>  # What to do next based on outcome
```

**Rationale**: Closes feedback loop - agent work either validates existing lessons or creates new ones.

**Example**:
```
agent_outcome:o001
├── session_id: agent_session:s001
├── outcome_type: "success"
├── lessons_learned: [
│    "lesson:token-efficiency-haiku-3x-cheaper",
│    "lesson:research-lineage-critical-for-validation"
│   ]
├── metrics: {
│    "session_duration_min": 45,
│    "token_efficiency_ratio": 3.2,
│    "decisions_made": 5,
│    "decisions_validated": 4
│   }
├── timestamp: 2026-02-11T16:30:00Z
```

---

### Relationship Types (8 Core Edges)

| Edge | From | To | Properties | Query Purpose |
|------|------|-----|-----------|-------------|
| **APPLIED_RESEARCH** | agent_decision | paper | `relevance_score` (0-1), `applied_at` (datetime) | "Which papers influenced this decision?" |
| **VALIDATES_LESSON** | agent_outcome | lesson | `alignment_score` (0-1), `validation_type` ("confirms"/"refutes"/"refines") | "What lessons from agent's work?" |
| **CHALLENGES_LESSON** | agent_reasoning | lesson | `challenge_type` ("contradicts"/"limits"/"extends") | "Where is agent misaligned with research?" |
| **INFLUENCED_BY_CONCEPT** | agent_decision | concept | `influence_strength` (0-1), `application_context` (string) | "Did agent apply cross-cutting concepts?" |
| **IMPLEMENTS_PATTERN** | agent_decision | pattern | `pattern_match_score` (0-1) | "Did agent reuse established patterns?" |
| **RELATES_TO_DECISION** | agent_decision | agent_decision | `dependency_type` ("blocks"/"enables"/"refines") | "How did decisions cascade?" |
| **EXPLORES_DOMAIN** | agent_context | domain | `exploration_depth` (0-1), `duration_min` (int) | "Which domains did agent focus on?" |
| **INFORMS_AGENT** | agent_reasoning | agent_context | `information_value` (0-1), `timestamp` (datetime) | "What shaped agent's current context?" |

---

## Query Examples

### Query 1: Research Lineage
```sql
-- Which papers influenced this agent's decisions?
SELECT
  agent_decision.{id, decision_type, reasoning, confidence_score},
  ->APPLIED_RESEARCH->paper.{title, date, tags},
  ->APPLIED_RESEARCH.relevance_score
FROM agent_decision
WHERE session_id = $session_id
  AND ->APPLIED_RESEARCH EXISTS
ORDER BY ->APPLIED_RESEARCH.relevance_score DESC;
```

### Query 2: Lesson Validation
```sql
-- What lessons come from this agent's work?
SELECT
  agent_outcome.{id, outcome_type, metrics},
  ->VALIDATES_LESSON->lesson.{title, severity, primary_source},
  ->VALIDATES_LESSON.alignment_score,
  ->VALIDATES_LESSON.validation_type
FROM agent_outcome
WHERE session_id = $session_id
ORDER BY ->VALIDATES_LESSON.alignment_score DESC;
```

### Query 3: Misalignment Detection
```sql
-- Where is agent reasoning misaligned with research?
SELECT
  agent_reasoning.{id, chain_of_thought, assumptions},
  ->CHALLENGES_LESSON->lesson.{title, severity, primary_source},
  ->CHALLENGES_LESSON.challenge_type
FROM agent_reasoning
WHERE decision_id->session_id = $session_id
  AND ->CHALLENGES_LESSON.challenge_type = "contradicts"
ORDER BY decision_id->timestamp ASC;
```

### Query 4: Decision Cascade
```sql
-- How did prior decisions cascade/block/enable each other?
SELECT
  agent_decision.{id, decision_type, timestamp, reasoning},
  <-RELATES_TO_DECISION<-agent_decision.{id, decision_type, timestamp},
  ->RELATES_TO_DECISION->agent_decision.{id, decision_type, timestamp}
FROM agent_decision
WHERE session_id = $session_id
ORDER BY timestamp ASC;
```

### Query 5: Context Timeline
```sql
-- What context conditions preceded each decision?
SELECT
  agent_decision.{id, decision_type, timestamp, reasoning},
  ->APPLIED_RESEARCH->paper.title,
  <-RELATES_TO_DECISION<-agent_context.{
    active_concepts,
    active_domains,
    token_budget_remaining,
    timestamp
  }
FROM agent_decision
WHERE session_id = $session_id
ORDER BY timestamp ASC;
```

---

## Metrics & Tracking

### Core Metrics
- **token_efficiency_ratio** = output_value / total_tokens (for Haiku vs Sonnet)
- **decision_validation_rate** = validated_decisions / total_decisions
- **research_alignment_score** = avg(APPLIED_RESEARCH.relevance_score) per session
- **lesson_integration_score** = lessons_validated / available_lessons
- **domain_exploration_entropy** = Shannon entropy of domain distribution

### Dimensional Mapping (12D Graph Integration)
```python
agent_context.relevance_snapshot = {
  "dim_temporal": agent_session.start_time,
  "dim_domain": agent_context.active_domains,
  "dim_connectivity": count(agent_decision->APPLIED_RESEARCH),
  "dim_agent_affinity": 1.0,  # Always 1.0 for agent's own context
  "dim_depth": avg(agent_reasoning.source_notes.count),
  "dim_citations": count(agent_outcome->VALIDATES_LESSON),
  # ... other dimensions
}
```

---

## Implementation Phases

### Phase 1: Core Lineage (2-3 days)
- `agent_session` + `agent_decision` nodes
- `APPLIED_RESEARCH` + `VALIDATES_LESSON` relationships
- Tools: `track_session()`, `record_decision()`, `record_outcome()`
- Enables: "Which papers influenced this decision?"

### Phase 2: Reasoning Depth (1 day)
- `agent_reasoning` node
- `CHALLENGES_LESSON` relationship
- Tool: `record_reasoning()` with chain-of-thought
- Enables: "Where is agent misaligned with research?"

### Phase 3: Context Snapshots (1 day)
- `agent_context` node + snapshot tracking
- `EXPLORES_DOMAIN` + `INFORMS_AGENT` relationships
- Tool: `track_context_state()`
- Enables: "What was agent thinking at time T?"

### Phase 4: Advanced Metrics (2 days)
- Full `agent_outcome` implementation
- Metrics computation + validation workflow
- Dimension 12 (Agent Affinity) integration
- Tools for outcome validation + metric extraction

---

## Integration Points

### With Cloud Vault MCP
- New tools: `track_session()`, `record_decision()`, `record_reasoning()`, `record_outcome()`
- Store decision IDs for later linking + validation
- Bidirectional sync with vault notes

### With Papers/Concepts/Lessons
- Obsidian frontmatter extensions: `agent_sessions: [s001, s002]`
- Backlinks from papers to agent decisions that cited them
- Concept usage tracking across agent sessions

### With 12D Graph
- `agent_context.relevance_snapshot` feeds Dimension 12
- Live queries update paper affinity scores as agent context evolves
- Agent journey visualization on top of existing graph

---

## Key Insights

1. **Research Lineage**: Every decision traced to papers that influenced it
2. **Lesson Loop**: Agent outcomes validate or challenge existing knowledge
3. **Misalignment Detection**: Reasoning nodes flag contradictions with research
4. **Decision Dependencies**: Relationships show how decisions cascade/block/enable
5. **Agent Affinity**: Integrates agent context into multi-dimensional visualization

---

## When to Use

- **When implementing agent tracking**: Start with Phase 1 (session + decision + research lineage)
- **When validating agent work**: Use agent_outcome + VALIDATES_LESSON to close feedback loop
- **When debugging agent decisions**: Query CHALLENGES_LESSON to find misalignment
- **When analyzing agent efficiency**: Compute metrics from agent_session + agent_outcome
- **When updating 12D graph**: Include agent_context snapshots in relevance calculations

---

## Related

**Tags**: surrealdb, knowledge-graph, agent-context, architecture

**Concepts**: [[graph-databases]], [[knowledge-graph-systems]], [[agent-context]], [[research-lineage]]

**Decisions**: [[2026-02-11-surrealdb-agent-context-schema-design]], [[2026-02-12-phase-2-schema-design]], [[2026-02-09-12d-graph-surrealdb-integration]], [[2026-02-11-adopt-graphrag-for-vault-knowledge-graph]]

**Papers**: [[surrealdb-graph-databases]] — SurrealDB's graph database capabilities that this schema leverages

**Patterns**: [[fastmcp-asgi-builder-pattern]], [[surrealdb-query-driven-analysis]]

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[3d-graph-plugin-selection]]
- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-14-track-a-sign-off-approved]]
- [[2026-02-13-phase-2-track-a-complete]]
- [[2026-02-14-phase-6c-semantic-contradiction-detection-complete]]
