---
title: GTT Carveout Illusion: Logical Isolation Does Not Guarantee Physical Separation
date: 2026-02-23
severity: HIGH
category: architecture
tags: [architecture, isolation, testing, system-design]
status: validated
---

# Lesson: GTT Carveout Illusion: Logical Isolation Does Not Guarantee Physical Separation

## Context

Systems that appear isolated via namespace carveout or config overrides can still share state through global singletons, shared file handles, or network ports. The carveout illusion is believing logical separation equals physical isolation.

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

## Recommendations

### Do
- Probe actual resources (files, ports, DB connections) to verify isolation
- Use unique identifiers per test run (UUIDs in file paths, DB schemas)

### Don't
- Trust namespace/config separation as proof of isolation
- Skip isolation verification under time pressure

## Related Concepts

- [[compound-engineering]] - Proper isolation enables reliable parallel compound work

## Validation

**Status**: Validated across Cohezion test infrastructure
