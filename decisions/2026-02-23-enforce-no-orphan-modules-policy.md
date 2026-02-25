---
title: 'Enforce no-orphan-modules policy'
date: '2026-02-23'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Orphan modules aren't 'future work' — they're maintenance burden. If nobody imports a module, nobody tests it, nobody updates it when APIs change, and nobody knows if it works. The concepts are valuable; the code without consumers is not.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Enforce no-orphan-modules policy'
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

Code review found several modules that had been written but were not imported or used anywhere: `bioelectric_field.py`, `journey_tracker_v2.py`, `morphospace.py`. These represented significant engineering effort. When asked about their purpose, the answer was "they're for a future feature."

The modules were not tested (nothing imported them to test against), not updated when APIs changed (causing silent staleness), and created confusion for anyone reading the codebase about what was actually active vs. speculative.

## Decision

No module may exist without at least one consuming module that imports and uses it. Dead code must be either:
1. Connected to the pipeline immediately, or
2. Documented in vault (concepts/patterns) and deleted

"Document then delete" preserves the ideas without the maintenance burden.

## Chosen Option

Enforce the rule via code review. Any PR introducing a new module must include at least one import and usage site. Existing orphans are deleted after documenting key concepts in vault.

## Alternatives Considered

1. Keep orphans with clear "experimental" markers
2. Move orphans to a `experimental/` subdirectory
3. Delete immediately without documenting
4. Enforce via import analysis in CI (e.g., `vulture`)

## Decision Reasoning

### Why This Option?

The documentation-then-deletion approach preserves value while eliminating maintenance burden. The vault captures the ideas; the codebase contains only what's active. This is better than "experimental/" directories because experimental code still creates maintenance surface area.

Future CI enforcement with `vulture` is a good next step but wasn't prioritized.

### Alternatives Rejected

- **"Experimental" markers** — Doesn't actually reduce maintenance burden; orphans still need updating when APIs change.
- **`experimental/` subdirectory** — Moves the problem; still creates confusion about what's production vs. exploratory.
- **Delete without documenting** — Wastes engineering insight. The concepts in orphan modules are often valid; only the premature implementation is the problem.

### Confidence Level

High. Orphan modules consistently cause confusion and accumulate silent staleness. The pattern is well-documented across software projects.

## Expected Outcomes

- Codebase contains only active code
- Every module has at least one clear consumer
- Concepts from deleted modules preserved in vault patterns/concepts
- New contributors can read the codebase and understand what's active

## Metrics & Impact

### Estimated

- 3 orphan modules deleted (~900 lines removed)
- Concepts preserved in 3 vault pattern documents

### Actual (Post-Implementation)

- Codebase cleanup: `bioelectric_field.py`, `journey_tracker_v2.py`, `morphospace.py` documented and removed

## Related Decisions & Lessons

- [[2026-02-24-anti-pattern-disconnected-modules-without-consumers]]
- [[patterns/bioelectric-field-modeling-for-action-generation]]
