---
title: 'Always set pytest timeouts for async tests'
date: '2026-02-23'
status: accepted
tags:
- decision
- inferred
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Async tests with improper event loop cleanup can hang forever. Without timeouts, these become zombie processes that accumulate RAM. 12 zombies × ~600 MB each = 7 GB wasted.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Always set pytest timeouts for async tests'
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

During overnight test runs on the FLUME project, async tests with improper event loop cleanup were hanging indefinitely. The root cause was `asyncio` event loops that weren't being torn down after each test, leaving processes in a zombie state that continued consuming memory. At peak, 12 zombie test processes were discovered consuming ~600 MB each — approximately 7 GB of RAM wasted.

The tests appeared to "pass" or just never terminate. CI eventually killed them via wall-clock limits, but local development sessions silently accumulated these processes.

## Decision

All async test functions must have explicit timeouts. Configure `timeout = 30` globally in `pyproject.toml` via `pytest-timeout`, and use `@pytest.mark.timeout(N)` for tests that legitimately require longer windows.

## Chosen Option

Global timeout via `pyproject.toml`:
```toml
[tool.pytest.ini_options]
timeout = 30
```

Per-test override where needed:
```python
@pytest.mark.timeout(120)
async def test_long_running_pipeline():
    ...
```

## Alternatives Considered

1. Manual `try/finally` cleanup in each test
2. No timeouts (status quo)
3. Timeouts only in CI configuration

## Decision Reasoning

### Why This Option?

`pytest-timeout` is the standard solution and applies automatically with zero per-test boilerplate. The global default in `pyproject.toml` means every future async test gets protection for free. Exceptions for long-running tests are explicit and documented in the test file.

### Alternatives Rejected

- **Manual cleanup** — Error-prone. The whole point is that cleanup was being skipped, so adding more cleanup code to tests doesn't solve the root cause.
- **No timeouts** — Proven to cause 7 GB RAM loss. Not viable.
- **CI-only timeouts** — Creates inconsistency between local and CI environments. Zombies would still accumulate locally.

### Confidence Level

High. The 7 GB RAM recovery from killing 12 processes is direct empirical evidence. The fix is low-risk and standard practice.

## Expected Outcomes

- No zombie processes accumulating during test runs
- Test suite terminates cleanly (no hanging)
- RAM usage stays bounded
- Failed async operations surface as TimeoutError instead of hanging silently

## Metrics & Impact

### Estimated

- 7 GB RAM freed per incident avoided
- Test suite completes in predictable time window

### Actual (Post-Implementation)

- Zombie processes eliminated
- Overnight test runs now terminate correctly

## Related Decisions & Lessons

- [[2026-02-24-anti-pattern-zombie-test-processes-from-async-event-loop-teardown]]
