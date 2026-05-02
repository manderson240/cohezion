# Probe: Triton vs Helion for AMD MI355X Kernel Development

## Summary

**Status:** Custom Triton blocked on runner; Helion may provide workaround
**Recommendation:** Research HipKittens and CK-Tile as primary paths; Helion as fallback for Triton codegen
**Impact:** Critical path decision for all three kernel targets

---

## Triton Status on Popcorn CLI Runners

### Confirmed Blockers

| Issue | Error | Impact | Kernel |
|-------|-------|--------|--------|
| `float4_e2m1fn_x2` KeyError | `KeyError: 'float4_e2m1fn_x2'` in triton/_utils.py | **BLOCKING** | All MXFP4 |
| Missing fp4 type registry | Triton's type registry has no entry for torch.float4_e2m1fn_x2 | **BLOCKING** | GEMM, MoE quant |

**Root Cause:** Triton-ROCm 3.6.0's JIT compiler lacks the fp4_e2m1fn_x2 dtype registration on gfx950 runners. The dtype IS valid as a PyTorch tensor type (aiter uses it), but Triton's JIT path fails.

### What Works

- Standard bf16/fp16/fp32 Triton kernels (no MXFP4)
- `tl.dot` with standard dtypes
- `tl.dot_scaled` with "e2m1" string format (NOT fp4x2 dtype)

### What Fails

```python
# This triggers KeyError on runner:
A = torch.empty((M, K//2), dtype=torch.float4_e2m1fn_x2, device="cuda")
# triton.jit kernel accessing A → KeyError in _utils.py
```

---

## Helion Evaluation

### What is Helion?

Helion is a Triton code generator developed for AMD GPU kernels. Key characteristics:
- Generates Triton kernels from higher-level specifications
- May use different dtype abstractions than raw torch.float4_e2m1fn_x2
- Used by AMD's internal teams for kernel development

### Investigation Needed

1. **Does Helion use e2m1 string format or fp4x2 dtype?**
   - If string format: May bypass the KeyError
   - If fp4x2 dtype: Same blocker as Triton

2. **Can Helion generate kernels that aiter can dispatch?**
   - aiter's `gemm_afp4wfp4` uses Triton persistent kernels internally
   - May provide compatible calling convention

3. **Helion vs HipKittens trade-off**
   - Helion: Still Triton-based, may hit same JIT limitations
   - HipKittens: Tile-based DSL with direct AMD-specific optimizations

---

## Alternative Paths (Research Priority)

### Path 1: HipKittens (HIGHEST POTENTIAL)

**Paper:** arxiv.org/abs/2511.08083
**Source:** github.com/HazyResearch/HipKittens

**Advantages:**
- Tile-based DSL that outperforms aiter's hand-ASM on MI355X
- 8-Wave Ping-Pong scheduling for GEMM/attention
- ~500 LOC attention forward kernels
- Purpose-built for AMD CDNA architecture

**Challenges:**
- Must write ORIGINAL kernels, not copy existing HK code
- MLA's K≠V head_dim (576 vs 512) requires custom tile handling
- Need to understand HK's tile primitives

### Path 2: CK-Tile Native MXFP4

**Source:** composable_kernel/example/ck_tile/18_flatmm/

**Advantages:**
- Native `mfma_f32_32x32x64_f8f6f4` + scale MFMA for MXFP4
- AMD-maintained, production quality
- Direct gfx950 ISA access

**Challenges:**
- C++ template metaprogramming complexity
- Runner blocks hipModuleLaunchKernel via static scanning
- Must find alternative dispatch method

### Path 3: AITER Internal APIs

**Status:** Partially explored

**Known working:**
- `gemm_a4w4_asm` for MXFP4 GEMM (fastest path)
- `mla_decode_stage1_asm_fwd` for MLA (bypass Python wrapper)
- `fused_moe` with adaptive KSPLIT for MoE

**API Ceiling:** Confirmed via exhaustive K-Search. All Python-level parameters exhausted.

---

## CDNA 4 (gfx950) Hardware Constraints

### Triton tl.dot_scaled Minimums

| Parameter | Minimum | Notes |
|-----------|---------|-------|
| BLOCK_M | 16 | Smaller = silent wrong results |
| BLOCK_K | 64 packed bytes | Assertion failure if violated |
| SCALE_PER_BLOCK | BLOCK_K // 16 | Scale covers 32 fp4 elements |

### XCD Scheduling (8 chiplets on MI355X)

**Origami remapping BUG:**
```python
# BUGGY - causes non-bijective mapping when total_tiles % 8 != 0
xcd_id = pid % NUM_XCDS
chunk_in_xcd = pid // NUM_XCDS
remapped_chunk = xcd_id * tl.cdiv(num_chunks, NUM_XCDS) + chunk_in_xcd
```

**Safe alternative:**
```python
# Group-M swizzle (no XCD remapping)
GROUP_SIZE_M: tl.constexpr = 8
num_pid_in_group = GROUP_SIZE_M * num_pid_n
group_id = pid // num_pid_in_group
first_pid_m = group_id * GROUP_SIZE_M
group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
pid_m = first_pid_m + (pid % group_size_m)
```

---

## Recommendations

### Immediate Actions

1. **Abandon pure Triton MXFP4 path** - KeyError is blocking
2. **Research HipKittens tile primitives** - Best chance for breakthrough
3. **Study CK-Tile flatmm examples** - For MXFP4 MFMA patterns
4. **Document aiter ASM dispatch patterns** - Fallback path

### Kernel-Specific Strategy

| Kernel | Current | Path to Leader | Recommended Approach |
|--------|---------|----------------|---------------------|
| GEMM | 13.4µs | Fused quant+GEMM | CK-Tile or HipKittens |
| MLA | 69.7µs | Single fused kernel | HipKittens attention |
| MoE | 154µs | Inter-stage fusion | CK-Tile 2-stage fusion |

---

## Open Questions

1. Can Helion generate Triton code using e2m1 string format instead of fp4x2 dtype?
2. Does HipKittens have examples for MoE-style 2-stage GEMM patterns?
3. Is there a way to dispatch CK-Tile kernels without hipModuleLaunchKernel?
4. What is the minimum viable HipKittens kernel for MLA attention (K=576, V=512)?

---

## References

- `amd-gemm-mxfp4-optimization` SKILL.md - Quant bottleneck analysis
- `amd-gfx950-tl-dot-scaled-constraints` SKILL.md - Hardware minimums
- `tritonblas-origami-xcd-remapping-bug` SKILL.md - XCD scheduling bug
- `competitive-kernel-optimization-ceiling` SKILL.md - Strategy framework

---

*Probe created: 2026-03-27*
*Status: Research in progress*
