# Lesson 18: MOCK LIVE SERVICES IN TESTS

## Original Text
**MOCK LIVE SERVICES IN TESTS**: API endpoint tests that call `get_compound_client()` hang if Ollama is down. Always mock with `patch("cohezion.swarm.compound_client.get_compound_client")` — patch at source module, not import site.

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
