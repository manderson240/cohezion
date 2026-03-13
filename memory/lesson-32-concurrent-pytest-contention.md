---
title: Concurrent Pytest Contention: Parallel Test Runners Sharing Resources Cause Flaky Tests
date: 2026-02-23
severity: HIGH
category: testing
cost_of_forgetting: "Intermittent test failures in parallel runs; tests pass individually but fail together"
tags: [pytest, concurrency, testing, flaky-tests, parallelism]
status: validated
aspect: knower
neural:
  activation: 0.73
  stage: growing
  synapse_in: 11
  synapse_out: 6
---

# Lesson: Concurrent Pytest Contention: Parallel Test Runners Sharing Resources Cause Flaky Tests

## Context

During Cohezion test suite optimization in February 2026, the team enabled parallel test execution using pytest-xdist (`pytest -n auto`) to reduce CI run times. Individual tests all passed when run sequentially, but parallel execution produced random, non-reproducible failures. The failure pattern was: run 1 passes, run 2 fails on test A, run 3 passes, run 4 fails on test B. Different tests failed each time.

## Problem

pytest-xdist spawns multiple worker processes that run tests concurrently. When tests share mutable resources, workers interfere with each other:

1. **Shared temp files**: Multiple workers writing to `/tmp/test_output.json` simultaneously. One worker reads a partially-written file from another worker, causing JSON parse errors or assertion failures.
2. **Port collisions**: Tests that start servers on hardcoded ports (e.g., `localhost:8888`) collide when two workers try to bind the same port. One gets `Address already in use`.
3. **Database table conflicts**: Tests that write to the same database table (even in SurrealDB) race on reads and writes, producing inconsistent results.

These failures are non-deterministic -- they depend on execution timing, making them extremely difficult to reproduce and debug. The tests pass individually (`pytest test_foo.py`) because there is no concurrent worker to create contention.

## Core Learning

**Parallel pytest requires resource isolation per worker. Use unique identifiers (worker ID, UUID) for all shared resources.**

### Pattern
```python
# WRONG: shared resource path
def test_output_file():
    output = Path("/tmp/test_output.json")  # Shared across workers!
    write_results(output)

# RIGHT: use pytest's tmp_path (worker-unique)
def test_output_file(tmp_path):
    output = tmp_path / "test_output.json"  # Worker-isolated by pytest
    write_results(output)
```

## Solution

Three isolation patterns were applied across the test suite:

1. **File paths**: Replace all hardcoded `/tmp/` paths with pytest's `tmp_path` fixture, which provides a unique temporary directory per test.
2. **Network ports**: Use `socket.bind((host, 0))` to dynamically allocate available ports instead of hardcoding.
3. **Database tables**: Use worker-specific table names or test-specific record IDs to prevent cross-worker interference.

After applying these patterns, parallel test reliability went from approximately 70% (random failures on most runs) to 99%+ across hundreds of CI runs.

## Prevention

- **Use `tmp_path` by default**: Never use hardcoded paths in tests; always accept `tmp_path` as a fixture parameter
- **Dynamic port allocation**: `socket.bind(("", 0))` lets the OS assign an available port
- **Worker-scoped fixtures**: Use `@pytest.fixture(scope="session")` with `worker_id` for resources that need worker-level isolation
- **Test isolation review**: When adding pytest-xdist to an existing project, audit all tests for shared mutable resources before enabling parallelism

## Cost of Forgetting

- **Non-reproducible test failures** that waste hours of debugging time
- **False CI failures** that erode developer trust in the test suite
- **Disabled parallelism**: Teams often disable `-n auto` rather than fixing isolation, losing the 3-5x speedup
- **Intermittent production bugs**: Shared resource patterns in tests often mirror shared resource patterns in production code

## Recommendations

### Do
- Always use tmp_path fixture instead of hardcoded /tmp paths
- Allocate ports dynamically with socket.bind((host, 0))

### Don't
- Use hardcoded file paths in tests
- Share database tables across parallel workers

## Related Concepts

- [[compound-engineering]] - Reliable test infrastructure enables reliable compound builds
- [[concept-testing]] - parallel pytest requires resource isolation per worker
- [[concept-isolation]] - worker-unique resource identifiers (tmp_path, dynamic ports) are the isolation mechanism
- [[python-314-free-threaded-gil-removal]] - free-threaded Python amplifies shared resource contention in parallel test runs
- [[lesson-07-gtt-carveout-illusion]] - concurrent pytest contention is a manifestation of the carveout illusion: test workers appear isolated by namespace but still share /tmp paths, ports, and database tables
- [[lesson-25-uv-venv-contention]] - another concurrency contention lesson: parallel uv installs corrupt shared venvs

## Validation

**Discovered**: Feb 2026 in Cohezion test suite optimization
**Impact**: Parallel test reliability from ~70% to 99%+
**Status**: Validated
