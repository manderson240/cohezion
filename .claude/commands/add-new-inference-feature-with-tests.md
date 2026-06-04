---
name: add-new-inference-feature-with-tests
description: Workflow command scaffold for add-new-inference-feature-with-tests in cohezion.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-new-inference-feature-with-tests

Use this workflow when working on **add-new-inference-feature-with-tests** in `cohezion`.

## Goal

Implements a new inference feature or capability, including core logic, integration with registry/routing, and comprehensive tests.

## Common Files

- `src/cohezion/inference/*.py`
- `src/cohezion/inference/registry.py`
- `src/cohezion/inference/model_card_harness.py`
- `src/cohezion/inference/fleet.py`
- `tests/inference/*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or modify core inference logic in src/cohezion/inference/ (e.g., capability_profile.py, route_by_capability.py, default_profiles.py).
- Update or extend registry/model harness logic (e.g., registry.py, model_card_harness.py, fleet.py) to integrate the new feature.
- Write new tests in tests/inference/ for the new feature, covering both positive and negative cases.
- Run and verify tests (pytest, make test-fast) and lint checks.
- Document or note follow-up integration points if the feature is foundational.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.