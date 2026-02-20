---
name: pytest-async-cascade-diagnosis
description: |
  Diagnose phantom test failures from missing pytest-asyncio. Use when:
  (1) tests pass individually but fail in full suite, (2) seeing hundreds
  of async-related failures, (3) async fixtures or async test functions exist.
  Key insight: missing pytest-asyncio causes cascading failures that look
  like real bugs or singleton pollution, not missing infrastructure.
author: Claude Code
version: 1.0.0
---

# Pytest Async Cascade Diagnosis

## Problem

Test suite has hundreds of failures that look like real bugs, but individual test files pass cleanly. Async test functions and fixtures exist in the codebase, but pytest-asyncio is not actually installed despite being listed in pyproject.toml.

## Context / Trigger Conditions

**Use this skill when:**

1. Tests pass when run individually: `pytest tests/module/test_file.py` ✅
2. Full suite has massive failures: `pytest tests/` ❌ (hundreds of failures)
3. Failures involve async fixtures, `@pytest.mark.asyncio`, or async test functions
4. Error messages vary wildly but many are async-related
5. You suspect singleton pollution or test isolation issues

**Symptoms:**
- `fixture 'event_loop' not found` errors
- `RuntimeError: no running event loop` errors
- Tests fail with `asyncio` errors but the code logic looks correct
- Individual test files pass but suite fails

## Solution

### Step 1: Verify pytest-asyncio is Actually Installed

```bash
uv pip show pytest-asyncio
```

**If output is:**
```
warning: Package(s) not found for: pytest-asyncio
```

Then pytest-asyncio is NOT installed, even if it's listed in pyproject.toml.

**Root cause:** Packages installed via `uv pip install` are transient — `uv sync` will drop them if they're not in pyproject.toml dependency groups.

### Step 2: Add to pyproject.toml

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",  # ← Ensure this is present
    "pytest-cov>=4.1.0",
    # ... other dev deps
]
```

### Step 3: Sync Dependencies

```bash
uv sync --extra dev
```

This locks the dependency in the virtual environment.

### Step 4: Verify Test Suite

```bash
uv run pytest tests/ -q --tb=line 2>&1 | tail -10
```

Expected: Massive reduction in failures (e.g., 453 failures → 13 failures or 0 failures).

## Verification

**Before fix:**
- Individual files: ✅ pass
- Full suite: ❌ hundreds of failures

**After fix:**
- Individual files: ✅ pass
- Full suite: ✅ pass (or minimal failures unrelated to async)

**Collection check:**
```bash
uv run pytest tests/ -q --co 2>&1 | tail -3
```

Should show `X tests collected` with 0 collection errors.

## Common Related Issues

| Missing Package | Symptom |
|---|---|
| `pytest-asyncio` | Async fixtures fail, event loop errors, cascading failures |
| `gymnasium` | `ModuleNotFoundError: No module named 'gymnasium'` in RL tests |
| `python-jose` | `ModuleNotFoundError: No module named 'jose'` in auth tests |
| `passlib` | Import error from `python-jose` (transitive dependency) |

**Pattern:** Always add test-only dependencies to `pyproject.toml[dev]`, not just install them.

## Example

**Scenario:** Test suite shows 453 failures, but running individual test files shows all passing.

**Diagnostic:**
```bash
# Individual file passes
$ uv run pytest tests/compound/test_executor.py -q
. . . . . .
6 passed in 2.45s

# Full suite fails
$ uv run pytest tests/ -q --tb=line 2>&1 | tail -5
453 failed, 2679 passed, 15 skipped

# Check pytest-asyncio
$ uv pip show pytest-asyncio
warning: Package(s) not found for: pytest-asyncio
```

**Fix:**
```bash
# Add to pyproject.toml[dev] (if not already there)
# Then:
uv sync --extra dev
uv run pytest tests/ -q --tb=line 2>&1 | tail -5
# → 3132 passed, 15 skipped
```

## References

- pytest-asyncio docs: https://pytest-asyncio.readthedocs.io/
- uv dependency management: https://docs.astral.sh/uv/
- Related: Learning 127 in `knowledge_graph/KEY_LEARNINGS.md`
