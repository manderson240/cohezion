---
aspect: thinker
neural:
  activation: 0.61
  stage: growing
  synapse_in: 0
  synapse_out: 7
---
# Lesson 9: ruff hook fights

## Original Text
**ruff hook fights**: PostToolUse ruff hook (`format-on-edit.sh`) runs `ruff format` + `ruff check --fix` after EVERY Python file edit. This reverts manual lint fixes (e.g., removing unused imports, adding noqa). Fix: suppress via pyproject.toml `[tool.ruff.lint.per-file-ignores]` or global `ignore` list — config-level suppression is the ONLY reliable approach. Also note: ruff won't auto-fix F401 in `__init__.py` files (treats as re-exports).

## Category
<!-- Add category: [Testing, Architecture, CI/CD, Debugging, Performance, etc] -->

## Context
<!-- Add relevant context or when this lesson was learned -->


## Tags
- #lesson
- #learning

---
Created: 2026-02-08 14:43:24

## Related
**Domains**: architecture, cicd, git, performance, testing
**Concepts**: [[concept-automation]], [[concept-optimization]], [[concept-testing]]

## Related Papers

  - [[emoticons-llm-silent-failures]] (similarity: 0.668)
  - [[claude-code-swiftui-skill-patterns]] (similarity: 0.652)
  - [[karpathy-claude-code-skills]] (similarity: 0.634)

## Related Decisions

  - [[10-log-mining-adversarial-review]] (relevance: 14)
