---
name: add-or-update-model-profiles-and-routing
description: Workflow command scaffold for add-or-update-model-profiles-and-routing in cohezion.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-or-update-model-profiles-and-routing

Use this workflow when working on **add-or-update-model-profiles-and-routing** in `cohezion`.

## Goal

Adds or updates model capability profiles and routing logic, ensuring models are properly described and dispatched according to their strengths/limitations.

## Common Files

- `src/cohezion/inference/default_profiles.py`
- `src/cohezion/inference/registry.py`
- `src/cohezion/inference/route_by_capability.py`
- `tests/inference/test_default_profiles.py`
- `tests/inference/test_route_by_capability.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or update profile data in src/cohezion/inference/default_profiles.py.
- Integrate profiles into registry entries (src/cohezion/inference/registry.py).
- Update or add routing logic (src/cohezion/inference/route_by_capability.py) to utilize new profiles.
- Write or update tests in tests/inference/ to validate profile correctness and routing behavior.
- Verify all tests and lint checks pass.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.