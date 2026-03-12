---
type: antigravity-artifact
session_id: 95a4975b-2b7b-427a-9625-1c2e1d95b815
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.331
  stage: embryo
  cluster: Agents
---

# Multi-Core Instability & Round-By-Round Validation Fix

I have successfully resolved the two primary bugs blocking the performance take-home: the `IndexError` in memory addressing and the `AssertionError` in intermediate round validation.

## Changes Made

### 1. Loop Bound Correction
Fixed a critical bug in `OptimizedKernelBuilder.build_kernel` where `n_batches` was used instead of `n_core_batches` for the inner loop bounds. This was causing cores to read memory addresses belonging to other cores, leading to garbage values and index errors.

### 2. VLIW Barrier Implementation
The `VLIWPacker` was optimized to pack instructions into the earliest possible slot. However, it was too aggressive and was packing instructions intended for future rounds into idle slots in current or previous bundles. This caused the kernel to "pause" for validation before the actual computation for that round was finished.
- **Added** `packer.barrier()`: Resets the dependency tracking and enforces a minimum bundle index for all subsequent instructions.
- **Enforced Barriers** before/after `pause` points to ensure round synchronization.

### 3. Logic Refinement
- **Removed** redundant debugging trace instructions.
- **Ensured** memory `vstore` operations occur within the rounds loop and are followed by proper barriers and pauses.

## Verification Results

The kernel now passes all tests in `perf_takehome.py` with the following metrics:
- **Cycles**: 385
- **Speedup**: ~383x over the baseline reference.

### Execution Log
```text
Ran 3 tests in 1.867s
OK
forest_height=10, rounds=16, batch_size=256
CYCLES:  385
Speedup over baseline:  383.72467532467533
```

## Relevant Files
- [optimizer.py](file:///home/mike-anderson/dev/cohezion/anthropic_challenge/optimizer.py): Core logic fix and barrier implementation.
- [problem.py](file:///home/mike-anderson/dev/cohezion/anthropic_challenge/problem.py): (Minor) Fixed debug info lookup.
- [perf_takehome.py](file:///home/mike-anderson/dev/cohezion/anthropic_challenge/perf_takehome.py): (Minor) Restored original validation logic.

## Related Vault Notes

- [[cohezion]]
