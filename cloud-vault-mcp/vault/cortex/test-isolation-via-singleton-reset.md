---
title: Test Isolation via Singleton Reset
date: 2026-02-23
tags: [testing, singleton, pattern, architecture]
status: active
aspect: knower
neural:
  activation: 0.81
  stage: mature
  synapse_in: 3
  synapse_out: 11
---

# Test Isolation via Singleton Reset

The singleton reset pattern is a testing technique that ensures test isolation when production code uses the singleton design pattern. Singletons maintain a single shared instance across the application, which creates a problem for testing: state from one test leaks into the next, causing order-dependent failures, flaky tests, and false positives/negatives.

The solution is straightforward: reset the singleton instance to `None` (or its initial state) before and after each test, typically via a pytest fixture with `autouse=True`. This guarantees that every test starts with a fresh singleton, eliminating state leakage. The pattern applies to any singleton — database connections, configuration managers, logger instances, executor pools, and agent session managers.

The technique is especially important in agentic AI systems where singletons are common: session managers, executor pools, and context caches are often implemented as singletons for performance and consistency. Without proper test isolation, concurrent test execution (pytest-xdist) can produce race conditions where parallel tests compete for the same singleton instance, leading to the contention issues documented in lesson-32.

## Pattern

```python
@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton instance before and after each test."""
    MySingleton._instance = None
    yield
    MySingleton._instance = None
```

For singletons with cleanup requirements (open connections, file handles):

```python
@pytest.fixture(autouse=True)
def reset_singleton():
    MySingleton._instance = None
    yield
    if MySingleton._instance is not None:
        MySingleton._instance.close()  # Clean up resources
    MySingleton._instance = None
```

For logger singletons (a common case):

```python
@pytest.fixture(autouse=True)
def reset_logger_handlers():
    """Prevent handler accumulation across tests."""
    logger = logging.getLogger("my_app")
    logger.handlers.clear()
    yield
    logger.handlers.clear()
```

## Key Properties

- **Bidirectional reset** — Reset both before and after each test to handle both test-order contamination and teardown failures
- **Autouse for safety** — Use `autouse=True` so the fixture applies to every test automatically; opt-in fixtures are easily forgotten
- **Resource cleanup** — Singletons holding resources (connections, file handles) must be explicitly closed before reset, not just set to None
- **Concurrent test safety** — Essential for pytest-xdist parallel execution where multiple workers share the same process space
- **Composable with other fixtures** — Singleton reset fixtures can be combined with other fixtures (database cleanup, mock injection) in conftest.py

## Examples

- **Session manager singleton** — Agent session manager holds current session state; resetting between tests prevents session ID contamination
- **Logger handler accumulation** — Without reset, each test that configures a logger appends handlers, causing duplicate log entries and test output noise
- **Executor pool singleton** — A singleton thread pool executor leaks tasks between tests if not properly drained and reset

## Primary Sources

- pytest fixtures documentation — https://docs.pytest.org/en/stable/how-to/fixtures.html
- Python logging cookbook: handler management — https://docs.python.org/3/howto/logging-cookbook.html

## Related

- [[lesson-32-concurrent-pytest-contention]]
- [[lesson-38-singleton-executor-for-sessions-new]]
- [[concept-testing]] — singleton reset is a specific testing technique applicable to concept validation pipelines that use singleton services
- [[event-driven-daemon-pattern]] — daemons often use singletons; this reset pattern enables isolated testing of daemon components

## Related Concepts

- [[agent-context]] — agent context managers are frequently implemented as singletons requiring test isolation
- [[safe-persistent-storage-lifecycle]] — storage singletons (database connections) must follow safe lifecycle policies during test teardown
- [[non-blocking-observability]] — observability singletons (metric collectors, loggers) are common reset targets
- [[concept-automation]] — automated concept testing pipelines must isolate singleton state between test runs
- [[compound-engineering]] — compound engineering sessions use singleton session managers that need isolation in integration tests

## Session References

- [[session-46-test-isolation-and-phase-2-security]] — logger handler clearing in conftest.py as direct application of singleton reset

## Relevance to Cohezion

The singleton reset pattern was adopted after the Cohezion test suite experienced flaky failures from state leakage between tests (documented in [[lesson-32-concurrent-pytest-contention]]). The executor singleton issue ([[lesson-38-singleton-executor-for-sessions-new]]) was a particularly costly instance: tests passed individually but failed when run together because the singleton executor retained tasks from previous tests. The pattern is now standard practice in all Cohezion conftest.py files and is enforced during [[adversarial-review]] of test code.
