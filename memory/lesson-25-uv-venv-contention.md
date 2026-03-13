---
title: UV Venv Contention: Concurrent UV Installs to Same Venv Cause Corruption
date: 2026-02-23
severity: HIGH
category: tooling
cost_of_forgetting: "Package metadata corruption in virtualenv; import errors and version conflicts from corrupted package state"
tags: [uv, venv, python, concurrency, dependency-management]
status: validated
aspect: knower
neural:
  activation: 0.69
  stage: growing
  synapse_in: 7
  synapse_out: 4
---

# Lesson: UV Venv Contention: Concurrent UV Installs to Same Venv Cause Corruption

## Context

During Cohezion CI parallel jobs in February 2026, multiple CI stages ran `uv pip install` simultaneously against the same shared virtualenv. The goal was to speed up dependency installation by parallelizing it. Instead, the package metadata in the virtualenv became corrupted, causing import errors and version conflicts in subsequent test runs.

## Problem

`uv` is designed for speed -- it is 10-100x faster than `pip`. But this speed comes from aggressive parallel I/O that is not safe for concurrent writes to the same virtualenv:

1. **Metadata corruption**: Two `uv pip install` processes writing to the same `site-packages/` directory simultaneously can leave package metadata files (`.dist-info/`) in an inconsistent state.
2. **Partial installs**: One process may read a package directory that another process is in the middle of writing, producing import errors for packages that appear installed but are incomplete.
3. **Version conflicts**: Two processes installing different versions of the same transitive dependency race on which version ends up in the final state.

The corruption is silent -- `uv pip install` reports success for both processes, but the resulting virtualenv is broken.

## Core Learning

**Serialize all uv install operations to the same venv. Use sequential execution for concurrent installs.**

### Pattern
```bash
# WRONG: concurrent installs to same venv
uv pip install -r req-a.txt &
uv pip install -r req-b.txt &
wait

# RIGHT: sequential installs
uv pip install -r req-a.txt
uv pip install -r req-b.txt

# Or merge requirements first
cat req-a.txt req-b.txt | sort -u > combined.txt
uv pip install -r combined.txt
```

## Solution

Two approaches work, depending on the use case:

1. **Merge requirements**: Combine all requirement files into a single install command. This is the simplest and most reliable approach: `uv pip install -r combined.txt`.
2. **Separate venvs**: If concurrent processes genuinely need different dependencies, give each its own virtualenv. Use `uv venv /path/to/unique-venv` for each.

After any install, validate with `uv pip check` to verify package metadata integrity.

## Prevention

- **Single install command**: Merge all requirements into one file and install once
- **Separate venvs for concurrency**: Each concurrent process gets its own virtualenv
- **Validate after install**: `uv pip check` verifies that all packages are correctly installed
- **CI pipeline design**: In CI, use a single install step before parallel test stages, not parallel installs

## Cost of Forgetting

- **Corrupted virtualenv**: Import errors for packages that appear installed
- **Version conflicts**: Wrong package versions loaded at runtime
- **Non-reproducible failures**: Corruption depends on race timing, making it intermittent
- **CI pipeline breakage**: Parallel CI stages fail unpredictably

## Recommendations

### Do
- Merge all requirements into a single install command
- Use separate venv directories for concurrent processes
- Check venv integrity with uv pip check after install

### Don't
- Run parallel uv pip install to the same venv

## Related Concepts

- [[compound-engineering]] - Reliable dependency management enables reliable compound builds
- [[concept-isolation]] - concurrent uv installs must be isolated to separate venv directories or serialized
- [[python-314-free-threaded-gil-removal]] - free-threaded Python changes the venv contention model
- [[lesson-32-concurrent-pytest-contention]] - another concurrency contention lesson: shared resources in parallel test runners

## Validation

**Discovered**: Feb 2026 in Cohezion CI parallel jobs
**Impact**: CI stability restored by serializing installs or using separate venvs
**Status**: Validated
