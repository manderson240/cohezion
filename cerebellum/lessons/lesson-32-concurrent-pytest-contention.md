---
aspect: thinker
neural:
  activation: 0.61
  stage: growing
  synapse_in: 0
  synapse_out: 8
title: "Lesson 32: CONCURRENT PYTEST CONTENTION"
date: 2026-02-01
---
# Lesson 32: CONCURRENT PYTEST CONTENTION

## Original Text
**CONCURRENT PYTEST CONTENTION**: Two simultaneous `uv run pytest` processes contend for `.venv` lock and can deadlock. Never run parallel test suites — use one process or use the background agent.

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
**Domains**: architecture, cicd, development, performance, testing
**Concepts**: [[concept-automation]], [[concept-optimization]], [[concept-testing]]

## Related Papers

  - [[claude-code-community-skills]] (similarity: 0.711)
  - [[openai-codex-agent-loop]] (similarity: 0.703)
  - [[claude-code-swiftui-skill-patterns]] (similarity: 0.682)

## Related Decisions

  - [[10-claude-log-mining-architecture]] (relevance: 13)
  - [[10-log-mining-adversarial-review]] (relevance: 13)
