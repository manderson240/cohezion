---
name: pytest-cov-import-masking
description: |
  Fix for broken Python import chains silently masked by pytest-cov's --cov flag.
  Use when: (1) tests pass with --cov=src but fail with 37+ collection errors without it,
  (2) ImportError only appears when running specific test files in isolation,
  (3) "cannot import name X from module Y" appears outside pytest but not inside,
  (4) pytest.ini addopts contains --cov=src or --cov=<package>.
  Root cause: pytest-cov pre-imports ALL source modules before collection, caching
  partially-initialized modules in sys.modules and hiding ImportError cascades.
author: Claude Code
version: 1.0.0
---

# pytest-cov Import Masking

## Problem

`--cov=src` in `pytest.ini` addopts causes pytest-cov to pre-import ALL source
modules before test collection begins. This caches broken imports in `sys.modules`,
hiding `ImportError` cascades that would normally surface as collection errors.

Result: the full test suite passes (3,958 tests), but running individual test files
produces 37 collection errors due to `ImportError: cannot import name X from Y`.

## Context / Trigger Conditions

```
# pytest.ini
addopts = --cov=src --cov-report=html -v
```

Tests pass with `uv run pytest` but fail when:
- Running a specific file: `uv run pytest tests/physics/test_hiho_invariant.py`
- Running without coverage: `uv run pytest --no-cov tests/`
- A fresh Python process imports the module: `python -c "from cohezion.compound import CompoundExecutor"`

Error pattern in collection:
```
ERROR collecting tests/physics/test_hiho_invariant.py
ImportError: cannot import name 'ConstraintType' from 'cohezion.compound.models'
```

## Solution

1. **Identify the broken import chain** by running without coverage:
   ```bash
   uv run pytest --no-cov tests/path/to/failing_test.py -v 2>&1 | head -50
   ```

2. **Find where types are expected vs where they live**:
   ```bash
   # Find what module tries to import the missing type
   grep -r "from cohezion.compound.models import" src/cohezion/compound/
   # Find where the type actually exists
   grep -r "class ConstraintType" src/cohezion/
   ```

3. **Fix the import** — choose ONE:

   **Option A** (canonical fix): Move types to the module they're expected from
   ```python
   # Add missing types to models.py (the canonical location)
   # Remove duplicate definitions from compat.py
   # Have compat.py import from models.py
   ```

   **Option B** (quick fix): Update the import in the file that's wrong
   ```python
   # Change: from cohezion.compound.models import ConstraintType
   # To:     from cohezion.compound.compat import ConstraintType
   ```

4. **Verify fix without coverage**:
   ```bash
   uv run pytest --no-cov tests/path/to/test.py -v
   ```

## Verification

```bash
# Should work both ways after fix:
uv run pytest --no-cov tests/compound/ -q          # Without cov (real test)
uv run pytest tests/compound/ -q                   # With cov (was always passing)
python -c "from cohezion.compound import CompoundExecutor; print('OK')"
```

## Example

In this codebase, `request_alignment_analyzer.py` imported 8 types
(`ConstraintType`, `ExecutionConstraint`, `HumanRequest`, etc.) from
`cohezion.compound.models` — but those types only existed in `cohezion.compound.compat`.

Fix: Added the 8 types to `models.py` as the canonical location, then updated
`compat.py` to import from `models.py` instead of redefining them.

## References

- `pytest.ini` addopts documentation: https://docs.pytest.org/en/stable/reference/reference.html#ini-options-ref
- pytest-cov import mechanics: coverage.py instruments modules at import time
