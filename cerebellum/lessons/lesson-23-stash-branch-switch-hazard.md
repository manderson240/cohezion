---
aspect: thinker
neural:
  activation: 0.373
  stage: growing
  cluster: patterns
---
# Lesson 23: STASH + BRANCH SWITCH HAZARD

## Original Text
**STASH + BRANCH SWITCH HAZARD**: `git stash pop` after switching branches can stage unrelated files from the stash. Always verify staged files with `git diff --cached --stat` before committing after a stash pop. Prefer `git stash apply` over `pop` until verified clean.

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
**Concepts**: [[concept-automation]], [[concept-caching]], [[concept-optimization]], [[concept-testing]], [[concept-versioning]]

## Related Papers

  - [[theorem-ai-formal-verification]] (similarity: 0.679)
  - [[circleci-ai-cicd-validation]] (similarity: 0.669)
  - [[llm-in-sandbox-agentic-intelligence]] (similarity: 0.658)
