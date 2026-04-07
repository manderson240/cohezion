# Kernel Reference - Popcorn Runner Direct Dispatch

## GEMM A4W4 Kernel Selection

All kernels located in `/home/runner/aiter/hsa/gfx950/f4gemm/`

### Available Configurations

Format: `f4gemm_bf16_per1x32Fp4_BpreShuffle_{M}x{N}.co`

**M (row tile size) × N (column tile size) combinations:**

| M\N | 128 | 256 | 384 | 512 | 640 | 768 | 896 | 1024 |
|-----|-----|-----|-----|-----|-----|-----|-----|------|
| 32  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 64  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 128 | ✓ | ✓ | ✓ | ✓ | - | - | - | - |
| 160 | ✓ | ✓ | ✓ | - | - | - | - | - |
| 192 | ✓ | ✓ | - | - | - | - | - | - |
| 224 | ✓ | ✓ | - | - | - | - | - | - |
| 256 | ✓ | ✓ | - | - | - | - | - | - |

**Total: 35 kernels available**

### Dispatch Method (Current)

```python
from aiter import gemm_a4w4, dtypes
from aiter.utility.fp4_utils import e8m0_shuffle

# Quantize inputs
A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())
A_h = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
B_h = e8m0_shuffle(B_scale).view(dtypes.fp8_e8m0)

# Dispatch
output = aiter.gemm_a4w4(
    A_q.view(dtypes.fp4x2),
    B_preshuffle,
    A_h,
    B_h,
    dtype=dtypes.bf16,
    bpreshuffle=True
)
```

### Alternative Dispatch (Potential - via load_inline)

The following parameters may be exposed via ASM APIs:
- `kernelName`: Select from compiled .co names (32x128, 64x256, etc.)
- `log2_k_split`: K-dimension split level
- `alpha`: Scaling parameter
- `beta`: Beta parameter for output
- `bias`: Optional bias tensor

---

## MoE Kernels

Located in `/home/runner/aiter/hsa/gfx950/fmoe/`

### Available Variants

| Kernel | File | Type | Config |
|--------|------|------|--------|
| FP8 Standard | `fmoe_fp8_blockscale_g1u1_subGU_256.co` | FP8 | With vertical scaling |
| FP8 Lightweight | `fmoe_fp8_blockscale_g1u1_novs_subGU_256.co` | FP8 | No vertical scaling |
| GELU | `gelu` | Activation | Standalone kernel |
| SILU | `silu` | Activation | Standalone kernel |

### Parameters from Naming Convention

- `g1u1`: 1 group, 1 unit
- `subGU_256`: Sub-gate-unit size = 256
- `novs`: No vertical scaling (lighter variant)

### Expected Signatures

```python
# Standard variant (from aiter export)
aiter.fmoe_fp8_blockscale_g1u1()
aiter.fmoe_g1u1()
aiter.fmoe_int8_g1u0()

# Generated dispatch
aiter.fmoe()  # High-level wrapper

# Stage decomposition
aiter.ck_moe_stage1()   # Expert selection/gating
aiter.ck_moe_stage2()   # Expert computation
```

---

## MLA / Attention Kernels

Located in `/home/runner/aiter/hsa/gfx950/mla/`

### 1. Prefill Kernels (High-Performance)

#### Core prefill variants

**A16W16 (full precision):**
```
mla_a16w16_qh16_m16x4_n16x1_coex0_mask1.co
mla_a16w16_qh16_m16x4_n16x1_coex0_mask1_ps.co    # persistent shader
mla_a16w16_qh16_m32x4_n16x1_coex0_mask1.co
mla_a16w8_qh16_m16x4_n16x1_coex0_mask1_ps.co     # A16W8 variant
```

**A8W8 (quantized) - Fixed query head:**
```
mla_a8w8_qh16_qseqlen1_gqaratio16.co             # qseqlen=1, GQA ratio=16
mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co          # persistent variant
mla_a8w8_qh16_qseqlen2_gqaratio16.co             # qseqlen=2
mla_a8w8_qh16_qseqlen2_gqaratio16_ps.co
mla_a8w8_qh16_qseqlen2_gqaratio16_ps_page.co     # with paging
mla_a8w8_qh16_qseqlen4_gqaratio16.co             # qseqlen=4
mla_a8w8_qh16_qseqlen4_gqaratio16_ps.co
mla_a8w8_qh16_qseqlen4_gqaratio16_ps_page.co
```

**A8W8 (quantized) - Variable query head:**
```
mla_a8w8_qh32_qseqlen4_gqaratio32_ps.co          # qh=32
mla_a8w8_qh64_qseqlen4_gqaratio16.co             # qh=64
mla_a8w8_qh64_qseqlen4_gqaratio16_ps.co
```

**A8W8 (quantized) - High-dimension:**
```
mla_a8w8_qh128_m32x4_n16x2_msk0.co               # qh=128, no mask
mla_a8w8_qh128_m32x4_n16x2_msk0_ps.co
mla_a8w8_qh128_m32x4_n16x2_msk1.co               # with mask
mla_a8w8_qh128_m32x4_n16x2_msk1_ps.co
```

#### High-dimensional prefill
```
mla_pfl_bf16_a16w16_causal_subQ128_mqa128.co     # subQ=128
mla_pfl_bf16_a16w16_causal_subQ16_mqa16.co       # subQ=16
mla_pfl_qh192_vh128_m32x8_n128x1_causal0.co      # qh=192, vh=128
mla_pfl_qh192_vh128_m32x8_n128x1_causal1.co
```

#### Legacy variants
```
MLA_A16W16_1TG_4W_32mx1_16nx1_Coex0_Msk1_QH16.co
MLA_A16W16_1TG_4W_64mx1_16nx1_Coex0_Msk1_QH16.co
```

### 2. Decode Kernels (KV Cache Single-Token)

```
mla_dec_stage1_bf16_a16w16_subQ128_mqa128.co     # subQ=128
mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co       # subQ=16
```

### 3. Configuration File

```
mla_asm.csv   # Performance tuning lookup table
```

### 4. Naming Convention Breakdown

Example: `mla_a8w8_qh16_qseqlen4_gqaratio16_ps_page.co`

| Component | Meaning |
|-----------|---------|
| `mla` | Multi-head Latent Attention |
| `a8w8` | Activation 8-bit, Weight 8-bit (FP8) |
| `qh16` | Query head dimension = 16 |
| `qseqlen4` | Query sequence length = 4 tokens |
| `gqaratio16` | GQA (Grouped Query Attention) ratio = 16 |
| `ps` | Persistent shader (register reuse variant) |
| `page` | Paging support (for memory efficiency) |

### Undocumented ASM APIs

```python
# Direct ASM dispatch (signature from build logs)
aiter.mla_decode_stage1_asm_fwd(
    Q: torch.Tensor,
    KV: torch.Tensor,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    kv_page_indices: torch.Tensor,
    kv_last_page_lens: torch.Tensor,
    num_kv_splits_indptr: Optional[torch.Tensor],
    work_meta_data: Optional[torch.Tensor],
    work_indptr: Optional[torch.Tensor],
    work_info_set: Optional[torch.Tensor],
    max_seqlen_q: int,
    page_size: int,
    nhead_kv: int,
    softmax_scale: float,
    splitData: torch.Tensor,
    splitLse: torch.Tensor,
    output: torch.Tensor,
    q_scale: Optional[torch.Tensor] = None,
    kv_scale: Optional[torch.Tensor] = None
) -> None

# Parallel attention persistent shader
aiter.pa_ps_fwd_asm(*args, **kwargs)

# MLA prefill ASM variants
aiter.mla_prefill_asm_fwd(*args, **kwargs)
aiter.mla_prefill_ps_asm_fwd(*args, **kwargs)

# Metadata generation
aiter.gen_pa_ps_fwd_asm(...)
aiter.get_mla_metadata_v1(
    seqlens_qo_indptr: torch.Tensor,
    seqlens_kv_indptr: torch.Tensor,
    ... (15+ parameters)
)
```

---

## FMHA v3 / Paged Attention APIs (40+ total)

### Flash Attention v3 Support

```python
aiter.fmha_v3_fwd(...)           # Forward pass
aiter.fmha_v3_bwd(...)           # Backward pass
aiter.fmha_v3_varlen_fwd(...)    # Variable length forward
aiter.fmha_v3_varlen_bwd(...)    # Variable length backward
aiter.can_impl_fmha_v3_bwd(...)  # Check backward implementation
```

### Paged Attention Variants (for KV Cache)

```python
aiter.paged_attention_v1(...)         # Standard version
aiter.paged_attention_v1_core(...)    # Core compute only
aiter.paged_attention_ragged(...)     # Irregular sequence layout
aiter.paged_attention_ragged_core(...)
aiter.paged_attention_rocm(...)       # ROCm optimized
aiter.paged_attention_rocm_core(...)
aiter.paged_attention_common(...)     # Generic version
```

### Sparse Decode Optimization

```python
aiter.top_k_per_row_decode(...)       # Top-K selection
aiter.top_k_per_row_decode_fast(...)  # Optimized variant
```

---

## TritonBLAS Integration

Available in `tritonblas` module:

```python
import tritonblas

# Standard matmul
tritonblas.matmul(A, B)

# Quantized variants
tritonblas.matmul_fp4(A_fp4, B_fp4)    # FP4 matmul
tritonblas.matmul_a8w8(A, B)           # A8W8 matmul
tritonblas.matmul_a8w8_lt(A, B)        # A8W8 with LT variant
tritonblas.matmul_lt(A, B)             # LT variant

# Kernel selection
selector = tritonblas.OrigamiMatmulSelector()
tritonblas.origami.remap(...)          # Origami remapping
```

---

## Performance Baseline (Current)

| Kernel | Our Time | Leader Time | Gap | Notes |
|--------|----------|-------------|-----|-------|
| GEMM (amd-mxfp4-mm) | 22.8 µs | 4.3 µs | 5.3x | Requires custom HIP kernel |
| MLA (amd-mixed-mla) | 69.7 µs | 33.0 µs | 2.1x | FMHA v3 available |
| MoE (amd-mixed-moe) | 154.2 µs | 109.8 µs | 1.4x | FP8 novs variant untested |

---

## Experimentation Strategy

### Phase 1: ASM API Parameter Testing
- Test each MLA kernel with actual sequence shapes
- Profile `pa_ps_fwd_asm` with K-Search parameters
- Measure overhead: kernel dispatch vs actual computation

### Phase 2: FP8 Variant Benchmarking
- Compare `novs` (no VS) vs standard FP8 MoE
- Quantify accuracy loss (acceptable if <0.5% relative)
- Profile speedup on full end-to-end task

### Phase 3: Load_inline Integration
- Wrap ASM APIs in custom HIP kernels
- Experiment with tile parameter mutations
- Test hybrid Python + HIP dispatch

### Phase 4: Advanced Optimizations
- K-Search over continuous parameter space
- Paged attention for variable sequence lengths
- Top-K sparse decode fusion with compute
