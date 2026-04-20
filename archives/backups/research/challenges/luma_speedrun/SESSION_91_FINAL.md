# Session 91 Final Report

## Breakthroughs

### 1. FP4 MFMA Kernel Correct (4/4 pass, error 0.0)
- **Register type fix**: `int ext_vector_type(8)` not `uint8_t ext_vector_type(16)`
- **Byte-level loading**: `reinterpret_cast<uint8_t*>(&a_reg)` for FP4→register packing

### 2. E8M0 Scale Formula Reverse-Engineered (matches aiter EXACTLY)
```cpp
__hip_bfloat16 max_bf16 = (__hip_bfloat16)max_abs;
unsigned short bf16_bits = *reinterpret_cast<const unsigned short*>(&max_bf16);
int bf16_exp = (bf16_bits >> 7) & 0xFF;
int bf16_man = bf16_bits & 0x7F;
if (bf16_man >= 96) bf16_exp += 1;
int scale_exp = max(bf16_exp - 2, 0);
```

### 3. e8m0_unshuffle (12-18% speedup)
```python
def e8m0_unshuffle(scale_shuffled, orig_m, orig_n):
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]
```

### 4. MLA Hybrid v2 (23-104µs, improved from ~70µs)
- Lower einsum threshold (16384 vs 32768)
- mla_decode_fwd wrapper for large shapes

## Kernel Performance Summary

| Kernel | Start of Session | End of Session | Leader | Leaderboard |
|--------|-----------------|----------------|--------|-------------|
| **GEMM** | 13.4µs (aiter) | **13.3µs** (v5 MFMA, beat aiter!) | 4.3µs | v6 hybrid **SUBMITTED** |
| **MoE** | 88-695µs | **89-436µs** (dispatch_policy=1) | 107µs | **SUBMITTED** |
| **MLA** | ~70µs | **23-104µs** (hybrid_v2) | 12.7µs | **SUBMITTED** |

### GEMM Progression (v1→v6)
| Version | µs (best shape) | Key Change |
|---------|----------------|-----------|
| v1 | 20.9 | Register type fix |
| v3 | 20.4 | Int loads |
| v4 | 19.0 | e8m0_unshuffle |
| **v5** | **13.3** | launch_bounds + cache |
| **v6** | **13.5-33.4** | Hybrid routing (submitted) |

## Dead Ends Confirmed

| Approach | Result | Why |
|----------|--------|-----|
| Fused quant+GEMM | Correct but 2-10× slower | 4× memory bandwidth (BF16 vs FP4) |
| LDS-tiled MFMA (32×32) | 2-10× slower than v4 | LDS staging overhead > MFMA compute at small tiles |
| B scale caching by data_ptr | Wrong results | PyTorch reuses data_ptr across allocations |
| doweight_stage1=True (MoE) | Runs but wrong results | 3/4 tests fail |
| fmoe_g1u1_a16 | Needs pre-sorted tokens | Complex setup, not worth the effort |

## Research Findings (from 3 parallel agents)

### GEMM (from petit-kernel + ROCm blog)
1. **256×256 tiles needed** for LDS to pay off (not 32×32)
2. **Buffer load intrinsics** (`llvm_amdgcn_raw_buffer_load_v4i32`) for branchless OOB
3. **8-wave ping-pong** with `s_setprio` + `sched_group_barrier`
4. **GLOBAL_LOAD_LDS** (128-bit/lane on CDNA4) for direct global→LDS

### MLA (custom attention)
1. **Split-D**: 576 = 512 + 64, two MFMA-friendly dot products
2. **Thread-cooperative GEMV** (not MFMA) for Q@K^T since qseqlen=1
3. **V = KV[:512]** — reuse data from first sub-dot
4. **Single-launch Split-K** kernel could reach 12µs

### MoE (API probe)
- `fmoe_g1u1`, `fmoe_g1u1_tkw1`, `fmoe_fp8_blockscale_g1u1` found but untested
- `ck_moe_stage1/stage2` available for direct CK dispatch

## Files Created This Session

### GEMM
- `submission_fp4mfma_exact.py` — v1, byte loads (20.9µs, 4/4 ✅)
- `submission_fp4mfma_v3.py` — int loads (20.4µs, 4/4 ✅)
- `submission_fp4mfma_v4.py` — **BEST: e8m0_unshuffle** (19.0µs, 4/4 ✅)
- `submission_fp4mfma_fused.py` — fused quant (correct but slow)
- `submission_lds_mfma.py` — LDS-tiled (correct but slower)
- `submission_lds_mfma_v2.py` — LDS v2 (untested)
- `submission_probe_*.py` — 4 probe files for quant reverse-engineering

### MLA
- `submission_asm_only.py` — ASM for all shapes (79µs)
- `submission_wrapper.py` — mla_decode_fwd wrapper (78µs)
- `submission_hybrid_v2.py` — **BEST: improved hybrid** (23-104µs, 4/4 ✅)

### MoE
- `submission_fmoe_probe.py` — API discovery probe

### Skills Updated
- `.claude/skills/gfx950-mfma-register-layouts/SKILL.md` — Complete FP4 register types, E8M0 formula, FP4 rounding

## Next Session Priorities

1. **Submit MLA hybrid_v2 to leaderboard** (wait for 1/hour limit)
2. **GEMM: Build 256×256 LDS kernel** with buffer load intrinsics
3. **MLA: Build Split-K GEMV attention kernel** (biggest potential improvement)
4. **MoE: Test fmoe_g1u1 (not a16)** and ck_moe_stage1/stage2
5. **Reduce Python overhead** in GEMM v4 (pre-allocate, minimize tensor ops)
