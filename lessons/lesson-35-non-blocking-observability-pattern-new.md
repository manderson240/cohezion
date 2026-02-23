---
title: Non-Blocking Observability Pattern: Telemetry Must Never Interrupt Primary Workflow
date: 2026-02-23
severity: MEDIUM
category: architecture
tags: [observability, telemetry, non-blocking, async, patterns]
status: validated
---

# Lesson: Non-Blocking Observability Pattern: Telemetry Must Never Interrupt Primary Workflow

## Context

Synchronous telemetry and observability calls were inserted in the critical path of agent workflows. When these calls were slow or failed, the primary workflow stalled.

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

## Validation

**Discovered**: Feb 2026 in Cohezion agent pipeline
**Status**: Validated
