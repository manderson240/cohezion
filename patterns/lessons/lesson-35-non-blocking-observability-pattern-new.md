# Lesson 35: NON-BLOCKING OBSERVABILITY PATTERN (NEW)

## Original Text
**NON-BLOCKING OBSERVABILITY PATTERN** (NEW): Vault operations must always be try/except. These are observability features (nice-to-have), never essential to execution. Pattern: `try: vault.log() except Exception as e: logger.debug("Non-critical", exc_info=True)`. This ensures vault failures never break compound execution.

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
**Domains**: architecture, cicd, observability, performance, testing
**Concepts**: [[concept-automation]], [[concept-optimization]], [[concept-testing]]
