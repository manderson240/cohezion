---
aspect: thinker
neural:
  activation: 0.67
  stage: growing
  synapse_in: 0
  synapse_out: 12
---
# Lesson 21: RUNTIME JSON POLLUTION

## Original Text
**RUNTIME JSON POLLUTION**: Tests/module init write timestamps to tracked JSON files (patterns.json, token_efficiency.json, capability_usage.json, workflow_registry.json, skill_registry.json). Pre-push hooks detect modifications and reject push. Fix: `git rm --cached` + `.gitignore` AFTER the `!src/**/*.json` re-include rule.

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
**Concepts**: [[concept-automation]], [[concept-caching]], [[concept-modularity]], [[concept-optimization]], [[compound-engineering]], [[concept-testing]], [[concept-versioning]]

## Related Papers

  - [[claude-code-swiftui-skill-patterns]] (similarity: 0.687)
  - [[openai-codex-agent-loop]] (similarity: 0.685)
  - [[karpathy-claude-code-skills]] (similarity: 0.678)

## Related Decisions

  - [[10-claude-log-mining-architecture]] (relevance: 13)
  - [[10-log-mining-adversarial-review]] (relevance: 13)
