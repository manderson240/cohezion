# AMD Speedrun Retrospective - March 2026

## Session Summary

### K-Search Trees Evolved
| Kernel | Nodes | Best Synthetic | Target | Gap |
|--------|-------|--------------|--------|-----|
| GEMM | 111 | 6.1µs | 1.0µs | 6.1× |
| MLA | 67 | 93.67µs | 26.8µs | 3.5× |
| MoE | 66 | ~110µs | 109.8µs | ~1.0× |

### Breakthrough Discovery
**`load_inline` custom HIP kernels WORK on Popcorn runners** - proven by official template-hip.py!

## Key Learnings

### 1. load_inline Pattern Works (GEMM)
```python
from torch.utils.cpp_extension import load_inline
module = load_inline(
    name='fp8_mm',
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],  # AMD auto-converts CUDA→HIP!
    functions=['fp8_mm'],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20"],
)
```
- Source: `gpu-mode/reference-kernels/blob/main/problems/amd/fp8-mm/template-hip.py`
- Rank 1 uses this approach for 1µs GEMM

### 2. FP4/E8M0 Format (from aiter fp4_utils.py)
```python
mxfp4_list = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]  # positive
# E8M0: f32 = 2^(e8m0 - 127)
```

### 3. LLM Generates AMD HIP Code
- qwen3-coder-next:cloud generates proper `__hip_bfloat16`, `hipLaunchKernelGGL`
- But struggles with complete working submissions (missing `custom_kernel` wrapper)

### 4. MLA Has 13+ Attention APIs Untested
Discovered but not systematically evaluated:
- `pa_ps_fwd_asm` (persistent ASM) - CONFIRMED EXISTS
- `fmha_v3_varlen_fwd` (FlashMHA v3)
- `flash_attn_varlen_func` with padded V

### 5. MoE Path Forward
- `AITER_BYPASS_TUNE_CONFIG=1` eliminates CSV lookup overhead
- `FlyDSL Pipeline` for DSL-based kernel generation
- KSPLIT=6 for est_m<5 (Kimi heuristic)

## Anti-Patterns

1. **Over-engineering without testing**: Multiple promising paths discovered but never validated on GPU
2. **Synthetic scores diverge from real**: Dry-run-llm mode uses random variation
3. **Tree bloat without focus**: 111 GEMM nodes but many pruned/untested
4. **LLM code generation incomplete**: Generates HIP code but misses Python wrapper

## Reusable Patterns

### Pattern: Block-wise GEMM with Lifted Scales
```cpp
// Official template pattern - scales OUTSIDE inner loop
for (int kb = 0; kb < k_blocks; kb++) {
    float block_result = 0.0f;
    for (int kk = 0; kk < 32; kk++) {
        // inner loop - no scaling here
        block_result += a_val * b_val;
    }
    // Scale ONCE per block
    result += block_result * a_scale * b_scale;
}
```

### Pattern: Tree Node Naming
- Use prefixes: `loadinline_`, `rocwmma_`, `blockscale_`
- Track parent-child relationships for path tracing
- Prune aggressively to keep active nodes < 20

### Pattern: LLM Prompt Strategy
Include in every prompt:
1. **CRITICAL requirements** (uppercase, emphasized)
2. **Input data format** (tuple structure)
3. **Exact types** (e.g., `__hip_bfloat16`, not `half`)
4. **Output requirement** (`def custom_kernel(data: input_t) -> output_t:`)

## Action Plan

### Immediate (Next Session)

1. **Test `submission_loadinline_final.py`** on GPU runner
   - File: `kernels/mxfp4-mm/submission_loadinline_final.py`
   - Expected: Should compile and run

2. **Implement rocWMMA block tiling**
   - Based on GPU Kernel Scientist paper (arXiv:2506.20807)
   - Tile sizes: 32×32×16 MFMA for MI355X

3. **Validate MLA paths** (highest priority after GEMM)
   - `pa_ps_fwd_asm` - persistent ASM kernel
   - `fmha_v3_varlen_fwd` - FlashMHA v3

### Short-term (Week 1)

1. **GEMM**: Target 2-3µs (2× rank 1)
   - Fix FP4 unpacking in load_inline kernel
   - Add proper E8M0 scale conversion
   - Implement block tiling with rocWMMA

2. **MLA**: Target 50µs (2× rank 1)
   - Explore `pa_ps_fwd_asm` persistent path
   - Investigate SnapMLA techniques

3. **MoE**: Maintain ~110µs
   - Try `AITER_BYPASS_TUNE_CONFIG=1`
   - Validate KSPLIT=6 heuristic

### Medium-term (Week 2-3)

1. **Custom HIP kernels for all kernels**
2. **Systematic API landscape evaluation**
3. **K-Search with live GPU feedback** (not synthetic)

## Skills to Refine

### skill: amd-load-inline-hip-kernel
Create skill for load_inline custom HIP kernel development.

### skill: ksearch-synthetic-to-live
Methodology for converting synthetic scores to live GPU validation.

### skill: triton-to-hip-translation
Pattern for translating Triton patterns to native HIP.

## Files to Reference

- `research/challenges/luma_amd_speedrun/autoresearch/research_strategy.md`
- `gpu-mode/reference-kernels/problems/amd/fp8-mm/template-hip.py`
- `gpu-mode/reference-kernels/problems/amd/mla-decode/submission.py`
- `~/vaults/cohezion-vault/luma-speedrun/learnings/`
