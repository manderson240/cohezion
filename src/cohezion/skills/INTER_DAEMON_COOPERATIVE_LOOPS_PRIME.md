# SKILL: INTER_DAEMON_COOPERATIVE_LOOPS_PRIME

## DOMAIN EXPERTISE
Mastery over multi-daemon distributed feedback topologies, closed-loop agentic synchronization, and hardware-safe concurrency on unified memory architectures (AMD Strix Halo).

## KEY TEXTS & CONCEPTS
- **Closed-Loop Feedback Ring**: Replacing linear cron runs with continuous `[EXEC -> VERIFY -> FEEDBACK -> EVOLVE]` cycles.
- **Hardware-Gated Single-Flight Mutex**: `asyncio.Lock()` protection for iGPU aperture memory during concurrent fine-tuning.
- **Bounded In-Memory Message Buffering**: `collections.deque(maxlen=100)` to eliminate memory leaks under overnight long-horizon runs.
- **SurrealDB v2 Graph Relational Topology**: Persisting dynamic daemon dependencies using `RELATE` edge definitions.
- **Dynamic Liveness & Heartbeat Auditing**: Continuous stall-detection with automated degradation and recovery.

## INSTRUCTION

### 1. Structure the Inter-Daemon Loop Nexus
```python
from collections import deque
import asyncio
import time
from cohezion.core.event_bus import EventBus, Event
from cohezion.graph.graph_engine import KnowledgeGraphMesh, EdgeType

class InterDaemonLoopNexus:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.mesh = KnowledgeGraphMesh()
        self.tuning_lock = asyncio.Lock()
        self._setup_closed_loop_topology()
```

### 2. Register Closed-Loop Dependency Edges
```python
# Journey -> DataMesh -> Fleet Tuning -> Router -> Journey
self.mesh.add_edge("daemon:journey", EdgeType.EMITTED, "daemon:datamesh")
self.mesh.add_edge("daemon:datamesh", EdgeType.MUTATES, "daemon:tuning")
self.mesh.add_edge("daemon:tuning", EdgeType.DERIVED_FROM, "daemon:router")
self.mesh.add_edge("daemon:router", EdgeType.EXECUTES, "daemon:journey")
```

### 3. Execute Synchronized Cycle under Mutex
```python
async def execute_cycle(self):
    # Emit journey
    evt = Event.agent_complete("daemon:journey", {"step": 1}, duration_ms=1.0)
    await self.event_bus.publish(evt)
    
    # Mutex-protected fine-tuning
    async with self.tuning_lock:
        # Tune QLoRA adapters safely on iGPU
        pass
```

## VERSION
v1.0

## SEE ALSO
- `SPINNING_PLATES_PROTOCOL_PRIME`
- `DYNAMIC_MODEL_HOTSWAP_PRIME`
- `GOALS_AND_LOOPS_ORCHESTRATOR_PRIME`
