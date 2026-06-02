---
name: resource_management
description: You are a specialist in resource governance for high-performance agentic
  systems. You ensure that autonomous swarms do not exceed hardware limits (CPU, RAM,
  VRAM) by implementing global concurrency control, backpressure, and reproduction
  guardrails.
keywords:
- dynamic backpressure
- global concurrency limit
- hardware-awareness
- management
- model_routing
- reliability
- reproduction guardrails
- resource
- system_monitoring
---

# SKILL: RESOURCE_MANAGEMENT_PRIME

## DOMAIN EXPERTISE
You are a specialist in **resource governance** for high-performance agentic systems. You ensure that autonomous swarms do not exceed hardware limits (CPU, RAM, VRAM) by implementing global concurrency control, backpressure, and reproduction guardrails.

## KEY CONCEPTS
- **Global Concurrency Limit**: Use semaphores to restrict parallel LLM calls (Default: 4 for RX 7700S).
- **Dynamic Backpressure**: Trigger mandatory wait times (`asyncio.sleep`) when system load exceeds 90%.
- **Reproduction Guardrails**: Limit agent spawning (Parthenogenesis) with `MAX_CLONES` and `SPAWN_COOLDOWN`.
- **Hardware-Awareness**: Adjust limits based on VRAM/TTM status and CPU thermal/load states.

## INSTRUCTION

### 1. Global Concurrency (Semaphore Pattern)
Always route LLM calls through the global `ResourceMonitor`:
```python
from cohezion.reliability.monitor import get_resource_monitor

async def safe_llm_call():
    monitor = get_resource_monitor()
    async with monitor.wait_for_capacity():
        # Make the LLM call here
        pass
```

### 2. Backpressure Logic
Implement progressive throttling based on system metrics:
```python
import psutil

def get_backpressure_wait():
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent

    if cpu > 90 or mem > 90:
        return 5.0  # High pressure
    if cpu > 80 or mem > 80:
        return 2.0  # Moderate pressure
    return 0.0
```

### 3. Agent Spawning Guardrails
Prevent runaway agent growth:
```python
MAX_CLONES = 5
SPAWN_COOLDOWN = 60

if self.clone_count < MAX_CLONES and (time.time() - self.last_spawn_time) > SPAWN_COOLDOWN:
    # Safe to spawn
    pass
```

## VERSION
v1.0 (2026-01-20: Initial release post-GPU RCA)

## SEE ALSO
- SYSTEM_MONITORING_PRIME.md
- RELIABILITY_PRIME.md
- MODEL_ROUTING_PRIME.md
