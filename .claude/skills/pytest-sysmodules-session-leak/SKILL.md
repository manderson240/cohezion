---
name: pytest-sysmodules-session-leak
description: |
  Fix for test failures that appear random under pytest-randomly — caused by
  module-level `sys.modules[X] = Mock()` in one test file leaking into every
  subsequent test in the session.
  Use when: (1) a test fails on CI but passes locally (or vice versa),
  (2) traceback shows "TypeError: '<' not supported between MagicMock and float",
  (3) "unsupported format string passed to MagicMock.__format__",
  (4) "AttributeError: ... got MagicMock" inside code that should never see a mock,
  (5) failures move around between runs when pytest-randomly is active,
  (6) grep reveals `sys.modules[...] = MagicMock()` at module (not function) scope.
author: Claude Code
version: 1.0.0
---

# pytest sys.modules Session Leak

## Problem

Writing this at module scope in a test file permanently poisons the test session:

```python
# tests/some_module/test_foo.py
from unittest.mock import MagicMock
import sys

mock_cc = MagicMock()
sys.modules["some_heavy_package"] = mock_cc
sys.modules["some_heavy_package.submodule"] = mock_cc

from code_under_test import Foo  # needs the mock during import
```

pytest collects all test files at session start, so every module-scope assignment
runs before the first test. Pytest never restores `sys.modules` — those entries
stay mocked for the **rest of the test run**. Any other test that does
`from some_heavy_package import X` later will receive a `MagicMock`, not the real
class.

Under `pytest-randomly` the file order changes between runs, so the same tests
pass locally (when they run *before* the poisoning file) and fail on CI (when
they run *after*). Test orderings make this highly intermittent and hard to
reproduce without pinning seeds.

## Trigger Conditions

- Traceback ends in the code under test, on a comparison / format-string / attribute
  access that should never see a mock:
  - `TypeError: '<' not supported between instances of 'MagicMock' and 'float'`
  - `TypeError: unsupported format string passed to MagicMock.__format__`
  - `AttributeError: MagicMock has no attribute '__len__'` etc.
- `grep -rn "sys.modules\[" tests/` returns module-level (not fixture-scoped) assignments.
- Failures appear *only on CI* or *only locally*, and disappear when `-p no:randomly` is added.
- Running the failing test file *in isolation* passes; running it alongside the poisoning
  file fails.

## Solution

Move the `sys.modules` mutations into an `autouse` fixture that saves and restores the
original state. Keep the import of the module under test at module scope (it runs
once, before any tests, which is the same timing — but the fixture still gets a chance
to re-mock on each test if needed).

```python
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_heavy_modules():
    """Scope the sys.modules mocks to this file's tests only.

    Previously these ran at module scope and poisoned sys.modules for the
    entire test session — any later test importing the real package got a
    MagicMock, producing opaque comparison/format errors whose locality
    depended on pytest-randomly ordering.
    """
    originals = {}
    for key in ("some_heavy_package", "some_heavy_package.submodule"):
        originals[key] = sys.modules.get(key)

    mock_cc = MagicMock()
    sys.modules["some_heavy_package"] = mock_cc
    sys.modules["some_heavy_package.submodule"] = mock_cc

    yield

    for key, original in originals.items():
        if original is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original


from code_under_test import Foo  # noqa: E402 — must be after fixture defn for clarity
```

### Alternative: per-test `monkeypatch.setitem`

If only specific tests need the mock, avoid `autouse=True`:

```python
def test_foo_without_heavy_import(monkeypatch):
    monkeypatch.setitem(sys.modules, "some_heavy_package", MagicMock())
    # monkeypatch restores automatically on teardown
    ...
```

## Verification

1. Confirm the failing test passes when run alone AND when run alongside the
   poisoning file's tests:
   ```bash
   uv run pytest tests/poisoning_file.py tests/failing_file.py -q --no-cov
   ```

2. Confirm pytest-randomly order no longer matters:
   ```bash
   for seed in 1 2 3 42 100; do
     uv run pytest -q --no-cov -p randomly --randomly-seed=$seed tests/failing_file.py tests/poisoning_file.py
   done
   ```

3. Sanity-check nothing else in the test file still uses module-scope `sys.modules`:
   ```bash
   rg -n "^sys\.modules\[" tests/  # must return nothing at module scope
   ```

## Real-World Example (Cohezion)

**Session date:** 2026-04-24, PR #75.
**File:** `tests/universe/test_engine.py` had at module scope:
```python
mock_cc = MagicMock()
sys.modules["cohezion_core"] = mock_cc
sys.modules["cohezion_core.cohezion_core_rs"] = mock_cc
```

**Symptom:** `tests/mass_sim/test_integration.py::test_demo_scale_integration`
failed on CI with:
```
TypeError: '<' not supported between instances of 'MagicMock' and 'float'
at src/cohezion/mass_sim/analysis.py:77
```

Local runs of `test_demo_scale_integration` alone passed (file collected before
`test_engine.py`). CI runs failed (file collected after). The `mass_sim/universe_factory.py`
module does `from cohezion_core.cohezion_core_rs import FlumePhysics` — which
returned the session-wide MagicMock, so `physics.compute_batch_stats()` returned
a MagicMock, which later comparisons and `:.3f` formats crashed on.

Fix: wrapped in autouse fixture with save/restore. Verified with both files in
either order: 7 passed.

## References

- pytest `monkeypatch.setitem` (scoped, auto-restores):
  https://docs.pytest.org/en/stable/how-to/monkeypatch.html#monkeypatch-setitem
- `pytest-randomly`: https://github.com/pytest-dev/pytest-randomly
- Python `sys.modules` docs (Python does not restore on import errors or test teardown):
  https://docs.python.org/3/library/sys.html#sys.modules
