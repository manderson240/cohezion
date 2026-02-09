# Lesson 9: ruff hook fights

## Original Text
**ruff hook fights**: PostToolUse ruff hook (`format-on-edit.sh`) runs `ruff format` + `ruff check --fix` after EVERY Python file edit. This reverts manual lint fixes (e.g., removing unused imports, adding noqa). Fix: suppress via pyproject.toml `[tool.ruff.lint.per-file-ignores]` or global `ignore` list — config-level suppression is the ONLY reliable approach. Also note: ruff won't auto-fix F401 in `__init__.py` files (treats as re-exports).

## Category
<!-- Add category: [Testing, Architecture, CI/CD, Debugging, Performance, etc] -->

## Context
<!-- Add relevant context or when this lesson was learned -->

## Related Lessons
<!-- Link to related lessons -->

## Tags
- #lesson
- #learning

---
Created: 2026-02-08 14:43:24
