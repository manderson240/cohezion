---
title: Runtime JSON Pollution: Debug Output Corrupts JSON Parsing in Pipelines
date: 2026-02-23
severity: HIGH
category: debugging
cost_of_forgetting: "Pipeline data corruption from mixed stdout -- JSON parsing fails silently or produces garbled results"
tags: [json, logging, debugging, pipeline, data-corruption]
status: validated
aspect: knower
neural:
  activation: 0.79
  stage: growing
  synapse_in: 16
  synapse_out: 9
---

# Lesson: Runtime JSON Pollution: Debug Output Corrupts JSON Parsing in Pipelines

## Context

During Cohezion data pipeline debugging in February 2026, several pipeline stages were producing corrupted output. The symptom was `json.JSONDecodeError` in downstream components, but the JSON being produced by the upstream component appeared correct in isolation. Investigation revealed that debug `print()` statements in the producing functions were writing human-readable text to stdout alongside the JSON output. Pipeline components consuming stdout received a mixture of debug text and JSON that could not be parsed.

## Problem

The failure mode is insidious because it is intermittent and hard to trace:

1. **Silent corruption**: When debug output appears before the JSON, `json.loads()` raises an error. When it appears after, some JSON parsers silently succeed on the first valid JSON object and discard the rest. When it appears between JSON lines in a streaming context, some lines parse and others fail.
2. **Development-only symptoms**: Debug print statements are often added during development and removed before merge. But if one is missed, it poisons the pipeline in production.
3. **Upstream blame**: The error surfaces in the consumer, not the producer. The consumer team debugs their parsing code when the real problem is upstream.

This is closely related to the [[2026-02-10-telemetry-corruption-fix]] incident where telemetry writes shared a data path with primary output.

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

## Solution

The fix has both immediate and structural components:

1. **Immediate**: Audit all pipeline functions for `print()` statements; replace with `logging.debug()` or `print(..., file=sys.stderr)`
2. **Structural**: Configure the Python `logging` module to always write to stderr by default. Add a project-wide linting rule that flags bare `print()` calls in production code.
3. **Validation**: Add a pipeline test that captures stdout and validates it as valid JSON (or empty) for every pipeline stage.

## Prevention

- **Use the logging module**: Configure handlers to write to stderr by default; never use bare `print()` in production code
- **Lint for print statements**: Use ruff rules to flag `print()` in non-test, non-CLI code
- **Test stdout purity**: Add pipeline tests that capture stdout and assert JSON validity
- **Separate data from diagnostics**: At the architecture level, data flows through stdout; diagnostics flow through stderr. No exceptions.

## Cost of Forgetting

- **Pipeline data corruption**: JSON parsing failures or silently garbled data
- **Upstream blame misdirection**: Debugging effort wasted in the consumer when the bug is in the producer
- **Intermittent failures**: Corruption only occurs when the debug code path is triggered, making it hard to reproduce
- **Credential exposure risk**: Debug print statements may also leak sensitive data (see [[lesson-26-never-print-credentials]])

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
- [[2026-02-10-telemetry-corruption-fix]] - related incident: telemetry writes sharing the data path with primary output
- [[data-pipelines]] - stdout/stderr discipline is foundational to reliable data pipeline architecture

## Validation

**Discovered**: Feb 2026 in Cohezion data pipeline debugging
**Status**: Validated -- logging module with stderr handlers now standard across project
