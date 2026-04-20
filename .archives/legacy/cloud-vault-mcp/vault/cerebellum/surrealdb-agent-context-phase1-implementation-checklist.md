---
title: "SurrealDB Agent Context - Phase 1 Implementation Checklist"
date: 2026-02-11
status: proposed
tags: [pattern, implementation-checklist, surrealdb, agent-context]
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 5
  synapse_out: 12
---

# Phase 1 Implementation Checklist

Implementation roadmap for Phase 1: Research Lineage (2-3 days)

**Goal**: Enable "Which papers influenced this decision?" query across the knowledge graph.

---

## Prerequisite Tasks

- [ ] SurrealDB instance running at http://localhost:8000
- [ ] Authentication credentials configured (user/pass in .env)
- [ ] Cloud Vault MCP server at /home/mike-anderson/dev/cohezion/cloud-vault-mcp/ available
- [ ] Vault has 84 papers + 21 concepts already imported in SurrealDB

---

## Step 1: Schema Definition (2 hours)

### 1.1 Create Table Definitions

```sql
-- In SurrealDB console or via API
DEFINE TABLE agent_session SCHEMAFULL;
DEFINE TABLE agent_decision SCHEMAFULL;
DEFINE TABLE agent_reasoning SCHEMAFULL;
DEFINE TABLE agent_outcome SCHEMAFULL;

DEFINE TABLE agent_decision_relates TYPE RELATION FROM agent_decision TO agent_decision;
DEFINE TABLE decision_applied_research TYPE RELATION FROM agent_decision TO paper;
DEFINE TABLE outcome_validates_lesson TYPE RELATION FROM agent_outcome TO lesson;
```

- [ ] Create agent_session table with fields
- [ ] Create agent_decision table with fields
- [ ] Create agent_reasoning table with fields
- [ ] Create agent_outcome table with fields
- [ ] Create relationship tables (3 needed for Phase 1)

### 1.2 Create Indexes

```sql
DEFINE INDEX idx_decision_session ON agent_decision FIELDS session_id;
DEFINE INDEX idx_decision_timestamp ON agent_decision FIELDS timestamp;
DEFINE INDEX idx_decision_confidence ON agent_decision FIELDS confidence_score;
DEFINE INDEX idx_outcome_session ON agent_outcome FIELDS session_id;
DEFINE FULL TEXT SEARCH fts_reasoning ON agent_reasoning FIELDS reasoning;
```

- [ ] Session lookup index
- [ ] Temporal ordering index
- [ ] Confidence scoring index
- [ ] Full-text search index

---

## Step 2: MCP Tools Implementation (4 hours)

### 2.1 track_session Tool

**File**: `cloud-vault-mcp/src/mcp_server/tools/agent_context.py` (new)

```python
@mcp.tool()
def track_session(
    agent_id: str,
    goals: list[str],
    model_used: str = "claude-haiku-4-5",
    phase: str = "research"
) -> str:
    """Create new agent session.

    Returns: session_id for use in subsequent operations
    """
    db = Surreal()
    session_id = f"session:{uuid.uuid4()}"

    db.create(f"agent_session:{session_id}", {
        "agent_id": agent_id,
        "start_time": datetime.now().isoformat(),
        "model_used": model_used,
        "phase": phase,
        "goals": goals,
        "status": "in_progress",
        "total_tokens": 0,
        "cost_usd": 0.0
    })

    return session_id
```

- [ ] Implement track_session() MCP tool
- [ ] Add to server.py tool registry
- [ ] Test with sample agent_id + goals

### 2.2 record_decision Tool

```python
@mcp.tool()
def record_decision(
    session_id: str,
    decision_type: str,  # "architecture", "feature", "refactor", "bugfix", "data"
    reasoning: str,
    papers_applied: list[str],  # Paper IDs from vault
    confidence_score: float = 0.7
) -> str:
    """Record architectural decision with research lineage.

    Creates:
    - agent_decision node
    - APPLIED_RESEARCH edges to cited papers

    Returns: decision_id for later linking
    """
    db = Surreal()
    decision_id = f"decision:{uuid.uuid4()}"

    # Create decision
    db.create(f"agent_decision:{decision_id}", {
        "session_id": session_id,
        "decision_type": decision_type,
        "timestamp": datetime.now().isoformat(),
        "reasoning": reasoning,
        "confidence_score": confidence_score,
        "validation_status": "pending",
        "implementation_status": "proposed"
    })

    # Link to papers
    for paper_id in papers_applied:
        db.relate(
            f"agent_decision:{decision_id}",
            "decision_applied_research",
            f"paper:{paper_id}",
            {
                "relevance_score": 0.8,  # Can be refined
                "applied_at": datetime.now().isoformat()
            }
        )

    # Update session token count
    db.update(session_id, {
        "total_tokens": db.select(session_id)[0].total_tokens + 500  # Estimated
    })

    return decision_id
```

- [ ] Implement record_decision() MCP tool
- [ ] Link to papers in SurrealDB
- [ ] Add to server.py tool registry
- [ ] Test with sample decision + papers

### 2.3 record_outcome Tool

```python
@mcp.tool()
def record_outcome(
    session_id: str,
    outcome_type: str,  # "success", "partial", "failed"
    lessons_learned: list[str],  # Lesson IDs from vault
    metrics: dict = None
) -> str:
    """Record session outcome and lessons.

    Creates:
    - agent_outcome node
    - VALIDATES_LESSON edges to vault lessons

    Returns: outcome_id
    """
    db = Surreal()
    outcome_id = f"outcome:{uuid.uuid4()}"

    # Create outcome
    db.create(f"agent_outcome:{outcome_id}", {
        "session_id": session_id,
        "outcome_type": outcome_type,
        "timestamp": datetime.now().isoformat(),
        "lessons_learned": lessons_learned,
        "metrics": metrics or {},
        "validated_by": None  # Can be set later
    })

    # Link to lessons
    for lesson_id in lessons_learned:
        db.relate(
            f"agent_outcome:{outcome_id}",
            "outcome_validates_lesson",
            f"lesson:{lesson_id}",
            {
                "alignment_score": 0.85,  # Can be refined by LLM
                "validation_type": "confirms"
            }
        )

    # Close session
    db.update(session_id, {
        "end_time": datetime.now().isoformat(),
        "status": "completed",
        "outcome_summary": f"{outcome_type.upper()} - {len(lessons_learned)} lessons validated"
    })

    return outcome_id
```

- [ ] Implement record_outcome() MCP tool
- [ ] Link to lessons in SurrealDB
- [ ] Close session in database
- [ ] Add to server.py tool registry
- [ ] Test with sample outcome

---

## Step 3: Query Testing (3 hours)

### 3.1 Research Lineage Query

```sql
-- Query: Which papers influenced this decision?
SELECT
  agent_decision.{id, decision_type, reasoning, confidence_score, timestamp},
  ->decision_applied_research->paper.{title, date, tags, file_path},
  ->decision_applied_research.{relevance_score, applied_at}
FROM agent_decision
WHERE session_id = $session_id
ORDER BY ->decision_applied_research.relevance_score DESC;
```

- [ ] Test query in SurrealDB console
- [ ] Verify result structure matches expected
- [ ] Test with multiple decisions in session
- [ ] Document result format

### 3.2 Lesson Validation Query

```sql
-- Query: What lessons did agent's work validate?
SELECT
  agent_outcome.{id, outcome_type, metrics, timestamp},
  ->outcome_validates_lesson->lesson.{id, title, severity, primary_source},
  ->outcome_validates_lesson.{alignment_score, validation_type}
FROM agent_outcome
WHERE session_id = $session_id
ORDER BY ->outcome_validates_lesson.alignment_score DESC;
```

- [ ] Test lesson validation query
- [ ] Verify lesson linking works
- [ ] Test with multiple outcomes
- [ ] Document result format

### 3.3 Session Metrics Query

```sql
-- Query: Overall session metrics
SELECT
  agent_session.{id, model_used, start_time, end_time, total_tokens, cost_usd, status},
  count(<-agent_session<-agent_decision) AS total_decisions,
  count(
    <-agent_session<-agent_decision
    ->decision_applied_research->paper
  ) AS research_citations,
  avg(<-agent_session<-agent_decision->confidence_score) AS avg_confidence
FROM agent_session
WHERE id = $session_id;
```

- [ ] Test session metrics query
- [ ] Verify aggregation works
- [ ] Test with complete session
- [ ] Document metrics structure

---

## Step 4: Integration Testing (3 hours)

### 4.1 Create Test Session

- [ ] Create test session with `track_session()`
  - `agent_id`: "test-agent"
  - `goals`: ["test-research-lineage", "validate-schema"]
  - Result: `session:test-001`

### 4.2 Record Test Decisions

- [ ] Create decision D1 with papers P1, P2
  - `decision_type`: "architecture"
  - `papers_applied`: [2-3 paper IDs from vault]
  - Result: `decision:test-001`

- [ ] Create decision D2 with paper P3
  - `decision_type`: "feature"
  - `papers_applied`: [1 paper ID from vault]
  - Result: `decision:test-002`

### 4.3 Record Test Outcome

- [ ] Create outcome with lessons L1, L2
  - `outcome_type`: "success"
  - `lessons_learned`: [2 lesson IDs from vault]
  - Result: `outcome:test-001`

### 4.4 Verify Queries Work

- [ ] Query research lineage → Should return D1 with P1, P2 ranked
- [ ] Query lesson validation → Should return L1, L2 with alignment scores
- [ ] Query session metrics → Should show 2 decisions, 3 papers, avg confidence

---

## Step 5: Documentation (2 hours)

### 5.1 Query Templates

- [ ] Document 5 query patterns in reference guide
- [ ] Create example queries with expected outputs
- [ ] Add performance tips for each query

### 5.2 Tool Documentation

- [ ] Document track_session() tool
  - Parameters, return value, example usage

- [ ] Document record_decision() tool
  - Parameters, return value, example usage
  - How to get paper IDs from vault

- [ ] Document record_outcome() tool
  - Parameters, return value, example usage
  - How to get lesson IDs from vault

### 5.3 Troubleshooting Guide

- [ ] What if query returns no results?
- [ ] What if relationship creation fails?
- [ ] How to debug token counting?
- [ ] Common SurrealDB connection issues

---

## Step 6: Validation (1 hour)

### 6.1 Completeness Check

- [ ] All 5 node types defined
- [ ] All 4 relationship types created (for Phase 1)
- [ ] All 3 MCP tools implemented + tested
- [ ] All 3 core queries working + documented
- [ ] All indexes created + performance verified

### 6.2 Production Readiness

- [ ] Error handling for null papers
- [ ] Error handling for missing session
- [ ] Transaction support for consistency
- [ ] Logging for audit trail
- [ ] No secrets in code (use env vars for DB credentials)

### 6.3 Knowledge Transfer

- [ ] All documentation committed to vault
- [ ] MCP tools tested by another team member
- [ ] Queries validated across different sessions
- [ ] Runbook created for troubleshooting

---

## Estimated Timeline

| Task | Estimate | Actual |
|------|----------|--------|
| Step 1: Schema | 2h | |
| Step 2: Tools | 4h | |
| Step 3: Queries | 3h | |
| Step 4: Integration | 3h | |
| Step 5: Docs | 2h | |
| Step 6: Validation | 1h | |
| **TOTAL** | **15h** | |

**2-3 days**: Assuming 5-8 hours/day (accounting for debugging, team communication)

---

## Success Criteria

- [ ] Can create agent_session
- [ ] Can record decision with paper links
- [ ] Can record outcome with lesson validation
- [ ] Query: "Which papers influenced this decision?" returns ranked results
- [ ] Query: "What lessons did agent validate?" returns validated lessons
- [ ] Query: "Overall session metrics?" returns aggregated stats
- [ ] All 3 test queries pass on test session
- [ ] Documentation complete + committed
- [ ] No production data corrupted (tests use isolated session IDs)

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| SurrealDB connection issues | Pre-test connection before starting |
| Paper IDs don't exist | Validate paper IDs before record_decision() |
| Query syntax errors | Test each query in console first |
| Transaction rollback needed | Keep notes on test session IDs for cleanup |
| Token counting inaccuracy | Use estimate for Phase 1, refine in Phase 2 |

---

## Next Steps After Phase 1

Once Phase 1 complete and approved:
- [ ] Phase 2: agent_reasoning + misalignment detection (1 day)
- [ ] Phase 3: agent_context snapshots (1 day)
- [ ] Phase 4: metrics + 12D integration (2 days)

---

## Files Modified/Created

**New Files**:
- `cloud-vault-mcp/src/mcp_server/tools/agent_context.py` (250 lines)
- `cloud-vault-mcp/src/tests/test_agent_context_phase1.py` (300 lines)
- `patterns/surrealdb-agent-context-phase1-runbook.md` (operations guide)

**Modified Files**:
- `cloud-vault-mcp/src/mcp_server/server.py` (add 3 tool registrations)
- `cloud-vault-mcp/.env` (add SurrealDB credentials)
- `decisions/2026-02-11-surrealdb-agent-context-schema-design.md` (update status to "in_progress")

---

## Related Documents

- **Decision**: `decisions/2026-02-11-surrealdb-agent-context-schema-design.md`
- **Schema**: `patterns/surrealdb-agent-context-schema.md`
- **Query Guide**: `patterns/surrealdb-agent-context-visual-guide.md`
- **Quick Reference**: `patterns/surrealdb-agent-context-quick-reference.md`

## Related

- [[surrealdb-agent-context-visual-guide]]
- [[surrealdb-agent-context-quick-reference]]
- [[surrealdb-agent-context-schema]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-14-track-a-sign-off-approved]]
- [[2026-02-13-phase-2-track-a-complete]]
- [[2026-02-14-phase-6c-semantic-contradiction-detection-complete]]
- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
- [[2026-02-12-phase-2-schema-design]]
