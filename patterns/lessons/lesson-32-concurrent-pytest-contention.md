# Lesson 32: CONCURRENT PYTEST CONTENTION

## Original Text
**CONCURRENT PYTEST CONTENTION**: Two simultaneous `uv run pytest` processes contend for `.venv` lock and can deadlock. Never run parallel test suites — use one process or use the background agent.

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
