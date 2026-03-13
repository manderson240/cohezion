---
type: antigravity-artifact
session_id: ae6acabc-a484-4e15-833b-207833b158e4
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.61
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# VLIW Optimization Validation Plan

This plan outlines the steps to verify and validate the VLIW optimization solution for the Anthropic research engineer take-home challenge.

## Proposed Steps

### 1. Strict Anti-Cheating Audit [CRITICAL]
- **Repository Comparison**: Compare local `problem.py`, `machine.py` (if exists), and `tests/` with the original Anthropic repository.
- **Simulator Integrity**: Verify `Machine.run()` and cycle counting logic haven't been modified to "skip" cycles or bypass limits.
- **Result Integrity**: Ensure the optimizer isn't just emitting hardcoded values into memory images.
- **Environment Parity**: Confirm `N_CORES`, `SLOT_LIMITS`, and `VLEN` match official specs.

### 2. Environment Preparation
- Ensure `uv` is installed and functioning correctly.
- Synchronize dependencies in `research/challenges/anthropic_challenge/`.

### 3. Execution of Performance Benchmarks
- Run the main benchmark using `uv run perf_takehome.py Tests.test_kernel_cycles`.
- Run the full verification suite using `uv run tests/submission_tests.py`.

### 4. Metric Verification
- Capture the cycle count from the output.
- Compare the result with the claimed "349 cycles" and "423x speedup".
- Verify that all correctness tests pass (`submission_tests.py`).

## Verification Plan

### Automated Tests
- **Benchmark Run**:
  ```bash
  cd research/challenges/anthropic_challenge/
  uv run perf_takehome.py Tests.test_kernel_cycles
  ```
  *Expected Output*: "CYCLES: 349" (or similar) and "Speedup over baseline: ~423".

- **Full Verification**:
  ```bash
  cd research/challenges/anthropic_challenge/
  uv run tests/submission_tests.py
  ```
  *Expected Output*: Validation that all thresholds (Correctness, Speedup) are passed.

### Manual Verification
- Review the `debug_output.txt` or trace logs if cycles deviate significantly from expected.

## Related Vault Notes

- [[anthropic-research-engineer]]
