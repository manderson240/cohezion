---
name: feature-development-with-test-first
description: Workflow command scaffold for feature-development-with-test-first in cohezion.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-with-test-first

Use this workflow when working on **feature-development-with-test-first** in `cohezion`.

## Goal

Develops a new feature by first writing failing tests (RED), then implementing the feature until tests pass (GREEN), ensuring test-driven development.

## Common Files

- `tests/inference/*.py`
- `src/cohezion/inference/*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Write new test cases in tests/inference/ for the intended feature (RED).
- Implement or modify feature logic in src/cohezion/inference/ or related modules.
- Iterate until all new tests pass (GREEN).
- Verify no regressions in existing tests.
- Document follow-up work if the feature is foundational.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.