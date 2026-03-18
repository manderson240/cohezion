# Luma AMD Speedrun - Iteration 1 Results

## Date: 2026-03-15
## Status: Pipeline operational, submissions successful

---

## What We Built

### 1. Automated Submission Pipeline (`triton_submission_pipeline.py`)
- Generates Helion kernels with different tile configurations
- Extracts pure Triton code (removes Helion dependencies)
- Submits to popcorn-cli in parallel
- Captures and analyzes logs

### 2. Key Learnings from Runner Feedback

#### Error Pattern Analysis:
1. **SyntaxError**: `from __future__` placement
   - Helion generates duplicate imports
   - **Fix**: Remove all `from __future__` from Helion output, add single one at top

2. **ModuleNotFoundError**: `helion` not installed
   - Runner doesn't have Helion library
   - **Fix**: Extract only the `@triton.jit` kernel function, remove all Helion imports

3. **NameError**: `_default_launcher` not defined
   - Helion's launcher abstraction doesn't exist on runner
   - **Fix**: Replace with direct Triton kernel launch: `kernel[grid](args)`

4. **File not found**: Relative path issues
   - **Fix**: Use absolute paths for submission files

#### Performance Insights:
- **Current**: ~23 µs (GEMM v9 with HIP + aiter)
- **Leader**: ~9.7 µs (need 2x improvement)
- **Key log message**: "not found tuned config in CKGEMM or asmGEMM, will use default config!"
  - We're using default configs, not optimized ones
  - Opportunity: Create custom tuned configs for each shape

---

## Successful Submission

### GEMM v9 (HIP + aiter)
- **Status**: ✅ Leaderboard submitted
- **Performance**: ~20-35 µs across shapes
- **Method**: HIP C++ quantization + aiter.gemm_a4w4_asm
- **JIT Time**: ~42 seconds

### Benchmark Results:
```
Shape (K, M, N)    | Mean    | Best    | Worst
-------------------|---------|---------|--------
512, 4, 2880       | 20.1 µs| 18.9 µs | 23.8 µs
7168, 16, 2112     | 34.8 µs| 33.2 µs | 37.6 µs
512, 32, 4096      | 22.0 µs| 20.8 µs | 25.9 µs
512, 32, 2880      | 21.6 µs| 20.7 µs | 24.9 µs
2048, 64, 7168     | 23.2 µs| 22.2 µs | 26.1 µs
1536, 256, 3072    | 21.9 µs| 21.1 µs | 26.0 µs
```

---

## Helion Integration Status

### What Works:
- ✅ Helion generates valid Triton code with `tl.dot_scaled`
- ✅ Proper MXFP4 scale handling
- ✅ Automatic tile size selection via `helion.Config`

### What Doesn't Work:
- ❌ Helion output includes Helion-specific infrastructure
- ❌ Runner doesn't have Helion installed
- ❌ Need post-processing to extract pure Triton

### Solution Path:
1. Generate Helion code locally
2. Extract only the `@triton.jit` kernel function
3. Remove all Helion imports and launcher code
4. Add proper `custom_kernel` entry point with direct Triton launch
5. Submit and iterate based on errors

---

## Optimization Opportunities

### 1. Tuned Configs (Highest Impact)
**Problem**: Using default configs, not optimized for our shapes
**Solution**: Create custom tuned configs for each competition shape
```python
# S1: (4, 2880, 512)
# S2: (16, 2112, 7168)
# S3: (32, 4096, 512)
# S4: (32, 2880, 512)
# S5: (64, 7168, 2048)
# S6: (256, 3072, 1536)
```

### 2. Fused Quantization + GEMM
**Problem**: Separate quant kernel (~10-15 µs) + GEMM (~10-15 µs)
**Solution**: Single kernel that quantizes and computes GEMM
**Potential gain**: Eliminate kernel launch overhead

### 3. Shape-Aware Dispatch
**Problem**: Same code path for all shapes
**Solution**: Different tile sizes and strategies per shape
**Potential gain**: 20-30% improvement

### 4. Helion-Generated Optimized Kernels
**Problem**: Manual Triton is error-prone
**Solution**: Use Helion to generate multiple variants, test all
**Potential gain**: Find optimal tile sizes automatically

---

## Next Iteration Plan

### Phase 1: Fix Helion Extraction (Immediate)
- [ ] Fix `extract_pure_triton()` to properly remove all Helion dependencies
- [ ] Ensure single `from __future__ import annotations` at top
- [ ] Replace launcher with direct Triton kernel launch
- [ ] Test extraction on sample Helion output

### Phase 2: Generate and Test Variants (Next 30 min)
- [ ] Generate 3 Helion variants with different tile sizes
- [ ] Extract pure Triton from each
- [ ] Submit all 3 in parallel
- [ ] Capture logs and analyze errors

### Phase 3: Iterate Based on Feedback (Next 60 min)
- [ ] Fix any runtime errors
- [ ] Compare performance of variants
- [ ] Feed winning configs back to Helion
- [ ] Generate next iteration with refined configs

### Phase 4: Optimization (Ongoing)
- [ ] Create shape-specific tuned configs
- [ ] Try fused quant+GEMM approach
- [ ] Benchmark against current best (GEMM v9)

---

## Files Created

### Pipeline Scripts:
- `triton_submission_pipeline.py` - Main pipeline
- `test_helion_output.py` - Test Helion generation
- `extract_triton.py` - Extraction utilities

### Submission Files:
- `submission_hip_v9.py` ✅ **WORKING - Leaderboard submitted**
- `submission_triton_manual.py` - Manual Triton attempt
- `submission_helion_*.py` - Generated variants (need fixing)

### Documentation:
- `HANDOFF.md` - Session handoff
- `gemm_success_2026-03-15.md` - GEMM success log
- `luma_amd_speedrun_session_2026-03-15.md` - Session notes

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Submissions attempted | 15+ |
| Successful submissions | 1 (GEMM v9) |
| Helion variants generated | 6 |
| Helion variants working | 0 (infrastructure issues) |
| Current best time | ~23 µs |
| Target time (Top 10) | ~10 µs |
| Gap to close | 2.3x |

---

## Critical Path to Success

1. **Get Helion-generated Triton working** (highest leverage)
   - Fix extraction pipeline
   - Test on runner
   - Iterate on tile sizes

2. **Create tuned configs** (immediate gain)
   - Profile each shape
   - Find optimal tile sizes
   - Hardcode in submission

3. **Fused kernel** (breakthrough potential)
   - Combine quant + GEMM
   - Eliminate overhead
   - Target: <15 µs

---

## Resources Used

### Local (Framework Desktop):
- **CPU**: 16 cores for parallel Helion generation
- **RAM**: ~4GB for Helion + Python processes
- **GPU**: Not usable (gfx1151 ≠ gfx950)

### Runner (MI355X):
- **Slots**: 3 concurrent submissions
- **Current utilization**: 1/3 (GEMM v9 running)
- **Available**: 2/3 slots for next iteration

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Helion extraction fails | Medium | High | Fallback to manual Triton |
| Runner rejects Triton | Low | High | Use working HIP submission |
| Time runs out | Medium | High | Focus on GEMM only |
| Context window exceeded | Low | Medium | Use Ollama fallback |

---

## Immediate Next Actions

1. **Wait for GEMM v9 leaderboard result** (in progress)
2. **Fix Helion extraction** (next 10 min)
3. **Generate 3 variants** (next 10 min)
4. **Submit in parallel** (next 2 min)
5. **Analyze results** (next 10 min)

---

**Status**: Pipeline operational, ready for next iteration
**Confidence**: Medium (working submission exists, Helion needs fixing)
**Blockers**: None (can proceed with both approaches in parallel)
