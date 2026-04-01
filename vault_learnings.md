# Luma AMD Speedrun - Key Learnings

## Date: 2026-03-18
## Session: hip-kernels-kimi-k2-5

---

## Technical Discoveries

### 1. Submission Wrapper Bug (CRITICAL)
- **Issue**: Popcorn CLI injects code at the beginning of submission files
- **Impact**: Breaks `from __future__ import annotations` statements
- **Solution**: Do NOT use `__future__` imports in submissions
- **Status**: Our submissions are clean (no `__future__` imports)

### 2. Local HIP Compilation Success (MLA)
- **Result**: MLA kernel compiled successfully to `/tmp/mla_fp8_kernel.so`
- **Significance**: Strong indicator it will work on MI355X
- **Verification**: No syntax errors, ctypes loading successful
- **Risk Level**: LOW for MLA submission

### 3. Data Format Verification
- **MLA FP8**: `kv_data["fp8"]` returns tuple `(tensor, scale)`
- **GEMM MXFP4**: Requires scale dequantization with E8M0 format
- **Implementation**: Both submissions handle formats correctly

### 4. Proven Fallback Paths
- **MLA**: Falls back to reference (~67µs baseline)
- **GEMM**: Falls back to `gemm_a4w4` (~22.7µs baseline)
- **Safety**: Both ensure correctness even if custom kernel fails

---

## Competition Status

### Timeline
- **Current**: March 18, 2026
- **Deadline**: March 30, 2026
- **Remaining**: 12 days

### Recent Activity
- **Last Submissions**: March 15, 2026 (3+ days ago)
- **Status**: All recent submissions FAILED (SyntaxError)
- **Runner Load**: Currently NOT overloaded

### Leaderboard Names (Confirmed/Expected)
- ✓ **GEMM**: `amd-mxfp4-mm` (confirmed working)
- ? **MLA**: `amd-mixed-mla` (to verify)
- ? **MoE**: `amd-moe-mxfp4` (to verify)

---

## Submission Strategy

### Pre-Submission Checklist
1. ✓ Verify no `__future__` imports
2. ✓ Test local compilation (if possible)
3. ✓ Ensure fallback paths work
4. ⚠ Check coordination (no concurrent submissions)

### Submission Order
1. **Test mode** - Verify correctness
2. **Benchmark mode** - Check performance
3. **Leaderboard mode** - Official submission

### Coordination Requirements
- Submit one kernel at a time
- Create lock file before submitting
- Wait for results before next submission
- Update status in shared location

---

## Files Ready for Submission

### MLA: `mla_fp8_hip.py`
- **Status**: Compilation verified locally
- **Format**: FP8 E5M2
- **Fallback**: Reference implementation
- **Risk**: LOW

### GEMM: `gemm_custom_hip.py`
- **Status**: Syntax valid, imports clean
- **Format**: MXFP4 with E8M0 scales
- **Fallback**: `gemm_a4w4`
- **Risk**: MEDIUM (cannot verify fully without aiter)

---

## Next Actions
1. Store this learning to SurrealDB
2. Create coordination lock mechanism
3. Submit MLA (test mode)
4. Submit GEMM (test mode)
5. Iterate based on results

## [2026-04-01] NEMOTRON-3 MOE ROUTER COLLAPSE
- **Architecture**: 30B total, 3.5B active. 128 routed experts + 1 shared expert.
- **Routing Strategy**: Top-5 routing per token.
- **Expert Collapse Risk**: Router becomes biased toward a small subset of experts, causing uniform routing logits or stagnant reasoning performance.
- **Mitigation (Phase 6 Strategy)**: Evaluate expert utilization histograms and pairwise cosine similarity of FFN weights in LoRA adapters. Freeze routing weights if collapse is detected during downstream SFT.
