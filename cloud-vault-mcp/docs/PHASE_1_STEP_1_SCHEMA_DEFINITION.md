# Phase 1 Step 1: SurrealDB Agent Context Schema Definition

**Status**: ✅ COMPLETE (2026-02-11)
**Time**: 2 hours
**Deliverables**: 5 node tables, 8 edge tables, initialization module

---

## Overview

Defined a 5-node graph database schema for capturing agent decision-making lifecycle:

```
agent_session (root)
    ↓ session_decision
agent_decision (what)
    ↓ decision_action
agent_action (how)
    ↓ action_outcome
agent_outcome (result)
    ↓ outcome_lesson
lesson_validation (learning)
```

**Purpose**: Enable research lineage queries (papers → decisions → lessons) and cost/outcome analysis.

---

## Schema Components

### Node Tables (5)

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `agent_session` | Root execution context | agent_name, started_at, status, decision_id, context |
| `agent_decision` | Single decision point | session_id, title, chosen_option, decision_reasoning, tags |
| `agent_action` | Concrete action/tool | decision_id, tool_name, sequence_order, executed_at, cost_usd |
| `agent_outcome` | Final result | decision_id, outcome_status, actual_cost, lessons_generated |
| `lesson_validation` | Lesson linkage | outcome_id, lesson_vault_file, confidence_score, applicability |

### Edge Tables (8)

| Edge | Direction | Purpose |
|------|-----------|---------|
| `session_decision` | session → decision | Link execution to decision |
| `decision_action` | decision → action | Chain decisions to actions |
| `action_outcome` | action → outcome | Aggregate actions to result |
| `outcome_lesson` | outcome → lesson | Link results to learning |
| `decision_vault_ref` | decision → vault file | Backlink to vault decision file |
| `outcome_vault_ref` | outcome → vault file | Backlink to vault experiment |
| `lesson_decision_cascade` | lesson → decision | Detect lesson-preventable errors |
| `error_pattern_edge` | error → lesson | Extract error patterns |

---

## Data Structures

### agent_session
```yaml
id: "session:UUID-or-timestamp"
agent_name: "observability-specialist"
started_at: "2026-02-11T23:00:00Z"
ended_at: null
status: "in-progress"  # or success/error/partial
decision_id: "decision:001"
context:
  model: "Haiku 4.5"
  temperature: 0.7
  max_tokens: 4000
metadata: {}
```

### agent_decision
```yaml
id: "decision:UUID"
session_id: "session:001"
vault_decision_file: "decisions/2026-02-11-example.md"
title: "Use Ollama embeddings vs API"
problem_statement: "Cost optimization for embeddings"
chosen_option: "Ollama embeddings"
alternatives:
  - "OpenAI API ($15)"
  - "Anthropic API ($10)"
decision_reasoning:
  rationale: "Cost $0 vs $15, local control, latency <100ms"
  confidence: 0.95
  reasoning_chain:
    - "Option A: Evaluate cost"
    - "Option B: Evaluate latency"
    - "Decision: Local wins on cost + latency"
estimated_cost: 2.00
estimated_time_hours: 4.5
created_at: "2026-02-11T23:00:00Z"
tags: ["cost-optimization", "infrastructure"]
```

### agent_action
```yaml
id: "action:UUID"
decision_id: "decision:001"
sequence_order: 1
tool_name: "Read"
tool_input:
  file_path: "/path/to/file"
executed_at: "2026-02-11T23:00:05Z"
completed_at: "2026-02-11T23:00:06Z"
execution_time_ms: 1200
status: "success"
result_summary: "File read successfully, 5KB content"
tokens_used: 450
cost_usd: 0.0001
```

### agent_outcome
```yaml
id: "outcome:UUID"
decision_id: "decision:001"
session_id: "session:001"
vault_experiment_file: "experiments/2026-02-11-embeddings-test.md"
outcome_status: "success"
summary: "Ollama embeddings implemented, $0 cost, 200ms latency"
actions_count: 12
actual_cost: 0.0
estimated_cost: 2.00
cost_delta_pct: -100.0
total_time_seconds: 1200
total_tokens: 5400
cost_per_lesson: 0.0
lessons_generated: ["lesson-local-embedding-performance"]
completed_at: "2026-02-11T23:20:00Z"
vault_note_generated: true
```

### lesson_validation
```yaml
id: "lesson_val:UUID"
outcome_id: "outcome:001"
lesson_vault_file: "lessons/lesson-cost-efficiency.md"
lesson_title: "Cost Efficiency: Prefer Local over API"
triggered_by_error: false
confidence_score: 0.95
applicability:
  scope: "All embedding use cases in cohezion"
  exceptions: "Real-time requirements >10K qps"
preventions:
  - "Default to local Ollama for cost metrics"
  - "Only use API if local latency violated"
created_at: "2026-02-11T23:20:00Z"
```

---

## Strategic Queries

### Query 1: Research Lineage (Papers → Decisions → Lessons)
Traces how research (papers) → architectural decisions → lessons learned

```sql
SELECT
  p.title as paper_title,
  d.title as decision_title,
  o.outcome_status,
  lv.lesson_title,
  lv.confidence_score
FROM paper as p
  <- concept_link <- concept as c
  <- decision_link <- agent_decision as d
  <- session_decision <- agent_session as s
  -> decision_action -> agent_action as a
  -> action_outcome -> agent_outcome as o
  -> outcome_lesson -> lesson_validation as lv
WHERE p.path LIKE '%papers%'
ORDER BY p.created_at DESC;
```

**Use case**: Validate decision lineage (does each lesson trace back to a decision?)

### Query 2: Lesson Validation (Outcomes Generating Lessons)
Shows which outcomes produced lessons and at what confidence

```sql
SELECT
  ao.outcome_status,
  COUNT(lv.id) as lessons_generated,
  SUM(ao.actual_cost) as total_cost,
  AVG(lv.confidence_score) as avg_confidence
FROM agent_outcome as ao
  -> outcome_lesson -> lesson_validation as lv
GROUP BY ao.id
ORDER BY lessons_generated DESC;
```

**Use case**: Identify high-value outcomes (outcomes that teach the most)

### Query 3: Cascade Detection (Preventing Future Errors)
Shows if a lesson prevented errors in subsequent decisions

```sql
SELECT
  lv.lesson_title,
  COUNT(DISTINCT ad.id) as future_decisions_affected,
  COUNT(CASE WHEN ao2.outcome_status = 'error' THEN 1 END) as prevented_errors
FROM lesson_validation as lv
  <- outcome_lesson <- agent_outcome as ao
  <- action_outcome <- agent_action as aa
  <- decision_action <- agent_decision as ad
  WHERE ad.created_at > ao.completed_at
    AND ad.tags CONTAINS (lv.lesson_title)
GROUP BY lv.id
ORDER BY prevented_errors DESC;
```

**Use case**: Measure lesson impact (how many future errors did this lesson prevent?)

---

## Implementation Files

### Schema Definition
- **SQL Reference**: `schemas/agent_context_schema.sql` (detailed schema with comments)
- **Python Module**: `src/mcp_server/agent_context_schema.py` (initialization + testing)

### Initialization

```python
from agent_context_schema import AgentContextSchema

schema = AgentContextSchema()
schema.initialize_schema()  # Creates all 5+8 tables
schema.test_schema()         # Verifies with sample insert
info = schema.get_schema_info()  # Returns status
```

### Location
- **Schema SQL**: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/schemas/agent_context_schema.sql`
- **Python Module**: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/agent_context_schema.py`

---

## SurrealDB Notes

### Table Creation Strategy
- **Method**: DEFINE TABLE (implicit on first UPSERT)
- **Indexing**: Handled automatically by SurrealDB for frequently accessed fields
- **Schemaless**: All tables are SCHEMALESS (flexible field structure)

### Tested Patterns
```python
# Working: Headers for namespace/database
headers = {
    "Content-Type": "text/plain",
    "NS": "cohezion",
    "DB": "vault"
}

# Working: Backtick-quoted IDs for special characters
f"UPSERT agent_session:`{session_id}` SET ..."

# Working: Multiple queries in one batch
query = "DEFINE TABLE t1; DEFINE TABLE t2; SELECT * FROM t1;"

# Not working: CREATE TABLE IF NOT EXISTS (SurrealDB uses DEFINE TABLE)
# Not working: Multi-query with semicolons on single line
```

---

## Next Steps (Step 2 → MCP Tools)

Step 2 (Integration Engineer) will implement 3 MCP tools:
1. `track_session()` - Create session with agent/model context
2. `record_decision()` - Log decision with reasoning + alternatives
3. `record_outcome()` - Capture result, cost, lessons

These tools will use this schema to populate the graph automatically during agent execution.

---

## Validation Checklist

- [x] 5 node tables created (agent_session, agent_decision, agent_action, agent_outcome, lesson_validation)
- [x] 8 edge tables created (session_decision, decision_action, action_outcome, outcome_lesson, decision_vault_ref, outcome_vault_ref, lesson_decision_cascade, error_pattern_edge)
- [x] Python initialization module (schema.py) working
- [x] Test insert successful (sample session created and deleted)
- [x] Schema info query returning active status
- [x] 3 strategic queries documented (research lineage, lesson validation, cascade detection)

---

## Files Changed

- Created: `schemas/agent_context_schema.sql` (380 lines)
- Created: `src/mcp_server/agent_context_schema.py` (270 lines)
- Created: `docs/PHASE_1_STEP_1_SCHEMA_DEFINITION.md` (this file)

---

**Phase 1 Step 1 Complete ✅**

Next: Step 2 (2026-02-11 evening) - MCP Tools Implementation (4h, integration-engineer lead)
