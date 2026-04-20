# Phase 1: Agent Context Integration with SurrealDB

**Status**: Step 1 Complete, Step 2-6 In Progress
**Target Completion**: 2026-02-13
**Total Effort**: 15 hours (2-3 day sprint)

---

## Overview

Phase 1 integrates entire.io agent execution context into SurrealDB to enable:

1. **Research Lineage Tracking**: Which papers informed agent decisions?
2. **Lesson Validation**: Which lessons are validated by agent work?
3. **Decision Cascades**: How do decisions impact downstream actions and outcomes?
4. **Vault Enrichment**: Auto-linking agent-generated insights to vault notes

---

## Deliverables

### Step 1: Schema Definition (COMPLETE ✅)

**Files**:
- `/src/mcp_server/agent_context_schema.sql` - 5 tables, 8 edges, 12 indexes
- `/src/mcp_server/agent_context_ops.py` - Python service (6 core methods)

**Schema Overview**:

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **session** | Agent execution session | id, timestamp, agent_names, status, model_used, metrics |
| **decision** | Critical decision point | session_id, title, reasoning, alternatives, chosen_path |
| **action** | Function/tool invocation | session_id, tool_name, input_params, status, duration_ms |
| **outcome** | Session result | session_id, status, summary, metrics, vault_notes_created |
| **lesson** | Extracted learning | session_id, title, severity, linked_lesson_path |

**Edges** (8):
- `session -> has_decisions -> decision`
- `session -> has_actions -> action`
- `session -> has_outcomes -> outcome`
- `decision -> informs_actions -> action`
- `outcome -> validates_lesson -> lesson`
- `session -> relates_to_paper -> paper`
- `decision -> derives_from_research -> paper`

**Indexes** (12): Optimized for session lookups, status filtering, relationship traversal

---

### Step 2: MCP Tools Development (IN PROGRESS)

**Owner**: integration-engineer
**Effort**: 4h
**Deliverables**: 3 core tools, 5-10 tests each, integration test

#### Core Tools

```python
@mcp.tool()
def track_session(
    agent_names: list[str],
    duration_ms: int,
    status: str,
    model_used: str = "haiku",
    total_turns: int = 0,
    total_functions: int = 0,
    error_message: str | None = None,
) -> str:
    """Track agent execution session.

    Args:
        agent_names: List of agent names
        duration_ms: Session duration
        status: running | completed | error
        model_used: haiku | sonnet | opus
        total_turns: Conversation turns
        total_functions: Function calls
        error_message: Error details if failed

    Returns:
        Session ID (e.g., "session:abc123f7")
    """
    return agent_context.track_session(...)


@mcp.tool()
def record_decision(
    session_id: str,
    title: str,
    context: str,
    reasoning: str,
    alternatives: list[str],
    chosen_path: str,
    confidence: float = 0.8,
    reversible: bool = True,
) -> str:
    """Record critical decision during agent work.

    Args:
        session_id: Parent session
        title: Decision title
        context: Why this decision was needed
        reasoning: How decision was made
        alternatives: Other options considered
        chosen_path: Which path was chosen
        confidence: Confidence level (0.0-1.0)
        reversible: Can be undone?

    Returns:
        Decision ID (e.g., "decision:def456a8")
    """
    return agent_context.record_decision(...)


@mcp.tool()
def record_outcome(
    session_id: str,
    status: str,
    summary: str,
    metrics: dict[str, Any] | None = None,
    artifacts: list[str] | None = None,
    vault_notes_created: list[str] | None = None,
) -> str:
    """Record session outcome.

    Args:
        session_id: Parent session
        status: success | partial | failed
        summary: Human-readable result
        metrics: Execution metrics (turns, functions, errors)
        artifacts: Files/results created
        vault_notes_created: Notes created during session

    Returns:
        Outcome ID (e.g., "outcome:ghi789b5")
    """
    return agent_context.record_outcome(...)
```

#### Optional Tools (Step 2.5)

- `record_action()` - Detailed function call tracking
- `record_lesson()` - Manual lesson extraction
- Query tools (see Step 3)

#### Testing Strategy

Each tool needs:
- **5-10 unit tests** covering happy path, errors, edge cases
- **1 integration test** per tool: successful execution → SurrealDB record
- **1 end-to-end test**: track_session → record_decision → record_outcome flow

See `/tests/test_agent_context_ops.py` for test templates.

---

### Step 3: Query Testing (PENDING)

**Owner**: data-graph-specialist
**Effort**: 3h
**Deliverables**: 3 working queries, documentation

#### Query 1: Research Lineage

**Purpose**: Find all papers that informed decisions in a session

**Implementation**:
```sql
-- Get all decisions from session
LET $decisions = (
    SELECT out FROM has_decisions WHERE in = $session_id
);

-- Find papers that informed those decisions
SELECT DISTINCT
    paper,
    decision:title,
    derives_from_research:source_type
FROM $decisions -> derives_from_research -> paper;
```

**Test Cases**:
- Session with 0 decisions
- Session with decisions informed by papers
- Session with decisions from other sources (no papers)
- Verify correct paper linkage

#### Query 2: Lesson Validation

**Purpose**: Find lessons validated by session outcomes

**Implementation**:
```sql
-- Get outcomes from session
LET $outcomes = (
    SELECT out FROM has_outcomes WHERE in = $session_id
);

-- Find lessons validated by those outcomes
SELECT DISTINCT
    lesson,
    outcome:status,
    lesson:severity,
    lesson:linked_lesson_path
FROM $outcomes -> validates_lesson -> lesson;
```

**Test Cases**:
- Session with no outcomes
- Session with outcomes + lessons
- Filter by severity
- Verify vault note linkage

#### Query 3: Cascading Impact

**Purpose**: Trace how a decision impacts actions and outcomes

**Implementation**:
```sql
SELECT
    id, title, reasoning, chosen_path,
    (SELECT out FROM informs_actions WHERE in = $decision_id) AS informed_actions
FROM $decision_id;
```

**Test Cases**:
- Decision with no actions
- Decision informing multiple actions
- Action -> outcome tracing
- Verify decision -> outcome cascade

---

### Step 4: Integration Testing (PENDING)

**Owner**: integration-engineer
**Effort**: 3h
**Deliverables**: End-to-end test suite, production validation

#### Test Scenarios

1. **Happy Path**: entire.io → track_session → record_decision → record_outcome
   - Verify all records created
   - Verify relationships created
   - Verify indexes working

2. **Error Handling**: Failed action → error_message recorded
   - Session tracks error status
   - Lesson extracted for post-mortem
   - Vault note created for remediation

3. **Query Validation**: After recording data, queries return correct results
   - Research lineage accurate
   - Lesson validation links correct
   - Cascading impact traces properly

4. **Concurrent Sessions**: Multiple agents working in parallel
   - No data corruption
   - Indexes remain performant
   - Relationships isolated per session

---

### Step 5: Documentation (PENDING)

**Owner**: data-graph-specialist
**Effort**: 2h
**Deliverables**: Query templates, tool documentation

#### Query Templates

Create `/docs/AGENT_CONTEXT_QUERIES.md`:

```markdown
## Agent Context Query Reference

### Research Lineage Query
[Template + examples]

### Lesson Validation Query
[Template + examples]

### Cascading Impact Query
[Template + examples]
```

#### Tool Documentation

Update server.py tool docstrings with:
- Parameter descriptions
- Return value format
- Usage examples
- Common patterns

#### Schema Documentation

Finalize `/docs/AGENT_CONTEXT_SCHEMA.md`:
- Table descriptions
- Edge semantics
- Index strategy
- Capacity planning

---

### Step 6: Production Validation (PENDING)

**Owner**: integration-engineer
**Effort**: 1h
**Deliverables**: Production sign-off

#### Validation Checklist

- [ ] SurrealDB tables + indexes created
- [ ] 3 MCP tools working + tested
- [ ] 3 strategic queries working
- [ ] Integration test suite passing (100%)
- [ ] Documentation complete
- [ ] Performance benchmarked (< 500ms per operation)
- [ ] Error handling verified
- [ ] Concurrent session handling validated

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│ Agent Execution (entire.io)                             │
│  - Decisions, actions, outcomes                         │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Cloud Vault MCP Server (port 8360)                      │
│ ┌───────────────────────────────────────────────────┐   │
│ │ AgentContextOps Service                           │   │
│ │  - track_session()                                │   │
│ │  - record_decision()                              │   │
│ │  - record_action()                                │   │
│ │  - record_outcome()                               │   │
│ │  - record_lesson()                                │   │
│ │  - query_research_lineage()                       │   │
│ │  - query_lesson_validation()                      │   │
│ │  - query_cascading_impact()                       │   │
│ └───────────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ SurrealDB (localhost:8000)                              │
│ ┌──────────────┬────────────┬───────────┬──────────┐   │
│ │ session      │ decision   │ action    │ outcome  │   │
│ │              │            │           │ lesson   │   │
│ └──────────────┴────────────┴───────────┴──────────┘   │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Edges: has_decisions, has_actions,               │   │
│ │        informs_actions, validates_lesson, etc    │   │
│ └──────────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Vault Enrichment                                        │
│  - Auto-link decisions to vault notes                   │
│  - Link lessons to vault/lessons/                       │
│  - Extract patterns from agent work                     │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
Agent Execution
    │
    ├─→ track_session(agent_names, status) → session record
    │       │
    │       ├─→ record_decision(...) → decision record
    │       │   └─→ RELATE session->has_decisions->decision
    │       │
    │       ├─→ record_action(...) → action record
    │       │   └─→ RELATE session->has_actions->action
    │       │
    │       ├─→ record_decision() → decision2 record
    │       │   └─→ RELATE decision2->informs_actions->action
    │       │
    │       └─→ record_outcome(...) → outcome record
    │           └─→ RELATE session->has_outcomes->outcome
    │           └─→ RELATE outcome->validates_lesson->lesson
    │
    └─→ Query: research_lineage() → papers that informed decisions
        Query: lesson_validation() → lessons validated by outcomes
        Query: cascading_impact() → decision→action→outcome trace
```

---

## Testing Strategy

### Unit Tests (Step 2)

- **AgentContextOps methods**: 5-10 tests each
- **Tool parameter validation**: Type checking, defaults
- **Error handling**: HTTP errors, SurrealDB errors

See `/tests/test_agent_context_ops.py`

### Integration Tests (Step 4)

- **Tool + SurrealDB**: Full execution flow
- **Query validation**: Correct results for test data
- **Concurrent execution**: No data corruption
- **Performance**: < 500ms per operation

### Performance Benchmarks

Baseline metrics to capture:
- Session creation: < 100ms
- Decision recording: < 150ms
- Query execution: < 500ms
- Bulk import: < 5s for 1000 records

---

## Success Criteria

Phase 1 complete when:

- [ ] **SurrealDB tables + indexes created** (Step 1 ✅)
- [ ] **3 MCP tools working + tested** (Step 2)
- [ ] **3 strategic queries working** (Step 3)
- [ ] **Integration test suite passing (100%)** (Step 4)
- [ ] **Documentation complete** (Step 5)
- [ ] **Production validation sign-off** (Step 6)

Target: **2026-02-13** (2-3 day sprint)

---

## Week 2: Daemon Implementation

After Phase 1 complete:

**entire_sync_daemon.py** (reuses sheets_research_daemon pattern):
- Poll entire.io API for completed sessions
- Batch create SurrealDB records
- Auto-generate vault notes
- 200-300 sessions/day capacity
- Error recovery + DLQ

Estimated: 3-4h implementation + 1-2h testing

---

## References

- Schema: `/src/mcp_server/agent_context_schema.sql`
- Python Service: `/src/mcp_server/agent_context_ops.py`
- Tests: `/tests/test_agent_context_ops.py`
- Examples: See query patterns in schema comments

---

**Phase 1 Owner**: data-graph-specialist + integration-engineer
**Last Updated**: 2026-02-11
**Next Review**: 2026-02-12
