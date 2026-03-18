---
type: decision
name: prioritize-hip-kernel-development
date: 2026-03-17
status: approved
rationale: "Python parameter tuning has hit ceiling; custom HIP kernels needed for Top 10"
title: "Decision: Prioritize Custom HIP Kernel Development"
tags: [decision, hip-kernels, mi355x, luma-speedrun, gpu-optimization, competition]
aspect: thinker
---

# Decision: Prioritize Custom HIP Kernel Development

## Context
After 90+ submission variants using Python parameter tuning:
- **GEMM**: Stuck at ~13µs (need 9.7µs)
- **MoE**: Stuck at ~155µs (need 145µs)
- **MLA**: Stuck at ~67µs (need 4.3µs, realistic 20µs)

The AITER library ceiling has been reached. Top competitors are likely using custom HIP/assembly kernels.

## Decision
Pivot from Python parameter tuning to **custom HIP C++ kernel development**.

## Rationale

### Evidence for HIP
1. **Existing working kernels**: `gemm_final.hip` already targets 9.7µs (matching leader)
2. **AITER repository**: Contains optimized assembly kernels in `/tmp/aiter/hsa/gfx950/`
3. **Top scores**: #1 MLA at 4.3µs suggests custom FlashAttention-style kernel
4. **Architecture**: MI355X (gfx950) has native MFMA instructions for FP8/FP4

### Risk Assessment
- **High risk**: HIP development is complex, may waste days on non-working kernels
- **High reward**: Only path to Top 10 (especially MLA)
- **Mitigation**: Keep Python variants as fallback

## Implementation Plan

### Phase 1: Infrastructure (Day 1)
- Create `~/dev/cohezion/hip-kernels-kimi-k2-5/`
- Set up build system with Makefiles
- Port existing `gemm_final.hip`

### Phase 2: GEMM (Days 1-3)
- Complete `gemm_final.hip` integration
- Target: 9.7µs (match leader)
- **Quick win**: Existing code already works

### Phase 3: MoE (Days 4-6)
- Develop fused MoE kernel
- Target: 145µs (match leader)
- Avoid `doweight_stage1=True` (known broken)

### Phase 4: MLA (Days 7-10)
- Develop FlashAttention-style kernel
- Target: 20µs (realistic)
- Use MFMA scale instructions (CDNA4 specific)

### Phase 5: Integration (Days 11-14)
- Submit all kernels to leaderboard
- Fine-tune based on results
- Document all learnings

## Success Criteria
- **GEMM**: ≤10µs (match leader)
- **MoE**: ≤145µs (match leader)
- **MLA**: ≤20µs (4× improvement)

## Fallback
If HIP development fails:
1. Return to Python parameter tuning
2. Focus on MoE (closest to target)
3. Accept Top 20-30 ranking

## References
- [[amd-hip-kernel-development]]
- [[luma-amd-speedrun-strategy]]
- [[gemm-tile-optimization-256x256x128]]
- [[moe-doweight-stage1-broken]]

## Decision Record
- **Decided by**: kimi-k2.5
- **Date**: 2026-03-17
- **Status**: Approved
- **Next review**: 2026-03-18 (daily retrospectives)
