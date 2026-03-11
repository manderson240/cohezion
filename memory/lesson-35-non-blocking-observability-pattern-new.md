---
title: Non-Blocking Observability Pattern: Telemetry Must Never Interrupt Primary Workflow
date: 2026-02-23
severity: MEDIUM
category: architecture
cost_of_forgetting: "Primary workflow stalls when telemetry is slow or fails; 100+ second latency from synchronous metric writes"
tags: [observability, telemetry, non-blocking, async, patterns]
status: validated
aspect: knower
neural:
  activation: 0.463
  stage: growing
  cluster: lessons
---

# Lesson: Non-Blocking Observability Pattern: Telemetry Must Never Interrupt Primary Workflow

## Context

During Cohezion agent pipeline development in February 2026, telemetry calls were placed in the critical path of agent workflows: after each agent step, metrics were recorded synchronously to an external service. When the telemetry service was slow (high latency) or unavailable (network errors), the primary workflow -- code generation, testing, verification -- stalled waiting for metric writes. A single slow telemetry endpoint added 2-5 seconds per write, and with 50+ observations per session, this accumulated to 100-250 seconds of dead time.

## Problem

Synchronous telemetry creates two categories of failure:

1. **Latency injection**: Even when the telemetry service is healthy, network round trips add latency to every observation. This latency is invisible in the primary workflow's output but degrades overall session time.
2. **Availability coupling**: When the telemetry service is down, the primary workflow is down. A non-essential monitoring system becomes a single point of failure for the entire agent pipeline.

This is the architectural complement to [[lesson-28-non-critical-tracking-pattern]], which addresses the same problem for Pilot Memory saves. This lesson focuses on the buffered write pattern for high-frequency metric recording.

## Core Learning

**All telemetry, metrics, and observability operations must be non-blocking. Use async, fire-and-forget, or buffered writes.**

### Pattern
```python
from collections import deque

_telemetry_buffer = deque(maxlen=1000)

def record_metric(name, value, tags=None):
    # Best-effort -- never raises, never blocks.
    try:
        _telemetry_buffer.append({"name": name, "value": value, "tags": tags or {}})
    except Exception:
        pass  # Truly non-blocking
```

## Solution

A bounded buffer pattern was implemented for all metric recording:

1. **Bounded deque**: `deque(maxlen=1000)` stores metrics in memory. When the buffer fills, old metrics are silently dropped.
2. **No exceptions**: The `record_metric()` function catches all exceptions and returns without raising. It cannot fail.
3. **Background flush**: A separate background task periodically flushes the buffer to the telemetry service. If the flush fails, the buffer continues accumulating until the service recovers.
4. **Acceptable loss**: Under high load, some metrics may be lost. This is acceptable because telemetry is statistical, not transactional.

## Prevention

- **Buffer all telemetry**: Never make synchronous network calls for metric recording
- **Bounded queues**: Use `deque(maxlen=N)` to prevent unbounded memory growth
- **No exceptions from telemetry**: Catch everything; telemetry code must never raise
- **Background flush**: Decouple metric recording (fast, in-process) from metric delivery (slow, network)

## Cost of Forgetting

- **100-250 second session latency** from synchronous metric writes
- **Pipeline stalls** when telemetry service is unavailable
- **Cascading availability failure**: Monitoring outage becomes primary workflow outage

## Recommendations

### Do
- Buffer all telemetry writes with bounded queues
- Use async fire-and-forget for metric recording
- Accept metric loss under high load as acceptable

### Don't
- Block primary workflow on metric writes
- Raise exceptions from telemetry operations

## Related Concepts

- [[compound-engineering]] - Non-blocking observability enables compound system reliability
- [[operational-data-ai-agents]] - telemetry must be isolated from primary data flow
- [[lesson-28-non-critical-tracking-pattern]] - the complementary pattern for Pilot Memory saves
- [[non-blocking-observability]] - the concept that both this lesson and lesson-28 implement
- [[2026-02-10-telemetry-corruption-fix]] - related: isolating telemetry write paths from primary data

## Validation

**Discovered**: Feb 2026 in Cohezion agent pipeline
**Impact**: Eliminated 100-250 seconds of telemetry-induced latency per session
**Status**: Validated
