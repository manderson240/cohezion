---
title: "SurrealDB Agent Context - Visual Guide & Query Patterns"
date: 2026-02-11
status: proposed
tags: [pattern, surrealdb, agent-context, reference]
aspect: thinker
neural:
  activation: 0.84
  stage: mature
  synapse_in: 3
  synapse_out: 10
---

# Agent Context Schema - Visual Guide

Quick reference for understanding agent context graph structure and common queries.

## Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT SESSION                               │
│  agent_id, session_id, start_time, model_used, total_tokens,   │
│  cost_usd, goals, status, phase                                  │
└────────────────┬────────────────┬──────────────────┬────────────┘
                 │                │                  │
                 ├─────┬──────────┘                  │
                 │     │                             │
        ┌────────▼──┐  │  ┌─────────────────────────▼────────┐
        │  DECISION  │  │  │       OUTCOME                    │
        │ (WHY made) │  │  │ (learnings + validation + metrics)
        └────┬───────┘  │  └──────────────────────────────────┘
             │          │
    ┌────────┼──────────┘
    │        │
    │   ┌────▼─────────┐
    │   │   REASONING  │
    │   │ (HOW decided) │
    │   └──────────────┘
    │
    │
    ├─APPLIED_RESEARCH──────→ PAPER (from vault)
    ├─INFLUENCED_BY_CONCEPT──→ CONCEPT (from vault)
    ├─IMPLEMENTS_PATTERN────→ PATTERN (from vault)
    └─RELATES_TO_DECISION───→ DECISION (cascade)

OUTCOME edges:
    ├─VALIDATES_LESSON─────→ LESSON (from vault)

REASONING edges:
    ├─CHALLENGES_LESSON────→ LESSON (misalignment)

CONTEXT edges:
    ├─EXPLORES_DOMAIN──────→ DOMAIN
    └─INFORMS_AGENT←─ REASONING
```

---

## Query Pattern Library

### Pattern 1: Research Lineage
**"Which research papers influenced this decision?"**

```sql
SELECT
  agent_decision.{
    id,
    decision_type,
    reasoning,
    confidence_score,
    timestamp
  },
  ->APPLIED_RESEARCH->paper.{
    title,
    date,
    tags,
    file_path
  } AS papers,
  ->APPLIED_RESEARCH.{
    relevance_score,
    applied_at
  } AS application
FROM agent_decision
WHERE session_id = $session_id
ORDER BY ->APPLIED_RESEARCH.relevance_score DESC;
```

**Response Structure**:
```json
{
  "id": "d001",
  "decision_type": "architecture",
  "reasoning": "Use SurrealDB because...",
  "confidence_score": 0.92,
  "papers": [
    {
      "title": "SurrealDB: A Multi-Model Database...",
      "date": "2023-06-15",
      "relevance_score": 0.95
    },
    {
      "title": "Graph Databases in Production",
      "date": "2022-03-20",
      "relevance_score": 0.72
    }
  ]
}
```

---

### Pattern 2: Lesson Validation
**"What lessons from the vault did this agent's work validate?"**

```sql
SELECT
  agent_outcome.{
    id,
    outcome_type,
    metrics,
    timestamp
  },
  ->VALIDATES_LESSON->lesson.{
    id,
    title,
    severity,
    primary_source,
    tags
  } AS lessons_validated,
  ->VALIDATES_LESSON.{
    alignment_score,
    validation_type
  } AS validation
FROM agent_outcome
WHERE session_id = $session_id
ORDER BY ->VALIDATES_LESSON.alignment_score DESC;
```

**Response Structure**:
```json
{
  "id": "o001",
  "outcome_type": "success",
  "metrics": {
    "session_duration_min": 45,
    "token_efficiency_ratio": 3.2,
    "decisions_made": 5,
    "decisions_validated": 4
  },
  "lessons_validated": [
    {
      "id": "lesson:001",
      "title": "Token Efficiency with Haiku Model",
      "severity": "CRITICAL",
      "validation_type": "confirms",
      "alignment_score": 0.98
    }
  ]
}
```

---

### Pattern 3: Misalignment Detection
**"Where does agent reasoning contradict established research?"**

```sql
SELECT
  agent_decision.{
    id,
    decision_type,
    timestamp
  },
  agent_reasoning.{
    id,
    reasoning_type,
    chain_of_thought,
    assumptions,
    source_notes
  },
  ->CHALLENGES_LESSON->lesson.{
    id,
    title,
    severity,
    primary_source
  } AS contradicted_lesson,
  ->CHALLENGES_LESSON.challenge_type
FROM agent_reasoning
WHERE decision_id->session_id = $session_id
  AND ->CHALLENGES_LESSON.challenge_type = "contradicts"
ORDER BY decision_id->timestamp ASC;
```

**Response Structure**:
```json
{
  "decision_id": "d002",
  "decision_type": "architecture",
  "reasoning": {
    "chain_of_thought": "We chose X because...",
    "assumptions": ["Assumption A is true"],
    "source_notes": ["paper:001"]
  },
  "contradicted_lesson": {
    "title": "Always use Sonnet for complex reasoning",
    "challenge_type": "contradicts",
    "primary_source": "decision:2025-experimental-results"
  }
}
```

---

### Pattern 4: Decision Cascade
**"How did this decision enable/block/refine other decisions?"**

```sql
SELECT
  agent_decision.{
    id,
    decision_type,
    reasoning,
    timestamp
  },
  <-RELATES_TO_DECISION<-agent_decision.{
    id,
    decision_type,
    timestamp
  } AS decisions_blocked_by_this,
  ->RELATES_TO_DECISION->agent_decision.{
    id,
    decision_type,
    timestamp
  } AS decisions_enabled_by_this,
  <-RELATES_TO_DECISION.dependency_type AS inbound_deps,
  ->RELATES_TO_DECISION.dependency_type AS outbound_deps
FROM agent_decision
WHERE session_id = $session_id
ORDER BY timestamp ASC;
```

**Response Structure**:
```json
[
  {
    "id": "d001",
    "decision_type": "architecture",
    "timestamp": "2026-02-11T10:00:00Z",
    "decisions_enabled_by_this": [
      {
        "id": "d002",
        "decision_type": "feature",
        "dependency_type": "enables"
      },
      {
        "id": "d003",
        "decision_type": "data",
        "dependency_type": "enables"
      }
    ],
    "decisions_blocked_by_this": []
  },
  {
    "id": "d002",
    "decision_type": "feature",
    "timestamp": "2026-02-11T11:30:00Z",
    "decisions_enabled_by_this": [],
    "decisions_blocked_by_this": [
      {
        "id": "d004",
        "decision_type": "refactor",
        "dependency_type": "blocks"
      }
    ]
  }
]
```

---

### Pattern 5: Context Timeline
**"What context conditions led to each decision?"**

```sql
SELECT
  agent_decision.{
    id,
    decision_type,
    reasoning,
    timestamp
  },
  ->APPLIED_RESEARCH->paper.title AS papers_cited,
  ->INFLUENCED_BY_CONCEPT->concept.title AS concepts_applied,
  <-INFORMS_AGENT<-agent_reasoning.id AS reasoning_nodes
FROM agent_decision
WHERE session_id = $session_id
ORDER BY timestamp ASC;
```

**Enriched with context** (via separate query):
```sql
SELECT
  agent_context.{
    id,
    timestamp,
    active_concepts,
    active_domains,
    token_budget_remaining
  }
FROM agent_context
WHERE session_id = $session_id
ORDER BY timestamp ASC;
```

**Response**: Timeline showing decisions with context at decision time

---

### Pattern 6: Agent Knowledge Application
**"Which papers/concepts from vault did agent apply in this session?"**

```sql
-- Papers applied (via APPLIED_RESEARCH)
SELECT
  DISTINCT ->APPLIED_RESEARCH->paper.{
    id,
    title,
    date,
    tags
  },
  count(<-APPLIED_RESEARCH<-agent_decision) AS times_cited,
  avg(<-APPLIED_RESEARCH<-agent_decision->confidence_score) AS avg_confidence
FROM agent_decision
WHERE session_id = $session_id
GROUP BY id
ORDER BY times_cited DESC;

-- Concepts applied (via INFLUENCED_BY_CONCEPT)
SELECT
  DISTINCT ->INFLUENCED_BY_CONCEPT->concept.{
    id,
    title,
    tags
  },
  count(<-INFLUENCED_BY_CONCEPT<-agent_decision) AS applications,
  avg(<-INFLUENCED_BY_CONCEPT<-agent_decision->influence_strength) AS avg_strength
FROM agent_decision
WHERE session_id = $session_id
GROUP BY id
ORDER BY applications DESC;
```

---

### Pattern 7: Session Metrics
**"What was the overall success and efficiency of this session?"**

```sql
SELECT
  agent_session.{
    id,
    model_used,
    start_time,
    end_time,
    total_tokens,
    cost_usd,
    status
  },
  count(<-RELATES_TO_SESSION<-agent_decision) AS total_decisions,
  count(<-RELATES_TO_SESSION<-agent_decision->APPLIED_RESEARCH) AS research_citations,
  avg(<-RELATES_TO_SESSION<-agent_decision->confidence_score) AS avg_confidence,
  count(<-RELATES_TO_SESSION<-agent_outcome) AS outcomes,
  <-RELATES_TO_SESSION<-agent_outcome.{
    outcome_type,
    metrics
  } AS results
FROM agent_session
WHERE id = $session_id;
```

**Computed Metrics**:
```python
session_metrics = {
  "duration_minutes": (end_time - start_time).total_seconds() / 60,
  "token_efficiency": total_decisions / total_tokens,
  "research_alignment": research_citations / total_decisions,
  "decision_confidence": avg_confidence,
  "outcomes": outcomes,
  "cost_per_decision": cost_usd / total_decisions
}
```

---

## Common Query Scenarios

### Scenario A: Decision Review (Post-Implementation)
**Goal**: Validate that architectural decision D001 was sound

**Steps**:
1. Query research lineage (Pattern 1) → see papers that influenced it
2. Query misalignment (Pattern 3) → check for contradictions
3. Query lesson validation (Pattern 2) → verify it aligns with vault lessons
4. Query decision cascade (Pattern 4) → understand ripple effects
5. Query session metrics (Pattern 7) → assess overall decision quality

### Scenario B: Agent Learning (Retrospective)
**Goal**: Extract learnings from agent session S001

**Steps**:
1. Query context timeline (Pattern 5) → understand agent's thinking over time
2. Query knowledge application (Pattern 6) → what papers/concepts did agent use
3. Query lesson validation (Pattern 2) → what did agent validate
4. Query misalignment (Pattern 3) → where did agent contradict research
5. Synthesize into lesson note for vault

### Scenario C: Research Alignment Check
**Goal**: Measure how research-driven agent decisions are

**Metric**:
```sql
SELECT
  avg(count(->APPLIED_RESEARCH) / count(*)) AS avg_papers_per_decision,
  count(<-APPLIES_RESEARCH<-agent_decision) / 84.0 AS vault_coverage
FROM agent_decision
WHERE session_id = $session_id;
```

**Interpretation**:
- High avg_papers_per_decision → research-heavy decisions
- High vault_coverage → vault papers are actively used
- Low both → agent making intuitive/pattern-based decisions

---

## Indexing Strategy

For efficient queries, create indexes on:

```sql
-- Temporal queries (decision cascade, timeline)
DEFINE INDEX idx_decision_timestamp ON agent_decision FIELDS timestamp;
DEFINE INDEX idx_decision_session ON agent_decision FIELDS session_id;

-- Relationship queries (papers, concepts, patterns)
DEFINE INDEX idx_decision_confidence ON agent_decision FIELDS confidence_score;

-- Lesson validation queries
DEFINE INDEX idx_outcome_session ON agent_outcome FIELDS session_id;

-- Text search (reasoning, chain of thought)
DEFINE FULL TEXT SEARCH fts_decision_reasoning ON agent_decision FIELDS reasoning;
DEFINE FULL TEXT SEARCH fts_reasoning_cot ON agent_reasoning FIELDS chain_of_thought;

-- Composite indexes for common WHERE clauses
DEFINE INDEX idx_decision_session_type ON agent_decision
  FIELDS session_id, decision_type;
```

---

## Performance Tips

1. **Use RELATIONSHIP queries** for traversal (faster than multiple SELECTs)
2. **Add LIMIT** for large result sets
3. **GROUP BY** to aggregate metrics before returning
4. **CACHE** dimension snapshots (don't recompute on every query)
5. **BATCH** updates of research relevance scores (not per-decision)

---

## Related

**Patterns**: [[surrealdb-agent-context-schema]]

**Decisions**: [[2026-02-11-surrealdb-agent-context-schema-design]]

**Tools**: `record_decision()`, `record_reasoning()`, `record_outcome()` (in Cloud Vault MCP)

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-14-track-a-sign-off-approved]]
- [[2026-02-13-phase-2-track-a-complete]]
- [[2026-02-14-phase-6c-semantic-contradiction-detection-complete]]
- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
