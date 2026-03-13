---
title: 'Post-Crash Venv Recovery: pytest Missing Despite pyproject.toml'
date: '2026-02-22'
status: accepted
tags: [decision, python, venv, crash-recovery, testing]
aspect: thinker
neural:
  activation: 0.7
  stage: growing
  synapse_in: 4
  synapse_out: 5
---

# Post-Crash Venv Recovery: pytest Missing Despite pyproject.toml

## Context

After a system crash (power loss, kernel panic, or OOM kill), the Python virtual environment (`.venv/`) can become corrupted without any visible damage to `pyproject.toml` or `uv.lock`. The corruption manifests as missing packages: `pytest`, `pytest-cov`, and `pytest-asyncio` were absent from the venv despite being declared as dev dependencies in `pyproject.toml`.

The failure signature was confusing: `uv run pytest` produced `ModuleNotFoundError: No module named 'pytest'`, but `pyproject.toml` clearly listed it under `[project.optional-dependencies.dev]`. The lock file (`uv.lock`) appeared intact. The root cause was that the venv's site-packages directory had partial writes interrupted by the crash, leaving the package metadata inconsistent with the lock file.

This is particularly dangerous because `pytest.ini` requires `pytest-cov` (via `addopts = --cov`) and `pytest-asyncio` (via `asyncio_mode = strict`). Without these, the entire test suite fails to start — not individual tests, but the entire pytest invocation.

## Decision

When pytest or other dev dependencies are missing after a crash:

1. **Use `uv add --dev`** to force reinstallation, even when the dependency appears present in `pyproject.toml`. This rebuilds the venv state regardless of the lock file:
   ```bash
   uv add --dev pytest pytest-cov pytest-asyncio
   ```

2. **Verify with `uv run pytest --version`** before running the test suite — a 1-second check that catches the problem before a confusing multi-test failure.

3. **Add venv integrity check to session start** (future improvement): a pre-session hook that verifies critical packages are importable.

## Consequences

**Positive:**
- `uv add --dev` is idempotent — safe to run even if packages are already installed correctly
- Immediate recovery without needing to delete and recreate the entire venv
- The 1-second version check prevents the confusing "83 tests fail" scenario

**Negative:**
- `uv add --dev` modifies `pyproject.toml` if the version specifier changes (minor risk — pin versions to avoid)
- Does not address venvs corrupted in ways that `uv add` cannot fix (rare — full `rm -rf .venv && uv sync` is the fallback)
- Adds a manual step to crash recovery that could be automated

## Alternatives Considered

**Delete and recreate venv:** `rm -rf .venv && uv sync`. Works but takes 30-60 seconds on large projects (downloading all packages). `uv add --dev` is faster because it only reinstalls the missing packages. Rejected as the first-line approach but kept as fallback.

**`pip install --force-reinstall`:** Works but does not respect `uv.lock` version pins. Using `uv add` ensures lock file consistency. Rejected for version safety.

**Ignore and debug test failures:** Treat each test failure individually without checking the venv. Wastes significant time — in the Session 70 case, 83 test failures were all caused by the same missing `pytest-asyncio`. Rejected for inefficiency.

## Related

- [[2026-02-22-session-70-heal-and-test-fix]] — the session that revealed this venv issue and fixed 83 test failures
- [[2026-02-22-cz-spec-workflow-retrospective]] — broader session context where venv integrity was critical for the 62-test suite
- [[concept-testing]] — venv recovery is a prerequisite for running concept and integration tests
- [[2026-02-22-asyncio-lock-in-init-not-class-level]] — sibling fix from the same crash recovery session
- [[session-retrospective]] — the crash recovery was documented through session retrospective practices
