---
aspect: thinker
neural:
  activation: 0.63
  stage: growing
  synapse_in: 0
  synapse_out: 9
---
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

## Related Papers

  - [[emoticons-llm-silent-failures]] (similarity: 0.718)
  - [[openai-codex-agent-loop]] (similarity: 0.702)
  - [[claude-code-swiftui-skill-patterns]] (similarity: 0.693)

## Related Decisions

  - [[10-claude-log-mining-architecture]] (relevance: 13)
  - [[10-log-mining-adversarial-review]] (relevance: 12)
