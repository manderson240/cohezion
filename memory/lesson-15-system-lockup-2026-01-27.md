---
title: System Lockup 2026-01-27: Resource Exhaustion from Unbound Agent Loops
date: 2026-02-23
severity: CRITICAL
category: infrastructure
cost_of_forgetting: "System lockup requiring hard reboot; all in-progress session state lost permanently"
tags: [system-lockup, resource-exhaustion, agent-loops, safety]
status: validated
aspect: knower
neural:
  activation: 0.472
  stage: growing
  cluster: lessons
---

# Lesson: System Lockup 2026-01-27: Resource Exhaustion from Unbound Agent Loops

## Context

On 2026-01-27, during a multi-agent compound engineering session, the development workstation became completely unresponsive. The OOM (Out of Memory) killer was triggered, but not before the system had exhausted all swap space. Recovery required a hard power-off reboot. All in-progress session state was lost -- continuation files had not been written yet because the session was still in its first hour.

## Problem

The root cause was an agent retry loop without termination conditions:

1. An agent task failed due to a transient network error (Ollama connection refused)
2. The orchestrator retried the task in a `while True` loop with no iteration limit
3. Each retry spawned a new sub-process that loaded the embedding model into memory (~2GB per instance)
4. After approximately 8 retries, the system had allocated 16GB+ of process memory for failed agent instances that never cleaned up
5. The OOM killer terminated processes, but the agent loop kept spawning new ones faster than they could be killed

The critical failure was the absence of three safety guards: no iteration limit, no runtime cap, and no memory pressure check.

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

## Solution

Three layers of protection were implemented for all agent loops:

1. **Iteration limit (`MAX_ITERATIONS`)**: Every loop uses `for i in range(MAX_ITERATIONS)` instead of `while True`. The default is 50 iterations.
2. **Runtime cap (`MAX_RUNTIME_SECONDS`)**: A wall-clock timeout (default: 3600 seconds) breaks the loop regardless of iteration count.
3. **Memory pressure guard**: Before each iteration, check `psutil.virtual_memory().percent`. If above 85%, terminate gracefully and save checkpoints.

Additionally, checkpoint saving was added so recovery from a terminated loop does not require restarting from scratch.

## Prevention

- **Never use `while True` without break conditions**: Always use `for i in range(limit)` with explicit break conditions
- **Three guards minimum**: Iteration limit + runtime cap + memory pressure check
- **Save checkpoints**: After each successful loop iteration, save state so recovery is possible
- **Test termination conditions**: Write tests that verify the loop terminates under failure conditions

## Cost of Forgetting

- **Complete system lockup**: All processes killed, including the development environment
- **Session state loss**: Continuation files not written; all in-progress work is gone
- **Hard reboot required**: No graceful recovery possible when OOM + infinite spawn interact
- **Multi-hour recovery**: Rebooting, restoring state, and restarting the session

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
- [[scaling-agent-systems]] - Error amplification and resource exhaustion as failure modes in multi-agent systems
- [[openai-codex-agent-loop]] - Agent loop architecture with explicit termination conditions
- [[ai-safety]] - unbounded loops are a direct AI safety failure; resource guards are mandatory safety mechanisms
- [[agent-loop-architecture]] - loop termination guards are a non-negotiable architectural requirement

## Validation

**Incident**: 2026-01-27 system lockup
**Impact**: Hard reboot required, session state lost
**Status**: Guards now mandatory for all production agent loops
