# Phase 2 MXFP4 Conversion Guide
# submission_custom_triton_v2.py → tl.dot_scaled

**Created:** 2026-03-20
**Source:** `kernels/moe-mxfp4/submission_custom_triton_v2.py`
**Skill:** `~/.claude/skills/amd-gfx950-tl-dot-scaled-constraints/SKILL.md`
**Spec:** `autoresearch/probes/custom_triton_moe_spec.md` §7, §9

---

## Executive Summary

Phase 1 dequantizes fp4x2 weights to bf16 once per call and uses plain `tl.dot`.
Phase 2 eliminates the dequantization step and replaces every `tl.dot` call with
`tl.dot_scaled("e2m1")`, passing fp4x2 weights and scales directly to the hardware.

There are exactly **two `tl.dot` call sites** to convert:
- Line 251: Stage 1 kernel — `acc = tl.dot(a, tl.trans(b), acc=acc, input_precision="ieee")`
- Line 401: Stage 2 kernel — `acc = tl.dot(a, tl.trans(b), acc=acc, input_precision="ieee")`

Both have identical structure but different scale sources.

---

## Pre-conditions: What Must Change in Python (Before Kernel Launch)

### Remove: dequantization (lines 504-510)

```python
# REMOVE ENTIRELY — these become dead code in Phase 2
w1_bf16 = _dequant_all_experts_bf16(gate_up_weight, gate_up_scale, E)  # line 504-506
w1_bf16 = w1_bf16.contiguous()                                          # line 506
w2_bf16 = _dequant_all_experts_bf16(down_weight, down_scale, E)         # line 508-509
w2_bf16 = w2_bf16.contiguous()                                          # line 510
```

Also remove `_dequant_fp4_weight_to_bf16` (lines 60-74) and `_dequant_all_experts_bf16`
(lines 77-88) entirely — unused in Phase 2.

### Add: uint8 views of all fp4/scale tensors (after line 493, before Step 3)

```python
# View fp4x2 weights as uint8 (MANDATORY — float4_e2m1fn_x2 KeyError blocker)
# w1 raw: [E, 2*d_expert_pad, d_hidden_pad//2] fp4x2 → uint8 same shape
w1_u8 = gate_up_weight.view(torch.uint8)
# w1 scale raw: [E, 2*d_expert_pad, scale_K] e8m0 → uint8 same shape
# scale_K = d_hidden_pad // 32
w1s_u8 = gate_up_scale.view(torch.uint8)

# w2 raw: [E, d_hidden_pad, d_expert_pad//2] fp4x2 → uint8 same shape
w2_u8 = down_weight.view(torch.uint8)
# w2 scale raw: [E, d_hidden_pad, scale_K2] e8m0 → uint8 same shape
# scale_K2 = d_expert_pad // 32
w2s_u8 = down_scale.view(torch.uint8)
```

### Add: activation quantization (Option B — before Stage 1 launch, ~line 530)

```python
# Pre-quantize activations bf16 → fp4x2 (Option B: external, simplest)
from aiter.ops.triton.quant import dynamic_mxfp4_quant

hs_cont = hidden_states.contiguous()
x_fp4, x_scale = dynamic_mxfp4_quant(hs_cont)
# x_fp4:   [M, d_hidden//2]  float4_e2m1fn_x2  (view as uint8)
# x_scale: [M, d_hidden//32] e8m0              (view as uint8)
x_u8  = x_fp4.view(torch.uint8)    # [M, d_hidden//2]
xs_u8 = x_scale.view(torch.uint8)  # [M, d_hidden//32]
```

### Add: intermediate re-quantization (between Stage 1 and Stage 2)

After SiLU+mul produces `inter_silu` (bf16), Stage 2 B input is fp4x2 but
Stage 2 A input is the intermediate — it must be quantized too:

```python
# Re-quantize intermediate after SiLU for Stage 2 A input
inter_fp4, inter_scale = dynamic_mxfp4_quant(inter_silu.contiguous())
inter_u8  = inter_fp4.view(torch.uint8)    # [M*top_k, d_expert_pad//2]
inters_u8 = inter_scale.view(torch.uint8)  # [M*top_k, d_expert_pad//32]
```

---

## Kernel Signature Changes

### Stage 1: `_moe_stage1_kernel`

**Remove** parameter:
- `w1_ptr` typed as bf16 `[E, 2*d_expert_pad, d_hidden_pad]`

**Add** parameters:
```python
w1_ptr,          # [E, 2*d_expert_pad, d_hidden_pad//2]  uint8 (fp4x2 packed)
w1s_ptr,         # [E, 2*d_expert_pad, scale_K]           uint8 (e8m0)
hs_u8_ptr,       # [M, d_hidden//2]                        uint8 (fp4x2 packed) — quantized activations
hs_scale_ptr,    # [M, d_hidden//32]                       uint8 (e8m0 scales)
# strides for scale tensors:
stride_hs_scale_m,   # hs_scale row stride (usually d_hidden//32)
stride_hs_scale_k,   # hs_scale col stride (usually 1)
stride_w1s_e,        # w1 scale expert stride
stride_w1s_n,        # w1 scale row stride (N dim)
stride_w1s_k,        # w1 scale col stride (K-scale dim)
# BLOCK_K interpretation changes:
# Phase 1: BLOCK_K = K elements in bf16
# Phase 2: BLOCK_K = K/2 packed bytes (uint8), minimum 64
```

Also add `SCALE_PER_BLOCK` as a derived constexpr at the top of the kernel:
```python
SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16
```

### Stage 2: `_moe_stage2_kernel`

**Remove**: `w2_ptr` bf16, `inter_ptr` bf16
**Add**:
```python
inter_ptr,       # [M*top_k, d_expert_pad//2]  uint8 (fp4x2 packed)
inters_ptr,      # [M*top_k, d_expert_pad//32] uint8 (e8m0 scales)
w2_ptr,          # [E, d_hidden_pad, d_expert_pad//2]  uint8 (fp4x2 packed)
w2s_ptr,         # [E, d_hidden_pad, scale_K2]          uint8 (e8m0)
stride_is_m,     stride_is_k,   # intermediate scale strides
stride_w2s_e,    stride_w2s_n,  stride_w2s_k,  # w2 scale strides
SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16,
```

---

## Line-by-Line Changes: Stage 1 Inner Loop

### Current (Phase 1) — lines 219-251

```python
for k_tile in range(k_iters):
    k_start = k_tile * BLOCK_K
    kk = k_start + k_offs             # [BLOCK_K] global K indices (bf16 cols)
    k_mask = kk < d_hidden

    # Load activation tile: [BLOCK_M, BLOCK_K] bf16
    a_offs = (
        orig_pos[:, None] * stride_hs_m
        + kk[None, :] * stride_hs_k
    )
    a_mask = sort_mask[:, None] & k_mask[None, :]
    a = tl.load(hs_ptr + a_offs, mask=a_mask, other=0.0).to(tl.bfloat16)

    # Load weight tile: [BLOCK_N, BLOCK_K] bf16
    n_global = n_start + n_offs
    n_mask = n_global < (2 * d_expert_pad)
    b_offs = (
        _e * stride_w1_e
        + n_global[:, None] * stride_w1_n
        + kk[None, :] * stride_w1_k
    )
    b_mask = n_mask[:, None] & k_mask[None, :]
    b = tl.load(w1_ptr + b_offs, mask=b_mask, other=0.0).to(tl.bfloat16)

    acc = tl.dot(a, tl.trans(b), acc=acc, input_precision="ieee")  # LINE 251
```

### Replacement (Phase 2) — full inner loop

```python
# d_hidden_half = d_hidden // 2  (packed uint8 columns in activation)
k_iters = tl.cdiv(d_hidden_half, BLOCK_K)  # BLOCK_K is now uint8 bytes

for k_tile in range(k_iters):
    k_start = k_tile * BLOCK_K
    kk = k_start + k_offs             # [BLOCK_K] packed-byte K indices

    # Bounds check against d_hidden_half (packed bytes), NOT d_hidden
    k_mask = kk < d_hidden_half

    # --- Load activation tile: [BLOCK_M, BLOCK_K] uint8 (fp4x2) ---
    # Gather rows using orig_pos (original token index, same as Phase 1)
    a_offs = (
        orig_pos[:, None] * stride_hs_m   # stride_hs_m = d_hidden//2 (uint8 row stride)
        + kk[None, :] * stride_hs_k       # stride_hs_k = 1
    )
    a_mask = sort_mask[:, None] & k_mask[None, :]
    a = tl.load(hs_u8_ptr + a_offs, mask=a_mask, other=0)  # uint8, no .to() needed

    # --- Load A scale: [BLOCK_M, SCALE_PER_BLOCK] uint8 ---
    # scale_K = d_hidden // 32; each scale covers 32 fp4 = 16 packed bytes
    scale_k_start = k_start // 16          # scale index for this k_tile
    offs_sk = scale_k_start + tl.arange(0, SCALE_PER_BLOCK)
    a_scale = tl.load(
        hs_scale_ptr
        + orig_pos[:, None] * stride_hs_scale_m
        + offs_sk[None, :] * stride_hs_scale_k,
        mask=sort_mask[:, None],
        other=0,
    )  # [BLOCK_M, SCALE_PER_BLOCK] uint8

    # --- Load weight tile: [BLOCK_K, BLOCK_N] uint8 (fp4x2, K-major) ---
    # w1 layout: [E, N=2*d_expert_pad, K_half=d_hidden_pad//2]
    # We need [BLOCK_K, BLOCK_N] for tl.dot_scaled, so load transposed:
    # Index as: w1[_e, n_global, kk] → then tl.dot_scaled treats it as [K, N]
    # (tl.dot_scaled computes A @ B where A=[M,K], B=[K,N] in uint8)
    n_global = n_start + n_offs       # [BLOCK_N]
    n_mask = n_global < (2 * d_expert_pad)

    b_offs = (
        _e * stride_w1_e
        + kk[:, None] * stride_w1_k           # K as outer dim (K-major for B)
        + n_global[None, :] * stride_w1_n     # N as inner dim
    )  # [BLOCK_K, BLOCK_N]
    b_mask = k_mask[:, None] & n_mask[None, :]
    b = tl.load(w1_ptr + b_offs, mask=b_mask, other=0)  # [BLOCK_K, BLOCK_N] uint8

    # --- Load B scale: [BLOCK_N, SCALE_PER_BLOCK] uint8 (N-FIRST, mandatory) ---
    # w1 scale layout: [E, N=2*d_expert_pad, scale_K=d_hidden_pad//32]
    # RHS scale must be [BLOCK_N, SCALE_PER_K] — keep N-first, NOT transposed
    b_scale = tl.load(
        w1s_ptr
        + _e * stride_w1s_e
        + n_global[:, None] * stride_w1s_n    # N is outer (N-first)
        + offs_sk[None, :] * stride_w1s_k,    # scale K is inner
        mask=n_mask[:, None],
        other=0,
    )  # [BLOCK_N, SCALE_PER_BLOCK] uint8

    # --- MXFP4 GEMM tile ---
    # tl.dot_scaled(A, A_scale, fmt, B, B_scale, fmt, acc=acc)
    # A: [BLOCK_M, BLOCK_K] uint8 — activations
    # B: [BLOCK_K, BLOCK_N] uint8 — weights (K-major)
    # Result: [BLOCK_M, BLOCK_N] fp32 accumulated
    acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)
```

### Key differences from Phase 1

| Aspect | Phase 1 (bf16) | Phase 2 (MXFP4) |
|--------|----------------|-----------------|
| `hs_ptr` type | bf16 (M, d_hidden) | uint8 (M, d_hidden//2) |
| `w1_ptr` type | bf16 (E, N, K) full | uint8 (E, N, K//2) packed |
| k-loop range | `d_hidden` cols | `d_hidden_half = d_hidden//2` bytes |
| k_mask bound | `< d_hidden` | `< d_hidden_half` |
| B load indexing | `[BLOCK_N, BLOCK_K]` then `tl.trans(b)` | `[BLOCK_K, BLOCK_N]` directly (K-major) |
| Scale loads | none | A_scale `[BLOCK_M, SCALE_PER_BLOCK]`, B_scale `[BLOCK_N, SCALE_PER_BLOCK]` |
| GEMM call | `tl.dot(a, tl.trans(b), ...)` | `tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)` |

**Note on B layout:** Phase 1 loads B as `[BLOCK_N, BLOCK_K]` and calls `tl.trans(b)`.
Phase 2 loads B directly as `[BLOCK_K, BLOCK_N]` (K outer, N inner) to avoid the transpose —
`tl.dot_scaled` expects `A=[M,K], B=[K,N]` in uint8 packed format.

---

## Line-by-Line Changes: Stage 2 Inner Loop

### Current (Phase 1) — lines 375-401

```python
for k_tile in range(k_iters):
    k_start = k_tile * BLOCK_K
    kk = k_start + k_offs
    k_mask = kk < d_expert_pad

    # Load intermediate tile: [BLOCK_M, BLOCK_K] bf16
    a_offs = (
        sort_idx[:, None] * stride_inter_m
        + kk[None, :] * stride_inter_k
    )
    a_mask = sort_mask[:, None] & k_mask[None, :]
    a = tl.load(inter_ptr + a_offs, mask=a_mask, other=0.0).to(tl.bfloat16)

    # Load down_weight tile: [BLOCK_N, BLOCK_K] bf16
    n_global = n_start + n_offs
    n_mask = n_global < d_hidden
    b_offs = (
        _e * stride_w2_e
        + n_global[:, None] * stride_w2_n
        + kk[None, :] * stride_w2_k
    )
    b_mask = n_mask[:, None] & k_mask[None, :]
    b = tl.load(w2_ptr + b_offs, mask=b_mask, other=0.0).to(tl.bfloat16)

    acc = tl.dot(a, tl.trans(b), acc=acc, input_precision="ieee")  # LINE 401
```

### Replacement (Phase 2)

```python
# d_expert_half = d_expert_pad // 2  (packed uint8 columns)
k_iters = tl.cdiv(d_expert_half, BLOCK_K)

for k_tile in range(k_iters):
    k_start = k_tile * BLOCK_K
    kk = k_start + k_offs
    k_mask = kk < d_expert_half    # packed-byte bound

    # --- Load intermediate tile: [BLOCK_M, BLOCK_K] uint8 ---
    # inter_ptr now points to uint8 (fp4x2) — already quantized before launch
    a_offs = (
        sort_idx[:, None] * stride_inter_m    # stride_inter_m = d_expert_pad//2
        + kk[None, :] * stride_inter_k        # stride_inter_k = 1
    )
    a_mask = sort_mask[:, None] & k_mask[None, :]
    a = tl.load(inter_ptr + a_offs, mask=a_mask, other=0)  # uint8

    # --- Load A scale: [BLOCK_M, SCALE_PER_BLOCK] uint8 ---
    scale_k_start = k_start // 16
    offs_sk = scale_k_start + tl.arange(0, SCALE_PER_BLOCK)
    a_scale = tl.load(
        inters_ptr                             # intermediate scale [M*top_k, d_expert_pad//32]
        + sort_idx[:, None] * stride_is_m
        + offs_sk[None, :] * stride_is_k,
        mask=sort_mask[:, None],
        other=0,
    )  # [BLOCK_M, SCALE_PER_BLOCK] uint8

    # --- Load down_weight tile: [BLOCK_K, BLOCK_N] uint8 (K-major) ---
    # w2 layout: [E, N=d_hidden_pad, K_half=d_expert_pad//2]
    n_global = n_start + n_offs
    n_mask = n_global < d_hidden

    b_offs = (
        _e * stride_w2_e
        + kk[:, None] * stride_w2_k           # K outer (K-major)
        + n_global[None, :] * stride_w2_n     # N inner
    )  # [BLOCK_K, BLOCK_N]
    b_mask = k_mask[:, None] & n_mask[None, :]
    b = tl.load(w2_ptr + b_offs, mask=b_mask, other=0)  # uint8

    # --- Load B scale: [BLOCK_N, SCALE_PER_BLOCK] uint8 (N-first) ---
    # w2 scale: [E, N=d_hidden_pad, scale_K2=d_expert_pad//32]
    b_scale = tl.load(
        w2s_ptr
        + _e * stride_w2s_e
        + n_global[:, None] * stride_w2s_n    # N outer (N-first, mandatory)
        + offs_sk[None, :] * stride_w2s_k,
        mask=n_mask[:, None],
        other=0,
    )  # [BLOCK_N, SCALE_PER_BLOCK] uint8

    acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)
```

---

## Scale Dimension Quick Reference

| Tensor | Shape | uint8 view shape | scale shape |
|--------|-------|-----------------|-------------|
| `gate_up_weight` (w1) | `[E, 2*d_expert_pad, d_hidden_pad//2]` fp4x2 | same, uint8 | `[E, 2*d_expert_pad, d_hidden_pad//32]` |
| `down_weight` (w2) | `[E, d_hidden_pad, d_expert_pad//2]` fp4x2 | same, uint8 | `[E, d_hidden_pad, d_expert_pad//32]` |
| `hidden_states` (A, Stage 1) | `[M, d_hidden]` bf16 → quant | `[M, d_hidden//2]` uint8 | `[M, d_hidden//32]` uint8 |
| `inter_silu` (A, Stage 2) | `[M*top_k, d_expert_pad]` bf16 → quant | `[M*top_k, d_expert_pad//2]` uint8 | `[M*top_k, d_expert_pad//32]` uint8 |

`SCALE_PER_BLOCK = BLOCK_K // 16` (since each scale covers 32 fp4 = 16 uint8 bytes)

For `BLOCK_K = 64`: `SCALE_PER_BLOCK = 4`
For `BLOCK_K = 128`: `SCALE_PER_BLOCK = 8`

---

## Autotune Config Adjustments (spec §9)

Phase 1 hard-coded:
```python
BLOCK_M = 32
BLOCK_N = 64
BLOCK_K = 64
num_warps = 4
num_stages = 2
```

Phase 2 should add `@triton.autotune`:
```python
@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk},
                      num_warps=nw, num_stages=ns)
        for bm in [16, 32, 64, 128]    # 16 is minimum (gfx950 BLOCK_M constraint)
        for bn in [64, 128, 256]
        for bk in [64, 128]            # 64 is minimum (gfx950 BLOCK_K constraint)
        for nw in [4, 8]
        for ns in [2, 3, 4]
    ],
    key=["M", "E", "d_hidden", "d_expert_pad"],
)
```

**Important**: The autotune `key` should include `"M"` because token count changes with batch size,
and `"E"` because expert count changes between 33-expert and 257-expert benchmark shapes.

---

## Known Pitfalls (from constraints skill)

### 1. float4_e2m1fn_x2 KeyError — MANDATORY workaround
Never pass a tensor with dtype `torch.float4_e2m1fn_x2` directly to any Triton kernel.
Always `.view(torch.uint8)` first. This is a permanent Triton JIT registration gap on Popcorn CLI.

### 2. BLOCK_M minimum: 16
Silent wrong results (no error) if BLOCK_M < 16. Use `max(16, ...)` in all configs.
The smallest benchmark shape has `bs=16, top_k=9` → 144 tokens / 257 experts = very small
per-expert tile → BLOCK_M=16 is real, not hypothetical.

### 3. BLOCK_K minimum: 64 (uint8 packed bytes)
GPU assertion `inputVals.size() % 4 == 0` fires if BLOCK_K < 64. Do not put BLOCK_K=32 in autotune.

### 4. B scale must be N-first
Even though B data is loaded `[BLOCK_K, BLOCK_N]` (K-major), the B scale must remain
`[BLOCK_N, SCALE_PER_BLOCK]` (N outer). Loading it as `[SCALE_PER_BLOCK, BLOCK_N]`
causes: `rhs_scale must be a tensor of shape [N, X]. Got ['X', 'N']`

### 5. A scale per-tile, not full K dimension
Load only `SCALE_PER_BLOCK` entries per k_tile for both A and B scales.
Loading the full scale row causes: `lhs_scale must be tensor of shape [M, X]. Got ['M', 'full_K//16']`

### 6. tl.arange requires power-of-2 range
`SCALE_PER_BLOCK = BLOCK_K // 16`. For BLOCK_K=64, SCALE_PER_BLOCK=4 (power of 2 — OK).
For BLOCK_K=128, SCALE_PER_BLOCK=8 (OK). Both are safe. Do not use BLOCK_K values that
produce non-power-of-2 SCALE_PER_BLOCK (e.g. BLOCK_K=96 → SCALE_PER_BLOCK=6 → crash).

### 7. stride semantics change for uint8 views
Phase 1 strides are in bf16 elements. Phase 2 strides are in uint8 bytes.
For packed fp4x2: `stride_w1_k` becomes `1` (uint8), `stride_w1_n` becomes `d_hidden_pad//2`.
Recalculate all strides from the uint8-viewed tensor (`.stride(0)`, `.stride(1)`, etc.).

### 8. XCD remapping — avoid cdiv (spec §8.1)
Do not add XCD remapping using `tl.cdiv(num_chunks, NUM_XCDS)` — non-bijective bug.
Use group-M swizzle (spec §8.2) instead if XCD locality is needed.

### 9. Inter-stage dtype
After `tl.dot_scaled` in Stage 1, `acc` is `float32`. Store to intermediate as `bfloat16`
(same as Phase 1: `acc.to(tl.bfloat16)`). Then `dynamic_mxfp4_quant` re-quantizes the
`bfloat16` intermediate back to fp4 for Stage 2 A input.

---

## Conversion Checklist

- [ ] Remove `_dequant_fp4_weight_to_bf16` and `_dequant_all_experts_bf16` functions
- [ ] Add `from aiter.ops.triton.quant import dynamic_mxfp4_quant` import
- [ ] Add `.view(torch.uint8)` for `w1`, `w1s`, `w2`, `w2s` before Stage 1 launch
- [ ] Add `dynamic_mxfp4_quant(hidden_states)` → `x_u8`, `xs_u8` before Stage 1 launch
- [ ] Add `dynamic_mxfp4_quant(inter_silu)` → `inter_u8`, `inters_u8` before Stage 2 launch
- [ ] Stage 1 kernel: add `w1s_ptr`, `hs_u8_ptr`, `hs_scale_ptr` and their strides to signature
- [ ] Stage 2 kernel: add `w2s_ptr`, `inters_ptr` and their strides to signature
- [ ] Both kernels: add `SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16` at top
- [ ] Stage 1: change k_iters bound to `d_hidden_half` (not `d_hidden`)
- [ ] Stage 1: change k_mask bound to `< d_hidden_half`
- [ ] Stage 1: change A load from `hs_ptr` bf16 gather to `hs_u8_ptr` uint8 gather
- [ ] Stage 1: add A_scale load `[BLOCK_M, SCALE_PER_BLOCK]` using `offs_sk`
- [ ] Stage 1: change B load from `[BLOCK_N, BLOCK_K]` to `[BLOCK_K, BLOCK_N]` (K-major)
- [ ] Stage 1: add B_scale load `[BLOCK_N, SCALE_PER_BLOCK]` (N-first)
- [ ] Stage 1: replace `tl.dot(a, tl.trans(b), acc=acc, input_precision="ieee")` with `tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)`
- [ ] Stage 2: repeat all the above for the Stage 2 inner loop (d_expert_half, inter_u8, w2_u8)
- [ ] Add `@triton.autotune` decorator with configs from §9, min BLOCK_M=16, min BLOCK_K=64
- [ ] Verify all stride arguments are recomputed from uint8 tensors (not bf16)
- [ ] Keep `tl.atomic_add` in Stage 2 — unchanged from Phase 1
- [ ] Keep token sorting logic unchanged — Python-side sorting is format-agnostic
