---
paths:
  - "src/cohezion/compound/**"
---

# Compound Engineering Rules

Compound engineering = Systematic knowledge accumulation where decisions, experiments, and patterns compound into reusable knowledge.

## Core Loop (executor.py)

```
1. get_experience_guidance() → Query vault for similar tasks
2. execute_task() → Run with guidance
3. log_execution() → Persist trajectory/decisions/metrics to vault (automatic)
4. extract_patterns() → Save reusable insights
```

**Entry point:** `CompoundExecutor` or `ExecutorFactory.create(mcp_client)`

## Key Components

| Module | Purpose | Key Pattern |
|--------|---------|-------------|
| `executor.py` | Main execution orchestrator | Vault-integrated lifecycle (query → execute → log → extract) |
| `feedback_loop.py` | Auto-retry with 4-level escalation | Adjusted params → alt skill → model escalation → human |
| `journey_tracker.py` | 12D FLUME trajectory monitoring | Record state transitions for skill refinement |
| `skill_selector.py` | Vault-guided skill selection | Composite scoring: coherence 50% + efficiency 30% + success 20% |
| `skill_refiner.py` | Continuous learning from executions | Update skill definitions based on performance |
| `session_manager.py` | Session state + checkpoint recovery | Persist compound cycles for cross-session continuity |
| `request_alignment_analyzer.py` | Pre-execution alignment check | Coherence, completeness, drift risk, token estimate |
| `degradation_detector.py` | Quality monitoring | Thermal, coherence thresholds, anomaly alerts |

## Usage Patterns

**Initialize executor with vault:**
```python
from cohezion.compound import CompoundExecutor, ExecutorFactory
from cohezion.core.mcp_client import MCPClient

mcp_client = MCPClient(config={...})  # Vault connection
executor = ExecutorFactory.create(mcp_client)

# Optional: Enable token-efficient client
from cohezion.cache import TokenEfficientClient
token_client = TokenEfficientClient(api_key="...")
executor = CompoundExecutor(mcp_client, token_client=token_client)
```

**Execute with experience guidance:**
```python
# 1. Get vault guidance
guidance = await executor.get_experience_guidance(task_description="deploy API")

# 2. Execute
result = await executor.execute_task(
    task="deploy API",
    context=guidance  # Apply learnings from similar tasks
)

# 3. Logs are automatically persisted to vault
# 4. Extract patterns for future use
await executor.extract_patterns(result)
```

**Team execution:**
```python
from cohezion.compound import TeamExecutor, AgentTask

team = TeamExecutor(mcp_client)
tasks = [
    AgentTask(id="1", skill="research", description="Find examples"),
    AgentTask(id="2", skill="implement", description="Write code", depends_on=["1"]),
    AgentTask(id="3", skill="test", description="Verify", depends_on=["2"]),
]

result = await team.execute(tasks)  # Parallel execution with dependency ordering
```

## Critical Rules

- **Vault first:** Query vault for guidance before executing new tasks (saves tokens via template reuse)
- **Log everything:** Execution trajectories, decisions, metrics → automatically logged to vault by CompoundExecutor
- **HIHO invariant:** Maintain 0.5 coherence overlap (monitored by DegradationDetector)
- **Circuit breakers:** All external calls must use `cohezion.reliability.get_circuit()`
- **Token awareness:** Use `RequestAlignmentAnalyzer` to estimate tokens before execution
- **Feedback loops:** Leverage CompoundFeedbackLoop for automatic retry/escalation on failures
- **Non-blocking logging:** Vault operations wrapped in try/except to prevent crashes

## Performance Targets

- **Cache hit rate:** >95% (L1 hash + L2 cosine + L3 vault)
- **Token savings:** 87-98% via template reuse from vault
- **Coherence:** ≥0.5 (HIHO stability)
- **Test coverage:** 99.3% (2,854 tests passing)

## Anti-Patterns

- ❌ Executing without vault guidance (wastes tokens, misses learnings)
- ❌ Skipping alignment check (risk token explosion)
- ❌ Ignoring degradation alerts (coherence collapse)
- ❌ Creating ad-hoc retry logic (use CompoundFeedbackLoop)
- ❌ Blocking operations in logging (wrap in try/except)
