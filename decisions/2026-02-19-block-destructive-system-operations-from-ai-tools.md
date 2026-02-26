---
title: 'Block destructive system operations from AI tools'
date: '2026-02-19'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Destructive operations (vacuum, rm -rf on logs, database drops) are irreversible. AI tools operate fast and don't naturally pause to consider irreversibility. The guard hook forces a manual step for destructive operations, which gives the human operator a moment to consider whether backup is needed. The journald config prevents the root cause (unbounded journal growth) so vacuum should rarely be needed. The cascade: crash loop → journal bloat → panic vacuum → lost diagnostics. Breaking ANY link in this chain prevents the problem.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Block destructive system operations from AI tools'
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

## Decision

## Chosen Option

## Alternatives Considered

## Decision Reasoning

### Why This Option?

### Alternatives Rejected

### Confidence Level

## Expected Outcomes

## Metrics & Impact

### Estimated

### Actual (Post-Implementation)

## Related Decisions & Lessons

- [[patterns/log-lifecycle-management|Log Lifecycle Management Pattern]] — the concrete pattern that emerged from the SurrealDB crash-loop incident; shows what happens when destructive operations (vacuum) are run without pre-flight checks
- [[concepts/compound-engineering-investigation-retrospection-before-destructive-operations|Compound Engineering: Investigation Before Destructive Operations]] — the principle this decision operationalizes
- [[decisions/2026-02-09-operational-principle-no-destructive-operations-without-learning|Operational Principle: No Destructive Operations Without Learning]] — the predecessor principle; this decision adds a system-level enforcement hook
- [[concepts/ai-safety|AI Safety]] — the broader field motivating guards on irreversible AI tool actions
