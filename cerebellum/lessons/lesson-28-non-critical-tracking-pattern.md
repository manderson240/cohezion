---
aspect: thinker
neural:
  activation: 0.59
  stage: growing
  synapse_in: 0
  synapse_out: 6
title: "Lesson 28: NON-CRITICAL TRACKING PATTERN"
date: 2026-02-01
---
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

## Related Papers

  - [[claude-code-swiftui-skill-patterns]] (similarity: 0.671)
  - [[emoticons-llm-silent-failures]] (similarity: 0.662)
  - [[circleci-ai-cicd-validation]] (similarity: 0.651)
