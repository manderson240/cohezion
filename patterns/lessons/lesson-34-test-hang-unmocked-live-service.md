# Lesson 34: TEST HANG = UNMOCKED LIVE SERVICE

## Original Text
**TEST HANG = UNMOCKED LIVE SERVICE**: When a test hangs, 99% it's calling unmocked Ollama/SurrealDB. Always mock `get_executor()` or pass a mock `compound_executor` to prevent lazy init of live clients.

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
**Domains**: architecture, cicd, performance, testing
**Concepts**: [[concept-automation]], [[concept-isolation]], [[concept-optimization]], [[concept-testing]]
