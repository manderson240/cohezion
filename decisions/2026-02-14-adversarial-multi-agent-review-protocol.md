---
title: "Adversarial Multi-Agent Review Protocol"
date: "2026-02-14"
status: proposed
tags: [decision]

# NEW FIELDS FOR OBSERVABILITY
decision_reasoning:
  chosen_option: "{{chosen_option}}"
  rationale: "Single-agent implementation misses bugs that would cause production crashes. The 3-agent review caught 2 CRITICAL bugs (metadata=None crash, silent data corruption) and 5 HIGH issues that all tests passed on. The cost (3 agent spawns) is negligible vs. production crash risk. Different lenses (correctness vs. tests vs. architecture) find different bug classes."
  confidence_score: 0.0  # 0-1 scale
  alternatives_rejected:
    - "{{alt1}}"
    - "{{alt2}}"
  reasoning_chain: []  # List of steps in reasoning process

metrics:
  estimated_cost: 0.0  # USD
  estimated_time_hours: 0.0
  actual_cost: 0.0  # USD (fill after implementation)
  actual_time_hours: 0.0  # Fill after implementation
  tokens_used: 0  # If applicable
  cost_per_lesson: 0.0  # Lessons generated ÷ actual cost
  lessons_generated: []  # Links to lesson notes
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

- [[multi-agent-systems]]
- [[agentic-ai]]
- [[2026-02-11-session-55-adversarial-review-blockers-identified]]
- [[honest-metrics-over-inflated-claims]]
- [[test-isolation-via-singleton-reset]]
- [[lesson-12-layered-validation]]
