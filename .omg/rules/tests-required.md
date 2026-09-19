---
description: "Require tests and static verification when behavior code changes"
globs: ["src/cohezion/**/*.py", "scripts/**/*.py"]
alwaysApply: false
---

# Rule: Tests & Quality Verification Required

## Triggers
- Modification of any behavioral Python module in `src/cohezion/` or `scripts/`.

## Enforced Behavior
1. **Unit Tests**: Run corresponding pytest test suite before committing.
2. **Formatting & Linting**: Run `ruff format` and `ruff check`.
3. **Mypy Ratchet**: Verify `mypy` type check does not exceed the baseline debt.
4. **AutoHarness Invariants**: Synthesized code must pass AST validation (`ast.parse`) and be free of `eval()`.
