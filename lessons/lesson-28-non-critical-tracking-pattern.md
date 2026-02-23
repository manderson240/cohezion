---
title: Non-Critical Tracking Pattern: Background Observations Must Not Block Primary Workflow
date: 2026-02-23
severity: LOW
category: agent-workflow
tags: [observability, tracking, agent-workflow, non-blocking]
status: validated
---

# Lesson: Non-Critical Tracking Pattern: Background Observations Must Not Block Primary Workflow

## Context

Tracking and observability operations (saving to memory, writing metrics) were blocking primary workflow steps. When memory saves failed, the entire agent pipeline stalled.

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

## Recommendations

### Do
- Wrap all tracking operations in try/except with warning-level logging
- Use async fire-and-forget for non-critical tracking

### Don't
- Let tracking system failures propagate to primary workflow
- Block on memory writes in the critical path

## Related Concepts

- [[compound-engineering]] - Non-blocking observability enables compound system resilience

## Validation

**Discovered**: Feb 2026 in Cohezion agent pipeline
**Status**: Validated
