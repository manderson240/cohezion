---
title: "Phase 1 Query Templates & Common Scenarios"
date: 2026-02-11
status: completed
tags: [phase1, queries, templates, scenarios, documentation]
aspect: thinker
neural:
  activation: 0.91
  stage: mature
  synapse_in: 3
  synapse_out: 11
---

# Phase 1 Query Templates & Common Scenarios

Ready-to-use SurrealQL queries for common agent context analysis tasks, with real-world scenarios and troubleshooting.

---

## Query Template 1: Research Lineage

### Purpose
Answer: **"Which papers influenced this decision?"**

### Query
```sql
SELECT
  agent_decision.{
    id,
    decision_type,
    reasoning,
    confidence_score,
    timestamp
  },
  ->decision_applied_research->paper.{
    id,
    title,
    date,
    tags,
    file_path
  } AS papers,
  ->decision_applied_research.{
    relevance_score,
    applied_at
  } AS application
FROM agent_decision
WHERE session_id = $session_id
ORDER BY ->decision_applied_research.relevance_score DESC;
```

### Parameters
- `$session_id`: Session ID from `track_session()` (e.g., "session:2026-02-11-xxx")

### Expected Output
```json
[
  {
    "id": "decision:2026-02-11-xxx-001",
    "decision_type": "architecture",
    "reasoning": "Use SurrealDB for native graph support...",
    "confidence_score": 0.95,
    "timestamp": "2026-02-11T15:30:00Z",
    "papers": [
      {
        "id": "paper:2023-surrealdb-benchmarks",
        "title": "SurrealDB: A Multi-Model Database Engine",
        "date": "2023-06-15",
        "tags": ["database", "surrealdb", "performance"],
        "file_path": "/papers/2023-surrealdb-benchmarks.md"
      },
      {
        "id": "paper:2024-graph-comparison",
        "title": "Comparing Graph Databases",
        "date": "2024-01-10",
        "tags": ["database", "graph"]
      }
    ],
    "application": [
      {
        "relevance_score": 0.95,
        "applied_at": "2026-02-11T15:30:00Z"
      },
      {
        "relevance_score": 0.85,
        "applied_at": "2026-02-11T15:30:00Z"
      }
    ]
  }
]
```

### Interpretation
- **Papers ranked by relevance_score** (highest first)
- Each decision shows which papers influenced it
- Relevance scores indicate how critical the paper was to the decision

### Common Variations

**Find papers for a specific decision type**:
```sql
SELECT ... FROM agent_decision
WHERE session_id = $session_id
  AND decision_type = "architecture"
ORDER BY ->decision_applied_research.relevance_score DESC;
```

**Find decisions with high confidence AND strong research**:
```sql
SELECT ... FROM agent_decision
WHERE session_id = $session_id
  AND confidence_score >= 0.8
  AND count(->decision_applied_research) >= 2
ORDER BY confidence_score DESC;
```

**Get papers by relevance across all decisions in session**:
```sql
SELECT DISTINCT
  ->decision_applied_research->paper.{id, title, date},
  avg(->decision_applied_research.relevance_score) AS avg_relevance
FROM agent_decision
WHERE session_id = $session_id
GROUP BY id
ORDER BY avg_relevance DESC;
```

---

## Query Template 2: Lesson Validation

### Purpose
Answer: **"What lessons were confirmed by this agent's work?"**

### Query
```sql
SELECT
  agent_outcome.{
    id,
    outcome_type,
    metrics,
    timestamp
  },
  ->outcome_validates_lesson->lesson.{
    id,
    title,
    severity,
    primary_source,
    tags
  } AS lessons_validated,
  ->outcome_validates_lesson.{
    alignment_score,
    validation_type
  } AS validation
FROM agent_outcome
WHERE session_id = $session_id
ORDER BY ->outcome_validates_lesson.alignment_score DESC;
```

### Parameters
- `$session_id`: Session ID (e.g., "session:2026-02-11-xxx")

### Expected Output
```json
[
  {
    "id": "outcome:2026-02-11-xxx-001",
    "outcome_type": "success",
    "metrics": {
      "session_duration_min": 45,
      "token_efficiency_ratio": 3.2,
      "decisions_made": 5,
      "decisions_validated": 5
    },
    "timestamp": "2026-02-11T16:30:00Z",
    "lessons_validated": [
      {
        "id": "lesson:token-efficiency-haiku",
        "title": "Token Efficiency with Haiku Model",
        "severity": "CRITICAL",
        "primary_source": "decision:kyutai-phase1",
        "tags": ["ai-models", "token-efficiency", "cost-optimization"]
      },
      {
        "id": "lesson:research-lineage-critical",
        "title": "Research Lineage Critical for Decision Quality",
        "severity": "HIGH",
        "primary_source": "pattern:surrealdb-agent-context-schema",
        "tags": ["decision-making", "research", "quality"]
      }
    ],
    "validation": [
      {
        "alignment_score": 0.98,
        "validation_type": "confirms"
      },
      {
        "alignment_score": 0.92,
        "validation_type": "confirms"
      }
    ]
  }
]
```

### Interpretation
- **Lessons ranked by alignment_score** (highest = strongest confirmation)
- Validation_type shows how lesson was validated ("confirms", "refutes", "refines")
- Metrics show concrete outcomes that validate each lesson

### Common Variations

**Find high-severity lessons validated**:
```sql
SELECT ... FROM agent_outcome
WHERE session_id = $session_id
AND ->outcome_validates_lesson->lesson.severity IN ["CRITICAL", "HIGH"]
ORDER BY ->outcome_validates_lesson.alignment_score DESC;
```

**Find lessons that were refuted or limited**:
```sql
SELECT ... FROM agent_outcome
WHERE session_id = $session_id
AND ->outcome_validates_lesson.validation_type IN ["refutes", "limits"]
ORDER BY timestamp DESC;
```

**Get metrics of sessions validating a specific lesson**:
```sql
SELECT
  agent_session.{id, agent_id, total_tokens, cost_usd},
  ->OUTCOMES->lesson.title AS validated_lesson
FROM agent_session
WHERE ->outcome->lesson.id = "lesson:token-efficiency-haiku"
ORDER BY total_tokens ASC;
```

---

## Query Template 3: Session Metrics

### Purpose
Answer: **"What was the overall success and efficiency of this session?"**

### Query
```sql
SELECT
  agent_session.{
    id,
    agent_id,
    model_used,
    start_time,
    end_time,
    total_tokens,
    cost_usd,
    status
  },
  count(<-agent_session<-agent_decision) AS total_decisions,
  avg(<-agent_session<-agent_decision->confidence_score) AS avg_decision_confidence,
  count(
    <-agent_session<-agent_decision
    ->decision_applied_research->paper
  ) AS total_papers_cited,
  count(<-agent_session<-agent_outcome) AS outcomes,
  <-agent_session<-agent_outcome.metrics AS outcome_metrics
FROM agent_session
WHERE id = $session_id;
```

### Parameters
- `$session_id`: Full session ID (e.g., "agent_session:session:2026-02-11-xxx")

### Expected Output
```json
{
  "id": "agent_session:session:2026-02-11-xxx",
  "agent_id": "data-graph-specialist",
  "model_used": "claude-haiku-4-5",
  "start_time": "2026-02-11T15:00:00Z",
  "end_time": "2026-02-11T16:30:00Z",
  "total_tokens": 42000,
  "cost_usd": 0.21,
  "status": "completed",
  "total_decisions": 5,
  "avg_decision_confidence": 0.845,
  "total_papers_cited": 8,
  "outcomes": 1,
  "outcome_metrics": {
    "session_duration_min": 90,
    "token_efficiency_ratio": 3.2,
    "decisions_made": 5,
    "decisions_validated": 5
  }
}
```

### Interpretation
- **Session Duration**: Time from start to end
- **Token Efficiency Ratio**: Output value per token (higher = better)
- **Papers Cited**: Total research lineage across all decisions
- **Decision Confidence**: Average confidence of all decisions (0-1)
- **Outcome Metrics**: Final measurements from record_outcome()

---

## Common Scenario 1: "Validate Decision is Research-Backed"

**Scenario**: Manager asks, "Is decision D123 actually backed by research, or just intuition?"

**Steps**:

1. **Get the decision with papers**:
```sql
SELECT
  id,
  reasoning,
  confidence_score,
  ->decision_applied_research->paper.{title, date} AS cited_papers,
  ->decision_applied_research.relevance_score
FROM agent_decision
WHERE id = "decision:d123"
ORDER BY relevance_score DESC;
```

2. **Interpret results**:
   - ✅ If 2+ papers cited with relevance_score > 0.8 → **Well-researched**
   - ⚠️ If 1-2 papers with relevance_score 0.5-0.8 → **Moderately researched**
   - ❌ If 0 papers cited → **Intuition-based** (not research-backed)

3. **Follow-up**: If inadequately researched, use the `papers` list to do additional research.

---

## Common Scenario 2: "What Lessons Did We Learn This Sprint?"

**Scenario**: End of sprint review. Want to capture learnings and validate lessons.

**Steps**:

1. **Get all outcomes from sprint sessions**:
```sql
SELECT
  agent_session.agent_id,
  ->outcome->lesson.{id, title, severity},
  ->outcome.metrics
FROM agent_session
WHERE start_time >= "2026-02-10T00:00:00Z"
  AND start_time <= "2026-02-12T23:59:59Z"
ORDER BY agent_session.start_time DESC;
```

2. **Group by severity**:
```sql
SELECT
  ->outcome->lesson.severity,
  ->outcome->lesson.{id, title} AS lessons,
  count(*) AS validation_count
FROM agent_outcome
WHERE session_id->start_time >= "2026-02-10T00:00:00Z"
GROUP BY severity
ORDER BY severity DESC;
```

3. **Create summary**:
   - List CRITICAL lessons first (highest priority)
   - Show how many times each was validated
   - Link to primary sources

---

## Common Scenario 3: "Which AI Model is Most Efficient?"

**Scenario**: Comparing costs between Haiku, Sonnet, GPT-4. Which should we use?

**Steps**:

1. **Get metrics by model**:
```sql
SELECT
  agent_session.model_used,
  count(*) AS sessions_run,
  avg(agent_session.total_tokens) AS avg_tokens,
  avg(agent_session.cost_usd) AS avg_cost,
  avg(<-agent_session<-agent_outcome.metrics.token_efficiency_ratio) AS avg_efficiency
FROM agent_session
WHERE status = "completed"
GROUP BY model_used
ORDER BY avg_efficiency DESC;
```

2. **Calculate efficiency ratio**: output_value / total_tokens
   - Haiku: typically 3.0-3.5
   - Sonnet: typically 1.2-1.8
   - GPT-4: varies

3. **Decision**: Higher efficiency ratio = better choice for cost optimization

---

## Common Scenario 4: "Did This Decision Enable Other Decisions?"

**Scenario**: Decision D1 (architectural) was made, then D2, D3, D4 followed. Did D1 enable them?

**Note**: This requires RELATES_TO_DECISION edge, which is Phase 2+.

**Placeholder for Phase 2**:
```sql
-- Phase 2: Decision cascade analysis
SELECT
  agent_decision.id,
  ->RELATES_TO_DECISION->agent_decision.{id, decision_type, timestamp}
FROM agent_decision
WHERE id = "decision:d1"
```

---

## Troubleshooting Guide

### Problem: "Query returned no results for session_id"

**Check**:
1. Session ID format correct: `session:xxx` or `agent_session:session:xxx`?
2. Session actually created: `SELECT * FROM agent_session WHERE id = $session_id`
3. Any decisions in session: `SELECT count() FROM agent_decision WHERE session_id = $session_id`

**Debug**:
```sql
-- List all sessions
SELECT id, agent_id, status FROM agent_session LIMIT 10;

-- List all decisions
SELECT id, session_id FROM agent_decision LIMIT 10;
```

### Problem: "Papers not showing in research lineage query"

**Check**:
1. Papers exist in vault: `SELECT * FROM paper WHERE id IN ["paper:xxx"]`
2. Decision-paper relationships created: `SELECT * FROM decision_applied_research`
3. Query syntax correct: `->decision_applied_research->paper`

**Debug**:
```sql
-- Check relationships from specific decision
SELECT * FROM decision_applied_research
WHERE from = "agent_decision:d123";

-- Verify papers linked
SELECT ->decision_applied_research->paper.id
FROM agent_decision
WHERE id = "agent_decision:d123";
```

### Problem: "Alignment scores seem wrong or missing"

**Check**:
1. record_outcome() was called with lessons
2. Outcome-lesson relationships created: `SELECT * FROM outcome_validates_lesson`
3. Alignment scores populated: `SELECT alignment_score FROM outcome_validates_lesson`

**Fix**: Alignment scores are auto-computed as 0.85 by default. To refine:
- In Phase 2, implement `record_decision_validation()` tool
- Manually update alignment_score based on actual validation

### Problem: "Performance slow on large sessions"

**Optimize**:
```sql
-- Add LIMIT to reduce result size
SELECT ... FROM agent_decision
WHERE session_id = $session_id
LIMIT 50;

-- Use aggregations instead of full results
SELECT
  count() AS total_decisions,
  avg(confidence_score) AS avg_confidence
FROM agent_decision
WHERE session_id = $session_id;
```

---

## Query Cheat Sheet

| Question | Query |
|----------|-------|
| All decisions in session | `SELECT * FROM agent_decision WHERE session_id = $id` |
| Decisions by type | `SELECT * FROM agent_decision WHERE decision_type = "architecture"` |
| High-confidence decisions | `SELECT * FROM agent_decision WHERE confidence_score >= 0.85` |
| Papers cited | `SELECT count(DISTINCT ->decision_applied_research->paper.id)` |
| Session cost | `SELECT total_tokens, cost_usd FROM agent_session WHERE id = $id` |
| Lessons validated | `SELECT ->outcome_validates_lesson->lesson.title FROM agent_outcome` |
| Decision timeline | `SELECT id, timestamp, decision_type FROM agent_decision ORDER BY timestamp` |

---

## Related Documents

- **Tool Reference**: `patterns/phase1-mcp-tool-reference.md`
- **Visual Guide**: `patterns/surrealdb-agent-context-visual-guide.md`
- **Quick Reference**: `patterns/surrealdb-agent-context-quick-reference.md`
- **Schema**: `patterns/surrealdb-agent-context-schema.md`

---

**Status**: Phase 1 Documentation Complete ✅
**Task**: Task #10 (Step 5)

[[phase-1-implementation]], [[Queries]], [[Scenarios]]

## Related Concepts

- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-11-phase1-execution-status]]
- [[2026-02-11-phase1-step1-schema-complete]]
- [[surrealdb-agent-context-phase1-step3-query-testing]]
- [[phase1-production-validation-runbook]]
- [[phase1-mcp-tool-reference]]
- [[bmad-scale-adaptive-documentation]]
- [[surrealdb-agent-context-phase1-step3-execution-plan]]
