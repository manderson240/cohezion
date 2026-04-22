# Agent Reasoning: MCP Tools & Query Guide

## Overview

Agent Reasoning extends Phase 1 SurrealDB with tracking for how decisions are made, what challenges they face, and how they cascade through the system.

**Phase 2 Status**: ✅ Complete (73/73 tests passing)

## Core Concepts

### Reasoning Chains
Document the step-by-step thinking behind a decision.

```python
# Create a reasoning node
result = reasoning_ops.record_reasoning(
    decision_id="agent_decision:001",
    reasoning_type="research",  # research|pattern|intuition|convention|hybrid
    reasoning_chain=["Analyzed alternatives", "Validated assumptions", "Chose best option"],
    confidence_score=0.92,  # 0.0-1.0
    assumptions=["API stable", "Load < 10K req/sec"],
    alternatives_rejected=[
        {"option": "Sync approach", "reason": "Too slow"},
        {"option": "Queue-based", "reason": "Operational complexity"}
    ]
)

if result["success"]:
    print(f"Reasoning recorded: {result['reasoning_id']}")
else:
    print(f"Error: {result['error']}")
```

### Challenges & Contradictions
Track when a decision contradicts or limits existing knowledge.

```python
# Record a challenge to a decision
result = reasoning_ops.record_challenge(
    decision_id="agent_decision:001",
    lesson_id="lesson-05",
    challenge_type="contradicts",  # contradicts|limits|refines|extends
    severity="major",  # major|minor|clarification
    notes="Lesson shows API rate limits were higher than assumed"
)

if result["success"]:
    print(f"Challenge recorded: {result['edge_id']}")
```

### Cascading Decisions
Track how decisions impact other decisions.

```python
# Record a decision cascade
result = reasoning_ops.record_cascade(
    source_decision_id="agent_decision:001",
    dependent_decision_id="agent_decision:002",
    dependency_type="blocks",  # blocks|enables|refines|requires
    impact_level="critical",  # critical|significant|minor
    notes="Auth decision blocks cache implementation"
)

if result["success"]:
    print(f"Cascade recorded: {result['edge_id']}")
```

## MCP Tools

### `record_reasoning`
Create a reasoning node explaining why a decision was made.

**Parameters:**
- `decision_id` (str, required): ID of the decision
- `reasoning_type` (str, required): One of: research, pattern, intuition, convention, hybrid
- `reasoning_chain` (list[str], required): Step-by-step reasoning steps
- `confidence_score` (float, optional): 0.0-1.0, default 0.7
- `assumptions` (list[str], optional): Assumptions made
- `alternatives_rejected` (list[dict], optional): Rejected options with reasons

**Returns:**
```python
{
    "success": bool,
    "reasoning_id": "agent_reasoning:uuid",
    "decision_id": str,
    "reasoning_type": str,
    "confidence_score": float,
    "error": str  # Only if success=False
}
```

**Example:**
```python
result = reasoning_ops.record_reasoning(
    decision_id="agent_decision:cache-ttl",
    reasoning_type="research",
    reasoning_chain=[
        "Reviewed cache hit rates: 68% baseline",
        "Analyzed memory usage: 512MB current",
        "Benchmarked TTL options: 5m=0.72, 10m=0.79, 30m=0.82",
        "Selected 10m as optimal (cost/benefit)"
    ],
    confidence_score=0.85,
    assumptions=["Usage patterns stable", "Memory budget: 1GB"],
    alternatives_rejected=[
        {"option": "5m TTL", "reason": "Rebuild overhead high"},
        {"option": "Variable TTL", "reason": "Operational complexity"}
    ]
)
```

### `record_challenge`
Record when a decision contradicts or is limited by existing knowledge.

**Parameters:**
- `decision_id` (str, required): ID of the decision
- `lesson_id` (str, required): ID of the lesson/observation challenging it
- `challenge_type` (str, required): One of: contradicts, limits, refines, extends
- `severity` (str, required): One of: major, minor, clarification
- `notes` (str, optional): Additional context

**Returns:**
```python
{
    "success": bool,
    "edge_id": "challenges_lesson:uuid",
    "decision_id": str,
    "lesson_id": str,
    "challenge_type": str,
    "severity": str,
    "error": str  # Only if success=False
}
```

### `record_cascade`
Record how one decision impacts or depends on another.

**Parameters:**
- `source_decision_id` (str, required): The decision that causes impact
- `dependent_decision_id` (str, required): The decision being impacted
- `dependency_type` (str, required): One of: blocks, enables, refines, requires
- `impact_level` (str, required): One of: critical, significant, minor
- `notes` (str, optional): Additional context

**Returns:**
```python
{
    "success": bool,
    "edge_id": "relates_to_decision:uuid",
    "source_decision_id": str,
    "dependent_decision_id": str,
    "dependency_type": str,
    "impact_level": str,
    "error": str  # Only if success=False
}
```

## Query Patterns

### Root Cause Analysis
Find all reasoning chains that led to a decision, ordered by confidence.

```python
result = reasoning_queries.root_cause_analysis(decision_id="agent_decision:001")

if result["success"]:
    print(f"Found {result['total_chains']} reasoning chains")
    print(f"Highest confidence: {result['highest_confidence']}")

    for chain in result["reasoning_chains"]:
        print(f"  - {chain['reasoning_type']}: {' → '.join(chain['reasoning_chain'])}")
        print(f"    Confidence: {chain['confidence_score']}")
```

**Returns:**
```python
{
    "success": bool,
    "decision_id": str,
    "reasoning_chains": [
        {
            "reasoning_id": str,
            "reasoning_type": str,
            "confidence_score": float,
            "chain_length": int,
            "reasoning_chain": list[str],
            "assumptions": list[str],
            "alternatives_rejected": list[dict],
            "created_at": str
        }
    ],
    "total_chains": int,
    "highest_confidence": float,
    "error": str  # Only if success=False
}
```

### Contradiction Detection
Find all challenges to decisions, filtered by severity.

```python
result = reasoning_queries.contradiction_detection(severity_filter="major")

if result["success"]:
    print(f"Major contradictions: {result['major_count']}")
    print(f"Minor contradictions: {result['minor_count']}")
    print(f"Clarifications: {result['clarification_count']}")

    for contradiction in result["contradictions"]:
        print(f"  - {contradiction['decision_id']} vs {contradiction['lesson_id']}")
        print(f"    Type: {contradiction['challenge_type']}, Severity: {contradiction['severity']}")
```

**Returns:**
```python
{
    "success": bool,
    "severity_filter": str,
    "contradictions": [
        {
            "decision_id": str,
            "lesson_id": str,
            "challenge_type": str,
            "severity": str,
            "notes": str,
            "created_at": str
        }
    ],
    "major_count": int,
    "minor_count": int,
    "clarification_count": int,
    "error": str  # Only if success=False
}
```

### Cascade Impact Analysis
Find all downstream decisions impacted by a source decision.

```python
result = reasoning_queries.cascade_impact(source_decision_id="agent_decision:001")

if result["success"]:
    print(f"Source decision: {result['source_decision']}")
    print(f"Critical impacts: {result['critical_count']}")
    print(f"Significant impacts: {result['significant_count']}")

    for cascade in result["cascades"]:
        print(f"  - {cascade['dependency_type']} → {cascade['dependent_decision']}")
        print(f"    Impact: {cascade['impact_level']}")
```

**Returns:**
```python
{
    "success": bool,
    "source_decision": str,
    "cascades": [
        {
            "source_decision": str,
            "dependent_decision": str,
            "dependency_type": str,
            "impact_level": str,
            "notes": str,
            "created_at": str
        }
    ],
    "critical_count": int,
    "significant_count": int,
    "minor_count": int,
    "error": str  # Only if success=False
}
```

### High Confidence Reasoning
Find all reasoning chains above a confidence threshold.

```python
result = reasoning_queries.high_confidence_reasoning(confidence_threshold=0.85)

if result["success"]:
    print(f"Found {len(result['reasoning_chains'])} high-confidence chains")

    for chain in result["reasoning_chains"]:
        print(f"  - {chain['decision_id']}: {chain['confidence_score']}")
```

**Returns:**
```python
{
    "success": bool,
    "confidence_threshold": float,
    "reasoning_chains": [
        {
            "decision_id": str,
            "reasoning_id": str,
            "reasoning_type": str,
            "confidence_score": float,
            "reasoning_chain": list[str],
            "created_at": str
        }
    ],
    "count": int,
    "avg_confidence": float,
    "error": str  # Only if success=False
}
```

### Reasoning by Type
Find reasoning chains of a specific type.

```python
result = reasoning_queries.reasoning_by_type(reasoning_type="research")

if result["success"]:
    print(f"Found {result['count']} research-based reasoning chains")
    print(f"Average confidence: {result['avg_confidence']}")
```

**Returns:**
```python
{
    "success": bool,
    "reasoning_type": str,
    "reasoning_chains": [
        {
            "decision_id": str,
            "reasoning_id": str,
            "confidence_score": float,
            "chain_length": int,
            "created_at": str
        }
    ],
    "count": int,
    "avg_confidence": float,
    "error": str  # Only if success=False
}
```

## Performance Characteristics

All queries are optimized with SurrealDB indexes for <500ms execution:

| Query | Index | Typical Time |
|-------|-------|--------------|
| root_cause_analysis | idx_reasoning_decision | <100ms |
| contradiction_detection | idx_challenges_severity | <150ms |
| cascade_impact | idx_relates_source | <150ms |
| high_confidence_reasoning | idx_reasoning_confidence | <100ms |

## Error Handling

All operations return `success: False` with an error message if:

1. **Referential Integrity**: Decision, lesson, or cascade references don't exist
2. **Validation**: Invalid enum values (reasoning_type, challenge_type, etc.)
3. **Range Errors**: confidence_score outside 0.0-1.0

**Example:**
```python
result = reasoning_ops.record_reasoning(
    decision_id="nonexistent:decision",  # This doesn't exist
    reasoning_type="research",
    reasoning_chain=["Step 1"],
    confidence_score=0.7
)

if not result["success"]:
    print(f"Error: {result['error']}")
    # Error: Decision not found: nonexistent:decision
```

## Integration with Phase 1

Phase 2 is fully backward compatible with Phase 1:

- All Phase 1 tools continue to work unchanged
- Phase 1 data is queryable alongside Phase 2 data
- No breaking changes to existing sessions, decisions, or outcomes

## Testing

All 73 tests pass with 100% success rate:
- 26 unit tests for Phase 2 tools
- 27 unit tests for Phase 2 queries
- 20 integration tests for Phase 1+2 workflows

Run tests:
```bash
pytest tests/test_agent_reasoning.py tests/test_agent_reasoning_queries.py tests/test_agent_reasoning_integration.py -v
```

## Next Steps

### Phase 2 Step 5: Documentation ✅ COMPLETE
- Query patterns guide (this document)
- Tool usage examples
- Performance characteristics

### Phase 2 Step 6: Sign-off
- Final validation
- Production approval
- Handoff to next phase

---

**Document Version**: 1.0
**Phase 2 Track A Status**: Steps 1-5 Complete (95%)
**Last Updated**: 2026-02-13
