---
title: Non-Critical Tracking Pattern: Background Observations Must Not Block Primary Workflow
date: 2026-02-23
severity: LOW
category: agent-workflow
cost_of_forgetting: "Agent pipeline stalls when observability system is down; primary work blocked by non-essential tracking"
tags: [observability, tracking, agent-workflow, non-blocking]
status: validated
aspect: knower
neural:
  activation: 0.460
  stage: growing
  cluster: lessons
---

# Lesson: Non-Critical Tracking Pattern: Background Observations Must Not Block Primary Workflow

## Context

During Cohezion agent pipeline development in February 2026, the Pilot Memory service experienced intermittent downtime (network issues, rate limits). During these outages, the agent pipeline stalled completely because `save_to_memory()` calls were synchronous and raised exceptions on failure. The primary work (code generation, testing, verification) was blocked by a non-essential observability operation.

## Problem

Coupling tracking to the primary workflow creates a fragile dependency:

1. **Memory system down**: `save_to_memory()` raises `ConnectionError`. The exception propagates through the pipeline, halting all work.
2. **Metric writes slow**: A slow metrics endpoint adds 2-5 seconds per observation. Over 50 observations per session, this adds 100-250 seconds of latency to the primary workflow.
3. **Cascading failure**: When the tracking system fails, the primary workflow fails. The tracking failure is logged, but the primary work -- the actual value delivery -- is lost.

The fundamental error is treating observability operations as critical path. They are not. Primary work must continue even when tracking fails entirely.

## Core Learning

**Observability and tracking are non-critical. Failures in tracking must never block primary work. Use fire-and-forget or best-effort patterns.**

### Pattern
```python
# WRONG: blocking tracking
result = do_work()
save_to_memory(result)  # Blocks if memory system is down

# RIGHT: non-blocking tracking
result = do_work()
try:
    save_to_memory(result)  # Best-effort
except Exception as e:
    logger.warning(f"Memory save failed (non-critical): {e}")
return result  # Work continues regardless
```

## Solution

All tracking and observability operations were wrapped in best-effort patterns:

1. **try/except with warning log**: Every tracking call is wrapped. Failures log a warning and continue.
2. **Bounded buffers**: Metrics use a `deque(maxlen=1000)` buffer (see [[lesson-35-non-blocking-observability-pattern-new]]). If the buffer overflows, old metrics are silently dropped.
3. **Async fire-and-forget**: For network-based tracking (memory saves), async calls with short timeouts ensure the primary workflow is never blocked.

## Prevention

- **Classify operations as critical or non-critical at design time**: If the operation is observability/tracking, it is non-critical
- **Wrap tracking in try/except**: Every observability call, without exception
- **Use bounded buffers**: Accept metric loss under high load as acceptable
- **Set short timeouts**: Tracking network calls should timeout in 2-3 seconds, not the default 30-60

## Cost of Forgetting

- **Primary work blocked**: Agent pipeline stalls when tracking system is down
- **100-250 second latency**: Slow tracking calls accumulate into significant session overhead
- **Cascading availability failure**: Tracking system outage becomes pipeline outage

## Recommendations

### Do
- Wrap all tracking operations in try/except with warning-level logging
- Use async fire-and-forget for non-critical tracking

### Don't
- Let tracking system failures propagate to primary workflow
- Block on memory writes in the critical path

## Related Concepts

- [[compound-engineering]] - Non-blocking observability enables compound system resilience
- [[operational-data-ai-agents]] - observability failures that block pipelines corrupt operational data quality
- [[lesson-35-non-blocking-observability-pattern-new]] - the complementary pattern: buffered telemetry that never blocks
- [[non-blocking-observability]] - the concept that this lesson implements in practice
- [[2026-02-10-telemetry-corruption-fix]] - related: telemetry sharing the write path with primary data

## Validation

**Discovered**: Feb 2026 in Cohezion agent pipeline -- pipeline stalled during memory service outage
**Status**: Validated -- all tracking operations now use best-effort patterns
