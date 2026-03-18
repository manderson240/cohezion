---
type: index
name: luma-amd-speedrun-kimi-k2-5-index
description: "Master index for Luma AMD Speedrun competition work by kimi-k2-5"
created: 2026-03-17
updated: 2026-03-17
status: active
title: "Luma AMD Speedrun — kimi-k2-5 Work Index"
date: 2026-03-17
tags: [competition, luma-speedrun, mi355x, gfx950, gpu-optimization, hip-kernels]
aspect: thinker
---

# Luma AMD Speedrun - kimi-k2-5 Work Index

## Overview
This directory contains all work related to the Luma AMD Speedrun competition ($650K prize pool) targeting Top 10 rankings on MI355X (gfx950).

## Current Status (2026-03-17)

### Leaderboard Positions
| Kernel | Current | Leader | Gap | Target |
|--------|---------|--------|-----|--------|
| GEMM | ~13.4µs | 9.671µs | 1.39× | ≤10µs |
| MoE | ~154µs | 145.177µs | 1.06× | ≤145µs |
| MLA | ~67µs | 4.335µs | 15.5× | ≤20µs |

### Submissions Made
- **Total variants created**: 90+ across all kernels
- **Python parameter tuning**: Exhausted (hit AITER ceiling)
- **Custom HIP kernels**: In development

## Directory Structure

```
luma-amd-speedrun-kimi-k2-5/
├── skills/           # Reusable skills for future agents
├── patterns/         # Successful optimization patterns
├── failures/         # Documented failures with analysis
├── decisions/        # Key decisions made
├── submissions/      # Submission file references
└── analysis/         # Performance analysis and insights
```

## Key Documents

### Skills (in cerebellum/)
- [[amd-hip-kernel-development]] - Custom HIP kernel development guide
- [[luma-amd-speedrun-strategy]] - Competition strategy and tactics

### Patterns
- [[gemm-tile-optimization-256x256x128]] - Optimal GEMM tile configuration

### Failures
- [[moe-doweight-stage1-broken]] - Critical bug in AITER MoE

### Decisions
- [[prioritize-hip-kernel-development]] - Pivot to custom HIP kernels

## Critical Learnings

### What Works
1. **Shape-aware dispatch** - Different parameters per M/N/K
2. **Conservative parallelism** - Avoid overflow (MoE KSPLIT)
3. **FP8 KV cache** - 2× bandwidth vs bf16 (MLA)
4. **OPUS sorting** - Helps MoE routing

### What Doesn't Work
1. **`doweight_stage1=True`** - Catastrophic failure (NEVER USE)
2. **Ultra-aggressive KSPLIT=8** - Numerical overflow
3. **Pure Triton** - Too many constraints
4. **Maximum aggression** - Breaks correctness

## Next Steps

### Immediate (Day 1)
1. ✅ Create vault structure
2. ✅ Document existing learnings
3. 🔄 Port existing `gemm_final.hip` to working submission
4. 🔄 Submit GEMM v18 hybrid variant

### Short-term (Days 1-3)
- Complete GEMM custom HIP kernel (target: 9.7µs)
- Develop MoE fused kernel (target: 145µs)
- Test MLA custom kernel approaches

### Medium-term (Days 4-10)
- Iterate on all three kernels
- Grid search tile sizes and parameters
- Document all results in vault

### Long-term (Days 11-14)
- Final submission push
- Fine-tune based on results
- Complete documentation for future agents

## Cross-References

### Related Vault Locations
- `cerebellum/` - Skills and procedural knowledge
- `cortex/` - Concepts and theory
- `prefrontal/` - Decisions and strategy
- `hippocampus/` - Session logs

### External Resources
- `/tmp/aiter/` - AITER repository with assembly kernels
- `~/dev/cohezion/research/challenges/luma_amd_speedrun/` - Competition files
- `~/.claude/skills/` - Available skills

## Contact
- **Agent**: kimi-k2-5
- **Session**: 2026-03-17
- **Status**: Active development

## Tags
#luma-amd-speedrun #mi355x #gfx950 #hip-kernels #competition #optimization
