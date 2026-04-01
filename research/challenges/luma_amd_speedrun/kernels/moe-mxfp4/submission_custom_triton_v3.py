"""
Custom Triton MoE Kernel — Phase 2: MXFP4 GEMM with tl.dot_scaled
==================================================================
Phase 2 goals (§9 of spec):
  1. Eliminate fp4x2 → bf16 dequantization (removed _dequant_* functions)
  2. Quantize activations bf16 → fp4x2 via dynamic_mxfp4_quant (Option B)
  3. Stage 1 Triton kernel: tl.dot_scaled("e2m1") with uint8 fp4x2 + e8m0 scales
  4. Re-quantize inter_silu bf16 → fp4x2 before Stage 2
  5. Stage 2 Triton kernel: tl.dot_scaled("e2m1"), atomic_add output
  6. @triton.autotune on both kernels (BLOCK_M >= 16, BLOCK_K >= 64)
  7. Fallback to aiter fused_moe via USE_CUSTOM_TRITON=0 env var

Key changes from Phase 1 (v2):
  - Removed: _dequant_fp4_weight_to_bf16, _dequant_all_experts_bf16
  - Added: dynamic_mxfp4_quant for activation and intermediate quantization
  - Added: .view(torch.uint8) for all fp4x2 / e8m0 tensors (float4_e2m1fn_x2 KeyError fix)
  - Changed: tl.dot(...) → tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)
  - Changed: BLOCK_K now counts uint8 packed bytes (d_hidden//2 columns, not d_hidden)
  - Changed: B load is [BLOCK_K, BLOCK_N] K-major (no tl.trans needed)
  - Changed: B scale is [BLOCK_N, SCALE_PER_BLOCK] N-first (mandatory per spec)
  - Added: SCALE_PER_BLOCK = BLOCK_K // 16 constexpr in both kernels
  - Added: @triton.autotune with gfx950-safe configs

CRITICAL constraints (§7, §10):
  - BLOCK_M >= 16 (silent wrong results on gfx950 otherwise)
  - BLOCK_K >= 64 uint8 bytes (GPU assertion inputVals.size() % 4 == 0)
  - tl.atomic_add in Stage 2 for multi-expert output accumulation
  - No XCD remapping with cdiv (non-bijective bug §8.1)
  - float4_e2m1fn_x2 tensors MUST be .view(torch.uint8) before passing to Triton
  - B scale shape must be [BLOCK_N, SCALE_PER_BLOCK], NOT [SCALE_PER_BLOCK, BLOCK_N]
"""

import os
import sys


# aiter JIT module path fix for runner environments
_AITER_JIT_BUILD = "/home/runner/aiter/aiter/jit/build"
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ["AITER_USE_NT"] = "1"

import torch
import torch.nn.functional as F
import triton
import triton.language as tl
from aiter import ActivationType as at
from aiter import QuantType as qt
from aiter.fused_moe import fused_moe as fm
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


# ---------------------------------------------------------------------------
# Toggle: set USE_CUSTOM_TRITON=0 in environment to fall back to aiter
# ---------------------------------------------------------------------------
USE_CUSTOM_TRITON = os.environ.get("USE_CUSTOM_TRITON", "1") != "0"

MXFP4_BLOCK_SIZE = 32


# ---------------------------------------------------------------------------
# Stage 1 Triton kernel — MXFP4 GEMM (Phase 2)
#   Inputs  : hs_u8_ptr   [M, d_hidden//2]           uint8 (fp4x2 packed activations)
#             hs_scale_ptr [M, d_hidden//32]          uint8 (e8m0 activation scales)
#             w1_ptr      [E, 2*d_expert_pad, d_hidden_pad//2]  uint8 (fp4x2 weights)
#             w1s_ptr     [E, 2*d_expert_pad, d_hidden_pad//32] uint8 (e8m0 weight scales)
#             sorted_token_pos [M*top_k] int32
#             expert_offsets   [E+1]     int32
#   Output  : intermediate [M*top_k, 2*d_expert_pad] bf16
#             (gate half [:, :d_expert_pad], up half [:, d_expert_pad:])
#
# Persistent-tile loop: each SM claims tiles (expert_id, tile_m, tile_n)
# round-robin until all tiles are processed.
# BLOCK_K now counts uint8 packed bytes (each byte holds 2 fp4 values).
# ---------------------------------------------------------------------------
@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk},
                      num_warps=nw, num_stages=ns)
        for bm in [16, 32, 64, 128]    # 16 is minimum (gfx950 BLOCK_M constraint)
        for bn in [64, 128, 256]
        for bk in [64, 128]            # 64 is minimum (gfx950 BLOCK_K uint8 constraint)
        for nw in [4, 8]
        for ns in [2, 3, 4]
    ],
    key=["M", "E", "d_hidden", "d_expert_pad"],
)
@triton.jit
def _moe_stage1_kernel(
    # --- input pointers ---
    hs_u8_ptr,        # [M, d_hidden//2]                        uint8 (fp4x2 packed)
    hs_scale_ptr,     # [M, d_hidden//32]                       uint8 (e8m0)
    w1_ptr,           # [E, 2*d_expert_pad, d_hidden_pad//2]    uint8 (fp4x2 packed)
    w1s_ptr,          # [E, 2*d_expert_pad, d_hidden_pad//32]   uint8 (e8m0)
    sorted_pos_ptr,   # [M*top_k]  int32  — original token index per sorted slot
    expert_off_ptr,   # [E+1]  int32  — start offset per expert in sorted arrays
    # --- output pointer ---
    out_ptr,          # [M*top_k, 2*d_expert_pad]  bf16
    # --- scalars ---
    M,                # number of tokens
    E,                # number of experts
    d_hidden,         # hidden dimension (actual, not padded) — bf16 elements
    d_hidden_half,    # d_hidden // 2 — packed uint8 columns for activations
    d_hidden_pad,     # hidden dimension padded
    d_expert_pad,     # expert intermediate dim padded (half of gate_up N axis)
    total_sorted,     # M * top_k
    # --- strides (all in uint8 element units for u8 tensors) ---
    stride_hs_m,      # hs_u8 row stride (= d_hidden//2)
    stride_hs_k,      # hs_u8 col stride (= 1)
    stride_hss_m,     # hs_scale row stride (= d_hidden//32)
    stride_hss_k,     # hs_scale col stride (= 1)
    stride_w1_e,      # w1_u8 expert stride (= 2*d_expert_pad * d_hidden_pad//2)
    stride_w1_n,      # w1_u8 row stride (= d_hidden_pad//2)
    stride_w1_k,      # w1_u8 col stride (= 1)
    stride_w1s_e,     # w1s_u8 expert stride
    stride_w1s_n,     # w1s_u8 row stride
    stride_w1s_k,     # w1s_u8 col stride (= 1)
    stride_out_m,     # output row stride
    stride_out_n,     # output col stride (= 1)
    # --- tile sizes (compile-time constants) ---
    BLOCK_M: tl.constexpr,   # >= 16 (gfx950 minimum)
    BLOCK_N: tl.constexpr,   # output tile rows (along 2*d_expert_pad axis)
    BLOCK_K: tl.constexpr,   # K reduction tile in uint8 packed bytes (>= 64)
):
    """
    Persistent MoE Stage 1: gather tokens per expert, MXFP4 GEMM via tl.dot_scaled.

    BLOCK_K is in uint8 bytes (packed fp4x2): each byte holds 2 fp4 values.
    SCALE_PER_BLOCK = BLOCK_K // 16 (each e8m0 scale covers 32 fp4 = 16 uint8 bytes).

    Each program (SM) iterates over a global flat tile index in strides of num_sms.
    """
    # SCALE_PER_BLOCK: how many e8m0 scale entries are loaded per k_tile
    # Each scale covers 32 fp4 elements = 16 packed uint8 bytes
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16

    sm_id = tl.program_id(0)
    num_sms = tl.num_programs(0)

    num_tiles_n = tl.cdiv(2 * d_expert_pad, BLOCK_N)

    tile_id = sm_id

    while True:
        expert_tile_start = 0
        found = False

        for _e in range(512):  # compile-time loop bound (harmless extra iters exit early)
            if _e >= E:
                break
            e_start = tl.load(expert_off_ptr + _e).to(tl.int32)
            e_end   = tl.load(expert_off_ptr + _e + 1).to(tl.int32)
            count_e = e_end - e_start
            num_tiles_m_e = tl.cdiv(count_e, BLOCK_M)
            tiles_for_e = num_tiles_m_e * num_tiles_n

            if tile_id < expert_tile_start + tiles_for_e:
                # This expert owns the tile
                local_tile = tile_id - expert_tile_start
                tile_m = local_tile // num_tiles_n
                tile_n = local_tile % num_tiles_n

                # Token range for this M-tile within expert _e
                token_start = e_start + tile_m * BLOCK_M
                token_end_clamped = tl.minimum(token_start + BLOCK_M, e_end)
                m_size = token_end_clamped - token_start

                # N range for this N-tile (into 2*d_expert_pad axis)
                n_start = tile_n * BLOCK_N

                # Build offset arrays
                m_offs = tl.arange(0, BLOCK_M)       # [BLOCK_M]
                n_offs = tl.arange(0, BLOCK_N)        # [BLOCK_N]
                k_offs = tl.arange(0, BLOCK_K)        # [BLOCK_K] — uint8 byte indices

                # --- Gather token indices ---
                sort_idx = token_start + m_offs       # [BLOCK_M] positions in sorted_pos
                sort_mask = m_offs < m_size

                # Load original token positions (int32) for each row in this tile
                orig_pos = tl.load(sorted_pos_ptr + sort_idx, mask=sort_mask, other=0)
                # orig_pos : [BLOCK_M]  int32

                # --- Accumulate GEMM over K in BLOCK_K chunks (uint8 bytes) ---
                acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

                # N range (shared across k_tiles)
                n_global = n_start + n_offs       # [BLOCK_N]
                n_mask = n_global < (2 * d_expert_pad)

                k_iters = tl.cdiv(d_hidden_half, BLOCK_K)
                for k_tile in range(k_iters):
                    k_start = k_tile * BLOCK_K
                    kk = k_start + k_offs             # [BLOCK_K] packed-byte K indices
                    k_mask = kk < d_hidden_half       # bound in uint8 bytes, NOT d_hidden

                    # --- Load activation tile: [BLOCK_M, BLOCK_K] uint8 (fp4x2) ---
                    # Gather rows using orig_pos (original token index)
                    a_offs = (
                        orig_pos[:, None] * stride_hs_m   # uint8 row stride = d_hidden//2
                        + kk[None, :] * stride_hs_k       # col stride = 1
                    )  # [BLOCK_M, BLOCK_K]
                    a_mask = sort_mask[:, None] & k_mask[None, :]
                    a = tl.load(hs_u8_ptr + a_offs, mask=a_mask, other=0)  # uint8

                    # --- Load A scale: [BLOCK_M, SCALE_PER_BLOCK] uint8 ---
                    # Each e8m0 scale covers 32 fp4 elements = 16 packed uint8 bytes
                    scale_k_start = k_start // 16          # scale index for this k_tile
                    offs_sk = scale_k_start + tl.arange(0, SCALE_PER_BLOCK)
                    a_scale = tl.load(
                        hs_scale_ptr
                        + orig_pos[:, None] * stride_hss_m
                        + offs_sk[None, :] * stride_hss_k,
                        mask=sort_mask[:, None],
                        other=0,
                    )  # [BLOCK_M, SCALE_PER_BLOCK] uint8

                    # --- Load weight tile: [BLOCK_K, BLOCK_N] uint8 (K-major) ---
                    # w1 layout: [E, N=2*d_expert_pad, K_half=d_hidden_pad//2]
                    # Load as [BLOCK_K, BLOCK_N] (K outer, N inner) — no tl.trans needed
                    # tl.dot_scaled expects A=[M,K], B=[K,N]
                    b_offs = (
                        _e * stride_w1_e
                        + kk[:, None] * stride_w1_k        # K as outer dim (K-major)
                        + n_global[None, :] * stride_w1_n  # N as inner dim
                    )  # [BLOCK_K, BLOCK_N]
                    b_mask = k_mask[:, None] & n_mask[None, :]
                    b = tl.load(w1_ptr + b_offs, mask=b_mask, other=0)  # [BLOCK_K, BLOCK_N] uint8

                    # --- Load B scale: [BLOCK_N, SCALE_PER_BLOCK] uint8 (N-FIRST, mandatory) ---
                    # w1 scale layout: [E, N=2*d_expert_pad, scale_K=d_hidden_pad//32]
                    # B scale MUST be [BLOCK_N, SCALE_PER_BLOCK] — N is outer, not scale_K
                    # (loading transposed causes: "rhs_scale must be [N, X]. Got ['X', 'N']")
                    b_scale = tl.load(
                        w1s_ptr
                        + _e * stride_w1s_e
                        + n_global[:, None] * stride_w1s_n    # N outer (N-first)
                        + offs_sk[None, :] * stride_w1s_k,    # scale K inner
                        mask=n_mask[:, None],
                        other=0,
                    )  # [BLOCK_N, SCALE_PER_BLOCK] uint8

                    # --- MXFP4 GEMM tile ---
                    # A: [BLOCK_M, BLOCK_K] uint8 activations
                    # B: [BLOCK_K, BLOCK_N] uint8 weights (K-major)
                    # Result: [BLOCK_M, BLOCK_N] fp32 accumulated
                    acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)

                # --- Store output tile ---
                # out layout: [M*top_k, 2*d_expert_pad]
                # row = sort position = token_start + m_offs
                # col = n_start + n_offs
                out_row = token_start + m_offs        # [BLOCK_M]
                out_col = n_start + n_offs             # [BLOCK_N]
                out_offs = (
                    out_row[:, None] * stride_out_m
                    + out_col[None, :] * stride_out_n
                )  # [BLOCK_M, BLOCK_N]
                out_mask = (
                    sort_mask[:, None]
                    & (out_col < 2 * d_expert_pad)[None, :]
                )
                # acc is fp32 from tl.dot_scaled; store as bf16 (same as Phase 1)
                tl.store(out_ptr + out_offs, acc.to(tl.bfloat16), mask=out_mask)

                found = True
                break  # exit expert scan loop

            expert_tile_start += tiles_for_e

        # If no expert was found for this tile_id, we've exhausted all tiles — exit
        if not found:
            break

        tile_id += num_sms


# ---------------------------------------------------------------------------
# Stage 2 Triton kernel — MXFP4 GEMM (Phase 2)
#   Inputs  : inter_ptr   [M*top_k, d_expert_pad//2]  uint8 (fp4x2 packed inter_silu)
#             inters_ptr  [M*top_k, d_expert_pad//32]  uint8 (e8m0 inter scales)
#             w2_ptr      [E, d_hidden_pad, d_expert_pad//2]  uint8 (fp4x2 packed)
#             w2s_ptr     [E, d_hidden_pad, d_expert_pad//32] uint8 (e8m0 weight scales)
#             sorted_token_pos  [M*top_k] int32
#             sorted_weights    [M*top_k] float32
#             expert_offsets    [E+1] int32
#   Output  : out [M, d_hidden] bf16  (atomic-accumulated)
#
# Atomic adds are required: multiple experts write to the same output token row.
# BLOCK_K counts uint8 packed bytes (d_expert_pad//2 columns, not d_expert_pad).
# ---------------------------------------------------------------------------
@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk},
                      num_warps=nw, num_stages=ns)
        for bm in [16, 32, 64, 128]
        for bn in [64, 128, 256]
        for bk in [64, 128]
        for nw in [4, 8]
        for ns in [2, 3, 4]
    ],
    key=["M", "E", "d_expert_pad", "d_hidden"],
)
@triton.jit
def _moe_stage2_kernel(
    # --- input pointers ---
    inter_ptr,        # [M*top_k, d_expert_pad//2]  uint8 (fp4x2 packed inter_silu)
    inters_ptr,       # [M*top_k, d_expert_pad//32] uint8 (e8m0 intermediate scales)
    w2_ptr,           # [E, d_hidden_pad, d_expert_pad//2]  uint8 (fp4x2 packed)
    w2s_ptr,          # [E, d_hidden_pad, d_expert_pad//32] uint8 (e8m0 weight scales)
    sorted_pos_ptr,   # [M*top_k]  int32
    sorted_w_ptr,     # [M*top_k]  float32
    expert_off_ptr,   # [E+1]  int32
    # --- output pointer ---
    out_ptr,          # [M, d_hidden]  bf16  (zeroed before launch)
    # --- scalars ---
    M,
    E,
    d_expert_pad,     # actual expert intermediate dim (bf16 elements)
    d_expert_half,    # d_expert_pad // 2 — packed uint8 K columns for inter
    d_hidden,         # actual output hidden dim
    d_hidden_pad,     # N axis of down_weight (padded)
    total_sorted,
    # --- strides (all in uint8 elements for u8 tensors) ---
    stride_inter_m,   # inter_u8 row stride (= d_expert_pad//2)
    stride_inter_k,   # inter_u8 col stride (= 1)
    stride_is_m,      # inters_u8 row stride (= d_expert_pad//32)
    stride_is_k,      # inters_u8 col stride (= 1)
    stride_w2_e,      # w2_u8 expert stride
    stride_w2_n,      # w2_u8 row stride (= d_expert_pad//2)
    stride_w2_k,      # w2_u8 col stride (= 1)
    stride_w2s_e,     # w2s_u8 expert stride
    stride_w2s_n,     # w2s_u8 row stride
    stride_w2s_k,     # w2s_u8 col stride (= 1)
    stride_out_m,
    stride_out_n,
    # --- tile sizes ---
    BLOCK_M: tl.constexpr,   # >= 16
    BLOCK_N: tl.constexpr,   # output hidden dim tile
    BLOCK_K: tl.constexpr,   # K reduction tile in uint8 packed bytes (>= 64)
):
    """
    Persistent MoE Stage 2: MXFP4 GEMM over down_weight, atomic-add to output.

    BLOCK_K is in uint8 bytes (packed fp4x2).
    SCALE_PER_BLOCK = BLOCK_K // 16.
    Tile layout mirrors Stage 1: for expert e: tiles_m * tiles_n, tiles_n = ceil(d_hidden / BLOCK_N).
    """
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16

    sm_id = tl.program_id(0)
    num_sms = tl.num_programs(0)

    num_tiles_n = tl.cdiv(d_hidden, BLOCK_N)

    tile_id = sm_id

    while True:
        expert_tile_start = 0
        found = False

        for _e in range(512):
            if _e >= E:
                break
            e_start = tl.load(expert_off_ptr + _e).to(tl.int32)
            e_end   = tl.load(expert_off_ptr + _e + 1).to(tl.int32)
            count_e = e_end - e_start
            num_tiles_m_e = tl.cdiv(count_e, BLOCK_M)
            tiles_for_e = num_tiles_m_e * num_tiles_n

            if tile_id < expert_tile_start + tiles_for_e:
                local_tile = tile_id - expert_tile_start
                tile_m = local_tile // num_tiles_n
                tile_n = local_tile % num_tiles_n

                token_start = e_start + tile_m * BLOCK_M
                token_end_clamped = tl.minimum(token_start + BLOCK_M, e_end)
                m_size = token_end_clamped - token_start

                n_start = tile_n * BLOCK_N

                m_offs = tl.arange(0, BLOCK_M)
                n_offs = tl.arange(0, BLOCK_N)
                k_offs = tl.arange(0, BLOCK_K)   # uint8 byte indices

                sort_idx = token_start + m_offs
                sort_mask = m_offs < m_size

                # Load original token positions and topk weights
                orig_pos = tl.load(sorted_pos_ptr + sort_idx, mask=sort_mask, other=0)
                weights  = tl.load(sorted_w_ptr  + sort_idx, mask=sort_mask, other=0.0)
                # orig_pos: [BLOCK_M] int32, weights: [BLOCK_M] float32

                # --- Accumulate GEMM over K (d_expert_half uint8 bytes) ---
                acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

                # N range (shared across k_tiles)
                n_global = n_start + n_offs
                n_mask = n_global < d_hidden

                k_iters = tl.cdiv(d_expert_half, BLOCK_K)
                for k_tile in range(k_iters):
                    k_start = k_tile * BLOCK_K
                    kk = k_start + k_offs
                    k_mask = kk < d_expert_half    # packed-byte bound

                    # --- Load intermediate tile: [BLOCK_M, BLOCK_K] uint8 ---
                    # inter_ptr points to uint8 (fp4x2) — quantized before Stage 2 launch
                    # Rows are sort positions (token_start + m_offs), same as Phase 1
                    a_offs = (
                        sort_idx[:, None] * stride_inter_m    # uint8 row stride = d_expert_pad//2
                        + kk[None, :] * stride_inter_k        # col stride = 1
                    )
                    a_mask = sort_mask[:, None] & k_mask[None, :]
                    a = tl.load(inter_ptr + a_offs, mask=a_mask, other=0)  # uint8

                    # --- Load A scale: [BLOCK_M, SCALE_PER_BLOCK] uint8 ---
                    scale_k_start = k_start // 16
                    offs_sk = scale_k_start + tl.arange(0, SCALE_PER_BLOCK)
                    a_scale = tl.load(
                        inters_ptr                             # [M*top_k, d_expert_pad//32]
                        + sort_idx[:, None] * stride_is_m
                        + offs_sk[None, :] * stride_is_k,
                        mask=sort_mask[:, None],
                        other=0,
                    )  # [BLOCK_M, SCALE_PER_BLOCK] uint8

                    # --- Load down_weight tile: [BLOCK_K, BLOCK_N] uint8 (K-major) ---
                    # w2 layout: [E, N=d_hidden_pad, K_half=d_expert_pad//2]
                    # Load K-major (K outer, N inner) — tl.dot_scaled expects A=[M,K], B=[K,N]
                    b_offs = (
                        _e * stride_w2_e
                        + kk[:, None] * stride_w2_k           # K outer (K-major)
                        + n_global[None, :] * stride_w2_n     # N inner
                    )  # [BLOCK_K, BLOCK_N]
                    b_mask = k_mask[:, None] & n_mask[None, :]
                    b = tl.load(w2_ptr + b_offs, mask=b_mask, other=0)  # uint8

                    # --- Load B scale: [BLOCK_N, SCALE_PER_BLOCK] uint8 (N-first, mandatory) ---
                    # w2 scale: [E, N=d_hidden_pad, scale_K2=d_expert_pad//32]
                    # B scale MUST remain N-first even though B data is K-major
                    b_scale = tl.load(
                        w2s_ptr
                        + _e * stride_w2s_e
                        + n_global[:, None] * stride_w2s_n    # N outer (N-first, mandatory)
                        + offs_sk[None, :] * stride_w2s_k,
                        mask=n_mask[:, None],
                        other=0,
                    )  # [BLOCK_N, SCALE_PER_BLOCK] uint8

                    acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)

                # --- Scale by topk_weight and atomic-add to output ---
                # weights: [BLOCK_M], acc: [BLOCK_M, BLOCK_N]
                scaled = (acc * weights[:, None].to(tl.float32)).to(tl.bfloat16)

                # Output rows indexed by orig_pos (original token position)
                n_mask_out = n_global < d_hidden

                for mi in range(BLOCK_M):
                    if mi < m_size:
                        row = orig_pos[mi]
                        out_row_offs = (
                            row * stride_out_m
                            + n_global * stride_out_n
                        )  # [BLOCK_N]
                        tl.atomic_add(out_ptr + out_row_offs, scaled[mi, :], mask=n_mask_out)

                found = True
                break

            expert_tile_start += tiles_for_e

        if not found:
            break

        tile_id += num_sms


# ---------------------------------------------------------------------------
# Python-side token sorting (§5.1) — unchanged from Phase 1
# ---------------------------------------------------------------------------
def _sort_tokens_by_expert(topk_ids, topk_weights, E):
    """
    Sort tokens by expert assignment.

    topk_ids     : [M, top_k]  int32
    topk_weights : [M, top_k]  float32
    E            : int  — total number of experts

    Returns:
        sorted_token_pos  [M*top_k]  int32  — original token row per sorted slot
        sorted_weights    [M*top_k]  float32
        expert_offsets    [E+1]      int32  — start/end in sorted arrays per expert
    """
    device = topk_ids.device
    top_k = topk_ids.shape[1]

    flat_ids     = topk_ids.view(-1).long()       # [M*top_k]
    flat_weights = topk_weights.view(-1)           # [M*top_k]

    # Sort by expert ID — stable=True for reproducibility
    sort_order = torch.argsort(flat_ids, stable=True)   # [M*top_k]  int64

    # Original token index = sort_order // top_k  (which token produced this slot)
    sorted_token_pos = (sort_order // top_k).to(torch.int32)    # [M*top_k]
    sorted_weights   = flat_weights[sort_order]                  # [M*top_k]

    # Count tokens per expert and build prefix-sum offsets
    tokens_per_expert = torch.bincount(flat_ids, minlength=E).to(torch.int32)  # [E]
    expert_offsets = torch.zeros(E + 1, dtype=torch.int32, device=device)
    expert_offsets[1:] = tokens_per_expert.cumsum(0)

    return sorted_token_pos, sorted_weights, expert_offsets


# ---------------------------------------------------------------------------
# Custom Triton MoE forward (Phase 2: MXFP4 GEMM with tl.dot_scaled)
# ---------------------------------------------------------------------------
def _custom_triton_moe(
    hidden_states,      # [M, d_hidden]  bf16
    gate_up_weight,     # [E, 2*d_expert_pad, d_hidden_pad//2]  fp4x2 (raw)
    down_weight,        # [E, d_hidden_pad, d_expert_pad//2]    fp4x2 (raw)
    gate_up_scale,      # [E, 2*d_expert_pad, scale_K]  e8m0 (raw)
    down_scale,         # [E, d_hidden_pad, scale_K]    e8m0 (raw)
    topk_weights,       # [M, top_k]  float32
    topk_ids,           # [M, top_k]  int32
    config,             # dict
):
    M, d_hidden = hidden_states.shape
    E = gate_up_weight.shape[0]
    d_expert_pad = config["d_expert_pad"]
    d_hidden_pad = config["d_hidden_pad"]
    d_expert     = config["d_expert"]
    top_k = topk_ids.shape[1]

    device = hidden_states.device

    # ------------------------------------------------------------------
    # Step 1: Token sorting (replaces moe_sorting_fwd) — unchanged
    # ------------------------------------------------------------------
    sorted_token_pos, sorted_weights_flat, expert_offsets = _sort_tokens_by_expert(
        topk_ids, topk_weights, E
    )

    # ------------------------------------------------------------------
    # Step 2: View all fp4x2 / e8m0 tensors as uint8
    # MANDATORY: Triton JIT has a float4_e2m1fn_x2 KeyError registration bug.
    # Always .view(torch.uint8) before passing to any Triton kernel.
    # Strides are recalculated from the uint8 views (element units change).
    # ------------------------------------------------------------------
    # w1 raw: [E, 2*d_expert_pad, d_hidden_pad//2] fp4x2 → uint8 same shape
    w1_u8 = gate_up_weight.view(torch.uint8)
    # w1 scale raw: [E, 2*d_expert_pad, d_hidden_pad//32] e8m0 → uint8
    w1s_u8 = gate_up_scale.view(torch.uint8)

    # w2 raw: [E, d_hidden_pad, d_expert_pad//2] fp4x2 → uint8 same shape
    w2_u8 = down_weight.view(torch.uint8)
    # w2 scale raw: [E, d_hidden_pad, d_expert_pad//32] e8m0 → uint8
    w2s_u8 = down_scale.view(torch.uint8)

    # ------------------------------------------------------------------
    # Step 3: Quantize activations bf16 → fp4x2 (Option B: external quant)
    # dynamic_mxfp4_quant returns (fp4_tensor, e8m0_scale_tensor)
    # ------------------------------------------------------------------
    hs_cont = hidden_states.contiguous()
    x_fp4, x_scale = dynamic_mxfp4_quant(hs_cont)
    # x_fp4:   [M, d_hidden//2]  float4_e2m1fn_x2 → view as uint8
    # x_scale: [M, d_hidden//32] e8m0              → view as uint8
    x_u8  = x_fp4.view(torch.uint8)    # [M, d_hidden//2]
    xs_u8 = x_scale.view(torch.uint8)  # [M, d_hidden//32]

    # Derived packed-byte dimension for Stage 1 K loop
    d_hidden_half = d_hidden // 2  # uint8 columns for activation (BLOCK_K unit)

    # ------------------------------------------------------------------
    # Step 4: Allocate intermediate buffer [M*top_k, 2*d_expert_pad] bf16
    # ------------------------------------------------------------------
    total_sorted = M * top_k
    intermediate = torch.zeros(
        (total_sorted, 2 * d_expert_pad), dtype=torch.bfloat16, device=device
    )

    # ------------------------------------------------------------------
    # Step 5: Launch Stage 1 kernel (persistent tiles, MXFP4 GEMM)
    # ------------------------------------------------------------------
    num_sms = torch.cuda.get_device_properties(device).multi_processor_count

    # Ensure contiguity so strides are simple (stride = size of inner dims)
    w1_u8  = w1_u8.contiguous()
    w1s_u8 = w1s_u8.contiguous()
    x_u8   = x_u8.contiguous()
    xs_u8  = xs_u8.contiguous()

    _moe_stage1_kernel[(num_sms,)](
        x_u8,                        # hs_u8_ptr
        xs_u8,                       # hs_scale_ptr
        w1_u8,                       # w1_ptr
        w1s_u8,                      # w1s_ptr
        sorted_token_pos,
        expert_offsets,
        intermediate,
        M, E,
        d_hidden,
        d_hidden_half,
        d_hidden_pad,
        d_expert_pad,
        total_sorted,
        # strides hs_u8  (uint8 elements)
        x_u8.stride(0),  x_u8.stride(1),
        # strides hs_scale (uint8 elements)
        xs_u8.stride(0), xs_u8.stride(1),
        # strides w1_u8 (uint8 elements)
        w1_u8.stride(0),  w1_u8.stride(1),  w1_u8.stride(2),
        # strides w1s_u8 (uint8 elements)
        w1s_u8.stride(0), w1s_u8.stride(1), w1s_u8.stride(2),
        # strides output (bf16 elements)
        intermediate.stride(0), intermediate.stride(1),
    )

    # ------------------------------------------------------------------
    # Step 6: SiLU + multiply — unchanged from Phase 1
    # intermediate layout: [:, :d_expert_pad] = gate, [:, d_expert_pad:] = up
    # ------------------------------------------------------------------
    gate = intermediate[:, :d_expert_pad]          # [M*top_k, d_expert_pad]
    up   = intermediate[:, d_expert_pad:]          # [M*top_k, d_expert_pad]
    inter_silu = F.silu(gate) * up                 # [M*top_k, d_expert_pad]  bf16
    inter_silu = inter_silu.contiguous()

    # ------------------------------------------------------------------
    # Step 7: Re-quantize intermediate bf16 → fp4x2 for Stage 2 A input
    # ------------------------------------------------------------------
    inter_fp4, inter_scale = dynamic_mxfp4_quant(inter_silu)
    # inter_fp4:   [M*top_k, d_expert_pad//2]  float4_e2m1fn_x2 → uint8
    # inter_scale: [M*top_k, d_expert_pad//32] e8m0              → uint8
    inter_u8  = inter_fp4.view(torch.uint8).contiguous()
    inters_u8 = inter_scale.view(torch.uint8).contiguous()

    # Derived packed-byte dimension for Stage 2 K loop
    d_expert_half = d_expert_pad // 2  # uint8 columns for intermediate (BLOCK_K unit)

    # Ensure w2 contiguous for simple strides
    w2_u8  = w2_u8.contiguous()
    w2s_u8 = w2s_u8.contiguous()

    # ------------------------------------------------------------------
    # Step 8: Launch Stage 2 kernel (persistent tiles, MXFP4 GEMM, atomic_add)
    # ------------------------------------------------------------------
    output = torch.zeros((M, d_hidden), dtype=torch.bfloat16, device=device)

    _moe_stage2_kernel[(num_sms,)](
        inter_u8,                    # inter_ptr
        inters_u8,                   # inters_ptr
        w2_u8,                       # w2_ptr
        w2s_u8,                      # w2s_ptr
        sorted_token_pos,
        sorted_weights_flat,
        expert_offsets,
        output,
        M, E,
        d_expert_pad,
        d_expert_half,
        d_hidden,
        d_hidden_pad,
        total_sorted,
        # strides inter_u8 (uint8 elements)
        inter_u8.stride(0),  inter_u8.stride(1),
        # strides inters_u8 (uint8 elements)
        inters_u8.stride(0), inters_u8.stride(1),
        # strides w2_u8 (uint8 elements)
        w2_u8.stride(0),  w2_u8.stride(1),  w2_u8.stride(2),
        # strides w2s_u8 (uint8 elements)
        w2s_u8.stride(0), w2s_u8.stride(1), w2s_u8.stride(2),
        # strides output (bf16 elements)
        output.stride(0), output.stride(1),
    )

    return output


# ---------------------------------------------------------------------------
# Competition entry point
# ---------------------------------------------------------------------------
def custom_kernel(data: input_t) -> output_t:
    """
    MoE forward pass.

    data: 12-element tuple per spec §2.
    Returns: [M, d_hidden] bf16 output tensor.

    Environment variables:
        USE_CUSTOM_TRITON=0  — fall back to aiter fused_moe (default: use custom)
    """
    (
        hs,     # hidden_states              [M, d_hidden]  bf16
        w1,     # gate_up_weight             [E, 2*d_expert_pad, d_hidden_pad//2]  fp4x2
        w2,     # down_weight                [E, d_hidden_pad, d_expert_pad//2]    fp4x2
        w1s,    # gate_up_weight_scale       [E, 2*d_expert_pad, scale_K]  e8m0
        w2s,    # down_weight_scale          [E, d_hidden_pad, scale_K]    e8m0
        w1sh,   # gate_up_weight_shuffled    (for aiter fallback)
        w2sh,   # down_weight_shuffled       (for aiter fallback)
        w1ssh,  # gate_up_weight_scale_shuffled  (for aiter fallback)
        w2ssh,  # down_weight_scale_shuffled     (for aiter fallback)
        tw,     # topk_weights               [M, top_k]  float32
        ti,     # topk_ids                   [M, top_k]  int32
        cfg,    # config dict
    ) = data

    if not USE_CUSTOM_TRITON:
        # Fallback: aiter fused_moe with pre-shuffled weights
        return fm(
            hs,
            w1sh,
            w2sh,
            tw,
            ti,
            expert_mask=None,
            activation=at.Silu,
            quant_type=qt.per_1x32,
            doweight_stage1=False,
            w1_scale=w1ssh,
            w2_scale=w2ssh,
            hidden_pad=cfg["d_hidden_pad"] - cfg["d_hidden"],
            intermediate_pad=cfg["d_expert_pad"] - cfg["d_expert"],
        )

    return _custom_triton_moe(hs, w1, w2, w1s, w2s, tw, ti, cfg)


# ---------------------------------------------------------------------------
# Syntax validation (run as script to verify before submission)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import ast
    import pathlib

    src = pathlib.Path(__file__).read_text()
    try:
        ast.parse(src)
        print("AST parse: OK")
    except SyntaxError as e:
        print(f"AST parse: FAILED — {e}")
        raise
