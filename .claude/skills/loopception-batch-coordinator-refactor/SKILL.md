---
name: loopception-batch-coordinator-refactor
description: |
  Pattern for refactoring a serial coordinator loop to batch-window dispatch.
  Use when: (1) LoopCoordinator calls execute_task() serially but execute_batch() exists,
  (2) coordinator test mocks have `del m.execute_batch` forcing sequential path,
  (3) upgrading throughput from 1× to batch_size× without breaking cloud escalation semantics.
  Key pitfall: tests that del m.execute_batch break immediately when coordinator calls batch.
  Must supply task_id-keyed result dicts in mock, not just success/failure booleans.
author: Claude Code
version: 1.0.0
---

# Loopception Batch-Window Coordinator Refactor

## Problem

`LoopCoordinator.run()` executes tasks ONE at a time via `local_exec.execute_task()`.
`LocalImprovementExecutor.execute_batch()` exists (ThreadPoolExecutor, 3× throughput)
but is never called. Coordinator tests intentionally suppress it with `del m.execute_batch`.

Three gaps:
1. **Throughput**: Serial → batch = 3× wall-clock improvement
2. **Verification**: `"completed without exception"` trivially passes — no real quality signal
3. **Complexity**: All tasks default to `category="synthesis"` — no routing signal

## Solution

### 1. Batch-window dispatch in coordinator (coordinator.py)

Replace the serial loop body with:
```python
# Add to LoopConfig:
batch_size: int = 3

# In run() loop body:
batch: list[Any] = []
cloud_task = None
next_task = remaining[0]

if fail_counts.get(next_task.id, 0) >= self.config.cloud_escalation_threshold or local_exec is None:
    cloud_task = remaining.pop(0)
else:
    while remaining and len(batch) < self.config.batch_size:
        candidate = remaining[0]
        if fail_counts.get(candidate.id, 0) < self.config.cloud_escalation_threshold and local_exec is not None:
            remaining.pop(0)
            batch.append(candidate)
        else:
            break

if batch and local_exec is not None:
    results = local_exec.execute_batch(batch, self.config.worktree_path)
    result_by_id = {r["task_id"]: r for r in results}
    for task in batch:
        result = result_by_id.get(task.id, {"success": False, "tokens_used": 0})
        # ... record result
    # Cloud re-queueing: preserve escalation semantics for repeated failures
    cloud_escalate_ids: set[str] = set()
    for task in batch:
        if fail_counts.get(task.id, 0) >= self.config.cloud_escalation_threshold and task.id not in cloud_escalate_ids:
            remaining.insert(0, task)
            cloud_escalate_ids.add(task.id)
```

**Key**: The cloud re-queueing inserts ONE instance per unique task ID — no duplicates.

### 2. Fix test mocks — CRITICAL

Old pattern (breaks after batch refactor):
```python
def _mock_local_exec():
    m = MagicMock()
    del m.execute_batch  # Forces serial path — BREAKS NOW
    m.execute_task.return_value = {"success": True, ...}
    return m
```

New pattern (works with batch):
```python
def _mock_local_exec(success: bool = True, tokens: int = 50) -> MagicMock:
    m = MagicMock()
    m._started = False
    
    def batch_result(batch, worktree_path=""):
        return [
            {"task_id": task.id, "success": success, "summary": "ok" if success else "failed",
             "tokens_used": tokens, "output": "", "returncode": 0 if success else 1}
            for task in batch
        ]
    
    m.execute_batch.side_effect = batch_result
    m.execute_task.return_value = {"success": success, "summary": "ok", "tokens_used": tokens, ...}
    return m
```

**Key pitfall**: `execute_batch` returns a LIST of result dicts with `task_id` keys. The coordinator
does `result_by_id = {r["task_id"]: r for r in results}` — missing task_id keys = silent fail.

Update assertions:
```python
# BEFORE:
local_exec.execute_task.assert_called_once()
# AFTER:
local_exec.execute_batch.assert_called_once()
```

### 3. Auto-verification and auto-complexity helpers

```python
def _auto_verification(prompt: str) -> str:
    p = prompt.lower()
    if any(k in p for k in ("research", "analyze", "review", "summarize", "survey")):
        return "output identifies specific findings with supporting rationale (>50 words)"
    if any(k in p for k in ("implement", "write", "create", "add", "build", "generate")):
        return "output describes concrete steps taken or code produced (>30 words)"
    if any(k in p for k in ("fix", "debug", "repair", "resolve", "patch")):
        return "output identifies root cause and describes the fix applied"
    if any(k in p for k in ("test", "verify", "validate", "check")):
        return "output reports pass/fail status and lists items verified"
    return "output is relevant, substantive, and addresses the stated task (>40 words)"

def _auto_complexity(prompt: str) -> str:
    try:
        from cohezion.inference.task_classifier import classify
        node = classify(prompt).node
        return {"npu": "routine", "igpu": "synthesis", "cpu": "reasoning"}.get(node, "synthesis")
    except Exception:
        return "synthesis"
```

Then in LoopTask construction:
```python
LoopTask(
    id=...,
    description=prompt,
    category=t.get("complexity", _auto_complexity(prompt)),
    verification=t.get("verification", _auto_verification(prompt)),
    estimated_tokens=min(2000, max(200, len(prompt.split()) * 10)),
)
```

## Verification

```bash
uv run pytest tests/compound/test_loop_coordinator.py -q  # 18/18 should pass
```

## References

- `src/cohezion/compound/autonomous_loop/coordinator.py` — LoopCoordinator + LoopConfig
- `~/cohezion-labs/compound_daemon.py` — _auto_verification, _auto_complexity helpers
- `tests/compound/test_loop_coordinator.py` — updated mock pattern
