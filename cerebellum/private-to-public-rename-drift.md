---
title: 'Private-to-Public Method Rename Drift'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.66
  stage: growing
  synapse_in: 6
  synapse_out: 8
---
# Pattern: Private-to-Public Method Rename Drift

**Domain**: refactoring, testing
**Source**: `src/cohezion/compound/journey_tracker.py`
**Discovered**: Session 70 — 2026-02-22

## Problem

When renaming methods from `_private` to `public` convention, callers in the same file and in test files are missed. Session 68 renamed `_holographic_project` → `holographic_project` and `_text_to_latent` → `text_to_latent`. But:

1. Line 408 of `journey_tracker.py` itself still called `self._holographic_project()` → `AttributeError`
2. `tests/compound/test_journey_tracker.py` called `tracker._text_to_latent()` × 9 → `AttributeError`

Python's error message gives it away: `Did you mean: 'holographic_project'?`

## Solution

After any method rename, grep ALL callers:

```bash
# Find all usages of old private name
grep -rn "\._old_name\b" src/ tests/

# Bulk fix with sed (safe for method calls only)
sed -i 's/\._old_method_name(/\.new_method_name(/g' src/cohezion/**/*.py tests/**/*.py
```

## Checklist for Method Renaming

- [ ] Update definition
- [ ] Search `src/` for internal call sites (same file! other files!)
- [ ] Search `tests/` for test call sites
- [ ] Update type annotations referencing the method
- [ ] Run tests immediately after to catch any missed sites

## Detection

`AttributeError: 'ClassName' object has no attribute '_method_name'. Did you mean: 'method_name'?`

The "Did you mean" suggestion is Python identifying the correct public name.

## Related Decisions

- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]] — consolidation refactoring where such renames commonly occur
- [[2026-02-23-enforce-no-orphan-modules-policy]] — methods renamed without updating callers create orphaned call paths
- [[2026-02-22-session-70-heal-and-test-fix]] — the session that discovered this pattern

## Related Patterns

- [[safe-file-split-checklist]] — file splits often involve method renames; this checklist includes caller verification
- [[platform-issue-analysis-template]] — AttributeError from missed renames is diagnosable via structured analysis

## Related Concepts

- [[concept-testing]] — method rename validation is analogous to concept testing: verifying all references point to the correct target after a change
- [[adversarial-review]] — adversarial review of rename PRs would catch missed call sites before they become runtime errors
- [[session-retrospective]] — this pattern was extracted during session 70 retrospective, demonstrating the value of structured post-session review
- KEY_LEARNINGS.md L131
