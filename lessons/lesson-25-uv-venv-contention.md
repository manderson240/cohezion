---
title: UV Venv Contention: Concurrent UV Installs to Same Venv Cause Corruption
date: 2026-02-23
severity: HIGH
category: tooling
tags: [uv, venv, python, concurrency, dependency-management]
status: validated
---

# Lesson: UV Venv Contention: Concurrent UV Installs to Same Venv Cause Corruption

## Context

uv pip install is fast but not safe for concurrent writes to the same virtualenv. Running multiple uv pip install processes simultaneously causes package metadata corruption.

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

## Recommendations

### Do
- Merge all requirements into a single install command
- Use separate venv directories for concurrent processes
- Check venv integrity with uv pip check after install

### Don't
- Run parallel uv pip install to the same venv

## Related Concepts

- [[compound-engineering]] - Reliable dependency management enables reliable compound builds

## Validation

**Discovered**: Feb 2026 in Cohezion CI parallel jobs
**Status**: Validated
