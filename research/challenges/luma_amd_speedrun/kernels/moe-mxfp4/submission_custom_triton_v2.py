"""
Custom Triton MoE Kernel — Phase 1: Correctness with bf16 GEMM
==============================================================
Phase 1 goals (§11 of spec):
  1. Python-side token sorting (§5.1): argsort + bincount → expert_offsets
  2. Stage 1 Triton kernel: persistent tiles, gather tokens, bf16 matmul → intermediate
  3. SiLU + multiply (torch.nn.functional.silu(gate) * up)
  4. Stage 2 Triton kernel: persistent tiles, atomic_add with topk_weight
  5. Fallback to aiter fused_moe via USE_CUSTOM_TRITON=0 env var

bf16 GEMM strategy for Phase 1:
  - Dequantize fp4x2 weights to bf16 once (per call, on GPU) using fp4_utils
  - Pass bf16 weights to Stage 1/2 kernels — no tl.dot_scaled needed
  - Phase 2 will replace with tl.dot_scaled("e2m1") and uint8-viewed fp4x2 weights

CRITICAL constraints (§7, §10):
  - BLOCK_M >= 16 (silent wrong results on gfx950 otherwise)
  - tl.atomic_add in Stage 2 for multi-expert output accumulation
  - No XCD remapping with cdiv (non-bijective bug §8.1)
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
from aiter.utility import fp4_utils
from task import input_t, output_t


# ---------------------------------------------------------------------------
# Toggle: set USE_CUSTOM_TRITON=0 in environment to fall back to aiter
# ---------------------------------------------------------------------------
USE_CUSTOM_TRITON = os.environ.get("USE_CUSTOM_TRITON", "1") != "0"

MXFP4_BLOCK_SIZE = 32


# ---------------------------------------------------------------------------
# Weight dequantization (bf16) — Phase 1 only
# Mirrors reference.py _dequant_mxfp4 but accepts batched expert index
# ---------------------------------------------------------------------------
def _dequant_fp4_weight_to_bf16(weight_fp4, scale_e8m0):
    """
    Dequantize a single expert's fp4x2 weight matrix to bf16.

    weight_fp4 : [N, K//2]  fp4x2  (raw, not shuffled)
    scale_e8m0 : [N_pad, ceil(K/32)]  e8m0  (raw, not shuffled)

    Returns    : [N, K]  bf16
    """
    w_f32 = fp4_utils.mxfp4_to_f32(weight_fp4)          # [N, K]   float32
    s_f32 = fp4_utils.e8m0_to_f32(scale_e8m0)            # [N_pad, scale_K] float32
    N, K = w_f32.shape
    s_f32 = s_f32[:N, :]                                  # trim padded N rows
    s_f32 = s_f32.repeat_interleave(MXFP4_BLOCK_SIZE, dim=-1)[:, :K]  # [N, K]
    return (w_f32 * s_f32).to(torch.bfloat16)


def _dequant_all_experts_bf16(weight_fp4, scale_e8m0, E):
    """
    Dequantize all E experts' weights in one call.

    weight_fp4 : [E, N, K//2]  fp4x2
    scale_e8m0 : [E, N_pad, scale_K]  e8m0

    Returns    : [E, N, K]  bf16
    """
    return torch.stack(
        [_dequant_fp4_weight_to_bf16(weight_fp4[e], scale_e8m0[e]) for e in range(E)]
    )  # [E, N, K]  bf16


# ---------------------------------------------------------------------------
# Stage 1 Triton kernel
#   Inputs  : hidden_states [M, d_hidden] bf16
#             gate_up_weight_bf16 [E, 2*d_expert_pad, d_hidden_pad] bf16
#             sorted_token_pos [M*top_k] int32
#             expert_offsets [E+1] int32
#   Output  : intermediate [M*top_k, 2*d_expert_pad] bf16
#             (gate half [:, :d_expert_pad], up half [:, d_expert_pad:])
#
# Persistent-tile loop: each SM claims tiles (expert_id, tile_m, tile_n)
# round-robin until all tiles are processed.
# ---------------------------------------------------------------------------
@triton.jit
def _moe_stage1_kernel(
    # --- input pointers ---
    hs_ptr,           # [M, d_hidden]  bf16
    w1_ptr,           # [E, 2*d_expert_pad, d_hidden_pad]  bf16
    sorted_pos_ptr,   # [M*top_k]  int32  — original token index per sorted slot
    expert_off_ptr,   # [E+1]  int32  — start offset per expert in sorted arrays
    # --- output pointer ---
    out_ptr,          # [M*top_k, 2*d_expert_pad]  bf16
    # --- scalars ---
    M,                # number of tokens
    E,                # number of experts
    d_hidden,         # hidden dimension (actual, not padded)
    d_hidden_pad,     # hidden dimension padded
    d_expert_pad,     # expert intermediate dim padded (half of gate_up N axis)
    total_sorted,     # M * top_k
    # --- strides ---
    stride_hs_m,      # hidden_states row stride
    stride_hs_k,      # hidden_states col stride (usually 1)
    stride_w1_e,      # gate_up_weight expert stride
    stride_w1_n,      # gate_up_weight row stride
    stride_w1_k,      # gate_up_weight col stride (usually 1)
    stride_out_m,     # output row stride
    stride_out_n,     # output col stride (usually 1)
    # --- tile sizes (compile-time constants) ---
    BLOCK_M: tl.constexpr,   # >= 16 (gfx950 minimum)
    BLOCK_N: tl.constexpr,   # output tile rows (along 2*d_expert_pad axis)
    BLOCK_K: tl.constexpr,   # K reduction tile
):
    """
    Persistent MoE Stage 1: gather tokens per expert, bf16 GEMM against gate_up weights.

    Each program (SM) iterates over a global flat tile index in strides of num_sms.
    Tile layout per expert e:
      - num_tiles_m(e) = ceil(tokens_for_e / BLOCK_M)
      - num_tiles_n    = ceil(2*d_expert_pad / BLOCK_N)
      - tiles_for_e    = num_tiles_m(e) * num_tiles_n
    """
    sm_id = tl.program_id(0)
    num_sms = tl.num_programs(0)

    # We iterate tile_id over [0, total_tiles) in steps of num_sms.
    # To decode tile_id → (expert, tile_m, tile_n) we scan expert_offsets.
    # For each expert e, the number of M-tiles depends on its token count.
    # This is a simple linear scan — acceptable for E up to ~257.

    tile_id = sm_id

    # Outer persistent loop — each SM claims one tile per iteration
    # tl.static_assert is not available in all Triton versions, use comment instead
    # BLOCK_M >= 16 is MANDATORY for gfx950 correctness (see spec §7.1)

    # We need to figure out total_tiles at runtime to bound the loop.
    # Compute it by scanning expert_offsets.
    # total_tiles = sum over e of ceil(count_e / BLOCK_M) * num_tiles_n
    # We'll compute inside the loop as we walk experts.

    # Since we can't easily compute total_tiles before the loop in Triton,
    # use a sentinel: if the expert scan finds no valid expert for a tile_id, exit.

    num_tiles_n = tl.cdiv(2 * d_expert_pad, BLOCK_N)

    # Max possible tiles upper bound (used as loop limit to allow compiler unrolling)
    # We exit early via a break-equivalent when tile_id exceeds actual total.
    while True:
        # Decode tile_id → expert e, tile_m_local, tile_n
        # Walk expert list to find which expert owns tile_id
        cumulative_tiles = 0
        found = False

        # Linear scan over experts — Triton JIT unrolls statically only for
        # tl.constexpr E; with runtime E we use a counted while loop.
        # We cap at 512 experts (compile-time const for the loop range).
        expert_tile_start = 0  # cumulative tile count up to expert e
        e = 0

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
                n_offs = tl.arange(0, BLOCK_N)       # [BLOCK_N]
                k_offs = tl.arange(0, BLOCK_K)       # [BLOCK_K]

                # --- Gather token indices ---
                sort_idx = token_start + m_offs       # [BLOCK_M] positions in sorted_pos
                sort_mask = m_offs < m_size

                # Load original token positions (int32) for each row in this tile
                orig_pos = tl.load(sorted_pos_ptr + sort_idx, mask=sort_mask, other=0)
                # orig_pos : [BLOCK_M]  int32

                # --- Accumulate GEMM over K in BLOCK_K chunks ---
                acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

                k_iters = tl.cdiv(d_hidden, BLOCK_K)
                for k_tile in range(k_iters):
                    k_start = k_tile * BLOCK_K
                    kk = k_start + k_offs             # [BLOCK_K] global K indices
                    k_mask = kk < d_hidden

                    # Load activation tile: [BLOCK_M, BLOCK_K] bf16
                    # Gather rows from hidden_states using orig_pos
                    a_offs = (
                        orig_pos[:, None] * stride_hs_m
                        + kk[None, :] * stride_hs_k
                    )  # [BLOCK_M, BLOCK_K]
                    a_mask = sort_mask[:, None] & k_mask[None, :]
                    a = tl.load(hs_ptr + a_offs, mask=a_mask, other=0.0).to(tl.bfloat16)

                    # Load weight tile: [BLOCK_N, BLOCK_K] bf16 (N-first, then K)
                    # w1 layout: [E, 2*d_expert_pad, d_hidden_pad]
                    # For expert _e, row n_start..n_start+BLOCK_N, col k_start..k_start+BLOCK_K
                    n_global = n_start + n_offs       # [BLOCK_N] global N indices
                    n_mask = n_global < (2 * d_expert_pad)

                    b_offs = (
                        _e * stride_w1_e
                        + n_global[:, None] * stride_w1_n
                        + kk[None, :] * stride_w1_k
                    )  # [BLOCK_N, BLOCK_K]
                    b_mask = n_mask[:, None] & k_mask[None, :]
                    b = tl.load(w1_ptr + b_offs, mask=b_mask, other=0.0).to(tl.bfloat16)

                    # bf16 GEMM tile: acc += A @ B^T  → [BLOCK_M, BLOCK_N]
                    # a: [BLOCK_M, BLOCK_K], b: [BLOCK_N, BLOCK_K]
                    # We need [BLOCK_M, BLOCK_K] @ [BLOCK_K, BLOCK_N]
                    # So transpose b: b.T → [BLOCK_K, BLOCK_N]
                    acc = tl.dot(a, tl.trans(b), acc=acc, input_precision="ieee")

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
                tl.store(out_ptr + out_offs, acc.to(tl.bfloat16), mask=out_mask)

                found = True
                break  # exit expert scan loop

            expert_tile_start += tiles_for_e

        # If no expert was found for this tile_id, we've exhausted all tiles — exit
        if not found:
            break

        tile_id += num_sms


# ---------------------------------------------------------------------------
# Stage 2 Triton kernel
#   Inputs  : intermediate_silu [M*top_k, d_expert_pad] bf16  (after SiLU+mul)
#             down_weight_bf16  [E, d_hidden_pad, d_expert_pad] bf16
#             sorted_token_pos  [M*top_k] int32
#             sorted_weights    [M*top_k] float32
#             expert_offsets    [E+1] int32
#   Output  : out [M, d_hidden] bf16  (atomic-accumulated)
#
# Atomic adds are required: multiple experts write to the same output token row.
# ---------------------------------------------------------------------------
@triton.jit
def _moe_stage2_kernel(
    # --- input pointers ---
    inter_ptr,        # [M*top_k, d_expert_pad]  bf16
    w2_ptr,           # [E, d_hidden_pad, d_expert_pad]  bf16
    sorted_pos_ptr,   # [M*top_k]  int32
    sorted_w_ptr,     # [M*top_k]  float32
    expert_off_ptr,   # [E+1]  int32
    # --- output pointer ---
    out_ptr,          # [M, d_hidden]  bf16  (zeroed before launch)
    # --- scalars ---
    M,
    E,
    d_expert_pad,     # K axis of down_weight (expert intermediate dim)
    d_hidden,         # N axis of down_weight (actual output hidden dim)
    d_hidden_pad,     # N axis of down_weight (padded)
    total_sorted,
    # --- strides ---
    stride_inter_m,
    stride_inter_k,
    stride_w2_e,
    stride_w2_n,
    stride_w2_k,
    stride_out_m,
    stride_out_n,
    # --- tile sizes ---
    BLOCK_M: tl.constexpr,   # >= 16
    BLOCK_N: tl.constexpr,   # output hidden dim tile
    BLOCK_K: tl.constexpr,   # K reduction tile (expert intermediate)
):
    """
    Persistent MoE Stage 2: bf16 GEMM over down_weight, atomic-add to output.

    Tile layout mirrors Stage 1:
      - For expert e: tiles_m * tiles_n where tiles_n = ceil(d_hidden / BLOCK_N)
    """
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
                k_offs = tl.arange(0, BLOCK_K)

                sort_idx = token_start + m_offs
                sort_mask = m_offs < m_size

                # Load original token positions and topk weights
                orig_pos = tl.load(sorted_pos_ptr + sort_idx, mask=sort_mask, other=0)
                weights  = tl.load(sorted_w_ptr  + sort_idx, mask=sort_mask, other=0.0)
                # orig_pos: [BLOCK_M] int32, weights: [BLOCK_M] float32

                # --- Accumulate GEMM over K (d_expert_pad) ---
                acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

                k_iters = tl.cdiv(d_expert_pad, BLOCK_K)
                for k_tile in range(k_iters):
                    k_start = k_tile * BLOCK_K
                    kk = k_start + k_offs
                    k_mask = kk < d_expert_pad

                    # Load intermediate tile: [BLOCK_M, BLOCK_K] bf16
                    # Rows are sort positions (token_start + m_offs), not orig_pos
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

                    acc = tl.dot(a, tl.trans(b), acc=acc, input_precision="ieee")

                # --- Scale by topk_weight and atomic-add to output ---
                # weights: [BLOCK_M], acc: [BLOCK_M, BLOCK_N]
                scaled = (acc * weights[:, None].to(tl.float32)).to(tl.bfloat16)

                # Output rows indexed by orig_pos (original token position)
                n_global = n_start + n_offs
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
# Python-side token sorting (§5.1)
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
# Custom Triton MoE forward (Phase 1: bf16 GEMM)
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
    # Step 1: Token sorting (replaces moe_sorting_fwd)
    # ------------------------------------------------------------------
    sorted_token_pos, sorted_weights_flat, expert_offsets = _sort_tokens_by_expert(
        topk_ids, topk_weights, E
    )

    # ------------------------------------------------------------------
    # Step 2: Dequantize weights to bf16 (Phase 1 — no tl.dot_scaled)
    # gate_up_weight: [E, 2*d_expert_pad, d_hidden_pad//2] fp4x2
    # After dequant:  [E, 2*d_expert_pad, d_hidden_pad]    bf16
    # down_weight:    [E, d_hidden_pad, d_expert_pad//2]    fp4x2
    # After dequant:  [E, d_hidden_pad, d_expert_pad]       bf16
    # ------------------------------------------------------------------
    w1_bf16 = _dequant_all_experts_bf16(gate_up_weight, gate_up_scale, E)
    # w1_bf16: [E, 2*d_expert_pad, d_hidden_pad]  bf16 — contiguous
    w1_bf16 = w1_bf16.contiguous()

    w2_bf16 = _dequant_all_experts_bf16(down_weight, down_scale, E)
    # w2_bf16: [E, d_hidden_pad, d_expert_pad]  bf16
    w2_bf16 = w2_bf16.contiguous()

    # ------------------------------------------------------------------
    # Step 3: Allocate intermediate buffer [M*top_k, 2*d_expert_pad]
    # ------------------------------------------------------------------
    total_sorted = M * top_k
    intermediate = torch.zeros(
        (total_sorted, 2 * d_expert_pad), dtype=torch.bfloat16, device=device
    )

    # ------------------------------------------------------------------
    # Step 4: Launch Stage 1 kernel (persistent tiles)
    # ------------------------------------------------------------------
    num_sms = torch.cuda.get_device_properties(device).multi_processor_count

    # Tile sizes — BLOCK_M >= 16 is mandatory (gfx950 constraint §7.1)
    BLOCK_M = 32
    BLOCK_N = 64
    BLOCK_K = 64

    hs = hidden_states.contiguous()

    _moe_stage1_kernel[(num_sms,)](
        hs,
        w1_bf16,
        sorted_token_pos,
        expert_offsets,
        intermediate,
        M, E,
        d_hidden,
        d_hidden_pad,
        d_expert_pad,
        total_sorted,
        # strides hidden_states
        hs.stride(0), hs.stride(1),
        # strides w1
        w1_bf16.stride(0), w1_bf16.stride(1), w1_bf16.stride(2),
        # strides output
        intermediate.stride(0), intermediate.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    # ------------------------------------------------------------------
    # Step 5: SiLU + multiply (in Python/torch — fused into Stage 1 in Phase 3)
    # intermediate layout: [:, :d_expert_pad] = gate, [:, d_expert_pad:] = up
    # ------------------------------------------------------------------
    gate = intermediate[:, :d_expert_pad]          # [M*top_k, d_expert_pad]
    up   = intermediate[:, d_expert_pad:]          # [M*top_k, d_expert_pad]
    inter_silu = F.silu(gate) * up                 # [M*top_k, d_expert_pad]  bf16
    inter_silu = inter_silu.contiguous()

    # ------------------------------------------------------------------
    # Step 6: Launch Stage 2 kernel (persistent tiles, atomic_add)
    # ------------------------------------------------------------------
    output = torch.zeros((M, d_hidden), dtype=torch.bfloat16, device=device)

    _moe_stage2_kernel[(num_sms,)](
        inter_silu,
        w2_bf16,
        sorted_token_pos,
        sorted_weights_flat,
        expert_offsets,
        output,
        M, E,
        d_expert_pad,
        d_hidden,
        d_hidden_pad,
        total_sorted,
        # strides intermediate
        inter_silu.stride(0), inter_silu.stride(1),
        # strides w2
        w2_bf16.stride(0), w2_bf16.stride(1), w2_bf16.stride(2),
        # strides output
        output.stride(0), output.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
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
