# Luma Speedrun - Key Learnings (March 31, 2026)

## BREAKTHROUGH: load_inline Works on Popcorn Runners!

Official `template-hip.py` from gpu-mode/reference-kernels **PROVES** custom HIP kernels work!

**This is how rank 1 achieves 1µs on GEMM - NOT using Python API!**

## Official Reference Templates
- GEMM: https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/fp8-mm/template-hip.py
- MLA: https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/mla-decode/submission.py
- MoE: https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/moe/submission.py

## load_inline Pattern
```python
from torch.utils.cpp_extension import load_inline

module = load_inline(
    name="kernel_name",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],  # AMD auto-converts CUDA to HIP!
    functions=["kernel_func"],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
)
```

## FP4 E2M1 Format
```python
# Values: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 (positive and negative)
vals = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0,
        -0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0]
```

## E8M0 Scale
```python
# f32 = 2^(e8m0 - 127)
exp2f((float)(e8m0 - 127))
```

## Lifted Scales Pattern (Key Optimization!)
```cpp
for (int kb = 0; kb < k_blocks; kb++) {
    float block_result = 0.0f;
    for (int kk = 0; kk < 32; kk++) {
        // NO SCALE HERE!
        block_result += a_val * b_val;
    }
    // Scale ONCE per block
    result += block_result * a_scale * b_scale;
}
```

## Current Submissions
- GEMM: `luma_speedrun/amd-mxfp4-mm/submission.py` - load_inline GEMM
- MLA: `luma_speedrun/amd-mixed-mla/submission.py` - SnapMLA
- MoE: `luma_speedrun/amd-moe-mxfp4/submission.py` - Adaptive KSPLIT

## Leaderboard Targets
| Kernel | Gap | Target |
|--------|-----|--------|
| GEMM | 22x | 1µs (rank 1) |
| MLA | 2.6x | 26.8µs (rank 1) |
| MoE | ~1x | 109.8µs (competitive) |

## Anti-Patterns
1. **LLM evolution doesn't work** in dry-run mode
2. **Synthetic scores don't predict** real GPU performance
3. **Trees get pruned aggressively** - all nodes eventually pruned

## Next Steps
1. **Test load_inline GEMM** on GPU runner
2. **Submit to leaderboard** - rate limit 1/hour
3. **Focus on GEMM** - biggest gap but clearest path
