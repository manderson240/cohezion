---
name: uv-sync-extra-vs-group
description: |
  Fix for CI failures where `uv sync --frozen --group dev` installs nothing
  because dev tools live in [project.optional-dependencies], not [dependency-groups].
  Use when: (1) CI fails with "Failed to spawn: `ruff`" or "No such file or directory"
  for pytest/mypy/black despite a `uv sync` step, (2) a GitHub Actions workflow uses
  `--group dev` but pyproject.toml defines dev tools under [project.optional-dependencies],
  (3) uv sync completes with exit 0 but dev tools are missing from the venv.
author: Claude Code
version: 1.0.0
---

# uv sync: --extra vs --group for dev dependencies

## Problem

CI fails with errors like:
```
error: Failed to spawn: `ruff`
  Caused by: No such file or directory (os error 2)
```

despite the workflow running `uv sync --frozen --group dev` first. Exit code is 0 —
the sync "succeeds" but installs nothing useful.

## Root Cause

Two distinct dependency mechanisms exist in `pyproject.toml`:

| Mechanism | Section | Install flag |
|-----------|---------|-------------|
| **Optional extras** | `[project.optional-dependencies]` | `uv sync --extra dev` |
| **PEP 735 dependency groups** | `[dependency-groups]` | `uv sync --group dev` |

These are **not interchangeable**. `--group dev` only reads `[dependency-groups]`.
If no `[dependency-groups]` section exists, `uv sync --group dev` succeeds with
zero installations. The most common pattern (ruff, pytest, mypy in `[project.optional-dependencies].dev`)
requires `--extra dev`.

## Diagnosis

```bash
# Check which section the dev tools live in
grep -A20 '\[project.optional-dependencies\]' pyproject.toml | grep -E "ruff|pytest|mypy"
grep -A20 '\[dependency-groups\]' pyproject.toml | grep -E "ruff|pytest|mypy" || echo "no PEP 735 groups"
```

If tools appear under `[project.optional-dependencies]` and not `[dependency-groups]`,
use `--extra`.

## Fix

In every `uv sync` step of the workflow:
```yaml
# WRONG
- name: Sync dependencies
  run: uv sync --frozen --group dev

# CORRECT
- name: Sync dependencies
  run: uv sync --frozen --extra dev
```

If the project uses both mechanisms, combine them:
```yaml
run: uv sync --frozen --extra dev --group lint
```

## Scope

In large CI pipelines with multiple job stages (lint → type-check → unit → integration),
**every stage that needs dev tools must have the fix**. Search the entire workflow file:

```bash
grep -n "uv sync" .github/workflows/surrealdb-tests.yml
```

Use `replace_all: true` when editing to fix all occurrences at once.

## Verification

```bash
# After fixing, verify ruff is available:
uv sync --frozen --extra dev && uv run ruff --version
```

## References

- [uv dependency-groups docs](https://docs.astral.sh/uv/concepts/dependencies/#dependency-groups)
- [PEP 735](https://peps.python.org/pep-0735/) — dependency groups specification
