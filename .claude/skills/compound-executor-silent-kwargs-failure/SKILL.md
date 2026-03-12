---
name: compound-executor-silent-kwargs-failure
description: |
  Fix for tests where CompoundExecutor always reports success=False even though
  execute functions return successfully. Root cause: execute function returns dict
  with keys not accepted by ExecutionMetrics(**metrics_dict), raising TypeError
  that is silently caught by `except Exception` in _attempt_execution, converting
  every "success" into a failure. Use when: (1) session.experiments_completed is 0
  or all retries exhausted despite execute function running normally, (2) call_count
  increments but completion count stays at 0, (3) no visible error in test output.
  Valid ExecutionMetrics keys: prompt_tokens, completion_tokens, total_tokens,
  duration_seconds, coherence, quality_score, cache_hit_rate.
author: Claude Code
version: 1.0.0
---

# CompoundExecutor Silent kwargs Failure

## Problem

`CompoundExecutor._attempt_execution` constructs `ExecutionMetrics` using:

```python
metrics = ExecutionMetrics(duration_seconds=duration, **metrics_dict)
```

If `metrics_dict` contains keys that `ExecutionMetrics` doesn't accept (e.g., `metric_value`,
`improvement`, `skill_name`), Python raises `TypeError: __init__() got an unexpected keyword
argument`. This exception is caught by the generic `except Exception` in the executor's retry
loop, which marks the attempt as failed — **silently, with no test output warning**.

## Trigger Conditions

- Test's execute function returns `(str, dict)` with dict keys like `metric_value`, `improvement`, `skill_name`
- `session.experiments_completed` stays at 0 despite `call_count` incrementing
- `assert call_count[0] == 3` passes but `assert session.experiments_completed == 3` fails
- No `TypeError` visible in test output (caught internally)

## Valid ExecutionMetrics Fields

Only these keys are valid in the metrics dict returned by execute functions:

```python
{"prompt_tokens", "completion_tokens", "total_tokens",
 "duration_seconds", "coherence", "quality_score", "cache_hit_rate"}
```

## Solution

Fix execute functions in tests to return only valid `ExecutionMetrics` keys:

```python
# WRONG — these keys don't exist on ExecutionMetrics
def execute(task, context):
    return "result", {"metric_value": 0.9, "improvement": 0.1, "skill_name": "x"}

# CORRECT — use only valid ExecutionMetrics fields
def execute(task, context):
    return "result", {"coherence": 0.8, "total_tokens": 10}
```

Define a module-level constant for test reuse:

```python
_VALID_METRICS: dict = {"coherence": 0.8, "total_tokens": 10}

def execute(task, context):
    return f"Result {call_count[0]}", _VALID_METRICS
```

## Verification

```bash
uv run pytest tests/research/test_compound_integration.py -q --tb=short
# Should show: N passed (not 0 passed, N errors or N failed)
```

Add a debug assertion if unsure — temporarily raise inside the except to see the real error:

```python
# In executor._attempt_execution, temporarily change:
except Exception as e:
    raise  # See the real exception
```

## Where the Silent Catch Lives

`src/cohezion/compound/core/executor.py` → `_attempt_execution` method:

```python
try:
    output, metrics_dict = self.execute_fn(task, context)
    metrics = ExecutionMetrics(duration_seconds=duration, **metrics_dict)
    ...
    return ExecutionResult(success=True, ...)
except Exception as e:
    logger.debug(f"Attempt failed: {e}")
    return ExecutionResult(success=False, ...)  # ← silently swallowed here
```
