---
name: fastapi-json-float-infinity
description: |
  Fix for "ValueError: Out of range float values are not JSON compliant: inf"
  in FastAPI responses. Occurs when Python code uses float('inf'), float('-inf'),
  or float('nan') as sentinel values that end up in API response payloads.
  Python's json module accepts Infinity literals but the JSON spec does not.
  FastAPI's response serialization rejects non-finite floats.
  Use when FastAPI returns 500 with "Out of range float values are not JSON
  compliant" or when test assertions fail on response.json() with that error.
author: Claude Code
version: 1.0.0
---

# FastAPI JSON Float Infinity Serialization

## Problem

FastAPI raises `ValueError: Out of range float values are not JSON compliant: inf`
when a response model contains `float('inf')`, `float('-inf')`, or `float('nan')`.

This typically happens with:
- Metrics/statistics that use `float('inf')` as initial "best" value sentinels
- ML training code that produces NaN/inf loss values
- Uninitialized fields defaulting to infinity

## Root Cause

The JSON spec does not allow `Infinity`, `-Infinity`, or `NaN` as values.
Python's `json` module accepts them in `json.loads()` (producing Python floats),
but **rejects** them in `json.dumps()` by default. FastAPI's response serializer
inherits this restriction.

## Fix

Add sanitization helpers that convert non-finite floats to `None`:

```python
import math
from typing import Any

def _sanitize_metric(value: float | None) -> float | None:
    """Return None for non-finite floats (inf, -inf, nan) to keep JSON valid."""
    if value is None or not math.isfinite(value):
        return None
    return value

def _sanitize_json(obj: Any) -> Any:
    """Recursively replace non-finite floats with None for JSON compliance."""
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(item) for item in obj]
    return obj
```

Apply at the response boundary:

```python
# For single values in response models
return MyResponse(
    best_metric=_sanitize_metric(agent.session.best_metric),
    other_metric=_sanitize_metric(result.score),
)

# For arbitrary nested dicts (e.g., experiment logs)
return {"experiments": [_sanitize_json(exp) for exp in experiment_list]}
```

## Alternative: Custom JSON encoder

For broader coverage, configure FastAPI to use a custom encoder globally:

```python
import json
import math

class InfSafeEncoder(json.JSONEncoder):
    def iterencode(self, obj, _one_shot=False):
        yield from super().iterencode(_sanitize_json(obj), _one_shot)

app = FastAPI()
app.json_encoder = InfSafeEncoder
```

## Verification

```bash
# Test endpoint returns 200 (not 500) with inf sentinel values present
uv run pytest tests/api/test_research_endpoints.py -v -k "status or results"
```

## Notes

- `math.isfinite(x)` returns `False` for `inf`, `-inf`, and `nan`
- Converting to `None` is correct for JSON — consumers treat `null` as "no value"
- The issue is usually in sentinel values like `best_metric = float('inf')` that
  never get updated before the response is returned
