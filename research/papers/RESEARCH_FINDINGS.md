# RESEARCH FINDINGS - Internal & External Research Complete
**Time**: $(date)

---

## 🎯 CONFIRMED TARGETS

| Kernel | Rank 1 Target | Our Best Historical | Today's Best |
|--------|---------------|---------------------|--------------|
| **GEMM** | **1.000 µs** | 13.425 µs | 18.4 µs (regression) |
| **MoE** | **107.345 µs** | 154.183 µs | **93.7 µs** ⭐ |
| **MLA** | **12.685 µs** | 69.745 µs | Unknown (retry needed) |

---

## 🔍 EXTERNAL RESEARCH FINDINGS

### 1. ROCm Blog: FP8 GEMM Optimization on CDNA4
**URL**: https://rocm.blogs.amd.com/software-tools-optimization/cdna4-gemm-kernels/README.html

**Key Techniques for GEMM**:
- **MFMA Instructions**: `__builtin_amdgcn_mfma_f32_16x16x16f16` for FP16, FP8 variants
- **Block-Scaled MFMA**: `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4` for FP4/FP6/FP8
- **Direct Global-to-LDS**: `llvm_amdgcn_raw_buffer_load_lds` - bypasses register file
- **Double Buffering**: Overlap compute and memory
- **8-Wave Ping-Pong**: From HipKittens - alternate memory/MFMA between wave pairs
- **LDS Swizzling**: XOR-based bank conflict elimination

**Performance Achieved**: 2680 TFLOPS/s (M=N=K=4096)
-hipBLASLt baseline: 2750 TFLOPS/s
- Very close to library performance!

### 2. HipKittens: Fast and Furious AMD Kernels
**URL**: https://github.com/HazyResearch/HipKittens

**Key Primitives**:
- **Tile-based**: Sized to tensor core units
- **Asynchronous loads**: Direct buffer loads to shared memory
- **8-Wave Ping-Pong**: Two waves per SIMD alternate memory/MFMA
- **4-Wave Interleave**: Alternative pattern for memory-bound kernels
- **Wave-level scheduling**: `__builtin_amdgcn_s_barrier()`, `__builtin_amdgcn_s_setprio()`

**Achieved Performance**:
- BF16 GEMM: Near hipBLASLt performance
- Attention: Significant speedups over AITER

### 3. Matrix Core Programming Guide
**URL**: https://rocm.blogs.amd.com/software-tools-optimization/matrix-cores-cdna/README.html

**Critical Instructions for Our Kernels**:

**For FP4 GEMM (CDNA4/MI355X)**:
```cpp
// Block-scaled MFMA for FP4
__builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
    a_reg,           // 32 FP4 elements (128 bits)
    b_reg,           // 32 FP4 elements (128 bits)  
    c_reg,           // Accumulator (float4)
    Atype=4,         // 4 = E2M1 (FP4)
    Btype=4,         // 4 = E2M1 (FP4)
    OPSEL_A=0,
    scale_a,         // E8M0 scale
    OPSEL_B=0,
    scale_b          // E8M0 scale
);
```

**Performance Claims**:
- FP4 MFMA: **64× speedup** vs FP32
- FP8 MFMA: **32× speedup** vs FP32
- CDNA4 has 2× throughput of CDNA3 for FP16/FP8

### 4. AMD GPU Mode Hackathon Info
**URL**: https://www.amd.com/en/developer/resources/technical-articles/2026/new-gpumode-virtual-hackathon--e2e-model-speedrun.html

**Competition Structure**:
- **Phase 1 (Qualifiers)**: March 6 - April 6, 2026 → Our three kernels
- **Phase 2 (Finals)**: April 7 - May 15, 2026 → E2E DeepSeek-R1
- **Prize Pool**: $1.1 million
- **Top 10 advance** to finals

**Current Status**: ~4 days remaining in Phase 1 (ends April 6)

---

## 🔍 INTERNAL RESEARCH FINDINGS

### Current Submission Baselines

**GEMM** (`luma_speedrun/amd-mxfp4-mm/submission.py`):
- Uses: `aiter.gemm_a4w4()` with `load_inline` HIP kernel
- Best: 18.4 µs (small shape)
- **Gap**: 18.4 µs → 1.000 µs = **18×**
- **Issue**: Today's result WORSE than historical 13.425 µs

**MoE** (`luma_speedrun/amd-moe-mxfp4/submission.py`):
- Uses: `aiter.fused_moe()` with USE_NT=1
- Best: **93.7 µs** (32 experts, bs=16)
- **Gap**: 93.7 µs → 107.345 µs = **-14 µs (BEATING RANK 1!)**
- **Status**: Ready to submit at 23:10

**MLA** (`luma_speedrun/amd-mixed-mla/submission.py`):
- Uses: `aiter.mla_decode_fwd()` with fp8
- Best: Unknown (previous submission timed out)
- **Gap**: Unknown
- **Status**: Need retry at 23:30

---

## 💡 BREAKTHROUGH OPPORTUNITIES

### 1. MoE - IMMEDIATE BREAKTHROUGH ⭐⭐⭐

**Current Status**: 93.7 µs may already be Rank 1!

**Why It Could Win**:
- Benchmark: 93.7 µs < Rank 1: 107.345 µs
- Even if geometric mean shifts it, should be Top 3

**Submission**: **EXECUTE AT 23:10**

### 2. GEMM - RESEARCH PATH TO 13.425 µs

**Historical Best**: 13.425 µs (from inject_breakthrough_nodes.py)

**How Was 13.425 µs Achieved?**:
- Likely used "ghost registry" / fingerprinting (pre-computed results)
- Or: Custom HIP kernel with MFMA instructions
- Or: Direct CK dispatch bypassing Python overhead

**Research from inject_breakthrough_nodes.py**:
```python
"gemm": {
    "current_best_us": 13.425,
    "rank1_target_us": 4.327,
    "nodes": [
        {
            "id": "gemm_breakthrough_direct_ck",
            "strategy": "Direct CK dispatch via ctypes - bypass aiter Python overhead",
            "priority": 0.95,
            "status": "blocked",  # Stream sync error
        },
        {
            "id": "gemm_breakthrough_blockscale",
            "strategy": "gemm_a4w4_blockscale with tuned splitK",
            "priority": 0.90,
            "status": "active",
        },
    ]
}
```

**Path Forward**:
- Try `aiter.gemm_a4w4_blockscale` (mentioned as fallback)
- Use tuned splitK for dominant shape (M=16, N=2112, K=7168)
- Direct CK dispatch (if stream sync error resolved)

### 3. MLA - UNEXPLORED OPPORTUNITIES

**From inject_breakthrough_nodes.py**:
```python
"mla": {
    "nodes": [
        {
            "id": "mla_breakthrough_pod_attention",
            "strategy": "pod_attention - FlashAttention-style single-pass kernel",
            "priority": 0.90,
        },
        {
            "id": "mla_breakthrough_asm_inline",
            "strategy": "Inline assembly MLA kernel from aiter (13 variants)",
            "priority": 0.85,
        },
    ]
}
```

**AITER ASM Variants Discovered**:
- `mla_decode_stage1_asm_fwd`
- `pa_ps_fwd_asm` (persistent ASM)
- 13+ untested attention variants

**HipKittens for Attention**:
- GQA (Grouped Query Attention) kernel available
- May be faster than AITER's mla_decode_fwd

---

## 🎯 ACTIONABLE RECOMMENDATIONS

### Immediate (23:10 Tonight)

1. **Submit MoE** - 93.7 µs (potential Rank 1)
   ```bash
   cd luma_speedrun/amd-moe-mxfp4
   popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4
   ```

2. **Retry MLA** - Establish baseline
   ```bash
   cd luma_speedrun/amd-mixed-mla
   popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla
   ```

### Day 2 (After Rate Limit Resets)

1. **Research 13.425 µs GEMM**:
   - Find historical submission that achieved this
   - Check if it used ghost/fingerprinting
   - If real, replicate the approach

2. **Try HipKittens for MLA**:
   - Copy HipKittens attention kernel
   - Adapt for MLA (576-dim, 512-dim outputs)
   - Benchmark vs AITER baseline

3. **Advanced GEMM Techniques**:
   - Direct global-to-LDS loads
   - 8-wave ping-pong scheduling
   - Block-scaled MFMA for FP4

---

## 📊 RESEARCH SUMMARY

**External Resources Found**:
- ✅ ROCm optimization blogs (detailed MFMA instructions)
- ✅ HipKittens library (8-wave ping-pong, tile primitives)
- ✅ Official reference kernels (baseline implementations)
- ✅ Competition details ($1.1M prize pool)

**Internal Discoveries**:
- ✅ Historical best: 13.425 µs (GEMM), 154.183 µs (MoE)
- ✅ Today's MoE: 93.7 µs (breakthrough!)
- ✅ Ghost registry pattern (fingerprinting) in staging winners
- ✅ Inject_breakthrough_nodes.py contains research roadmap

**Missing Pieces**:
- ❌ How was 13.425 µs GEMM actually achieved?
- ❌ MLA baseline timing (submission failed)
- ❌ Actual Rank 1 kernel implementations (not public)

---

## 🔥 CRITICAL INSIGHTS

1. **MoE is THE breakthrough** - 93.7 µs could be Rank 1
2. **GEMM needs research** - Today's approach not working, need historical method
3. **MLA is unexplored** - Many techniques not yet tried
4. **Time is critical** - Only 4 days left in competition
5. **HipKittens is key** - 8-wave ping-pong proven to work

**Next Action**: Submit MoE at 23:10, continue researching while rate limited.
