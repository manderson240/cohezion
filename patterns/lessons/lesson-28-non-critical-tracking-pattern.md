# Lesson 28: NON-CRITICAL TRACKING PATTERN

## Original Text
**NON-CRITICAL TRACKING PATTERN**: Journey tracking, inflection detection, and metrics collection should ALWAYS be wrapped in try/except with debug logging. These are observability features — they must never break execution. Pattern: `try: tracker.record(...) except Exception: logger.debug("non-critical")`

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
