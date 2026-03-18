# Luma AMD Speedrun - Path to Top 10

**Date**: 2026-03-16
**Status**: EXECUTION MODE ACTIVATED
**Goal**: Top 10 on ALL three leaderboards
**Deadline**: March 30, 2026 (14 days remaining)

---

## Current Leaderboard Status

| Kernel | #1 Score | Our Best | Gap | Our Rank | Target |
|--------|----------|----------|-----|----------|--------|
| **GEMM** | 8.752μs | ~13-14μs | +58% | ~60th | ~10μs |
| **MoE** | 114.607μs | ~155μs | +35% | ~14th | ~145μs |
| **MLA** | 4.329μs | ~69μs | **+1493%** | ~22nd | ~54μs |

### Critical Analysis

**MLA - THE DISASTER:**
- Gap: 16x slower than #1
- Root cause: Using hybrid einsum + aiter instead of persistent kernels
- #1 likely uses: Pure Triton flash attention with persistent mode
- Action: COMPLETE PIVOT needed

**GEMM - THE CHALLENGE:**
- Gap: 58% slower
- Current: HIP + aiter hybrid
- #1 likely uses: Pure Triton with proper MXFP4 handling
- Action: Need pure Triton or better split-K

**MoE - THE HOPE:**
- Gap: 35% slower (closest!)
- Current: KSPLIT tuning with aiter
- #1 likely uses: Same approach, better parameters
- Action: Systematic parameter sweep

---

## Execution Plan

### Phase 1: MLA Emergency Surgery (Days 1-3)

**Goal**: Get MLA from 69μs to ~20μs (still 4x off, but closer)

**Strategy**: Abandon hybrid approach, go pure Triton flash attention

**Actions**:
1. [ ] Research proper MLA flash attention Triton kernels
2. [ ] Implement persistent kernel mode (fast_mode=True)
3. [ ] Test different num_kv_splits (1, 4, 8, 16, 32)
4. [ ] Create 10+ variants with different tile sizes
5. [ ] Submit all and analyze

**Success Metric**: Get below 20μs

### Phase 2: GEMM Optimization (Days 4-7)

**Goal**: Get GEMM from 13μs to ~10μs

**Strategy**: Pure Triton with proper MXFP4 dot_scaled

**Actions**:
1. [ ] Fix Helion generator (scale dimension issue)
2. [ ] Generate proper Triton MXFP4 kernels
3. [ ] Test different block sizes (M=16,32,64,128)
4. [ ] Test different split-K values
5. [ ] Create 10+ variants
6. [ ] Submit all and analyze

**Success Metric**: Get below 10μs

### Phase 3: MoE Fine-Tuning (Days 8-10)

**Goal**: Get MoE from 155μs to ~145μs (Top 10)

**Strategy**: Systematic KSPLIT sweep with expert-aware dispatch

**Actions**:
1. [ ] Analyze results from 9 submitted variants
2. [ ] Identify winning KSPLIT values per shape
3. [ ] Create refined variants with optimal params
4. [ ] Test E=257 vs E=33 specific tuning
5. [ ] Submit 5+ refined variants

**Success Metric**: Get below 145μs (Top 10)

### Phase 4: Integration & Polish (Days 11-14)

**Goal**: All three kernels in Top 10

**Actions**:
1. [ ] Combine winning strategies
2. [ ] Create final submission set
3. [ ] Verify all pass correctness tests
4. [ ] Submit final variants
5. [ ] Monitor leaderboard rankings

---

## Experimental Learning Framework

### Hypothesis-Driven Development

For each kernel, we follow:

1. **Hypothesis**: "KSPLIT=8 will improve sparse MoE by 20%"
2. **Experiment**: Create submission with KSPLIT=8
3. **Measure**: Check benchmark results
4. **Learn**: Document what worked/failed
5. **Iterate**: Refine hypothesis

### Documentation Requirements

Every submission must document:
- Hypothesis being tested
- Expected outcome
- Actual results
- Learnings
- Next experiment

### Recursive Improvement

```
Submit v1 → Analyze → Learn → Submit v2 → Analyze → Learn → ...
```

Each iteration builds on previous learnings.

---

## Current Assets

### Submissions Created (16 variants)

**MoE (9 variants)**:
- v4: Balanced KSPLIT (6/3/2/default) ✅ Working
- v5: Ultra-aggressive (8/4/2/1) 🔄 Testing
- v6: Adaptive fine-tuned 🔄 Testing
- v7: Aggressive sparse 🔄 Testing
- v8: KSPLIT sweep A (8/4/2) 🔄 Testing
- v9: KSPLIT sweep B (6/3/2) 🔄 Testing
- v10: Expert-aware 🔄 Testing
- v11: Uniform KSPLIT=4 🔄 Testing
- v12: Uniform KSPLIT=2 🔄 Testing

**GEMM (5 variants)**:
- v1: HIP fused ✅ Working (~13-14μs)
- v2: Shape-aware split-K 🔄 Testing
- v3: Aggressive split-K 🔄 Testing
- v4: Split-K sweep A 🔄 Testing
- v5: Split-K sweep B 🔄 Testing

**MLA (2 variants)**:
- v1: Hybrid einsum + aiter ✅ Working (~69μs)
- v2: HIP flash-decode 🔄 Testing

### Tools Available

- **Helion**: Triton code generator (has bugs but usable)
- **aiter**: AMD's optimized library
- **HIP**: Custom kernel compilation
- **Popcorn CLI**: Submission system
- **Vault**: Documentation and tracking
- **SurrealDB**: Structured data storage

---

## Risk Mitigation

### Risk: MLA Gap Too Large
**Mitigation**: 
- Research #1 submissions (what are they doing?)
- Try completely different approaches
- Focus on persistent kernels
- Accept that MLA might be hardest

### Risk: Helion Bugs Block Progress
**Mitigation**:
- Work around scale dimension issues
- Use manual Triton if needed
- Fall back to aiter if Triton fails

### Risk: Time Running Out
**Mitigation**:
- Prioritize MoE (closest to winning)
- Parallel development on all kernels
- Submit early and often
- Don't wait for perfect solutions

---

## Success Criteria

### Minimum Viable Success
- [ ] MoE: Top 10 (≤145μs)
- [ ] GEMM: Top 20 (≤12μs)
- [ ] MLA: Top 20 (≤20μs)

### Target Success
- [ ] MoE: Top 5 (≤130μs)
- [ ] GEMM: Top 10 (≤10μs)
- [ ] MLA: Top 10 (≤10μs)

### Stretch Goal
- [ ] All three kernels: Top 5
- [ ] Advance to Phase 2 Finals
- [ ] Win prize money

---

## Daily Execution Log

### Day 1 (2026-03-16)
- [x] Created 16 submission variants
- [x] Implemented stealth naming
- [x] Submitted all variants to leaderboard
- [ ] Awaiting results

### Day 2 (2026-03-17)
- [ ] Check results from 16 submissions
- [ ] Analyze winning strategies
- [ ] Create next batch of variants
- [ ] Focus on MLA emergency fix

### Day 3 (2026-03-18)
- [ ] Continue MLA pivot
- [ ] Test pure Triton approaches
- [ ] Document learnings

... (continue daily)

---

## Key Learnings So Far

### What Works:
1. ✅ KSPLIT tuning for MoE (35% improvement possible)
2. ✅ HIP kernels bypass Python overhead
3. ✅ Shape-aware dispatch is critical
4. ✅ Stealth naming protects competitive advantage

### What Doesn't Work:
1. ❌ Hybrid approaches for MLA (too slow)
2. ❌ Ultra-aggressive KSPLIT (causes overflow)
3. ❌ Helion has bugs (scale dimension issues)
4. ❌ aiter has ceiling (~155μs for MoE)

### Unknowns:
1. ❓ What are #1 using for MLA? (4.33μs seems impossible with current approach)
2. ❓ Can we beat ~10μs for GEMM with aiter?
3. ❓ Is pure Triton required for Top 10?

---

## Resources

### Documentation:
- Vault: `~/vaults/cohezion-vault/infinity/`
- Strategy map: `submission_strategy_map.md`
- This plan: `path_to_top10.md`

### Code:
- Submissions: `opencode_kimi-k2.5_cloud/`
- Helion generators: `helion_*.py`
- Reference: `kernels/*/reference.py`

### External:
- Leaderboard: https://www.gpumode.com/
- Discord: amd-competition channel
- Popcorn CLI: https://github.com/gpu-mode/popcorn-cli

---

## Motivation

**$1.1M prize pool**
**Top 10 advance to Finals**
**Prestige of winning AMD competition**
**Learning cutting-edge GPU optimization**

**We will NOT give up until Top 10 is achieved on ALL leaderboards.**

**Recursive learning. Experimental approach. Document everything.**

**Let's win this.** 🎯

---

**Last Updated**: 2026-03-16
**Next Review**: Daily
**Status**: 🔥 EXECUTING
