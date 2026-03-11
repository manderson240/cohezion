---
title: GTT Carveout Illusion: Logical Isolation Does Not Guarantee Physical Separation
date: 2026-02-23
severity: HIGH
category: architecture
cost_of_forgetting: "Intermittent failures from shared state that appears isolated; debugging hours wasted on phantom resource collisions"
tags: [architecture, isolation, testing, system-design]
status: validated
aspect: knower
neural:
  activation: 0.481
  stage: growing
  cluster: lessons
---

# Lesson: GTT Carveout Illusion: Logical Isolation Does Not Guarantee Physical Separation

## Context

During Cohezion test infrastructure development, the test suite used environment configuration carveouts to isolate tests: each test received a "separate" configuration with different database names, different log paths, and different API endpoints. Despite this logical separation, tests still interfered with each other intermittently. The term "GTT Carveout Illusion" (Global/Temp/Transport) was coined to describe the three most common channels through which logically isolated components still share physical state.

## Problem

Logical isolation through configuration gives a false sense of separation:

1. **Global singletons**: Python modules loaded once share global state. A singleton database connection pool is shared across all test configurations, regardless of the config "namespace."
2. **Temp file collisions**: Tests writing to `/tmp/test_output.json` collide because the OS filesystem is shared. Different configs do not create different `/tmp` directories.
3. **Network port contention**: Tests starting servers on hardcoded ports (`:8080`) collide even when configured with different "server names."

The carveout illusion is especially dangerous because the isolation appears to work most of the time. Failures are intermittent, depending on timing and execution order, making them extremely difficult to reproduce.

## Core Learning

**Verify isolation with actual resource probes, not logical reasoning about architecture.**

### Why This Matters
- Tests that appear isolated may share database connections, temp files, or ports
- Failures in isolated modules can corrupt shared state
- Intermittent failures from carveout illusions are hard to reproduce

### Pattern
```python
# WRONG: assume config carveout = isolation
with isolated_env("test"):
    run_test()  # May still touch shared /tmp or db

# RIGHT: verify isolation before asserting it
with isolated_env("test") as env:
    assert env.temp_dir != shared_temp_dir
    assert env.db_connection != shared_db
    run_test()
```

## Solution

True isolation requires physical separation, not just logical naming:

1. **File paths**: Use `tmp_path` fixtures or UUID-based directory names instead of shared `/tmp` paths
2. **Database connections**: Create genuinely separate connection pools per test, not just different database names on the same pool
3. **Network ports**: Use dynamic port allocation (`socket.bind(("", 0))`) instead of hardcoded ports
4. **Global state**: Reset singleton state in test setup/teardown, or use dependency injection to avoid singletons entirely

The key principle: if you cannot probe the resource and prove it is unique to this test, it is not isolated.

## Prevention

- **Probe, do not assume**: After setting up isolation, verify it with assertions on actual resource handles
- **Use per-test unique identifiers**: UUIDs in file paths, database schemas, port numbers
- **Avoid global singletons in testable code**: Use dependency injection so resources can be swapped per test
- **Watch for the three channels**: Global state, temp files, and network ports are the most common leaks

## Cost of Forgetting

- **Intermittent test failures** that pass individually but fail in combination
- **Hours of debugging** phantom resource collisions that only reproduce under specific timing conditions
- **False confidence** in isolation that masks real shared-state bugs
- **Parallel execution disabled**: Teams disable pytest-xdist rather than fixing isolation (see [[lesson-32-concurrent-pytest-contention]])

## Recommendations

### Do
- Probe actual resources (files, ports, DB connections) to verify isolation
- Use unique identifiers per test run (UUIDs in file paths, DB schemas)

### Don't
- Trust namespace/config separation as proof of isolation
- Skip isolation verification under time pressure

## Related Concepts

- [[compound-engineering]] - Proper isolation enables reliable parallel compound work
- [[testing-agent-skills-with-evals]] - agent eval isolation suffers the same carveout illusion
- [[lesson-32-concurrent-pytest-contention]] - concurrent pytest is a direct manifestation of the carveout illusion in test infrastructure
- [[concept-isolation]] - this lesson defines the deeper principle behind test isolation: physical, not just logical
- [[test-isolation-via-singleton-reset]] - singleton reset is one technique for breaking global state sharing

## Validation

**Discovered**: Feb 2026 during test infrastructure debugging
**Status**: Validated across Cohezion test infrastructure
