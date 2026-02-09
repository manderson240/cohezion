# Lesson 21: RUNTIME JSON POLLUTION

## Original Text
**RUNTIME JSON POLLUTION**: Tests/module init write timestamps to tracked JSON files (patterns.json, token_efficiency.json, capability_usage.json, workflow_registry.json, skill_registry.json). Pre-push hooks detect modifications and reject push. Fix: `git rm --cached` + `.gitignore` AFTER the `!src/**/*.json` re-include rule.

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
