---
type: research
name: aiter-kernel-analysis
date: 2026-03-17
---

# AITER Kernel Analysis

## GEMM Kernels (/tmp/aiter/hsa/gfx950/f4gemm/)

### Available Tile Sizes
- **Small M (≤32)**: 32×128, 32×256, 32×512, 32×640, 32×768, 32×1024
- **Medium M (32-128)**: 128×128, 128×256
- **Large M (128-256)**: 192×128, 192×256, 224×128, 224×256, 256×128, 256×256
- **Wide N**: 160×128, 160×256, 160×384

### Key Pattern
All kernels follow naming: `f4gemm_bf16_per1x32Fp4_BpreShuffle_{M}x{N}.co`
- `per1x32`: per-1x32 block scaling
- `BpreShuffle`: Pre-shuffled weights for better cache

## MoE Kernels (/tmp/aiter/hsa/gfx950/fmoe_2stages/)

### Stage1 Kernels
- Tile sizes: 112×128, 128×128, 144×128, 160×128
- Variants: PF2, PF3 (different parallelism factors)
- Format: `fmoe_stage1_bf16_pertokenFp8_blockscale_g1u1_{M}x{N}_pf{X}.co`

### Key Implementation Details (from moe_fused_gate.cu)
- Uses ck_tile for expert dispatch
- OPUS sorting for routing efficiency
- Block size M = 32 optimal
- Sigmoid activation for gating
- Warp-level reduction for top-k selection

## MLA Kernels (/tmp/aiter/hsa/gfx950/mla/)

### Available Variants
- **A16W16**: BF16 query, BF16 KV
- **A8W8**: FP8 query, FP8 KV
- **Tile configs**: 32×4, 64×4 (M×N per head)
- **Head variants**: QH16, QH128

### Two-Stage Architecture
1. **Stage 1**: Attention scores (Q×K) - ASM kernel
2. **Stage 2**: Reduction (Softmax×V) - Triton kernel

### Metadata Generation (from metadata.cu)
- `get_mla_metadata_v1`: Creates work distribution
- `fast_mode=True`: Uses v1_2_device (faster, less flexible)
- `intra_batch_mode=True`: Uses v1_0_device (more flexible)
- Key parameters: work_indptr, reduce_indptr, reduce maps

### Optimal num_kv_splits Formula
```python
# From mla.py
overhead = 84.1
avg_kv = total_kv / bs
cu_num = 304  # MI355X

# Minimize: (bs * i) / ((bs * i + cu_num - 1) // cu_num * cu_num) * avg_kv / (avg_kv + overhead * i)
# for i in range(1, 17)
```

## Key Learnings

### 1. Tile Size Selection
- Small M → Small tiles + high split-K
- Large M → Large tiles + low/no split-K
- N dimension: Match to actual output size

### 2. Memory Layout
- Pre-shuffled weights (BpreShuffle) improve cache
- FP8 provides 2× bandwidth vs BF16
- LDS swizzle avoids bank conflicts

### 3. Parallelism
- Split-K helps small M (parallelize K dimension)
- num_kv_splits balances parallelism vs overhead
- Wavefront count: 8 optimal for MI355X

### 4. Critical Parameters
- **GEMM**: log2_k_split (0-4), kernel selection
- **MoE**: KSPLIT (1-8), OPUS sorting, doweight_stage1=False
- **MLA**: num_kv_splits (1-64), fast_mode, intra_batch_mode

## Custom HIP Development Opportunities

### GEMM
- Fuse quantization + GEMM in single kernel
- Direct global→LDS 128-bit transfers
- 8-wave ping-pong scheduling

### MoE
- Fuse routing + stage1 computation
- Persistent kernel with expert switching
- Shared memory for routing weights

### MLA
- Single-stage fused attention (QK + SoftmaxV)
- Warp-level softmax reduction
- LDS caching for Q/K/V
