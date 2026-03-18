---
aspect: thinker
neural:
  activation: 0.61
  stage: growing
  synapse_in: 0
  synapse_out: 8
title: "Lesson 18: MOCK LIVE SERVICES IN TESTS"
date: 2026-02-01
---
# Lesson 18: MOCK LIVE SERVICES IN TESTS

## Original Text
**MOCK LIVE SERVICES IN TESTS**: API endpoint tests that call `get_compound_client()` hang if Ollama is down. Always mock with `patch("cohezion.swarm.compound_client.get_compound_client")` — patch at source module, not import site.

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
**Concepts**: [[concept-automation]], [[concept-isolation]], [[concept-modularity]], [[concept-optimization]], [[concept-testing]]

## Related Papers

  - [[circleci-ai-cicd-validation]] (similarity: 0.692)
  - [[claude-code-community-skills]] (similarity: 0.686)
  - [[openai-codex-agent-loop]] (similarity: 0.686)
