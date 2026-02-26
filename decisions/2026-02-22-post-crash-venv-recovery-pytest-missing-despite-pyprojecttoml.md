---
title: 'Post-Crash Venv Recovery: pytest Missing Despite pyproject.toml'
date: '2026-02-22'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'System crashes can corrupt venv without touching pyproject.toml. The lock file and installed packages can desync. `uv add --dev` forces reinstallation even when deps appear present. pytest-cov and pytest-asyncio are required by pytest.ini addopts and asyncio_mode=strict respectively.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Post-Crash Venv Recovery: pytest Missing Despite pyproject.toml'
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

- [[experiments/2026-02-22-session-70-heal-and-test-fix|Session 70: Heal + Test Fix Cycle]] — the experiment that revealed this venv issue and fixed 83 test failures in the same session
- [[decisions/2026-02-22-cz-spec-workflow-retrospective|cz spec workflow retrospective]] — broader session context where venv integrity was critical for 62-test suite
