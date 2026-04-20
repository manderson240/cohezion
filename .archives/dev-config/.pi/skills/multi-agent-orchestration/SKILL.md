---
name: multi-agent-orchestration
description: Dynamic agent selection based on task characteristics with hardware-aware routing and self-improving feedback loops.
---

# Multi-Agent Orchestration Pattern

Use this pattern when you need:
- **Dynamic agent selection** based on task characteristics
- **Hardware-aware routing** (NPU → GPU → Cloud)
- **Self-improving routing** that learns from past performance
- **Hot-reload capability** for agents without restart
- **Specialized agents** for different task types

## Architecture

```
Task Input
    ↓
[TaskAnalyzer] → Extract features (code/reasoning/long_ctx)
    ↓
[AdaptiveRouter] → Score candidates, select optimal agent
    ↓
[DynamicAgentRegistry] → Get agent instance
    ↓
[SpecialistAgent] → Execute with appropriate backend
    ↓
[Feedback Loop] → Update success matrix
```

## Quick Start

### 1. Define Validated Specialists

```python
from cohezion.swarm import SpecialistAgent
from cohezion.swarm.compute_backend_router import BackendType

# Always validate performance first!
REASONING_SPECIALIST = SpecialistAgent(
    name="ReasoningSpecialist",
    description="Complex reasoning with long context",
    model="Gemma-4-E2B-it-GGUF",
    backend=BackendType.GPU_VULKAN,  # ✅ Validated: 97 TPS
    capabilities=["complex_reasoning", "long_context"],
    performance_stats={
        "tps": 97.26,  # Measured, not theoretical
        "latency_ms": 10.3,
        "context_window": 256000,
        "memory_mb": 4096,
    },
    validated=True,  # Mark only after benchmarking
    fallback_chain=["PhiSpecialist", "OpenAISpecialist"],
)
```

### 2. Add Tools (Optional)

```python
@REASONING_SPECIALIST.tool_registry.register()
async def query_vault(query: str) -> list:
    """Query knowledge base for context."""
    return await vault.find_relevant(query)
```

### 3. Execute Tasks

```python
from cohezion.swarm import MultiAgentOrchestrator
orch = await get_orchestrator()

# Automatically routed to best agent
result = await orch.execute(
    "Explain quantum computing simply",
)

print(f"Agent: {result.agent_name}")  # ReasoningSpecialist
print(f"Backend: {result.backend}")  # GPU_VULKAN
print(f"Latency: {result.latency_ms}ms")  # ~10ms
```

## Advanced Usage

### Custom Routing

```python
from cohezion.swarm import AdaptiveRouter

router = AdaptiveRouter(registry)

# Get routing decision with metadata
decision = await router.route(
    task="Your task",
    strategy="greedy",  # "adaptive" (default), "greedy", "explore"
)

print(f"Selected: {decision.agent_name}")
print(f"Confidence: {decision.confidence}")
print(f"Alternatives: {decision.alternative_agents}")
```

### Batch Processing

```python
tasks = ["Task 1", "Task 2", "Task 3"]
results = await orch.execute_batch(
    tasks,
    max_concurrent=5,  # Limit concurrent executions
)

for result in results:
    print(f"{result.agent_name}: {result.output}")
```

### Providing Feedback (Learning)

```python
# After execution, provide feedback
await router.feedback(
    decision,
    {
        "success": True,
        "latency_ms": 85,
        "quality_score": 0.92,
    }
)
# System learns: this agent good for this task type
```

### Hot-Reload Agents

```python
# Start file watcher
await orch.registry.start_watching(interval=5.0)

# Now edit agent files - changes auto-detected!
# vim src/cohezion/swarm/agents/modules/my_agent.py

# Zero-downtime reload happens automatically
```

### Register New Agent at Runtime

```python
# Create new agent file
await orch.registry.register_from_file("path/to/new_specialist.py")

# Immediately available for routing!
```

## Design Patterns

### Pattern 1: Hardware-First Agent Design

**Problem**: Agents assigned to backends that don't work  
**Solution**: Validate before adding

```python
# ❌ Bad: Theoretical assignment
SpecialistAgent(
    model="some-model",
    backend=BackendType.GPU_ROCM,  # May hang!
    validated=False,
)

# ✅ Good: Validated assignment
SpecialistAgent(
    model="Gemma-4-E2B",
    backend=BackendType.GPU_VULKAN,  # Tested: 97 TPS
    performance_stats={"tps": 97.26},  # Measured
    validated=True,
)
```

### Pattern 2: Fallback Chains

**Problem**: Single agent failure blocks task  
**Solution**: Predefined alternatives

```python
REASONING_SPECIALIST = SpecialistAgent(
    name="ReasoningSpecialist",
    fallback_chain=["PhiSpecialist", "OpenAISpecialist"],
)

# If ReasoningSpecialist fails, automatically tries PhiSpecialist
```

### Pattern 3: Capability Matching

**Problem**: Code task routed to chat agent  
**Solution**: Feature extraction + capability scoring

```python
# Router automatically detects:
# - "Write a function" → has_code=True → CodeSpecialist
# - "Summarize document" → has_long_context=True → ReasoningSpecialist
# - "Explain quantum" → has_reasoning=True → ReasoningSpecialist
```

## Testing Patterns

### Async Fixture Testing

```python
import pytest_asyncio

@pytest_asyncio.fixture
async def registry():
    """Works with pytest-asyncio strict mode."""
    reg = DynamicAgentRegistry()
    yield reg
    await reg.stop_watching()

@pytest.mark.asyncio
async def test_agent_routing(registry):
    """Test async code correctly."""
    router = AdaptiveRouter(registry)
    decision = await router.route("Test task")
    assert hasattr(decision, 'agent_name')
```

### Duck Typing for Resilience

```python
# ❌ Brittle - fails if multiple RoutingDecision classes
assert isinstance(decision, RoutingDecision)

# ✅ Resilient - works across module boundaries
assert hasattr(decision, 'agent_name')
assert hasattr(decision, 'confidence')
assert decision.confidence > 0
```

## Common Pitfalls

### ❌ Don't: Register Unvalidated Models

```python
# Never add without benchmarking
SpecialistAgent(
    model="random-model-from-huggingface",
    backend=BackendType.GPU_ROCM,  # ❌ May not work!
    validated=True,  # ❌ LIE! Never validated
)
```

### ❌ Don't: Ignore Fallbacks

```python
# Fragile - single point of failure
SpecialistAgent(
    name="OnlyAgent",
    fallback_chain=[],  # ❌ No alternatives
)
```

### ❌ Don't: Block on Agent Loading

```python
# ❌ Synchronous loading blocks event loop
registry.register_from_file_sync("agent.py")  # Blocks!

# ✅ Async loading keeps system responsive
await registry.register_from_file("agent.py")
```

### ✅ Do: Use Type-Checking Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cohezion.swarm.dynamic_agent_registry import AgentModule
```

## Performance Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| Routing Decision | <10ms | 0.1ms |
| Agent Retrieval | <1ms | 0.01ms |
| Hot-Reload | <5s | ~1s |
| Learning Update | <1ms | Async |
| Batch Throughput | 100/s | 500/s |

## Integration with Cohezion

### FLUME-First Design

```python
# Tasks encode/decode through FLUME before routing
task_vector = await flume.encode(task)
# Router uses latent space for similarity matching
```

### Vault MCP Integration

```python
@agent.register_tool()
async def get_context_from_vault(query: str):
    """Query vault for relevant prior work."""
    return await mcp.vault_find_relevant_context(query)
```

### HIHO Alignment

```python
from cohezion.compound import CompoundSessionManager

mgr = CompoundSessionManager()
success, result = await mgr.execute_aligned(
    request=task,
    execute_fn=orchestator.execute,  # Our orchestrator
    skill_name="multi_agent",
    threshold=0.7,  # HIHO gate
)
```

## Files and Locations

```
src/cohezion/swarm/
├── specialist_agents.py           # Specialist definitions
├── dynamic_agent_registry.py    # Hot-reload, registration
├── adaptive_router.py           # Learning engine
├── multi_agent_orchestrator.py # Execution pipeline
└── __init__.py                  # Public API

tests/swarm/
└── test_multi_agent_orchestration.py  # Example tests

examples/
└── multi_agent_demo.py          # Working demonstration

docs/
└── MULTI_AGENT_GETTING_STARTED.md  # User guide
```

## References

- **Implementation**: `cloud-vault-mcp/vault/cortex/multi-agent-orchestration-implementation-complete.md`
- **Phase 2**: `cloud-vault-mcp/vault/cortex/multi-agent-phase2-integration-complete.md`
- **Design**: `~/gemma4-npu-conversion/ADAPTIVE_MULTI_AGENT_DESIGN.md`
- **Architecture**: `~/gemma4-npu-conversion/INTEGRATED_ARCHITECTURE.md`

## See Also

- `cohezion-patterns` skill - Compound engineering patterns
- `cohezion-test` skill - Testing patterns for Cohezion
- `compute-backend-router` - Hardware-aware routing

---

**Version**: 1.0  
**Last Updated**: 2026-04-10  
**Status**: Production Ready
