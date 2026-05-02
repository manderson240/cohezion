# MFMA-Tiled GEMM Blueprint for MI355X

## Goal: Beat aiter's 13.4µs geomean across 6 ranked shapes

## Architecture: 8-Wave Ping-Pong (from ROCm CDNA4 blog)

### Thread Block Configuration
- 512 threads = 8 waves of 64
- Output tile: 128×128 (4×4 grid of 32×32 MFMA tiles)
- K tile: 64 FP4 elements = 32 bytes

### Memory Layout
- LDS: 2 × (128×32 A + 128×32 B) = 2 × 8KB = 16KB (fits in 160KB)
- Cooperative loading: 512 threads load 8KB = 16 bytes/thread
- GLOBAL_LOAD_LDS: 128-bit per lane direct transfer (CDNA4 feature)

### Compute Pipeline
```
Wave 0-3: Load tile t+1 from global → LDS buffer B
Wave 4-7: Compute MFMA on tile t from LDS buffer A
Then swap roles
```

### MFMA Intrinsic
```cpp
c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
    a_reg, b_reg, c_reg, 4, 4, 0, scale_a, 0, scale_b);
```
- Register type: `int __attribute__((ext_vector_type(8)))` (VERIFIED)
- Scale: E8M0 via `bf16_exp - 2 + (mantissa >= 96 ? 1 : 0)` (VERIFIED)
- FP4 rounding: round-to-nearest-even (VERIFIED)

### Wave Scheduling Intrinsics
```cpp
__builtin_amdgcn_s_setprio(3);     // High priority for compute waves
__builtin_amdgcn_sched_barrier(0);  // Prevent instruction reordering
__builtin_amdgcn_s_barrier();       // Wave barrier
```

### Shape Specialization (CRITICAL for geomean)
| M | Strategy |
|---|----------|
| 4 | 1 wave, 32×128 tile, all N parallelism |
| 16 | 4 waves, 32×128 tile, N+K parallelism |
| 32 | 4 waves, 32×128 tile |
| 64 | 8 waves, 128×128 tile |
| 256 | 8 waves, 128×128 tile, full ping-pong |

### Implementation Steps
1. Start with 32×32 single-wave LDS kernel (DONE — submission_lds_mfma.py, but too slow)
2. Fix: use LARGER tiles (128×128) to amortize LDS overhead
3. Add cooperative loading with 4-byte aligned reads
4. Add double buffering (ping-pong between 2 LDS slots)
5. Add wave scheduling (s_setprio, sched_barrier)
6. Add shape-specialized dispatch
7. Profile and tune per ranked shape

### References
- ROCm blog: https://rocm.blogs.amd.com/software-tools-optimization/cdna4-gemm-kernels/README.html
- HipKittens: https://arxiv.org/html/2511.08083v1
- Petit-kernel: https://github.com/causalflow-ai/petit-kernel
- Our verified MFMA skill: .claude/skills/gfx950-mfma-register-layouts/SKILL.md
