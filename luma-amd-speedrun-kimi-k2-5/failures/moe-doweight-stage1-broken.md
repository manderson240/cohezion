---
type: failure
name: moe-doweight-stage1-broken
kernel: moe
severity: critical
status: confirmed
date: 2026-03-17
title: "MoE doweight_stage1=True is Broken (AITER bug)"
tags: [failure, moe, aiter, mi355x, luma-speedrun, critical, bug]
aspect: thinker
---

# MoE doweight_stage1=True is BROKEN

## Problem
The `doweight_stage1=True` parameter in `aiter.fused_moe()` causes catastrophic failures.

## Symptoms

### CK Path (default)
- **Error**: 82% element mismatches
- **Behavior**: Silent wrong results (not crash)
- **Detection**: Only visible in correctness testing

### CK Tile Path (with AITER_BYPASS_TUNE_CONFIG)
- **Error**: GPU memory fault
- **Behavior**: Immediate crash
- **Detection**: Runtime error

## Root Cause
The `doweight_stage1` parameter attempts to apply weight scaling in stage 1 of the MoE computation, but:
1. The CK (Composable Kernel) implementation has a bug in the weight scaling logic
2. The cktile path has a memory access violation
3. Both paths are fundamentally broken for this parameter

## Impact
- **Numerical correctness**: COMPLETELY BROKEN
- **Performance**: N/A (doesn't work)
- **Safety**: CRITICAL - produces wrong results silently

## Fix
**ALWAYS use `doweight_stage1=False`**

```python
# CORRECT
return fused_moe(
    hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
    topk_weights, topk_ids,
    doweight_stage1=False,  # ← CRITICAL
    ...
)

# WRONG - DO NOT USE
return fused_moe(
    ...
    doweight_stage1=True,  # ← BROKEN
    ...
)
```

## Verification
Test with `doweight_stage1=False`:
- CK path: ✅ Passes correctness
- cktile path: ✅ Passes correctness

## References
- [[moe-ksplit-optimization]]
- [[luma-amd-speedrun-strategy]]
- [[aiter-fused-moe-api]]

## Related Failures
- None (this is unique to doweight_stage1)

## Notes
- This is a known AITER bug
- May be fixed in future versions
- Until then, NEVER use doweight_stage1=True
