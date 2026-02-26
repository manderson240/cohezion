---
title: System Lockup 2026-01-27: Resource Exhaustion from Unbound Agent Loops
date: 2026-02-23
severity: CRITICAL
category: infrastructure
tags: [system-lockup, resource-exhaustion, agent-loops, safety]
status: validated
---

# Lesson: System Lockup 2026-01-27: Resource Exhaustion from Unbound Agent Loops

## Context

On 2026-01-27, the development system locked up due to an agent loop that consumed all available RAM. The loop spawned sub-processes without bound, each allocating model inference memory. Recovery required a hard reboot.

## Core Learning

**All agent loops MUST have explicit termination conditions and resource guards. Unbounded loops are a production hazard.**

### Pattern
```python
MAX_ITERATIONS = 50
MAX_RUNTIME_SECONDS = 3600
start_time = time.time()

for i in range(MAX_ITERATIONS):
    if time.time() - start_time > MAX_RUNTIME_SECONDS:
        break
    result = agent_step(state)
    if result.done:
        break
    if psutil.virtual_memory().percent > 85:
        logger.error("Memory pressure -- terminating agent loop")
        break
```

## Recommendations

### Do
- Set MAX_ITERATIONS on ALL agent loops
- Set MAX_RUNTIME_SECONDS as a hard cap
- Save checkpoints so recovery is possible without full restart

### Don't
- Use while True loops without explicit break conditions
- Skip resource monitoring in production agent systems

## Related Concepts

- [[agentic-ai]] - Core safety property for all agent systems
- [[scaling-agent-systems]] - The paper's findings on error amplification and capability saturation include resource exhaustion as a failure mode; explicit loop termination guards are prerequisite for safe multi-agent scaling
- [[openai-codex-agent-loop]] - The Codex inner/outer loop architecture describes how agent loops must have explicit termination conditions; unbounded loops are the failure mode this lesson documents

## Validation

**Incident**: 2026-01-27 system lockup
**Impact**: Hard reboot required, session state lost
**Status**: Guards now mandatory for all production agent loops
