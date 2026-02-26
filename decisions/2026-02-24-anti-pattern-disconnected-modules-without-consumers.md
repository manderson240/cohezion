---
title: 'Anti-pattern: Disconnected modules without consumers'
date: '2026-02-24'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Disconnected modules create an illusion of progress without delivering value. They accumulate tech debt, confuse new contributors, and make the codebase harder to navigate. Good ideas in dead code should be logged to vault and the code removed.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Anti-pattern: Disconnected modules without consumers'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.0
  actual_cost: 0.0
  actual_time_hours: 0.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated: []
---

## Context

**Anti-pattern:** Writing modules that are never imported or called by any other code in the codebase.

Found during sprint 4 code review: `bioelectric_field.py`, `journey_tracker_v2.py`, `morphospace.py` — three complete modules, none of which were imported anywhere. Total: ~900 lines of untested, unmaintained code.

How orphan modules accumulate:
1. Good idea → write module
2. Plan to "wire it in later"
3. Later never comes, or API changes make wiring harder
4. Module silently diverges from the pipeline it was meant to join
5. Nobody updates it when APIs change (nobody is forced to)
6. New contributor finds it and doesn't know if it's active

Orphan modules create an illusion of progress: lines of code increase, git log shows activity, but nothing actually works end-to-end.

## Decision

Enforce the no-orphan policy: every module must have at least one import site. Good ideas from deleted modules are preserved as vault documents.

## Chosen Option

Code review enforcement: PRs introducing new modules must show at least one consumption site. Existing orphans are audited, their concepts documented in vault patterns/concepts, and the code deleted.

## Alternatives Considered

1. Keep orphans with "WIP" or "experimental" labels
2. Move to `experimental/` subdirectory
3. Document and delete (chosen)
4. Ignore the problem

## Decision Reasoning

### Why This Option?

The concepts in orphan modules are often valid; only the premature implementation is the problem. Documenting in vault preserves the idea without the maintenance surface area. The code can always be rewritten when it's actually needed.

### Alternatives Rejected

- **Labels/markers** — Don't reduce maintenance burden. Code still needs updating when APIs change.
- **`experimental/` subdirectory** — Creates two classes of code with unclear rules about which gets tested and maintained.
- **Ignore** — Orphan count compounds; eventual large-scale cleanup is more expensive.

### Confidence Level

High. Orphan modules are a well-documented failure mode in software engineering.

## Expected Outcomes

- Codebase contains only active, tested code
- New contributors can read the codebase and understand what's actually running
- Vault patterns document the ideas worth preserving

## Metrics & Impact

### Estimated

- ~900 lines removed, 3 vault patterns created

### Actual (Post-Implementation)

- `bioelectric_field.py`, `journey_tracker_v2.py`, `morphospace.py` documented and removed

## Related Decisions & Lessons

- [[2026-02-23-enforce-no-orphan-modules-policy]]
- [[patterns/bioelectric-field-modeling-for-action-generation]] — example: bioelectric_field.py was an orphan module, now preserved as vault pattern
- [[patterns/morphospace-stability-wells]] — example: morphospace.py was an orphan module, now preserved as vault pattern
- [[failure-mode-test-priority]] — orphan modules have 0% test coverage because nothing imports them; failure modes go undetected
