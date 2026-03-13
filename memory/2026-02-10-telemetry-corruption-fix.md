---
title: Telemetry Corruption Fix: Isolate Observability Writes from Primary Data
date: 2026-02-23
severity: MEDIUM
category: debugging
cost_of_forgetting: "Telemetry errors silently corrupt primary data; corrupted output traced to shared write path"
tags: [lesson, telemetry, debugging, data-corruption]
status: validated
aspect: knower
neural:
  activation: 0.68
  stage: growing
  synapse_in: 1
  synapse_out: 5
---

# Lesson: Telemetry Corruption Fix: Isolate Observability Writes from Primary Data

## Context

On 2026-02-10, the Cohezion agent pipeline produced corrupted output data. Investigation traced the corruption to a shared write path: both telemetry (observability metrics) and primary data (agent output) were writing to the same file or output stream. When a telemetry write failed mid-stream, it left partial data in the output, which the primary data writer then appended to, producing a corrupted hybrid file.

## Problem

Sharing a write path between telemetry and primary data creates a dangerous coupling:

1. **Interleaved writes**: Telemetry and primary data write to the same file/stream. Their outputs interleave unpredictably.
2. **Failure contamination**: A failed telemetry write leaves partial data that corrupts the primary data stream.
3. **Silent corruption**: The primary writer succeeds (no error), but the output file contains a mixture of telemetry fragments and primary data.

## Core Learning

**Telemetry must never share a write path with primary data. Separate them at the architecture level.**

## Solution

The write paths were completely separated:

1. **Primary data**: Writes to dedicated output files/streams. No telemetry code touches these paths.
2. **Telemetry**: Writes to separate files, separate streams, or buffered queues (see [[lesson-35-non-blocking-observability-pattern-new]]).
3. **Architecture enforcement**: The separation is at the module level, not just the function level. Telemetry modules have no access to primary data write handles.

## Prevention

- **Separate write paths at architecture level**: Telemetry and primary data should use different files, streams, or channels
- **Never share file handles**: If telemetry and primary data both need to write, use separate file handles
- **Test output purity**: Validate that primary output files contain only primary data
- **Review write paths during design**: When adding telemetry to a pipeline, verify it uses a separate output channel

## Cost of Forgetting

- **Corrupted primary data**: Output files contain telemetry fragments mixed with primary content
- **Silent failures**: No error is raised; the corruption is only discovered when the output is consumed
- **Debugging difficulty**: The corruption source (shared write path) is non-obvious

## Related

- [[lesson-21-runtime-json-pollution]] - related: debug output polluting stdout (same class of shared-path corruption)
- [[lesson-28-non-critical-tracking-pattern]] - non-blocking tracking prevents telemetry failures from affecting primary workflow
- [[lesson-35-non-blocking-observability-pattern-new]] - buffered telemetry pattern that isolates write paths
- [[non-blocking-observability]] - the concept behind telemetry isolation
- [[data-pipelines]] - write path isolation is a foundational data pipeline integrity principle
