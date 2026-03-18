---
title: "MoE MXFP4 Optimization State: Rank 13/58"
date: 2026-03-14
status: complete
tags: [gpu-optimization, moe, mxfp4, aiter, amd-mi355x, popcorn-leaderboard]
aspect: thinker
---

# MoE MXFP4: Rank 13/58 (~155µs vs 145µs leader, 1.07x gap)

## Current Best
- `fused_moe` with adaptive KSPLIT routing
- `doweight_stage1=False` (Phase 10)
- Expert-count-aware KSPLIT: dense→tuned CSV, sparse-large-E→K4, moderate→K2

## Under Test (Phase 12, March 14 2026)
1. `doweight_stage1=True` — fuses topk weight into stage1 GEMM
2. `doweight_stage1=True` + `block_size_M=32` for sparse shapes
3. 1-stage probe — introspecting fused_moe_ for run_1stage path

## Exhausted Paths
| Approach | Outcome | Why |
|----------|---------|-----|
| `fused_moe_2stages` direct | TypeError + GPU fault | Positional arg conflict |
| `fmoe_g1u1` direct | Hidden calling convention | torch.ops.aiter wrapper |
| `AITER_USE_NT=1` | Neutral (~155µs) | CK tiles reuse weights via L2 |
| `AITER_ONLINE_TUNE=1` | Not confirmed improved | Runtime tuning overhead unclear |
| `cktile_moe_stage1/stage2` direct | Not attempted | Requires full sorting setup |

## Key Shapes (DeepSeek R1)
- E=257, bs=16: ~0.56 tokens/expert (extremely sparse)
- E=257, bs=512: ~18 tokens/expert (moderate sparse)
- E=33, bs=16: ~4.4 tokens/expert (sparse)
- E=33, bs=512: ~140 tokens/expert (dense)

## Architecture Notes
- 2-stage pipeline: stage1 (gate_up GEMM + SiLU) → stage2 (down GEMM)
- Token sorting: moe_sorting_gpu reorders by expert
- CK vs cktile: KSPLIT=0 uses ck_moe_stage1/2 (MXFP4 optimized), KSPLIT>0 uses cktile path
- The 10µs gap likely comes from: sorting overhead + buffer allocation + weight multiply

## Related
- [[2026-03-14-doweight-cktile-incompatibility|doweight_stage1 bug]] — critical: doweight_stage1=True is broken on both paths
- [[2026-03-14-gemm-api-ceiling|GEMM API ceiling]] — same MXFP4 quantization bottleneck
- [[machine-learning-optimization]] — broader optimization context
- See `infinity/alpha/a2/TUNING_REPORT.md` for block_m/split_k tuning analysis
- See `infinity/alpha/a3/` for buffer pool and dispatch optimization designs
