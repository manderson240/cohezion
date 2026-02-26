---
title: Runtime JSON Pollution: Debug Output Corrupts JSON Parsing in Pipelines
date: 2026-02-23
severity: HIGH
category: debugging
tags: [json, logging, debugging, pipeline, data-corruption]
status: validated
---

# Lesson: Runtime JSON Pollution: Debug Output Corrupts JSON Parsing in Pipelines

## Context

Functions that return JSON output can be corrupted when debug print statements write to stdout. Pipeline components that parse stdout JSON receive polluted output with extra non-JSON text mixed in.

## Core Learning

**Never write to stdout in code that produces machine-parseable output. Use stderr for all debug/log output.**

### Pattern
```python
# WRONG: print to stdout in a JSON output function
def get_results():
    print("DEBUG: fetching results")  # POLLUTES stdout
    return json.dumps(results)

# RIGHT: use stderr for all diagnostic output
def get_results():
    print("DEBUG: fetching results", file=sys.stderr)  # safe
    return json.dumps(results)
```

## Recommendations

### Do
- Use logging module with stderr handlers for all diagnostic output
- Test pipeline output by capturing stdout and checking JSON validity

### Don't
- Mix debug output and data output on stdout
- Assume log handlers write to stderr by default

## Related Concepts

- [[compound-engineering]] - Clean data pipelines require pollution-free stdout
- [[agent-context]] - JSON pollution corrupts context pipelines that parse stdout
- [[data-analysis]] - clean stdout is foundational to trustworthy data analysis pipelines
- [[api-design]] - API outputs must separate data (stdout) from diagnostics (stderr)
- [[concept-modularity]] - module boundaries should enforce stdout/stderr discipline at each layer
- [[operational-data-ai-agents]] - debug output contaminating stdout is a concrete data hygiene failure; agents that parse stdout JSON receive corrupted "senses" when print statements pollute the stream

## Validation

**Discovered**: Feb 2026 in Cohezion data pipeline debugging
**Status**: Validated
