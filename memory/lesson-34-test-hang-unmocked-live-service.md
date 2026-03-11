---
title: Test Hang from Unmocked Live Service: Tests Hang Indefinitely on Connection Timeout
date: 2026-02-23
severity: HIGH
category: testing
cost_of_forgetting: "Entire test suite stalls indefinitely; CI runners timeout and block all deployments"
tags: [testing, mocking, timeout, test-hang, live-services]
status: validated
aspect: knower
neural:
  activation: 0.507
  stage: growing
  cluster: lessons
---

# Lesson: Test Hang from Unmocked Live Service: Tests Hang Indefinitely on Connection Timeout

## Context

During Cohezion test suite debugging in February 2026, the test suite began intermittently stalling during CI runs. The symptoms were confusing: some runs completed in 30 seconds, others hung for the full CI timeout (10 minutes) before being killed. The root cause was tests that made real network calls to external services (SurrealDB, Ollama) without mocking. When those services were available (local development), tests passed quickly. When services were unavailable (CI environment, or local service not running), TCP connection attempts would hang for the default system timeout -- often 2+ minutes per connection attempt.

## Problem

pytest does not kill hanging tests by default. A single test waiting on a TCP connection to a downed service blocks the entire test runner:

1. **Indefinite hang**: A test calling `surrealdb.query()` with no timeout waits for the default TCP timeout (often 120 seconds per attempt, with retries).
2. **Suite-wide stall**: pytest runs tests sequentially by default. One hanging test blocks all subsequent tests.
3. **CI cascade**: CI runners have a global timeout (10 minutes), but that is far too long to wait. The feedback loop goes from 30 seconds to 10 minutes.
4. **Intermittent nature**: Tests pass locally when services are running, making the issue hard to reproduce during development.

## Core Learning

**Set explicit timeout on ALL tests that could contact external services. Mock is preferred; timeout is required when not mocking.**

### Pattern
```python
# Option 1: Mock (preferred)
@patch("src.db.surrealdb_client")
def test_store_agent(mock_db):
    mock_db.create.return_value = {"id": "agent:123"}
    result = store_agent("session-1")
    assert result["id"] == "agent:123"

# Option 2: Timeout guard
@pytest.mark.timeout(5)
def test_live_db_connection():
    result = db.query("SELECT 1")
    assert result is not None
```

```ini
# pytest.ini -- global safety net
[pytest]
timeout = 30
```

## Solution

A two-layer defense was implemented:

1. **Global timeout in pytest.ini**: `timeout = 30` ensures no test can run longer than 30 seconds. This is the safety net that catches any unmocked service call.
2. **Systematic mocking**: All external service calls in unit tests were replaced with mocks (see [[lesson-18-mock-live-services-in-tests]]). Integration tests that need real services are in a separate `tests/integration/` directory and run with `pytest -m integration` only when services are available.

The result: test suite reliability improved from approximately 60% to 98%, and CI feedback time dropped back to 30 seconds.

## Prevention

- **Add `timeout = 30` to pytest.ini** in every project as the first CI configuration step
- **Mock at the client level**: Patch the client object, not individual methods, for cleaner tests
- **Separate integration tests**: Use `tests/integration/` and pytest markers to isolate tests that need real services
- **Default CI command**: Use `pytest -m "not integration"` as the default CI test command

## Cost of Forgetting

- **Entire test suite hangs indefinitely** when any external service is unavailable
- **CI pipeline blocks**: 10-minute timeouts instead of 30-second runs
- **Intermittent failures** that are impossible to reproduce locally when services are running
- **Developer trust erodes**: Flaky CI leads to "retry and hope" behavior instead of investigating failures

## Recommendations

### Do
- Set timeout = 30 in pytest.ini as a global safety net
- Mock all external services in unit tests

### Don't
- Run tests without a global timeout configured
- Assume tests fail quickly when services are unavailable

## Related Concepts

- [[compound-engineering]] - Reliable test suite timing enables reliable compound CI
- [[testing-agent-skills-with-evals]] - Agent skill evals require explicit timeout guards to prevent indefinite hangs when live services are unavailable during evaluation runs
- [[lesson-18-mock-live-services-in-tests]] - The preferred solution: mock external services entirely rather than rely on timeout guards
- [[concept-testing]] - unmocked live services cause indefinite test hangs; global timeout is the safety net
- [[concept-isolation]] - test isolation via mocking prevents test suite stalls from unavailable services
- [[lesson-32-concurrent-pytest-contention]] - another testing infrastructure lesson: parallel tests compound the hanging problem when multiple workers hit unavailable services simultaneously

## Validation

**Discovered**: Feb 2026 in Cohezion test suite debugging
**Impact**: Test suite reliability improved from 60% to 98%; CI time from 10 min to 30 sec
**Status**: Validated
