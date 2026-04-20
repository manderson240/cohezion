# Probe: CDNA 4 (MI355X/gfx950) Tiling Strategies

## Summary

**Hardware:** AMD Instinct MI355X (CDNA 4, gfx950)
**Architecture:** 8 XCDs (chiplets), each with matrix cores supporting MFMA instructions
**Key Instructions:** `mfma_f32_32x32x64_f8f6f4` for MXFP4 mixed precision
**Status:** Documented optimal tile strategies for all three kernel targets

---

## MI355X Hardware Characteristics

### Compute Units

| Property | Value | Implication |
|----------|-------|-------------|
| XCDs | 8 | Thread block scheduling across chiplets |
| CUs per XCD | 38-40 (304 total) | High parallelism for GEMM |
| Wave size | 64 threads | Warp-level operations |
| Matrix cores | Per-CU MFMA units | Native fp8/fp6/fp4 support |

### Memory Hierarchy

| Level | Size | Strategy |
|-------|------|----------|
| LDS (shared mem) | ~64KB per CU | Quantization fusion, tile staging |
| L2 cache | Distributed per XCD | XCD-aware scheduling for locality |
| HBM3 | High bandwidth | MXFP4 reduces by 2x vs FP8 |

---

## MFMA Instruction Details (CDNA 4)

### `mfma_f32_32x32x64_f8f6f4`

**Operation:** 32x32 output tile with 64-element K reduction
- Supports mixed precision: fp8, fp6, fp4 (f8f6f4)
- Accumulates in f32
- Covers 64 K-elements packed (32 bytes for fp4)

**Tile shape implications:**
- M-tile: 32 (output rows)
- N-tile: 32 (output columns)
- K-tile: 64 (reduction dimension in packed bytes)

**Scale application:**
- Separate MFMA for scale multiplication
- Scale is E8M0 (1 byte), one per 32 fp4 elements

---

## Optimal Tile Sizes by Kernel

### 1. MXFP4 GEMM (amd-mxfp4-mm)

**Current best:** `gemm_a4w4_asm` from aiter
**Tile constraints:**
- BLOCK_M >= 16 (Triton minimum for correctness)
- BLOCK_K >= 64 (MFMA K-dimension alignment)
- BLOCK_N: 32-128 (depends on output size)

**Recommended tile strategy:**
```python
# For GEMM with shape (M, N, K):
BLOCK_M = max(16, min(128, triton.next_power_of_2(M)))
BLOCK_N = 64  # Good balance for N=2112-4096 range
BLOCK_K = 64  # MFMA alignment

# Group-M swizzle for L2 locality
GROUP_SIZE_M = 8  # Process 8 M-tiles together
```

**XCD scheduling:**
- Use simple round-robin across 8 XCDs
- Avoid Origami-style remapping (bug when tiles % 8 != 0)

### 2. MLA Decode (amd-mixed-mla)

**Current best:** Direct ASM dispatch with adaptive num_kv_splits
**Tile constraints:**
- QK_HEAD_DIM = 576 (not power-of-2, pad to 1024 if using Triton)
- V_HEAD_DIM = 512 (power-of-2, efficient)
- Variable batch/KV sizes (4-256 bs, 1k-8k KV)

**Three-regime tile strategy:**
```python
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768
A16W8_THRESHOLD = 262144

total_kv = bs * kvseqlen

if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
    # Regime 1: torch.matmul (no XCD scheduling needed)
    # 3D batched GEMM with softmax
    pass
elif total_kv <= A16W8_THRESHOLD:
    # Regime 2: A16W8 ASM (bf16 Q + bf16 KV)
    num_kv_splits = _choose_splits(total_kv)  # 1/4/8
else:
    # Regime 3: A8W8 ASM (fp8 Q + fp8 KV)
    num_kv_splits = _choose_splits(total_kv)  # 8/16/32

def _choose_splits(total_kv):
    if total_kv <= 2048:    return 1
    if total_kv <= 16384:   return 4
    if total_kv <= 131072:  return 8
    if total_kv <= 524288:  return 16
    return 32
```

**Custom kernel tile strategy (HipKittens):**
```python
# For MLA with K=576, V=512:
# Use separate tiles for Q@K^T and softmax@V
# Tile Q: (BLOCK_M, BLOCK_K) where BLOCK_K covers 576
# Tile KV: (BLOCK_N, BLOCK_K) for keys, (BLOCK_N, BLOCK_V) for values

BLOCK_M = 16  # Decode: small batches
BLOCK_N = 64  # KV sequence parallelism
QK_PAD = 1024  # Next pow2(576) for Triton

# HipKittens may handle non-pow2 more efficiently
```

### 3. MoE MXFP4 (amd-moe-mxfp4)

**Current best:** `aiter.fused_moe` with adaptive KSPLIT
**Tile constraints:**
- d_hidden = 7168 (largest dimension)
- d_expert varies: 256-2048 (TP-split)
- E_total = 257 or 33 (routed + shared)
- top_k = 8-9

**Two-stage tile strategy:**
```python
# Stage 1: Gate+Up GEMM
# M = bs, K = d_hidden, N = 2 * d_expert

# Stage 2: Down GEMM
# M = bs, K = d_expert, N = d_hidden

# Per-expert parallelism:
estimated_m = (bs * top_k) // E_total

if estimated_m >= 50:
    # Dense: Use CK path with large tiles
    block_m = 64  # CK auto-selects
    split_k = 0   # No K-split
elif E_total >= 200 and estimated_m < 10:
    # Sparse 257E: KSPLIT=4 for K-parallelism
    block_m = 32
    split_k = 4
else:
    # Moderate: KSPLIT=2
    block_m = 32
    split_k = 2
```

**Custom kernel fusion strategy:**
```python
# Goal: Fuse Stage 1 + SiLU + Stage 2 into single kernel
# Eliminate intermediate activation writeback

# Tile through experts:
# - Each workgroup processes one expert
# - Load weights into LDS
# - Gate+Up GEMM in registers
# - SiLU in-place
# - Down GEMM to output

EXPERT_TILE_M = 32  # Tokens per expert per iteration
EXPERT_TILE_N = 256  # Hidden dimension chunks
```

---

## CDNA 4-Specific Optimizations

### 1. MFMA Block Scaling (MXFP4)

**E8M0 scale layout:**
```c
// One scale per 32 fp4 elements = 16 packed bytes
// For BLOCK_K = 64 packed bytes: 4 scale entries needed
// Scale tensor: [BLOCK_M, BLOCK_K // 32] for LHS
// Scale tensor: [BLOCK_N, BLOCK_K // 32] for RHS (N-first!)
```

**Scale application pattern:**
```python
# In kernel (Triton/HIP):
# 1. Load fp4 values
# 2. Unpack to f32 (or use dot_scaled)
# 3. Multiply by E8M0-converted scale
# 4. MFMA accumulate

# HipKittens may have native tile.scale() primitive
```

### 2. LDS Usage for Fusion

**Optimal LDS allocation:**
```c
// For fused MoE:
// - Reserve LDS for: input activations + gate/up weights + intermediate
// - SwiGLU activation in registers, not global memory
// - Only write final output to HBM

// LDS budget per workgroup: ~32-48KB
// - A tile: BLOCK_M * BLOCK_K bytes (bf16)
// - W1 tile: BLOCK_K * BLOCK_N * 0.5 bytes (fp4 packed)
// - Intermediate: BLOCK_M * BLOCK_N * 2 bytes (bf16)
```

### 3. XCD-Aware Scheduling

**Correct XCD remapping:**
```python
# Use floor division, not ceiling:
tiles_per_xcd = total_tiles // NUM_XCDS  # floor
remainder = total_tiles % NUM_XCDS

xcd_id = pid % NUM_XCDS
chunk_in_xcd = pid // NUM_XCDS

if xcd_id < remainder:
    offset = xcd_id * (tiles_per_xcd + 1)
    remapped = offset + chunk_in_xcd
else:
    offset = remainder * (tiles_per_xcd + 1) + (xcd_id - remainder) * tiles_per_xcd
    remapped = offset + chunk_in_xcd
```

**Simple alternative (no XCD remapping):**
```python
# Just use standard group-M swizzle
# MI355X L2 is large enough that XCD-aware scheduling provides marginal benefit
# for small-to-medium GEMMs
```

---

## Implementation Template: HipKittens MoE Tile

```python
# Hypothetical HipKittens-style tile specification
# For MoE Stage 1+2 fusion on MI355X

import hipkittens as hk

@hk.kernel
def fused_moe_tile(
    hidden: hk.Tensor[M, K],      # bf16
    w1: hk.Tensor[K//2, N*2],     # fp4x2 packed
    w1_scale: hk.Tensor[N*2, K//32],  # e8m0
    w2: hk.Tensor[N//2, K],       # fp4x2 packed
    w2_scale: hk.Tensor[K, N//32],   # e8m0
    output: hk.Tensor[M, K],      # bf16
):
    # Tile specification
    tile_m = 32
    tile_n = 256
    tile_k = 64  # packed

    # Stage 1: Gate+Up
    # Use MXFP4 tile GEMM primitive
    gate_up = hk.tile.gemm_mxfp4(
        hidden, w1, w1_scale,
        tile_m, tile_n*2, tile_k
    )

    # SwiGLU in registers
    gate, up = gate_up.split(N)
    activated = hk.silu(gate) * up

    # Stage 2: Down
    # Quantize activated to MXFP4 in LDS
    activated_q, activated_scale = hk.quantize_mxfp4(activated)

    output_tile = hk.tile.gemm_mxfp4(
        activated_q, w2, w2_scale, activated_scale,
        tile_m, tile_k, tile_n
    )

    hk.store(output, output_tile)
```

---

## Open Questions

1. Does HipKittens support non-power-of-2 dimensions (MLA's 576)?
2. What is the optimal split between LDS-resident vs HBM data for MoE fusion?
3. Can CK-Tile express the 2-stage MoE pattern with in-kernel SiLU?
4. What is the MFMA throughput difference between fp8 and fp4 on gfx950?

---

## References

- `amd-gfx950-tl-dot-scaled-constraints` SKILL.md - Triton minimums
- `tritonblas-origami-xcd-remapping-bug` SKILL.md - XCD scheduling bug
- `amd-moe-mxfp4-optimization` SKILL.md - MoE-specific tile strategy
- `amd-mla-decode-optimization` SKILL.md - MLA regime thresholds
- AMD CDNA 4 whitepaper (MI355X)
- CK-Tile examples: composable_kernel/example/ck_tile/

---

*Probe created: 2026-03-27*
*Status: Research in progress*
