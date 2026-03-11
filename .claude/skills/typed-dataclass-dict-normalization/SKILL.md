---
name: typed-dataclass-dict-normalization
description: |
  Fix for AttributeError when a typed dataclass field receives a plain dict.
  Use when: (1) AttributeError: 'dict' object has no attribute 'X' on a
  field typed as a dataclass, (2) tests pass dicts but production code
  uses attribute access on that field, (3) ExecutionResult.metrics typed
  as ExecutionMetrics but callers pass {"metric_value": ..., "duration_seconds": ...}.
author: Claude Code
version: 1.0.0
---

# Typed Dataclass / Dict Normalization

## Problem

A dataclass field is typed as `SomeDataclass` but callers (especially tests
or legacy code) pass plain `dict`. The consumer accesses attributes
(`result.field_name`) which works on dataclasses but raises `AttributeError`
on dicts (`'dict' object has no attribute 'field_name'`).

## Trigger Conditions

- `AttributeError: 'dict' object has no attribute 'duration_seconds'`
- A test file creates `SomeResult(metrics={"key": value, ...})`
- Production code accesses `result.metrics.key` or `result.metrics.duration_seconds`
- The field is annotated as `metrics: ExecutionMetrics` but no validator enforces it

## Solution

Two valid approaches depending on context:

### Option A: Fix callers (preferred when tests are isolated)

Change test/caller code to use the proper dataclass:
```python
# Before
ExecutionResult(metrics={"duration_seconds": 1.0, "total_tokens": 100})

# After
from cohezion.compound.models import ExecutionMetrics
ExecutionResult(metrics=ExecutionMetrics(duration_seconds=1.0, total_tokens=100))
```

### Option B: Add isinstance() normalization in production code (when callers are diverse)

When many callers exist or the field genuinely accepts both:
```python
def _log_experiment(self, exp_id: str, result: ExecutionResult) -> None:
    m = result.metrics
    if isinstance(m, dict):
        # Legacy dict path
        metric_value = m.get("metric_value", float("inf"))
        duration_seconds = m.get("duration_seconds", 0.0)
        improved = m.get("improved", False)
    else:
        # Typed dataclass path
        metric_value = getattr(m, "metric_value", float("inf"))
        duration_seconds = m.duration_seconds
        improved = getattr(m, "improved", False)
```

## Verification

```bash
uv run pytest tests/research/ -q --no-cov --tb=short
# All tests pass; no AttributeError for 'dict' object
```

## Key Insight

`getattr(dict_obj, "key", default)` does NOT access dict items — it accesses
object attributes (like dict methods: `.keys`, `.values`, `.items`). To read
a dict item, you must use `dict_obj.get("key", default)` or `dict_obj["key"]`.
This is why `getattr(m, "metric_value", float("inf"))` silently returns
`float("inf")` on a dict even when `m["metric_value"]` would return `2.5`.
