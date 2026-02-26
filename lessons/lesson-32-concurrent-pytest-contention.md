---
title: Concurrent Pytest Contention: Parallel Test Runners Sharing Resources Cause Flaky Tests
date: 2026-02-23
severity: HIGH
category: testing
tags: [pytest, concurrency, testing, flaky-tests, parallelism]
status: validated
---

# Lesson: Concurrent Pytest Contention: Parallel Test Runners Sharing Resources Cause Flaky Tests

## Context

Running pytest with -n auto (parallel execution via pytest-xdist) against tests that share resources (temp files, database tables, ports) causes random test failures that pass individually.

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
- [[python-314-free-threaded-gil-removal]] - free-threaded Python amplifies shared resource contention in parallel test runs; with true parallelism, the tmp_path and dynamic port isolation discipline becomes mandatory rather than just best practice
- [[lesson-07-gtt-carveout-illusion]] - concurrent pytest contention is a manifestation of the carveout illusion: test workers appear isolated by namespace but still share /tmp paths, ports, and database tables

## Validation

**Discovered**: Feb 2026 in Cohezion test suite optimization
**Status**: Validated
