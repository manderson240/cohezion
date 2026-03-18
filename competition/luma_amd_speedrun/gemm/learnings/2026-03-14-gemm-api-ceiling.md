---
title: "GEMM MXFP4: API Ceiling at ~23µs"
date: 2026-03-14
status: complete
tags: [gpu-optimization, gemm, mxfp4, amd-mi355x, popcorn-leaderboard]
aspect: thinker
---

# GEMM MXFP4: API Ceiling at ~23µs (Rank 73/89)

## Current Best
- `dynamic_mxfp4_quant` + `gemm_a4w4` ASM kernel
- ~23µs geomean vs leader 9.7µs (2.4x gap)

## Exhausted Paths (DO NOT RETRY)
| Approach | Outcome | Why |
|----------|---------|-----|
| `gemm_afp4wfp4` (Triton) | Slower than ASM | JIT overhead |
| CUDA graph wrapping | +78% regression | `copy_()` overhead exceeds kernel time |
| `get_triton_quant` | Wrong results | Unpatched fp4_utils.py bug (PR #975) |
| `get_torch_quant` | Wrong results | Different rounding |
| `gemm_a4w4_asm` direct | Not found | Only 2 pre-compiled .co files |
| Custom `tl.dot_scaled` | +68% slower | Standard tiled cannot beat persistent ASM |
| `deepgemm` | Requires group_layout | MoE-only, not standalone GEMM |
| `hipblaslt` | Empty attrs | No fp4 GEMM exposed |

## Only Remaining Path
Fused quant+GEMM persistent Triton kernel — fuse the 10-13µs A-quant into the GEMM itself. Multi-day implementation effort.

## Key Insight
The bottleneck is quantization time (~10-13µs), which equals the GEMM time itself (~10µs). The leader likely has a fused kernel.

## Related
- [[2026-03-14-moe-optimization-state|MoE optimization state]] — MoE kernel uses same GEMM primitives
- [[machine-learning-optimization]] — broader optimization context
- See `infinity/gemm/kernel_design.md` for the fused kernel design attempt
