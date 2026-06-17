---
name: module-level-import-for-mocking
description: |
  Two solutions for the AttributeError when patching lazily-imported dependencies.
  Symptom A: patch("calling_module.DepClass") raises AttributeError — class imported
  inside a function, not at module level.
  Symptom B: patch("calling_module.DepClass") silently has no effect — the lazy
  import inside the function re-binds from source, ignoring the calling-module patch.
  Use when: (1) a class is imported lazily inside def run() / def execute(), (2)
  moving the import to module level is blocked by circular imports or optional deps,
  (3) you need to intercept the exact class the function constructs. Two fixes:
  Fix 1 (preferred): Move import to module level with try/except ImportError guard.
  Fix 2 (when Fix 1 is blocked): Patch at SOURCE module, not calling module —
  from-imports pick up the patched class at call time.
author: Claude Code
version: 1.1.0
---

# Module-Level Import for Mocking

## Problem

Patching `"mymodule.httpx"` requires that `httpx` exist as a module-level attribute.
If it's imported lazily inside a method (`import httpx` inside `def _call_inference`),
the attribute doesn't exist at patch time → `AttributeError`.

```
AttributeError: <module 'cohezion.compound.rubric_middleware'> does not have the attribute 'httpx'
```

## Solution

Import at module level with `try/except ImportError` guard:

```python
# TOP OF MODULE — not inside the method
try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]
```

Now `patch("cohezion.compound.rubric_middleware.httpx")` works because `httpx` is
a real attribute of the module object at patch registration time.

## Pattern in Tests

```python
with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
    import httpx as _real_httpx
    mock_httpx.post.side_effect = _real_httpx.ConnectError("refused")
    mock_httpx.ConnectError = _real_httpx.ConnectError
    verdict = rm.evaluate("some output")

assert verdict.passed is True  # fail-open confirmed
```

## Why Not Just Mock httpx.post Directly?

`patch("httpx.post")` patches globally — affects every module using httpx in the
same test. Module-local patching (`"mymodule.httpx"`) is scoped and avoids
cross-test pollution.

## Fix 2: Patch at Source Module (when Fix 1 is blocked)

When the import can't move to module level (circular imports, optional heavy deps),
patch at the **source module** where the class is defined. The `from … import` inside
the function will pick up the patched version at call time.

```
# coordinator.py — lazy import inside run():
def run(self):
    from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor
    local_exec = LocalImprovementExecutor(base_url, degradation_detector=self._detector)
```

```python
# WRONG — coordinator doesn't have LocalImprovementExecutor as an attribute:
patch("cohezion.compound.autonomous_loop.coordinator.LocalImprovementExecutor")
# → AttributeError: module does not have the attribute 'LocalImprovementExecutor'

# RIGHT — patch at source, from-import picks it up:
with patch(
    "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
    side_effect=capture_factory,
):
    coordinator.run()
```

The `side_effect=capture_factory` trick captures exact constructor kwargs (e.g.
`degradation_detector`) so the test can assert what was passed, not just that the
class was instantiated.

## Applies To

Any external I/O library or internal class used in a method that needs to be mocked:
- `httpx` (HTTP calls to :13305 / external APIs)
- `requests`, `boto3`, `subprocess`
- Internal classes with heavyweight init (DB connections, model loaders)

## Canonical Examples in Cohezion

- `src/cohezion/compound/rubric_middleware.py` — httpx for :13305 calls (Fix 1)
- `src/cohezion/compound/clr_quality_gate.py` — httpx fallback (Fix 1)
- `src/cohezion/learning/vault_neuron_reader.py` — `_httpx` with try/except (Fix 1)
- `src/cohezion/compound/autonomous_loop/coordinator.py` — `LocalImprovementExecutor`
  lazy inside `run()`, patched at source module (Fix 2, 2026-06-17)

## Relationship to clr-gate-test-isolation

That skill covers WHERE to mock (definition site vs import site). This skill covers
WHETHER the attribute exists to mock at all (module-level vs lazy inline import).
Both apply together when mocking inference dependencies.
