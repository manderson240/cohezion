---
description: Enforce Code Quality (Ruff and MyPy)
---

# Enforce Quality Workflow

This workflow autonomously enforces the project's code quality standards by running formatting, linting, and type checking operations. It leverages Ruff and MyPy natively via `uv`, the project's dependency manager.

## Prerequisites

- `uv` is installed and the project dependencies are up-to-date (`uv sync`).

## Steps

1. Auto-fix linting issues and formatting
   // turbo

```bash
uv run ruff check --fix .
uv run ruff format .
```

2. Run strict type-checking
   // turbo

```bash
uv run mypy src/ tests/ scripts/
```

3. Review the outputs. If there are remaining errors that cannot be auto-fixed by Ruff, or Type Errors reported by MyPy, investigate the files and fix the issues manually.

4. (Optional) Run the test suite to ensure no logic was broken by the auto-fixes

```bash
uv run pytest
```

5. Once you run this workflow and address all remaining issues, your codebase should be in a clean state and ready for commit. The Git pre-commit hook will automatically run these checks on staged files during commit to prevent regression.
