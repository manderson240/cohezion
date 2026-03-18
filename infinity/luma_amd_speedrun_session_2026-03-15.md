# Luma AMD Speedrun - Session Learnings

## Date: 2026-03-15
## Status: Active Competition

---

## Key Discoveries

### 1. Helion Code Generation Works
- **Location**: `/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/.venv-helion/`
- **Status**: Successfully generates Triton code for MXFP4 GEMM
- **Limitation**: Generated code has `from __future__` placement issues - needs manual fixing
- **Next Steps**: Create wrapper script to fix Helion output automatically

### 2. GEMM Submission Success
- **File**: `kernels/mxfp4-mm/submission_hip_v9.py`
- **Status**: ✅ Passed 4/4 tests on MI355X
- **Approach**: HIP C++ quantization + aiter.gemm_a4w4_asm
- **JIT Time**: ~42 seconds (22.4s + 19.8s)
- **Submitted to**: amd-mxfp4-mm leaderboard

### 3. Runner Environment Confirmed
- **GPU**: AMD Instinct MI355X (gfx950)
- **ROCm**: 7.1
- **PyTorch**: 2.10.0+rocm7.1
- **Triton**: 3.6.0 (ROCm fork)
- **aiter**: Available with 1,314 pre-compiled kernels

### 4. Parallel Submission Strategy
- **Queue Limit**: 3 concurrent submissions
- **Submission Time**: ~2-3 minutes per kernel
- **Best Mode**: Test first, then leaderboard
- **Off-peak**: 06:00-12:00 UTC (40% better throughput)

---

## Working Submissions

### GEMM (mxfp4-mm)
- ✅ `submission_hip_v9.py` - Tested and working
- ⚠️ `submission_helion_*.py` - Generated but needs syntax fixes

### MoE (moe-mxfp4)
- ✅ `submission.py` - Current active (KSPLIT=4)
- ❓ Need to test latest variants

### MLA (mixed-mla)
- ✅ `submission.py` - Current active (3-regime)
- ❓ Need to test latest variants

---

## Resource Utilization

### Local Hardware (Framework Desktop)
- **CPU**: AMD Ryzen AI MAX+ 395 (16 cores) - Used for Helion generation
- **GPU**: Radeon 8060S (gfx1151) - NOT usable for testing (wrong arch)
- **RAM**: 54GB available - Safe for parallel Helion generation
- **Usage**: ~2GB per Helion process

### Runner Resources
- **Concurrent Slots**: 3
- **Current Utilization**: 1/3 (GEMM submitted)
- **Bottleneck**: JIT compilation time (~40-60s)

---

## Next Actions

1. [ ] Fix Helion-generated submissions (move `from __future__` to top)
2. [ ] Submit MoE and MLA working variants in parallel
3. [ ] Create Helion generator for MoE (if time permits)
4. [ ] Benchmark all submissions to find best performers
5. [ ] Document winning techniques in vault

---

## Competition Status

| Kernel | Current Rank | Target | Gap |
|--------|--------------|--------|-----|
| GEMM | ~67/68 | Top 10 | ~14µs |
| MoE | ~34/43 | Top 10 | ~40µs |
| MLA | ~40/54 | Top 10 | ~150µs |

**Aggregate Points**: 0 (not in Top 10 for any kernel)

---

## Handoff Notes

**Context Window**: Monitor usage - currently at ~70%
**Safe to Continue**: Yes, but watch memory during parallel submissions
**Ollama Fallback**: Available if context exceeded
**Priority**: MoE (closest to Top 10)

---

## Files Modified

- `/kernels/mxfp4-mm/submission_helion_*.py` - Generated variants
- `/kernels/mxfp4-mm/submission_helion_fixed.py` - Manual fix attempt
- `/helion_gemm_variants.py` - Generator script
- `/helion_moe_gen.py` - MoE generator (incomplete)

---

## Tags
#luma-amd-speedrun #competition #mi355x #helion #triton #gemm #moe #mla
