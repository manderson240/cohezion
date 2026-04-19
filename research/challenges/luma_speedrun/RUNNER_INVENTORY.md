# Popcorn Runner Kernel Inventory Discovery

## Probe 1: .co Kernel Inventory (SUCCESSFUL)

Submission: `submission_probe_co_inventory.py` on `amd-mxfp4-mm` leaderboard
Status: **PASSED 4/4 tests** (100% correct)
Execution time: ~265 seconds total

### GEMM Kernels (f4gemm) - 36 files

**Location**: `/home/runner/aiter/hsa/gfx950/f4gemm/`

Available tile sizes (M x N patterns):
- **32x** tiles: 32x128, 32x256, 32x384, 32x512, 32x640, 32x768, 32x896, 32x1024
- **64x** tiles: 64x128, 64x256, 64x384, 64x512, 64x640, 64x768, 64x896, 64x1024
- **128x** tiles: 128x128, 128x256, 128x384, 128x512
- **160x** tiles: 160x128, 160x256, 160x384
- **192x** tiles: 192x128, 192x256
- **224x** tiles: 224x128, 224x256
- **256x** tiles: 256x128, 256x256

Format: `f4gemm_bf16_per1x32Fp4_BpreShuffle_{M}x{N}.co`

**Total: 35 .co kernels + 1 CSV config**

Key insight: `BpreShuffle` is in the filename - this is pre-shuffled weight format.

### MoE Kernels (fmoe) - 4 files

**Location**: `/home/runner/aiter/hsa/gfx950/fmoe/`

```
fmoe_fp8_blockscale_g1u1_novs_subGU_256.co
fmoe_fp8_blockscale_g1u1_subGU_256.co
gelu  (activation kernel)
silu  (activation kernel)
```

**Observations:**
- Two FP8 blockscale kernels with different gate configurations (`novs` vs standard)
- Both use subGU (sub-gate-unit) with 256 parameter
- g1u1 = 1 group, 1 unit config
- Separate activation kernels available

### MLA/Attention Kernels - 28 files

**Location**: `/home/runner/aiter/hsa/gfx950/mla/`

#### Prefill kernels (main):
```
mla_a16w16_qh16_m16x4_n16x1_coex0_mask1.co
mla_a16w16_qh16_m16x4_n16x1_coex0_mask1_ps.co
mla_a16w16_qh16_m32x4_n16x1_coex0_mask1.co
mla_a16w8_qh16_m16x4_n16x1_coex0_mask1_ps.co
mla_a8w8_qh128_m32x4_n16x2_msk0.co
mla_a8w8_qh128_m32x4_n16x2_msk0_ps.co
mla_a8w8_qh128_m32x4_n16x2_msk1.co
mla_a8w8_qh128_m32x4_n16x2_msk1_ps.co
mla_a8w8_qh16_qseqlen1_gqaratio16.co
mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co
mla_a8w8_qh16_qseqlen2_gqaratio16.co
mla_a8w8_qh16_qseqlen2_gqaratio16_ps.co
mla_a8w8_qh16_qseqlen2_gqaratio16_ps_page.co
mla_a8w8_qh16_qseqlen4_gqaratio16.co
mla_a8w8_qh16_qseqlen4_gqaratio16_ps.co
mla_a8w8_qh16_qseqlen4_gqaratio16_ps_page.co
mla_a8w8_qh32_qseqlen4_gqaratio32_ps.co
mla_a8w8_qh64_qseqlen4_gqaratio16.co
mla_a8w8_qh64_qseqlen4_gqaratio16_ps.co
```

#### Decode kernels:
```
mla_dec_stage1_bf16_a16w16_subQ128_mqa128.co
mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co
```

#### High-dim prefill:
```
mla_pfl_bf16_a16w16_causal_subQ128_mqa128.co
mla_pfl_bf16_a16w16_causal_subQ16_mqa16.co
mla_pfl_qh192_vh128_m32x8_n128x1_causal0.co
mla_pfl_qh192_vh128_m32x8_n128x1_causal1.co
```

#### Legacy variants:
```
MLA_A16W16_1TG_4W_32mx1_16nx1_Coex0_Msk1_QH16.co
MLA_A16W16_1TG_4W_64mx1_16nx1_Coex0_Msk1_QH16.co
```

#### Config:
```
mla_asm.csv
```

**Key observations:**
- `_ps` suffix = persistent shader variant (register reuse)
- `_page` suffix = paging variant for memory efficiency
- qh16/qh32/qh64 = query head dimensions (16, 32, 64)
- qseqlen1/2/4 = query sequence length variants
- gqaratio16/32 = GQA (Grouped Query Attention) ratio
- coex0/coex1 = coexistence flags
- msk0/msk1 = mask variants (no mask vs with mask)
- subQ128/subQ16 = subquery group sizes
- mqa128/mqa16 = MQA (Multi-Query Attention) sizes

---

## Triton/BLAS Support

**tritonblas module available** - provides:
- `matmul()` - standard matmul
- `matmul_fp4()` - FP4 quantized matmul
- `matmul_a8w8()` - A8W8 quantized matmul
- `matmul_a8w8_lt()` - A8W8 with LT (Low-Threshold) variant
- `matmul_lt()` - LT variant
- `OrigamiMatmulSelector` - kernel selection logic
- `origami` - origami remapping

---

## aiter API Inventory

### MoE APIs (25 functions)

```
ck_moe_stage1
ck_moe_stage1_fwd
ck_moe_stage2
ck_moe_stage2_fwd
cmdGenFunc_ck_moe_stage
cmdGenFunc_ck_moe_stage2
fmoe
fmoe_fp8_blockscale_g1u1
fmoe_g1u1
fmoe_g1u1_a16
fmoe_g1u1_tkw1
fmoe_int8_g1u0
fmoe_int8_g1u0_a16
gen_moe_fused_gate_fake_tensor
get_moe_stage_module
moe_align_block_size
moe_cktile2stages_gemm1
moe_cktile2stages_gemm1_ck
moe_cktile2stages_gemm2
moe_cktile2stages_gemm2_ck
moe_fused_gate
moe_smoothquant_fwd
moe_sorting_fwd
moe_sorting_opus_fwd
moe_stage1_g1u1
moe_sum
```

### MLA/Attention APIs (21 functions)

```
concat_and_cache_mla
fused_qk_rope_concat_and_cache_mla
gen_pa_fwd_asm
gen_pa_fwd_native_fake
gen_pa_ps_fwd_asm
get_mla_metadata_info_v1
get_mla_metadata_v1
get_mla_metadata_v1_no_redundant
get_pa_metadata_info_v1
get_pa_metadata_v1
mla
mla_decode_stage1_asm_fwd         <-- UNDOCUMENTED ASM API
mla_prefill_asm_fwd               <-- UNDOCUMENTED ASM API
mla_prefill_ps_asm_fwd            <-- UNDOCUMENTED ASM API
mla_reduce_v1
pa_decode_gluon
pa_fwd_asm                        <-- UNDOCUMENTED ASM API
pa_fwd_naive
pa_persistent_fwd
pa_ps_fwd_asm                     <-- UNDOCUMENTED ASM API
pa_reduce_v1
```

**Critical discovery**: Four **undocumented ASM APIs** are available:
1. `mla_decode_stage1_asm_fwd` - MLA decode stage 1 with direct ASM dispatch
2. `mla_prefill_asm_fwd` - MLA prefill with direct ASM dispatch
3. `mla_prefill_ps_asm_fwd` - MLA prefill persistent shader variant
4. `pa_ps_fwd_asm` - Parallel attention persistent shader variant

These APIs bypass the CK-tile abstraction and provide direct kernel selection.

---

## Probe 2: MLA Undocumented APIs

**Status**: PASSED 4/4 tests (100% correct)
Execution time: ~360 seconds total

### NEW Discovered APIs (undocumented, signature available)

```python
pa_ps_fwd_asm(*args, **kwargs)         # Parallel attention persistent shader ASM variant
fmha_v3_varlen_fwd(*args, **kwargs)    # FMHA v3 variable length forward
mla_decode_stage1_asm_fwd(*args, **kwargs)  # MLA decode stage 1 ASM
```

### Complete MLA API Inventory (40+ functions)

**Backward compatible V3 variants:**
```
fmha_v3_fwd            # FMHA v3 forward
fmha_v3_bwd            # FMHA v3 backward
fmha_v3_varlen_fwd     # FMHA v3 variable length forward
fmha_v3_varlen_bwd     # FMHA v3 variable length backward
can_impl_fmha_v3_bwd   # Check if backward is implemented
gen_fmha_v3_fwd_fake_tensors
gen_fmha_v3_bwd_fake_tensors
gen_fmha_v3_varlen_fwd_fake_tensor
gen_fmha_v3_varlen_bwd_fake_tensor
```

**Paged attention variants (for KV cache):**
```
paged_attention_common
paged_attention_ragged
paged_attention_ragged_core
paged_attention_rocm
paged_attention_rocm_core
paged_attention_v1
paged_attention_v1_core
top_k_per_row_decode
top_k_per_row_decode_fast
```

**Original MLA APIs (from Probe 1):**
```
concat_and_cache_mla
fused_qk_rope_concat_and_cache_mla
gen_pa_fwd_asm
gen_pa_fwd_native_fake
gen_pa_ps_fwd_asm
get_mla_metadata_info_v1
get_mla_metadata_v1
get_mla_metadata_v1_no_redundant
get_pa_metadata_info_v1
get_pa_metadata_v1
mla
mla_decode_stage1_asm_fwd
mla_prefill_asm_fwd
mla_prefill_ps_asm_fwd
mla_reduce_v1
pa_decode_gluon
pa_fwd_asm
pa_fwd_naive
pa_persistent_fwd
pa_ps_fwd_asm
pa_reduce_v1
```

### Type Hints Extracted (from build logs)

```python
# mla_decode_stage1_asm_fwd signature (extracted from stderr):
def mla_decode_stage1_asm_fwd(
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

# get_mla_metadata_v1 signature (partial, extracted):
def get_mla_metadata_v1(
    seqlens_qo_indptr: torch.Tensor,
    seqlens_kv_indptr: torch.Tensor,
    kv_last_page_lens: torch.Tensor,
    num_heads_per_head_k: int,
    num_heads_k: int,
    is_causal: bool,
    work_metadata_ptrs: torch.Tensor,
    work_info_set: torch.Tensor,
    work_indptr: torch.Tensor,
    reduce_indptr: torch.Tensor,
    reduce_final_map: torch.Tensor,
    reduce_partial_map: torch.Tensor,
    page_size: int = 1,
    kv_granularity: int = 16,
    max_seqlen_qo: int = -1,
    uni_seqlen_qo: int = -1,
    fast_mode: bool = True,
    topk: int = -1,
    max_split_per_batch: int = -1,
    intra_batch_mode: bool = False,
    dtype_q: Optional[torch.dtype] = None,
    dtype_kv: Optional[torch.dtype] = None
) -> None
```

### Test Results

All 4 tests passed:
```
✅ seed: 5412; qseqlen: 1; kvseqlen: 1024; batchsize: 32
> Maximum error: 0.0185546875
✅ seed: 1360; qseqlen: 1; kvseqlen: 8192; batchsize: 64
> Maximum error: 0.0107421875
✅ seed: 9826; qseqlen: 1; kvseqlen: 8192; batchsize: 256
> Maximum error: 0.0107421875
```

### Key Discoveries from Probe 2

1. **FMHA v3 backward pass available** - Both forward and backward implemented
2. **Variable length sequences** - `fmha_v3_varlen_fwd` and `_bwd` for variable length
3. **Paged attention for KV cache** - Nine variants of paged attention for memory efficiency
4. **Top-K decode optimization** - `top_k_per_row_decode` and `top_k_per_row_decode_fast` for sparse decode
5. **Ragged tensor support** - `paged_attention_ragged` for irregular sequence layouts
6. **Generalized PA metadata** - Generic `get_pa_metadata_v1` with extensive options

The presence of FMHA v3 variants suggests recent compatibility with newer Flash Attention versions.

---

## Key Strategic Findings

### 1. Tile Size Coverage (GEMM)
The runner has 35 pre-compiled GEMM tiles covering:
- Width: 128-1024 (8 increments: 128, 256, 384, 512, 640, 768, 896, 1024)
- Height: 32-256 (5 values: 32, 64, 128, 160, 192, 224, 256)
- **Total: 35 different tile configurations**

This is much broader than tuning alone. The ranking gap (5.3x) cannot be closed by choosing different tiles - leaders must be using **custom load_inline kernels**.

### 2. ASM API Bypass Available
Four undocumented `_asm_fwd` functions allow direct kernel dispatch:
- `pa_ps_fwd_asm()` - For parallel attention prefill
- `mla_prefill_ps_asm_fwd()` - For MLA prefill
- `mla_decode_stage1_asm_fwd()` - For MLA decode

These may accept custom kernel parameters or support `load_inline` dispatch that the high-level APIs don't expose.

### 3. Activation Kernels Separate
MoE has standalone `gelu` and `silu` activation .co files. These can be tuned independently or fused via `load_inline`.

### 4. FP8 MoE Variants
Two FP8 blockscale kernels:
- `novs` (no VS = no vertical scaling): lighter weight
- Standard (with VS): higher precision

The `novs` variant may be faster at cost of accuracy - worth benchmarking.

### 5. Triton Direct Access
`tritonblas.matmul_fp4()` is exposed but slower than ASM. However, it's a baseline for load_inline experimentation.

---

## Next Steps

1. **Test Probe 2 after rate limit expires** (~50s from 18:52) - Focus on signature analysis of undocumented APIs
2. **Query ASM API signatures** - Use `inspect.signature()` on `pa_ps_fwd_asm`, `mla_prefill_ps_asm_fwd`
3. **Test load_inline dispatch** - Write custom HIP kernel that calls undocumented ASM APIs with K-Search parameters
4. **Profile FP8 novs variant** - Benchmark `fmoe_fp8_blockscale_g1u1_novs_subGU_256.co` vs standard
5. **Experiment with persistent shader variants** - All MLA kernels have `_ps` versions; test performance delta

---

## Files Created
- Probe 1 submission: `/home/mike-anderson/dev/cohezion/luma_speedrun/amd-mxfp4-mm/submission_probe_co_inventory.py`
- Probe 2 submission: `/home/mike-anderson/dev/cohezion/luma_speedrun/amd-mixed-mla/submission_probe_mla_apis.py`
- This inventory: `/home/mike-anderson/dev/cohezion/luma_speedrun/RUNNER_INVENTORY.md`
