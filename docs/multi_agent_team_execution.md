# Multi-Agent Team Execution

## Overview

Multi-Agent Team Execution enables coordinated execution of tasks across multiple AI agents with:
- **Dependency resolution** - Tasks execute in order respecting dependencies
- **Vault-guided skill selection** - Each task automatically selects the best-performing skill
- **Parallel execution** - Independent tasks run concurrently with configurable parallelism
- **Comprehensive scoring** - Team performance measured via composite metric (60% success rate, 25% coherence, 15% efficiency)
- **Error handling** - Graceful failure with partial success reporting

## Architecture

```
Team Execution Workflow
    ↓
Parse tasks and build dependency graph
    ↓
Topological sort for execution order
    ├─ Sequential: respects task.dependencies
    ├─ Parallel: independent tasks grouped
    └─ Resource-aware: parallel_degree limit
    ↓
For each task in sorted order:
├─ Wait for all dependencies to complete
├─ Select best skill via vault history
├─ Execute on assigned agent
├─ Store result for dependent tasks
└─ Log to vault if critical
    ↓
Compute team metrics:
├─ Success rate (how many succeeded)
├─ Avg coherence (quality of outputs)
├─ Avg efficiency (token efficiency)
└─ Composite score = (success×0.6 + coherence×0.25 + efficiency×0.15)
    ↓
Return TeamExecutionResult with all outcomes
```

## Core Components

### AgentTask

```python
@dataclass
class AgentTask:
    """Single task in a team execution."""

    task_id: str              # Unique task identifier
    agent_id: str             # Which agent executes this task
    description: str          # Human-readable task description
    operation_type: str       # "generate", "analyze", "search", etc.
    dependencies: list[str]   # task_ids that must complete first
    available_skills: list[str] = None  # Candidate skills to choose from
    timeout_seconds: float = 300.0
    execute_fn: Callable = None  # Custom execution function
```

### AgentTaskResult

```python
@dataclass
class AgentTaskResult:
    """Outcome of a single task execution."""

    task_id: str
    agent_id: str
    success: bool
    output: str                    # Task output
    metrics: dict[str, Any]        # Coherence, efficiency, etc.
    selected_skill: str            # Which skill was selected
    execution_result: ExecutionResult = None  # Full execution details
    error: str | None = None
```

### TeamExecutionResult

```python
@dataclass
class TeamExecutionResult:
    """Overall outcome of team execution."""

    success: bool                  # True if all tasks succeeded
    tasks_executed: int
    tasks_failed: int
    results: list[AgentTaskResult]  # Per-task results
    compound_score: float          # 0.0-1.0 team performance metric
    execution_time_seconds: float
    errors: list[str] = field(default_factory=list)
```

### TeamExecutor

Main orchestrator for team execution:

```python
class TeamExecutor:
    """Coordinate multi-agent task execution with vault guidance."""

    def __init__(
        self,
        agents: dict[str, CompoundExecutor],  # agent_id -> executor
        mcp_client: MCPClient,                 # For vault access
        project: str = "cohezion"              # Project scope
    )
```

**Key Methods:**

- `execute_team(tasks, parallel_degree=4)` - Main entry point, async
- `_topological_sort(tasks)` - Order tasks respecting dependencies
- `_select_skill_for_task(task)` - Query vault for best skill
- `_execute_task(task, agent, parent_results)` - Run single task
- `_compute_compound_score(results)` - Calculate team performance

## Skill Selection

TeamExecutor automatically selects the best skill for each task using **experience-guided selection**:

1. **Query Vault**: Search for past executions of similar tasks
2. **Extract Metrics**: Get coherence, efficiency, and success rates from patterns
3. **Rank Skills**: Use composite score = (coherence×0.5 + efficiency×0.3 + success×0.2)
4. **Select Best**: Use highest-scoring skill from available options
5. **Fallback**: If no vault data, use first available skill

## API Usage

### Basic Team Execution

```python
from cohezion.compound import CompoundExecutor, TeamExecutor, AgentTask
from cohezion.core.mcp_client import MCPClient, MCPConfig

# Initialize MCP and executors
config = MCPConfig(server_url="http://localhost:8360/mcp")
mcp_client = MCPClient(config)

# Create agents (each agent is a CompoundExecutor)
agents = {
    "researcher": CompoundExecutor(mcp_client=mcp_client),
    "analyst": CompoundExecutor(mcp_client=mcp_client),
    "writer": CompoundExecutor(mcp_client=mcp_client),
}

# Create team executor
team_executor = TeamExecutor(agents, mcp_client, project="cohezion")

# Define tasks with dependencies
tasks = [
    AgentTask(
        task_id="research",
        agent_id="researcher",
        description="Research climate change impacts",
        operation_type="analyze",
        dependencies=[],  # No dependencies
    ),
    AgentTask(
        task_id="analyze",
        agent_id="analyst",
        description="Analyze research findings",
        operation_type="analyze",
        dependencies=["research"],  # Waits for research to complete
    ),
    AgentTask(
        task_id="write",
        agent_id="writer",
        description="Write summary report",
        operation_type="generate",
        dependencies=["analyze"],  # Waits for analysis
    ),
]

# Execute team
result = await team_executor.execute_team(tasks, parallel_degree=2)

# Check results
print(f"Success: {result.success}")
print(f"Compound Score: {result.compound_score:.3f}")
for task_result in result.results:
    print(f"  {task_result.task_id}: {task_result.success}")
```

### With Custom Execution Function

```python
def custom_analyzer(guidance):
    """Custom execution logic with vault guidance."""
    return f"Analyzed with {guidance}", {"coherence": 0.88}

task = AgentTask(
    task_id="custom_analysis",
    agent_id="analyst",
    description="Custom analysis",
    operation_type="analyze",
    dependencies=[],
    execute_fn=custom_analyzer,  # Use custom function
)

result = await team_executor.execute_task(task, agent)
```

### With Parallelism Control

```python
# Execute up to 3 tasks in parallel
result = await team_executor.execute_team(tasks, parallel_degree=3)

# vs. Sequential execution
result = await team_executor.execute_team(tasks, parallel_degree=1)

# vs. Unlimited parallelism (all independent tasks at once)
result = await team_executor.execute_team(tasks, parallel_degree=999)
```

### Diamond Dependencies

```python
# Diamond DAG: A → B,C → D
tasks = [
    AgentTask("A", "agent1", "Task A", "generate", []),
    AgentTask("B", "agent2", "Task B", "analyze", ["A"]),
    AgentTask("C", "agent3", "Task C", "analyze", ["A"]),
    AgentTask("D", "agent1", "Task D", "transform", ["B", "C"]),
]

# B and C run in parallel after A completes
# D waits for both B and C
result = await team_executor.execute_team(tasks, parallel_degree=4)
```

## Composition Patterns

### Sequential Pipeline

```python
# Each task depends on the previous one
tasks = [
    AgentTask("step1", "agent1", "Step 1", "generate", []),
    AgentTask("step2", "agent2", "Step 2", "analyze", ["step1"]),
    AgentTask("step3", "agent3", "Step 3", "transform", ["step2"]),
    AgentTask("step4", "agent1", "Step 4", "persist", ["step3"]),
]
```

### Fan-Out Pattern

```python
# One task spawns multiple parallel tasks
tasks = [
    AgentTask("gather", "agent1", "Gather data", "search", []),
    AgentTask("analyze_a", "agent2", "Analyze A", "analyze", ["gather"]),
    AgentTask("analyze_b", "agent3", "Analyze B", "analyze", ["gather"]),
    AgentTask("analyze_c", "agent1", "Analyze C", "analyze", ["gather"]),
    AgentTask("consolidate", "agent2", "Consolidate", "transform",
              ["analyze_a", "analyze_b", "analyze_c"]),
]
```

### Multi-Stage DAG

```python
# Complex coordination across stages
tasks = [
    # Stage 1: Parallel information gathering
    AgentTask("search_web", "agent1", "Search web", "search", []),
    AgentTask("search_docs", "agent2", "Search docs", "search", []),

    # Stage 2: Analysis (depends on stage 1)
    AgentTask("analyze", "agent3", "Analyze results", "analyze",
              ["search_web", "search_docs"]),

    # Stage 3: Report (depends on stage 2)
    AgentTask("report", "agent1", "Generate report", "generate", ["analyze"]),
]
```

## Skill Selection Configuration

Control which skills each task can use:

```python
task = AgentTask(
    task_id="analysis",
    agent_id="analyst",
    description="Analyze market data",
    operation_type="analyze",
    available_skills=["analyze_reports", "summarize", "extract_insights"],
    # TeamExecutor will select the best skill from this list
)
```

Without `available_skills`, all skills are candidates.

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Topological sort | O(V+E) | V=tasks, E=dependencies |
| Skill selection | 50-200ms | Per task, vault lookup |
| Task execution | Variable | Depends on skill |
| Dependency polling | 100ms intervals | Non-blocking wait |
| Result aggregation | <1ms | Per 100 tasks |

## Scoring Algorithm

### Composite Score Calculation

```python
# For each task result:
success_rate = successful_tasks / total_tasks      # 0.0-1.0

# Average metrics from successful tasks
avg_coherence = mean(r.metrics["coherence"] for r in successful)
avg_efficiency = mean(r.execution_result.cache_hit_rate
                     for r in successful)

# Weighted combination
compound_score = (
    success_rate * 0.60 +      # Success is primary (60%)
    avg_coherence * 0.25 +     # Quality of outputs (25%)
    avg_efficiency * 0.15      # Token efficiency (15%)
)
```

**Example:**
- 3 tasks, all successful: success_rate = 1.0
- Average coherence: 0.88
- Average efficiency: 0.75
- Compound = (1.0×0.6) + (0.88×0.25) + (0.75×0.15) = 0.60 + 0.22 + 0.1125 = **0.9325**

## Error Handling

### Task Failure (non-critical)

If one task fails, other independent tasks continue:

```python
# A → B → D
#      C → D

tasks = [
    AgentTask("A", "agent1", "A", "gen", []),
    AgentTask("B", "agent2", "B", "analyze", ["A"]),
    AgentTask("C", "agent3", "C", "analyze", ["A"]),  # May fail
    AgentTask("D", "agent1", "D", "transform", ["B", "C"]),
]

result = await executor.execute_team(tasks)

# If C fails:
# - A succeeds
# - B succeeds
# - C fails (error in result.results[2])
# - D cannot run (dependency failed), also fails

print(result.success)  # False (D failed due to missing dependency)
print(result.tasks_failed)  # 2 (C and D)
```

### Missing Agent

```python
task = AgentTask("work", "unknown_agent", "Do work", "gen", [])
result = await executor._execute_task(task, None, {})

# Returns AgentTaskResult with:
# - success: False
# - error: "Agent unknown_agent not found"
# - output: ""
```

### Exception Handling

```python
try:
    result = await team_executor.execute_team(tasks)
except Exception as e:
    logger.error(f"Team execution failed: {e}")
    # Returns TeamExecutionResult with:
    # - success: False
    # - tasks_executed: 0
    # - errors: [str(e)]
    # - compound_score: 0.0
```

## Integration with Compound Executor

TeamExecutor coordinates **CompoundExecutor** instances. Each agent runs the full 7-step compound pipeline:

1. Experience guidance (vault lookup)
2. Input validation (guardrails)
3. Skill execution
4. Output validation (guardrails)
5. Anomaly detection (inflection)
6. Pattern extraction (learning)
7. Skill refinement (improvement)

This means **each team task automatically learns** from vault patterns and refines skills over time.

## Vault Integration

### Skill Selection from Vault

When selecting a skill, TeamExecutor queries vault for:
- Past executions of similar tasks
- Performance metrics (coherence, efficiency, success rate)
- Ranked candidates by composite score

### Execution Logging

Each task execution logs to vault:
- Task description and operation type
- Selected skill and metrics
- Results and errors
- Timestamps for learning

### Experience Guidance

Future team executions benefit from accumulated knowledge:
- First run: uses default skill selection
- Second run: vault has patterns from first run
- Third run: all skills ranked by performance
- N-th run: optimal skills automatically selected

## Testing

### Unit Tests

```bash
uv run pytest tests/compound/test_team_executor.py -v
```

Coverage includes:
- Topological sorting (linear, DAG, diamond)
- Dependency graphs
- Skill selection
- Task execution (success/failure)
- Compound scoring
- Team execution workflows
- Error handling

All **30 tests passing**.

### Integration Test Example

```python
async def test_team_workflow():
    """Test realistic team scenario."""
    # 1. Create agents
    agents = {
        "researcher": CompoundExecutor(...),
        "analyst": CompoundExecutor(...),
    }
    executor = TeamExecutor(agents, mcp_client)

    # 2. Define multi-stage workflow
    tasks = [
        AgentTask("research", "researcher", "Research", "search", []),
        AgentTask("analyze", "analyst", "Analyze", "analyze", ["research"]),
    ]

    # 3. Execute
    result = await executor.execute_team(tasks)

    # 4. Verify
    assert result.success
    assert result.compound_score > 0.7
    assert all(r.success for r in result.results)
```

## Performance Tuning

### Parallelism

```python
# Conservative (safe for resource-limited environments)
await executor.execute_team(tasks, parallel_degree=2)

# Aggressive (maximize throughput)
await executor.execute_team(tasks, parallel_degree=8)

# Optimal depends on:
# - Number of agents
# - System resources
# - Vault query load
```

### Skill Selection Caching

Vault queries are non-blocking and cached at the MCPClient level. Multiple tasks of same type benefit from cached selections.

### Dependency Polling

Default: 100ms polling interval (configurable via internal constants). Lower latency machines can increase frequency.

## Troubleshooting

### All Tasks Fail

1. Check agent availability: `agents.get(task.agent_id) is not None`
2. Verify CompoundExecutor initialization: `executor = CompoundExecutor(mcp_client=mcp_client)`
3. Check vault connectivity: `mcp_client.health_check()`

### Circular Dependencies

TeamExecutor includes cycle detection in topological sort:

```python
# This raises ValueError during sort
tasks = [
    AgentTask("A", "agent1", "A", "gen", ["B"]),
    AgentTask("B", "agent2", "B", "gen", ["A"]),
]

try:
    await executor.execute_team(tasks)
except ValueError as e:
    # Cycle detected
```

### Low Compound Scores

1. Check individual task metrics in `result.results[i].metrics`
2. Verify skill selection: `result.results[i].selected_skill`
3. Review vault patterns: `mcp_client.vault_search(f"{task_description}")`
4. Increase available_skills to improve selection

### Task Timeout

```python
task = AgentTask(
    ...,
    timeout_seconds=600.0  # 10 minutes instead of 5
)
```

## See Also

- [CompoundExecutor Documentation](compound_executor.md)
- [Experience-Guided Skill Selection](experience_guided_skill_selection.md)
- [Vault Integration](vault_integration.md)
- [Team Architecture](team_architecture.md)
