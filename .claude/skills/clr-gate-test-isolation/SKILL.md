---
name: clr-gate-test-isolation
description: |
  Pattern for isolating CLRQualityGate from MyceliumRegistry singleton-wiring tests.
  Use when: (1) `test_real_writer_path_closes_loop` or similar end-to-end singleton
  tests fail because PATTERN_SYNTHESIZED / ROUTING_SYNTHESIZED is never created,
  (2) the CLR gate calls a real local inference endpoint and rejects toy task content
  ("Executed skill_0: task 0", "task 1", etc.) with passes=False,
  (3) you want to verify writer→reader singleton wiring without testing CLR scoring.
  The fix: mock at "cohezion.compound.clr_quality_gate.CLRQualityGate" (where it's
  constructed), not at the import site.
author: Claude Code
version: 1.0.0
---

# CLR Gate Test Isolation (MyceliumRegistry Wiring Tests)

## Problem

`PostExecutionOrchestrator._run_mycelium()` calls `CLRQualityGate().passes(content)` before
ingesting a `JournalEntry`. The gate makes a real local inference call and scores the content
on three claims. Toy test content like `"Executed skill_0: task 0"` scores below the 0.7
threshold → `passes=False` → `ingest_entry()` is never called → `run_audit()` never fires
→ `PATTERN_SYNTHESIZED` is never created → wiring test fails.

Two concerns must stay separated:
- **Wiring tests**: does the writer use the SAME registry the reader reads? (CLR: irrelevant)
- **CLR tests** (`TestMyceliumWiring`): does the gate correctly block low-quality content?

## Correct Mock Pattern

```python
from unittest.mock import MagicMock, patch

mock_gate = MagicMock()
mock_gate.passes.return_value = True   # force pass for wiring tests

with patch("cohezion.compound.clr_quality_gate.CLRQualityGate", return_value=mock_gate):
    for i in range(10):
        orch._run_mycelium(success=True, skill_name=f"skill_{i}", task_description=f"task {i}")
```

**Mock location**: `"cohezion.compound.clr_quality_gate.CLRQualityGate"` — this is WHERE
the class is DEFINED, which is also where `post_execution` imports it from. If `post_execution`
imported with `from cohezion.compound.clr_quality_gate import CLRQualityGate` you would mock
at `"cohezion.compound.post_execution.CLRQualityGate"`, but since the import is inside the
method body with `from cohezion.compound.clr_quality_gate import CLRQualityGate`, mocking at
the definition site works (the import happens AFTER the patch is active).

## Why 10 iterations?

`_run_mycelium` ingests one entry per call. `run_audit()` is called every 10 entries
(`len(self._ex._mycelium_registry._entries) % 10 == 0`). With 10 entries in domain `"pattern"`,
`run_audit()` synthesizes `PATTERN_SYNTHESIZED`.

## Full Test Example

```python
def test_real_writer_path_closes_loop():
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    from cohezion.api.services import mycelium_api
    from cohezion.compound.post_execution import PostExecutionOrchestrator

    fake_executor = SimpleNamespace()
    orch = PostExecutionOrchestrator(fake_executor)

    mock_gate = MagicMock()
    mock_gate.passes.return_value = True

    with patch("cohezion.compound.clr_quality_gate.CLRQualityGate", return_value=mock_gate):
        for i in range(10):
            orch._run_mycelium(success=True, skill_name=f"skill_{i}", task_description=f"task {i}")

    reader = mycelium_api._get_registry()
    assert "PATTERN_SYNTHESIZED" in reader.skills, (
        "reader must see the skill synthesized via the REAL executor writer path"
    )
```

## Anti-pattern

```python
# WRONG — mocks at the wrong level, CLRQualityGate constructor still runs
with patch.object(CLRQualityGate, "passes", return_value=True):
    ...

# WRONG — patches after the import is already cached (method-body import is fine, module-level import is not)
with patch("cohezion.compound.post_execution.CLRQualityGate", ...):
    ...  # only works if post_execution has a module-level import; fails if import is inside method
```

## Separation of Concerns

| Test class | CLR gate | Purpose |
|---|---|---|
| `test_real_writer_path_closes_loop` | **MOCKED** (passes=True) | Verify singleton wiring |
| `TestMyceliumWiring.test_clr_fail_blocks_ingest` | **REAL** or mocked passes=False | Verify gate correctly blocks |

## References

- `src/cohezion/compound/post_execution.py` — `_run_mycelium()` method
- `src/cohezion/compound/clr_quality_gate.py` — `CLRQualityGate.passes()`
- `tests/learning/test_mycelium_singleton.py` — full test suite
