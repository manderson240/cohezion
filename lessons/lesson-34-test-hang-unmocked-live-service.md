---
title: Test Hang from Unmocked Live Service: Tests Hang Indefinitely on Connection Timeout
date: 2026-02-23
severity: HIGH
category: testing
tags: [testing, mocking, timeout, test-hang, live-services]
status: validated
---

# Lesson: Test Hang from Unmocked Live Service: Tests Hang Indefinitely on Connection Timeout

## Context

Tests that call unmocked live services can hang indefinitely when the service is unavailable. pytest doesn't kill hanging tests by default -- the entire test suite stalls.

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

## Validation

**Discovered**: Feb 2026 in Cohezion test suite debugging
**Status**: Validated
