# Luma AMD Speedrun: MXFP4 Kernel Optimization Plan

Created: 2026-03-11
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: No

> **Status Lifecycle:** PENDING -> COMPLETE -> VERIFIED
> **Deadline:** March 30, 2026

## Summary

Optimize three GPU kernels (MXFP4 GEMM, MLA Decode, MXFP4 MoE) for AMD MI355X.
Priority: GEMM -> MLA -> MoE. Submissions via Popcorn CLI.

## Progress Tracking

- [x] Task 1: Knowledge Accumulation & Baseline Benchmarks
- [x] Task 2: MXFP4 GEMM - Optimized Quantization
- [ ] Task 3: MXFP4 GEMM - Custom Triton GEMM Kernel
- [x] Task 4: MLA Decode - MXFP4 KV Cache Attention
- [ ] Task 5: MoE - Optimized Dispatch & Fusion
- [ ] Task 6: Final Leaderboard Submissions

**Total Tasks:** 6 | **Completed:** 3 | **Remaining:** 3

## Implementation Notes

### Task 1 (DONE): Knowledge & Baselines
- Reference perf numbers from task.yml documented in results.md
- Popcorn CLI auth needs browser-based GitHub OAuth (CLI ID saved, awaiting validation)
- All kernel structures fully understood: input types, benchmark shapes, tolerances

### Task 2 (DONE): GEMM Optimized Quantization
- Module-level quant_func caching (avoids per-call get_triton_quant overhead)
- Removed unnecessary B.contiguous() (B unused in GEMM path)
- Probed for Triton GEMM (gemm_afp4wfp4) at module level
- Conservative: same CK gemm_a4w4 path, pending remote benchmark

### Task 4 (DONE): MLA Decode
- MAJOR rewrite: replaced naive torch._scaled_mm loop with aiter mla_decode_fwd
- Uses fp8 Q + fp8 KV persistent-mode kernel (matches reference approach)
- Expected massive speedup over previous Python-loop implementation
- MXFP4 KV path deferred (need to verify if mla_decode_fwd supports fp4x2)

### Task 5 (IN PROGRESS): MoE
- Currently identical to reference (fused_moe is heavily optimized)
- Shared expert specialization strategy identified but not yet implemented
- Need remote benchmarking to validate any changes

### Blockers
- Popcorn CLI 401 auth error: CLI ID issued but OAuth not validated
  - Fix: User needs to run `popcorn-cli reregister github` interactively
