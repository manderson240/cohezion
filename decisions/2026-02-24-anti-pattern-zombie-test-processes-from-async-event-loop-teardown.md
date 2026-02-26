---
title: 'Anti-pattern: Zombie test processes from async event loop teardown'
date: '2026-02-24'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Zombie processes accumulate silently and consume resources that could be used for actual development. The 7 GB RAM recovery from killing 12 processes is significant on any machine.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Anti-pattern: Zombie test processes from async event loop teardown'
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

**Anti-pattern:** Writing async tests without explicit timeouts, relying on asyncio to clean up event loops on test teardown.

When `asyncio` event loops are not properly closed — common when coroutines are cancelled or exceptions occur mid-flight — test processes hang indefinitely. They don't crash; they don't produce output; they just wait. The pytest runner treats them as in-progress tests. On CI, this triggers wall-clock limits. Locally, they silently accumulate.

Discovered when 12 zombie processes from overnight test runs were found consuming ~600 MB each (~7 GB total).

## Decision

Always add explicit timeouts to async tests. This is the positive formulation of this lesson.

## Chosen Option

`pytest-timeout` with global `timeout = 30` in `pyproject.toml`. Per-test override with `@pytest.mark.timeout(N)` for legitimately long operations.

## Alternatives Considered

1. Trust asyncio cleanup (anti-pattern)
2. pytest-timeout with global config (chosen)
3. Manual try/finally in each test
4. anyio with timeout scope

## Decision Reasoning

### Why This Option?

`pytest-timeout` sends `SIGALRM` after the timeout, which forces cleanup regardless of event loop state. This is the only solution that works even when the event loop itself is stuck.

### Alternatives Rejected

- **Trust asyncio cleanup** — Proven to fail. When a coroutine is cancelled mid-await, the cleanup path may not execute, leaving the event loop running.
- **Manual try/finally** — Doesn't work when the loop itself hangs; the finally block also hangs.

### Confidence Level

High. Empirically observed; solution is standard.

## Expected Outcomes

- Hung tests surface as `TimeoutError` instead of zombie processes
- Test suite terminates within predictable wall-clock window
- 7 GB RAM no longer consumed by zombie processes

## Metrics & Impact

### Estimated

- 7 GB RAM freed when zombie processes avoided

### Actual (Post-Implementation)

- Overnight test runs now terminate cleanly

## Related Decisions & Lessons

- [[2026-02-23-always-set-pytest-timeouts-for-async-tests]]
- [[async-singleton-lock-isolation]] — pattern for proper event loop isolation in singleton async tests
- [[async-mock-subprocess-in-tests]] — prevents test hangs from unmocked external service calls
- [[failure-mode-test-priority]] — zombie processes are a resource-exhaustion failure mode; test suites must detect them
- [[patterns/lessons/lesson-32-concurrent-pytest-contention|lesson-32]] — concurrent pytest contention and async process accumulation
- [[patterns/lessons/lesson-34-test-hang-unmocked-live-service|lesson-34]] — test hang patterns from unmocked live services
