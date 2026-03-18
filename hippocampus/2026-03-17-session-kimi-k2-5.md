---
type: session-log
session: 2026-03-17-kimi-k2-5
agent: kimi-k2-5
status: active
title: "Session Log: Luma AMD Speedrun — 2026-03-17 (kimi-k2-5)"
date: 2026-03-17
tags: [hippocampus, session-log, luma-speedrun, mi355x, gpu-optimization, hip-kernels]
---

# Session Log: 2026-03-17 - Luma AMD Speedrun

## Summary
Initiated compound engineering approach for Luma AMD Speedrun competition. Created dedicated workspace, vault structure, and began systematic submission of optimized kernel variants.

## Actions Taken

### 1. Workspace Setup
- Created `~/dev/cohezion/hip-kernels-kimi-k2-5/`
- Organized into: gemm/, moe/, mla/, common/, build/, submissions/, analysis/

### 2. Vault Documentation
- Created skills in `cerebellum/`: amd-hip-kernel-development, luma-amd-speedrun-strategy
- Created patterns in `luma-amd-speedrun-kimi-k2-5/patterns/`: gemm-tile-optimization-256x256x128
- Created failures: moe-doweight-stage1-broken
- Created decisions: prioritize-hip-kernel-development
- Created master index: README.md

### 3. Submission Variants Created
**GEMM (4 variants)**:
- v1: Shape-aware kernel selection
- v2: Aggressive split-K
- v3: Discovered optimal kernels from AITER
- v4: Conservative baseline

**MoE (4 variants)**:
- v1: Conservative KSPLIT
- v2: Ultra-aggressive KSPLIT
- v3: Discovered stage1 kernels
- v4: Conservative baseline (no KSPLIT)

**MLA (4 variants)**:
- v1: Balanced FP8 splits
- v2: Aggressive parallelism
- v3: Discovered assembly kernels
- v4: Conservative BF16 baseline

### 4. Submissions Made
- Submitted v1 variants for all 3 kernels (IDs: 577235, 577236, 577234)
- Submitted v4 conservative variants
- All pending in queue

### 5. Research Conducted
- Explored `/tmp/aiter/hsa/gfx950/` for pre-compiled kernels
- Found FP4 GEMM kernels: 32×128 to 256×256 tiles
- Found MoE stage1 kernels: various tile sizes
- Found MLA kernels: A16W16, A8W8 variants

## Key Discoveries

### Pre-compiled Kernels Available
```
/tmp/aiter/hsa/gfx950/
├── f4gemm/          # 20+ variants
├── fmoe_2stages/    # Stage1 kernels
└── mla/             # Attention kernels
```

### Optimal Tile Sizes
- **Small M (≤32)**: 32×128, 32×256, 32×512
- **Medium M (32-128)**: 128×128
- **Large M (>128)**: 192×128, 256×128

## Pending Actions
- Wait for submission results
- Analyze which variants perform best
- Create additional variants based on results
- Begin custom HIP kernel development if needed

## Next Session Priorities
1. Check submission results
2. Identify winning patterns
3. Double down on successful approaches
4. Document learnings in vault

## Token Efficiency Notes
- Created 12 submission variants
- Documented 4 skills/patterns/failures
- Explored AITER repository for kernel patterns
- Submitted 6 variants to leaderboard
- Total: High output with structured approach

## Vault Links

- [[luma-amd-speedrun-strategy]] — Competition strategy and current standings
- [[amd-hip-kernel-development]] — HIP kernel development guide created this session
- [[MOC-machine-learning]] — Parent map of content
