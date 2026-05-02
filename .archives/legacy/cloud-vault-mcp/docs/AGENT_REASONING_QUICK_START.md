# Agent Reasoning: Quick Start Guide

## 5-Minute Setup

### 1. Initialize Operations
```python
from src.mcp_server.agent_reasoning import AgentReasoningOps
from src.mcp_server.agent_reasoning_queries import AgentReasoningQueries
from src.mcp_server.surrealdb_sync import SurrealDBSync

db = SurrealDBSync()
ops = AgentReasoningOps(db)
queries = AgentReasoningQueries(db)
```

### 2. Record a Decision's Reasoning
```python
reasoning_ops.record_reasoning(
    decision_id="agent_decision:cache-strategy",
    reasoning_type="research",
    reasoning_chain=["Analyzed workload", "Tested TTL values", "Chose 10m"],
    confidence_score=0.85
)
```

### 3. Query the Reasoning
```python
result = queries.root_cause_analysis("agent_decision:cache-strategy")
print(f"Confidence: {result['highest_confidence']}")
```

### 4. Record Challenges
```python
ops.record_challenge(
    decision_id="agent_decision:cache-strategy",
    lesson_id="lesson-performance-limits",
    challenge_type="limits",
    severity="minor"
)
```

### 5. Track Decision Cascades
```python
ops.record_cascade(
    source_decision_id="agent_decision:auth-scheme",
    dependent_decision_id="agent_decision:token-cache",
    dependency_type="blocks",
    impact_level="critical"
)
```

## Common Patterns

### Pattern 1: Document Alternative Rejection
```python
ops.record_reasoning(
    decision_id="agent_decision:sync-vs-async",
    reasoning_type="research",
    reasoning_chain=["Benchmarked both approaches", "Chose async"],
    alternatives_rejected=[
        {"option": "Sync API", "reason": "High latency on network calls"},
        {"option": "Simple queue", "reason": "Delivery guarantees weak"}
    ]
)
```

### Pattern 2: Find All Reasoning for a Decision
```python
result = queries.root_cause_analysis("agent_decision:xyz")
for chain in result["reasoning_chains"]:
    print(f"{chain['reasoning_type']}: {chain['confidence_score']}")
```

### Pattern 3: Find Contradicting Evidence
```python
result = queries.contradiction_detection(severity_filter="major")
print(f"Found {len(result['contradictions'])} major issues")
```

### Pattern 4: Trace Decision Impact
```python
result = queries.cascade_impact("agent_decision:auth")
print(f"{result['critical_count']} critical downstream impacts")
```

## Enum Reference

### reasoning_type
- `research`: Based on investigation/testing
- `pattern`: Based on recurring patterns
- `intuition`: Based on experience/gut feel
- `convention`: Following established practice
- `hybrid`: Combination of above

### challenge_type
- `contradicts`: Directly conflicts with decision
- `limits`: Identifies constraints/limitations
- `refines`: Improves/clarifies decision
- `extends`: Adds new considerations

### challenge_severity
- `major`: Significant impact, needs review
- `minor`: Small issue, note for future
- `clarification`: Needed info/context

### dependency_type
- `blocks`: Source must complete first
- `enables`: Source enables the dependent
- `refines`: Source clarifies/improves
- `requires`: Dependent needs source

### impact_level
- `critical`: Changes dependent decision fundamentally
- `significant`: Important modifications needed
- `minor`: Small tweaks or considerations

## Error Codes & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Decision not found" | Decision doesn't exist | Ensure decision created in Phase 1 first |
| "Lesson not found" | Lesson ID doesn't exist | Use full qualified ID: `lesson:xyz` |
| "Invalid reasoning_type" | Typo in enum | Use one of: research, pattern, intuition, convention, hybrid |
| "confidence_score must be between 0.0 and 1.0" | Out of range | Use float 0.0-1.0 |

## Performance Tips

1. **Batch reasoning creation**: Record all reasoning at once, not incrementally
2. **Use high_confidence_reasoning** for quick summaries (avg 0.8+)
3. **Query by type** instead of all reasoning if type-specific
4. **Cascade queries** scale linearly with dependent count (not recursive)

## Testing Your Integration

```python
# Quick smoke test
def test_reasoning_workflow():
    # 1. Create decision (Phase 1)
    # 2. Record reasoning
    reasoning = ops.record_reasoning(
        decision_id="test:decision",
        reasoning_type="research",
        reasoning_chain=["Step 1", "Step 2"],
        confidence_score=0.9
    )
    assert reasoning["success"]

    # 3. Query it back
    result = queries.root_cause_analysis("test:decision")
    assert result["success"]
    assert result["highest_confidence"] >= 0.9

    print("✅ Integration working")

test_reasoning_workflow()
```

## Where to Go from Here

- **Full Guide**: See `AGENT_REASONING_GUIDE.md`
- **API Reference**: See source code docstrings
- **Examples**: Check `tests/test_agent_reasoning_integration.py`
- **Troubleshooting**: See main guide "Error Handling" section

---

**Quick Start Version**: 1.0
**Phase**: 2 Track A (Agent Reasoning)
**Status**: Production Ready ✅
