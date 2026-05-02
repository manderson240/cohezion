---
title: "Phase 1 Step 3: Query Testing Preparation"
date: 2026-02-11
status: proposed
tags: [phase1, implementation, surrealdb, query-testing]
aspect: thinker
neural:
  activation: 0.88
  stage: mature
  synapse_in: 9
  synapse_out: 11
---

# Phase 1 Step 3: Query Testing Preparation

**Status**: Prepared (ready to execute once Step 2 tools complete)
**Estimated Duration**: 3 hours
**Dependency**: Step 2 (MCP tools) must complete first

---

## Overview

Step 3 validates that all SurrealDB queries work correctly by:
1. Creating test data using Step 2 MCP tools
2. Running 3 core queries on test data
3. Validating results match expectations
4. Documenting query syntax + examples

---

## Prerequisites (from Step 2)

Before starting Step 3, you need:
- ✅ SurrealDB schema deployed (Step 1)
- ✅ MCP tools working: `track_session()`, `record_decision()`, `record_outcome()`
- ✅ Sample data created in SurrealDB (5-10 decisions, 2-3 outcomes)

---

## Section 1: Create Test Data (30 minutes)

### 1.1 Create Test Session

Use MCP tool:
```python
session_id = track_session(
    agent_id="test-agent-phase1",
    goals=["test-research-lineage", "test-lesson-validation"],
    model_used="claude-haiku-4-5",
    phase="research"
)
# Result: session_id = "session:test-001"
```

**Verify in SurrealDB**:
```sql
SELECT * FROM agent_session WHERE agent_id = "test-agent-phase1";
-- Should return 1 record with status="in_progress"
```

### 1.2 Create Test Decisions (with Paper Links)

Use MCP tool 3 times:

**Decision 1: Architecture**
```python
decision_id_1 = record_decision(
    session_id="session:test-001",
    decision_type="architecture",
    reasoning="Use SurrealDB because native graph support enables research lineage tracking",
    papers_applied=[
        "paper:2023-surrealdb-benchmarks",  # Must exist in vault
        "paper:2024-graph-database-comparison"
    ],
    confidence_score=0.95
)
# Result: decision_id_1 = "decision:test-001"
```

**Decision 2: Feature**
```python
decision_id_2 = record_decision(
    session_id="session:test-001",
    decision_type="feature",
    reasoning="Add agent_context snapshots to track evolving goals during session",
    papers_applied=[
        "paper:2023-agent-context-management"
    ],
    confidence_score=0.85
)
```

**Decision 3: Refactor**
```python
decision_id_3 = record_decision(
    session_id="session:test-001",
    decision_type="refactor",
    reasoning="Simplify decision-reasoning relationship to improve query performance",
    papers_applied=[
        "paper:2024-surrealdb-optimization"
    ],
    confidence_score=0.72
)
```

**Verify in SurrealDB**:
```sql
SELECT count() FROM agent_decision WHERE session_id = "session:test-001";
-- Should return 3

SELECT * FROM decision_applied_research;
-- Should return 6 records (3 decisions × 2-1 papers each, approximately)
```

### 1.3 Create Test Outcome (with Lesson Links)

Use MCP tool:
```python
outcome_id = record_outcome(
    session_id="session:test-001",
    outcome_type="success",
    lessons_learned=[
        "lesson:token-efficiency-haiku",  # Must exist in vault
        "lesson:research-lineage-critical"
    ],
    metrics={
        "session_duration_min": 45,
        "token_efficiency_ratio": 3.2,
        "decisions_validated": 3
    }
)
# Result: outcome_id = "outcome:test-001"
```

**Verify in SurrealDB**:
```sql
SELECT * FROM agent_outcome WHERE session_id = "session:test-001";
-- Should return 1 record

SELECT * FROM outcome_validates_lesson;
-- Should return 2 records (1 outcome × 2 lessons)
```

---

## Section 2: Test Core Queries (2 hours)

### 2.1 Query 1: Research Lineage

**Purpose**: Verify decisions are linked to papers that influenced them

**Query**:
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
WHERE session_id = "session:test-001"
ORDER BY ->decision_applied_research.relevance_score DESC;
```

**Expected Result**:
```json
[
  {
    "id": "decision:test-001",
    "decision_type": "architecture",
    "reasoning": "Use SurrealDB because...",
    "confidence_score": 0.95,
    "papers": [
      {
        "id": "paper:2023-surrealdb-benchmarks",
        "title": "SurrealDB: A Multi-Model Database...",
        "date": "2023-06-15",
        "relevance_score": 0.95
      },
      {
        "id": "paper:2024-graph-database-comparison",
        "title": "Comparing Graph Databases",
        "date": "2024-01-10",
        "relevance_score": 0.85
      }
    ]
  }
  // ... more decisions
]
```

**Validation**:
- [ ] All 3 decisions returned
- [ ] Papers ranked by relevance_score (high to low)
- [ ] Reasoning field contains explanation
- [ ] Confidence_score between 0-1

**✅ Pass Criteria**: All 3 decisions returned with papers ranked by relevance

### 2.2 Query 2: Lesson Validation

**Purpose**: Verify outcomes are linked to lessons they validate

**Query**:
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
WHERE session_id = "session:test-001"
ORDER BY ->outcome_validates_lesson.alignment_score DESC;
```

**Expected Result**:
```json
[
  {
    "id": "outcome:test-001",
    "outcome_type": "success",
    "metrics": {
      "session_duration_min": 45,
      "token_efficiency_ratio": 3.2,
      "decisions_validated": 3
    },
    "lessons_validated": [
      {
        "id": "lesson:token-efficiency-haiku",
        "title": "Token Efficiency with Haiku Model",
        "severity": "CRITICAL",
        "primary_source": "decision:kyutai-phase1",
        "validation_type": "confirms",
        "alignment_score": 0.98
      },
      {
        "id": "lesson:research-lineage-critical",
        "title": "Research Lineage Critical for Decision Quality",
        "severity": "HIGH",
        "primary_source": "pattern:surrealdb-agent-context-schema",
        "validation_type": "confirms",
        "alignment_score": 0.92
      }
    ]
  }
]
```

**Validation**:
- [ ] Outcome record returned
- [ ] Lessons ranked by alignment_score
- [ ] Validation_type field populated
- [ ] Metrics object preserved

**✅ Pass Criteria**: 1 outcome returned with 2 lessons ranked by alignment

### 2.3 Query 3: Session Metrics

**Purpose**: Verify aggregated session statistics

**Query**:
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
  avg(<-agent_session<-agent_decision->confidence_score) AS avg_confidence,
  count(
    <-agent_session<-agent_decision
    ->decision_applied_research->paper
  ) AS total_papers_cited
FROM agent_session
WHERE id = "session:test-001";
```

**Expected Result**:
```json
{
  "id": "session:test-001",
  "agent_id": "test-agent-phase1",
  "model_used": "claude-haiku-4-5",
  "start_time": "2026-02-11T15:00:00Z",
  "end_time": "2026-02-11T15:45:00Z",
  "total_tokens": 1500,
  "cost_usd": 0.075,
  "status": "completed",
  "total_decisions": 3,
  "avg_confidence": 0.84,  // (0.95 + 0.85 + 0.72) / 3
  "total_papers_cited": 4   // 2 + 1 + 1
}
```

**Validation**:
- [ ] Session record returned
- [ ] total_decisions = 3
- [ ] avg_confidence between 0.8-0.9
- [ ] total_papers_cited >= 3
- [ ] Status field set correctly

**✅ Pass Criteria**: Aggregations match expected counts

---

## Section 3: Debug Queries (if tests fail)

### 3.1 Verify Table Data Exists

```sql
-- Check session count
SELECT count() FROM agent_session;

-- Check decision count
SELECT count() FROM agent_decision;

-- Check outcome count
SELECT count() FROM agent_outcome;

-- Check relationship counts
SELECT count() FROM decision_applied_research;
SELECT count() FROM outcome_validates_lesson;
```

### 3.2 Inspect Individual Records

```sql
-- View specific session
SELECT * FROM agent_session WHERE id = "session:test-001";

-- View decisions in session
SELECT * FROM agent_decision WHERE session_id = "session:test-001";

-- View relationships from decision
SELECT * FROM decision_applied_research
  WHERE from = "agent_decision:test-001";

-- View outcome
SELECT * FROM agent_outcome WHERE session_id = "session:test-001";
```

### 3.3 Test Relationship Traversal

```sql
-- Can we traverse from decision to paper?
SELECT ->decision_applied_research->paper.title
FROM agent_decision
WHERE id = "agent_decision:test-001";

-- Can we traverse from outcome to lesson?
SELECT ->outcome_validates_lesson->lesson.title
FROM agent_outcome
WHERE id = "agent_outcome:test-001";
```

---

## Section 4: Documentation (30 minutes)

Once queries pass:

### 4.1 Query Template Documentation

Create reference with:
- [ ] Query SQL
- [ ] Expected output format (JSON schema)
- [ ] Result interpretation
- [ ] Performance notes

### 4.2 Example Data Documentation

Create examples showing:
- [ ] Typical research lineage results
- [ ] Typical lesson validation results
- [ ] Typical metrics aggregations

### 4.3 Troubleshooting Guide

Document:
- [ ] Common query failures
- [ ] How to debug relationship issues
- [ ] How to verify data integrity

---

## Success Criteria

All of the following must pass:

- [ ] Test data created successfully (3+ decisions, 1+ outcome)
- [ ] Query 1 (Research Lineage) returns all decisions with papers
- [ ] Query 2 (Lesson Validation) returns outcome with lessons
- [ ] Query 3 (Session Metrics) returns correct aggregations
- [ ] All query results match expected JSON structures
- [ ] Query documentation completed
- [ ] No production data touched (test data only)

---

## Timeline

| Task | Estimate | Actual |
|------|----------|--------|
| 1.1-1.3: Create test data | 30 min | |
| 2.1: Research lineage query | 30 min | |
| 2.2: Lesson validation query | 30 min | |
| 2.3: Session metrics query | 30 min | |
| 3: Debug queries (if needed) | 15 min | |
| 4: Documentation | 30 min | |
| **TOTAL** | **3h** | |

---

## Files to Create/Update

**New**:
- `patterns/phase1-step3-query-results.md` — Query outputs + examples

**Update**:
- `patterns/surrealdb-agent-context-visual-guide.md` — Add test results
- `decisions/2026-02-11-phase1-step1-schema-complete.md` — Add Step 3 completion

---

## Notes

- Test data will be in SurrealDB (not production)
- Use session_id starting with "test-" to identify test data
- Can clean up test data after validation if needed
- Results will feed into Step 5 documentation

---

**Status**: Ready to execute once Step 2 completes

**Assigned**: data-graph-specialist
**Dependency**: integration-engineer Step 2 completion

[[phase-1-implementation]], [[query-testing]], [[surrealdb]]

## Related Concepts

- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-14-track-a-sign-off-approved]]
- [[2026-02-13-phase-2-track-a-complete]]
- [[2026-02-14-phase-6c-semantic-contradiction-detection-complete]]
- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-11-phase1-execution-status]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
