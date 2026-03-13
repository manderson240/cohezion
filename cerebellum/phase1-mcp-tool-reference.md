---
title: "Phase 1 MCP Tool Reference - Agent Context Integration"
date: 2026-02-11
status: completed
tags: [phase1, mcp-tools, reference, documentation]
aspect: thinker
neural:
  activation: 0.91
  stage: mature
  synapse_in: 7
  synapse_out: 11
---

# Phase 1 MCP Tool Reference

Complete documentation for the three MCP tools that power the agent context schema in SurrealDB.

---

## Overview

Three MCP tools enable agent context tracking:
1. **`track_session()`** — Create agent work session + initialize resource tracking
2. **`record_decision()`** — Record architectural decision with research lineage
3. **`record_outcome()`** — Finalize session with learnings + metrics

All tools write to SurrealDB and are available via Cloud Vault MCP server.

---

## Tool 1: `track_session()`

### Purpose
Create a new agent session wrapper that tracks work boundaries, resource usage, and high-level goals.

### Signature
```python
def track_session(
    agent_id: str,
    goals: list[str],
    model_used: str = "claude-haiku-4-5",
    phase: str = "research"
) -> str:
    """
    Create new agent session for context tracking.

    Args:
        agent_id: Unique identifier for agent (e.g., "data-graph-specialist")
        goals: List of goals for this session (e.g., ["test-research-lineage", "validate-schema"])
        model_used: AI model used (default: "claude-haiku-4-5")
        phase: Work phase (default: "research")
               Options: "research", "decision", "implementation", "validation"

    Returns:
        session_id: Unique session identifier (e.g., "session:abc123")

    Raises:
        ValueError: If agent_id or goals empty
        ConnectionError: If SurrealDB unavailable
    """
```

### Examples

**Example 1: Research Phase Session**
```python
session_id = track_session(
    agent_id="data-graph-specialist",
    goals=["design-schema", "benchmark-performance"],
    model_used="claude-haiku-4-5",
    phase="research"
)
# Returns: "session:2026-02-11-data-graph-001"
```

**Example 2: Implementation Phase**
```python
session_id = track_session(
    agent_id="integration-engineer",
    goals=["implement-mcp-tools", "write-unit-tests", "integration-tests"],
    model_used="claude-haiku-4-5",
    phase="implementation"
)
# Returns: "session:2026-02-11-integration-001"
```

### Return Value
```json
{
  "session_id": "session:2026-02-11-xxx",
  "agent_id": "data-graph-specialist",
  "start_time": "2026-02-11T15:00:00Z",
  "model_used": "claude-haiku-4-5",
  "phase": "research",
  "status": "in_progress",
  "goals": ["design-schema", "benchmark-performance"],
  "total_tokens": 0,
  "cost_usd": 0.0
}
```

### When to Use
- At the **start of any agent task** requiring context tracking
- Before making decisions that need research lineage
- When you want metrics on token efficiency and cost
- For retrospective analysis of agent work

### Notes
- Session remains `in_progress` until `record_outcome()` called
- Token count and cost automatically updated as decisions made
- One session can contain multiple decisions (3-10 typical)

---

## Tool 2: `record_decision()`

### Purpose
Record an architectural/feature/refactor decision with full research lineage, reasoning, and confidence scoring.

### Signature
```python
def record_decision(
    session_id: str,
    decision_type: str,
    reasoning: str,
    papers_applied: list[str],
    confidence_score: float = 0.7
) -> str:
    """
    Record decision with research lineage in agent session.

    Args:
        session_id: Session ID from track_session() (e.g., "session:xxx")
        decision_type: Type of decision
                      Options: "architecture", "feature", "refactor", "bugfix", "data"
        reasoning: Full explanation of why decision was made (100-500 chars)
        papers_applied: List of paper IDs that informed decision
                       (e.g., ["paper:2023-surrealdb-benchmarks", "paper:2024-graph-comparison"])
        confidence_score: How confident in decision (0.0-1.0, default 0.7)

    Returns:
        decision_id: Unique decision identifier (e.g., "decision:abc123")

    Raises:
        ValueError: If session_id invalid or papers_applied empty
        ConnectionError: If SurrealDB unavailable
    """
```

### Examples

**Example 1: Architecture Decision**
```python
decision_id = record_decision(
    session_id="session:2026-02-11-data-graph-001",
    decision_type="architecture",
    reasoning="Use SurrealDB for native graph support enabling research lineage tracking with real-time subscriptions",
    papers_applied=[
        "paper:2023-surrealdb-benchmarks",
        "paper:2024-graph-comparison"
    ],
    confidence_score=0.95
)
# Returns: "decision:2026-02-11-xxx-001"
```

**Example 2: Feature Decision**
```python
decision_id = record_decision(
    session_id="session:2026-02-11-integration-001",
    decision_type="feature",
    reasoning="Add agent_context snapshots to track evolving goals during session for retrospective analysis",
    papers_applied=["paper:2023-agent-context-management"],
    confidence_score=0.85
)
# Returns: "decision:2026-02-11-xxx-002"
```

**Example 3: Refactor Decision**
```python
decision_id = record_decision(
    session_id="session:2026-02-11-integration-001",
    decision_type="refactor",
    reasoning="Simplify decision-reasoning relationship structure to improve query performance by 40%",
    papers_applied=["paper:2024-surrealdb-optimization"],
    confidence_score=0.72
)
# Returns: "decision:2026-02-11-xxx-003"
```

### Return Value
```json
{
  "decision_id": "decision:2026-02-11-xxx-001",
  "session_id": "session:2026-02-11-xxx",
  "decision_type": "architecture",
  "timestamp": "2026-02-11T15:30:00Z",
  "reasoning": "Use SurrealDB for native graph support...",
  "confidence_score": 0.95,
  "validation_status": "pending",
  "implementation_status": "proposed",
  "papers_applied": [
    {
      "id": "paper:2023-surrealdb-benchmarks",
      "relevance_score": 0.95,
      "applied_at": "2026-02-11T15:30:00Z"
    },
    {
      "id": "paper:2024-graph-comparison",
      "relevance_score": 0.85,
      "applied_at": "2026-02-11T15:30:00Z"
    }
  ]
}
```

### When to Use
- **After** calling `track_session()`
- When making **any significant architectural or feature decision**
- When you've **researched papers** that inform the choice
- Multiple times per session (typically 3-10 decisions)

### Best Practices

1. **Research First**: Only call `record_decision()` for decisions informed by actual research
2. **Cite Papers**: Always include papers that influenced decision
3. **Be Specific**: Write reasoning that explains the "why", not just "what"
4. **Confidence Matters**: Adjust confidence_score based on conviction level
   - 0.9-1.0: Very confident, well-researched, proven approach
   - 0.7-0.89: Moderately confident, some research, reasonable tradeoffs
   - 0.5-0.69: Uncertain, limited research, significant assumptions
   - < 0.5: Experimental, very uncertain, needs validation

### Notes
- Creates both `agent_decision` and `agent_reasoning` records
- Automatically creates `decision_applied_research` edges to papers
- Updates session's token count and cost metrics
- Decision remains in `pending` validation status until validated manually

---

## Tool 3: `record_outcome()`

### Purpose
Record session outcome with learned lessons, metrics, and validation status. Closes session and triggers feedback loop.

### Signature
```python
def record_outcome(
    session_id: str,
    outcome_type: str,
    lessons_learned: list[str],
    metrics: dict = None
) -> str:
    """
    Record session outcome with learnings and metrics.

    Args:
        session_id: Session ID from track_session() (e.g., "session:xxx")
        outcome_type: Result of session
                     Options: "success", "partial", "failed"
        lessons_learned: List of lesson IDs validated or created
                        (e.g., ["lesson:token-efficiency-haiku", "lesson:research-lineage-critical"])
        metrics: Dictionary of metrics for this session
                Suggested keys:
                - session_duration_min: int
                - token_efficiency_ratio: float (output_value / total_tokens)
                - decisions_made: int
                - decisions_validated: int
                - features_delivered: int
                - tests_passing: int

    Returns:
        outcome_id: Unique outcome identifier (e.g., "outcome:abc123")

    Raises:
        ValueError: If session_id invalid or outcome_type invalid
        ConnectionError: If SurrealDB unavailable
    """
```

### Examples

**Example 1: Success Outcome**
```python
outcome_id = record_outcome(
    session_id="session:2026-02-11-data-graph-001",
    outcome_type="success",
    lessons_learned=[
        "lesson:token-efficiency-haiku",
        "lesson:research-lineage-critical",
        "lesson:design-first-approach"
    ],
    metrics={
        "session_duration_min": 45,
        "token_efficiency_ratio": 3.2,
        "decisions_made": 5,
        "decisions_validated": 5,
        "papers_researched": 12,
        "documents_created": 5
    }
)
# Returns: "outcome:2026-02-11-xxx-001"
```

**Example 2: Partial Success**
```python
outcome_id = record_outcome(
    session_id="session:2026-02-11-integration-001",
    outcome_type="partial",
    lessons_learned=[
        "lesson:mcp-tool-testing-strategy",
        "lesson:jwt-authentication-surrealdb"
    ],
    metrics={
        "session_duration_min": 120,
        "token_efficiency_ratio": 2.8,
        "decisions_made": 3,
        "decisions_validated": 2,
        "tests_passing": 11,
        "tests_failing": 1
    }
)
# Returns: "outcome:2026-02-11-xxx-002"
```

### Return Value
```json
{
  "outcome_id": "outcome:2026-02-11-xxx-001",
  "session_id": "session:2026-02-11-xxx",
  "outcome_type": "success",
  "timestamp": "2026-02-11T16:30:00Z",
  "lessons_learned": [
    {
      "id": "lesson:token-efficiency-haiku",
      "title": "Token Efficiency with Haiku Model",
      "severity": "CRITICAL",
      "alignment_score": 0.98,
      "validation_type": "confirms"
    },
    {
      "id": "lesson:research-lineage-critical",
      "title": "Research Lineage Critical for Decision Quality",
      "severity": "HIGH",
      "alignment_score": 0.92,
      "validation_type": "confirms"
    }
  ],
  "metrics": {
    "session_duration_min": 45,
    "token_efficiency_ratio": 3.2,
    "decisions_made": 5,
    "decisions_validated": 5
  }
}
```

### When to Use
- **At the end of agent session** after decisions made and validated
- When you have **concrete metrics** on session success
- When you want to **validate or create lessons** from your work
- To **close the feedback loop** (lessons → decisions → validation → refined lessons)

### Best Practices

1. **Accurate Metrics**: Capture real metrics, not estimated
2. **Lesson Selection**: Only include lessons actually validated in this session
3. **Outcome Honesty**: Be truthful about success/partial/failed (don't inflate)
4. **Link to Learnings**: Include lessons created or confirmed by this work

### Notes
- Sets session status to "completed"
- Updates session end_time
- Creates `outcome_validates_lesson` edges to each lesson
- Enables retrospective analysis of what agent learned
- Feeds into Phase 2+ features for lesson refinement

---

## Tool Usage Patterns

### Pattern 1: Complete Workflow
```python
# 1. Start session
session_id = track_session(
    agent_id="data-graph-specialist",
    goals=["implement-feature", "write-tests"],
    phase="implementation"
)

# 2. Record decisions as you make them
for decision in decisions_made:
    decision_id = record_decision(
        session_id=session_id,
        decision_type=decision["type"],
        reasoning=decision["reasoning"],
        papers_applied=decision["papers"],
        confidence_score=decision["confidence"]
    )

# 3. When done, record outcome
outcome_id = record_outcome(
    session_id=session_id,
    outcome_type="success",
    lessons_learned=["lesson:xxx", "lesson:yyy"],
    metrics={
        "session_duration_min": 120,
        "token_efficiency_ratio": 3.0,
        "decisions_made": 5
    }
)
```

### Pattern 2: Research-Driven Decisions
```python
# Before making decision, research papers
papers = web_search(decision_topic)
# Extract key papers: ["paper:xxx", "paper:yyy"]

# Record decision citing research
record_decision(
    session_id=session_id,
    decision_type="architecture",
    reasoning="Based on research comparing X vs Y, chose Y because...",
    papers_applied=papers,
    confidence_score=0.9
)
```

### Pattern 3: Decision Validation
```python
# Initial decision
decision_id_1 = record_decision(
    session_id=session_id,
    decision_type="feature",
    reasoning="...",
    papers_applied=[...],
    confidence_score=0.7
)

# Later, validate decision
# (In Phase 2+: record_decision_validation() tool)
# For now, use record_outcome() to link lessons
```

---

## Error Handling

### Common Errors

**Invalid Session ID**
```python
record_decision(session_id="invalid", ...)
# Error: ValueError: Session ID not found in database
# Fix: Use session_id returned from track_session()
```

**Empty Papers List**
```python
record_decision(..., papers_applied=[], ...)
# Error: ValueError: At least one paper must be cited
# Fix: Research and cite at least one relevant paper
```

**SurrealDB Connection**
```python
record_decision(...)
# Error: ConnectionError: SurrealDB unavailable
# Fix: Check SurrealDB service status (http://localhost:8000/health)
```

---

## Related Tools & Future Enhancements

**Phase 2+ Tools** (planned):
- `record_decision_validation()` — Validate decision after implementation
- `update_agent_reasoning()` — Add chain-of-thought to existing decision
- `query_agent_journey()` — Retrieve all decisions in a session with lineage
- `compute_research_alignment()` — Calculate how research-driven session was

---

## Reference

- **Schema**: `patterns/surrealdb-agent-context-schema.md`
- **Query Guide**: `patterns/surrealdb-agent-context-visual-guide.md`
- **Quick Ref**: `patterns/surrealdb-agent-context-quick-reference.md`
- **Implementation**: `cloud-vault-mcp/src/mcp_server/tools/agent_context.py`

---

**Status**: Phase 1 Documentation Complete ✅
**Task**: Task #10 (Step 5)

[[phase-1-implementation]], [[mcp-infrastructure-architecture]], [[agent-context]]

## Related Concepts

- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-11-phase1-execution-status]]
- [[2026-02-11-phase1-step1-schema-complete]]
- [[surrealdb-agent-context-phase1-step3-query-testing]]
- [[phase1-production-validation-runbook]]
- [[surrealdb-agent-context-quick-reference]]
- [[bmad-scale-adaptive-documentation]]
- [[surrealdb-agent-context-visual-guide]]
