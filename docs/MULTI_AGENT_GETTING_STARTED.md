# Multi-Agent Orchestration: Getting Started Guide

**System**: Cohezion Dynamic + Adaptive Multi-Agent Orchestration  
**Version**: 1.0.0  
**Status**: ✅ Production Ready

---

## Quick Start

### 1. Basic Usage

```python
from cohezion.swarm import MultiAgentOrchestrator

async def main():
    # Create orchestrator
    orchestrator = MultiAgentOrchestrator()
    await orchestrator.start()
    
    # Execute task - router automatically selects best agent
    result = await orchestrator.execute(
        "Write a Python function to calculate fibonacci numbers"
    )
    
    print(f"Agent: {result.agent_name}")
    print(f"Backend: {result.backend}")
    print(f"Latency: {result.latency_ms:.1f}ms")
    print(f"Success: {result.success}")
    
    await orchestrator.stop()

# Run
import asyncio
asyncio.run(main())
```

**Output**:
```
Agent: CodeSpecialist
Backend: NPU
Latency: 85.3ms
Success: True
```

---

## Core Concepts

### 1. Specialist Agents

Pre-configured agents optimized for specific tasks:

| Agent | Model | Backend | Use Case |
|-------|-------|---------|----------|
| **CodeSpecialist** | qwen3:4b | NPU | Code generation, debugging |
| **ReasoningSpecialist** | Gemma-4-E2B-it | GPU Vulkan | Complex reasoning, 256K context |
| **NovelSpecialist** | Jan-v1-4B | GPU Vulkan | Research, experiments |

### 2. Adaptive Routing

The router **learns** which agent performs best for each task type:

```python
# First execution - uses rules
result = await orchestrator.execute("Write code...")
# → CodeSpecialist (rule: code task)

# Over time - learns from outcomes
decision = await router.route("Write code...")
# → CodeSpecialist (learned: high success rate)
# → Confidence: 0.94
```

### 3. Dynamic Loading

Add new agents **without restart**:

```python
# Create new_agent.py
class MyAgent(SpecialistAgent):
    __agent_metadata__ = {
        'name': 'MyAgent',
        'capabilities': ['my_task'],
    }

# Copy to plugins/
cp new_agent.py plugins/agents/

# Automatically detected and loaded
# Available immediately for routing
```

---

## Usage Patterns

### Pattern 1: Simple Task Execution

```python
result = await orchestrator.execute("Your task here")
print(result.output)
```

### Pattern 2: Batch Processing

```python
tasks = [
    "Task 1",
    "Task 2",
    "Task 3",
]

results = await orchestrator.execute_batch(
    tasks,
    max_concurrent=5
)

# All results
for result in results:
    print(f"{result.agent_name}: {result.output}")
```

### Pattern 3: Custom Routing

```python
from cohezion.swarm import AdaptiveRouter

router = AdaptiveRouter(registry)

# Get routing decision with metadata
decision = await router.route(
    task="Your task",
    strategy="greedy"  # or "adaptive", "explore"
)

print(f"Selected: {decision.agent_name}")
print(f"Confidence: {decision.confidence}")
print(f"Alternatives: {decision.alternative_agents}")
```

### Pattern 4: Tool Integration

```python
# Define tool
@agent.register_tool()
async def query_vault(query: str) -> list:
    """Query knowledge base."""
    return await vault.find_relevant(query)

# Agent uses tool automatically
result = await agent.execute(
    "Analyze this topic",
    use_tools=["query_vault"]
)
```

---

## Configuration

### Environment Variables

```bash
# Routing
COHEZION_ROUTING_LEARNING_RATE=0.3
COHEZION_ROUTING_HISTORY_SIZE=1000

# Performance
COHEZION_DEFAULT_TIMEOUT=60
COHEZION_MAX_CONCURRENT=10

# Paths
COHEZION_AGENT_MODULES_DIR=/home/user/agents
COHEZION_ROUTING_WEIGHTS_FILE=data/routing_weights.json
```

### Custom Specialists

```python
from cohezion.swarm import SpecialistAgent

MY_SPECIALIST = SpecialistAgent(
    name="MedicalSpecialist",
    description="Healthcare domain expert",
    model="medical-llm-v1",
    backend=BackendType.GPU_VULKAN,
    capabilities=["medical_qa", "symptoms"],
    validated=False,  # Mark as unvalidated
)
```

---

## Monitoring

### Performance Metrics

```python
# Get orchestrator stats
stats = orchestrator.get_stats()

print(f"Total executions: {stats['total_executions']}")
print(f"Success rate: {stats['success_rate']:.1%}")
```

### Routing Analytics

```python
from cohezion.swarm import AdaptiveRouter

router = AdaptiveRouter(registry)
stats = router.get_routing_stats()

print(f"Total routings: {stats['total_routings']}")
print(f"Avg confidence: {stats['avg_confidence']:.2f}")
print(f"Top agents: {stats['top_agents']}")
```

### Agent Performance

```python
# Per-agent metrics
agent = orchestrator.registry.get_agent("CodeSpecialist")
summary = agent.get_performance_summary()

print(f"Calls: {summary['total_calls']}")
print(f"Success rate: {summary['success_rate']:.1%}")
print(f"Avg latency: {summary['avg_latency_ms']:.1f}ms")
```

---

## Advanced Features

### Hot Reload

```python
# Start file watcher
await orchestrator.registry.start_watching(interval=5.0)

# Now edit agent file:
# vim src/cohezion/swarm/agents/my_agent.py

# Changes automatically detected and reloaded
# Zero downtime updates
```

### Fallback Chains

```python
# Automatic fallback on failure
result = await orchestrator.execute(
    "Complex task",
    fallback_on_error=True  # Try alternatives on failure
)

# Manually check alternatives
if not result.success:
    for agent in decision.alternative_agents:
        result = await orchestrator.execute_with_agent(agent, task)
```

### Performance Feedback

```python
# Explicitly provide feedback
await orchestrator.provide_feedback(
    decision=decision,
    outcome={
        "success": True,
        "latency_ms": 85,
        "quality_score": 0.92,
    }
)
```

---

## Troubleshooting

### Issue: Task routed to wrong agent

**Diagnosis**:
```python
decision = await orchestrator.router.route(task)
print(f"Features: {decision.features}")
print(f"Confidence: {decision.confidence}")
```

**Solution**: Provide feedback to correct routing

### Issue: New agent not recognized

**Check**:
```python
agents = orchestrator.registry.list_agents()
print([a.name for a in agents])

# Force reload
await orchestrator.registry._check_for_changes()
```

### Issue: High latency

**Check routing**:
```python
decision = await orchestrator.router.route(task)
print(f"Expected: {decision.expected_latency_ms}")
print(f"Alternative: {decision.alternative_agents}")

# Consider switching backend
```

---

## Best Practices

### 1. Task Design

**Good**:
```python
"Write a Python function that calculates the nth fibonacci number recursively"
```

**Bad**:
```python
"Help"  # Too vague
```

### 2. Context Size

- **<4K**: Use NPU (CodeSpecialist)
- **4K-64K**: Use GPU Vulkan (ReasoningSpecialist)
- **64K+**: Use Gemma-4-E2B (256K context)

### 3. Fallback Strategy

```python
# Always enable fallback for critical tasks
result = await orchestrator.execute(
    task,
    fallback_on_error=True,
    timeout=30.0,
)
```

### 4. Performance Monitoring

```python
# Regular health checks
stats = orchestrator.get_stats()
if stats['success_rate'] < 0.9:
    print("⚠️ Success rate below threshold")
```

---

## API Reference

### MultiAgentOrchestrator

| Method | Description |
|--------|-------------|
| `execute(task, context)` | Execute task with auto-routing |
| `execute_batch(tasks)` | Execute multiple tasks |
| `start()` | Initialize services |
| `stop()` | Cleanup |
| `get_stats()` | Performance statistics |

### AdaptiveRouter

| Method | Description |
|--------|-------------|
| `route(task, context)` | Get routing decision |
| `feedback(decision, outcome)` | Provide learning feedback |
| `get_routing_stats()` | Routing analytics |

### DynamicAgentRegistry

| Method | Description |
|--------|-------------|
| `get_agent(name)` | Get agent by name |
| `list_agents(capability)` | List agents (filtered) |
| `start_watching()` | Enable hot-reload |
| `register_from_file(path)` | Load agent from file |

---

## Examples

See `examples/multi_agent_demo.py` for complete working examples.

---

## Support

- **Issues**: File in GitHub
- **Documentation**: See `ADAPTIVE_MULTI_AGENT_DESIGN.md`
- **Tests**: Run `pytest tests/swarm/test_multi_agent_orchestration.py -v`

---

**Version**: 1.0.0 | **Last Updated**: 2026-04-10
