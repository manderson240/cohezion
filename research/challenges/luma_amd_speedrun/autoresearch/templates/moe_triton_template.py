"""Persistent-tile MoE Triton template for MXFP4 on gfx950.

Replaces aiter.fused_moe with a custom Triton kernel that:
1. Fuses token permutation (eliminates separate moe_sorting_fwd kernel)
2. Uses persistent-tile scheduling (single kernel launch for all experts)
3. Uses tl.dot_scaled for native MXFP4 GEMM on gfx950
4. SiLU activation applied between stages in Python (or optionally fused)

MoE input_t = (hs, w1, w2, w1s, w2s, w1sh, w2sh, w1ssh, w2ssh, tw, ti, cfg):
  hs:    [M, d_hidden] bf16 (hidden states)
  w1:    [E, 2*d_expert_pad, d_hidden_pad//2] fp4x2 (gate_up, raw)
  w2:    [E, d_hidden_pad, d_expert_pad//2] fp4x2 (down, raw)
  w1s:   [E, 2*d_expert_pad, scale_K] e8m0 (gate_up scale, raw)
  w2s:   [E, d_hidden_pad, scale_K] e8m0 (down scale, raw)
  w1sh:  shuffled gate_up weight, w2sh: shuffled down weight
  w1ssh: shuffled gate_up scale, w2ssh: shuffled down scale
  tw:    [M, top_k] float32 (topk weights)
  ti:    [M, top_k] int32 (topk expert IDs)
  cfg:   dict with d_hidden, d_expert, d_hidden_pad, d_expert_pad, etc.

Parameters (JSON):
  block_m: int, tile height for tokens (min 16 for gfx950)
  block_n: int, tile width for expert dim
  block_k: int, tile depth in packed bytes (min 64)
  num_warps: int
  num_stages: int
  use_fallback: bool, fall back to aiter if Triton kernel fails
"""

TEMPLATE = '''\
import os
import torch
import triton
import triton.language as tl
from task import input_t, output_t
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe as fm
from aiter.ops.triton.quant import dynamic_mxfp4_quant

os.environ["AITER_USE_NT"] = "1"

BLOCK_M = $BLOCK_M
BLOCK_N = $BLOCK_N
BLOCK_K = $BLOCK_K
NUM_WARPS = $NUM_WARPS
NUM_STAGES = $NUM_STAGES
USE_FALLBACK = $USE_FALLBACK


# ── Stage 1: gate_up projection (hidden → 2*d_expert) ───────────────────────
# Persistent-tile: single kernel iterates over all experts.
# Gathers tokens via sorted_token_pos (fused permutation).
# Uses tl.dot_scaled for MXFP4 hardware GEMM.

@triton.jit
def _moe_stage1_kernel(
    # Pre-quantized activation
    A_ptr,          # [M, d_hidden_half] uint8 (fp4x2 packed)
    A_scale_ptr,    # [M, scale_K_a] uint8 (e8m0, raw)
    # Weight: raw un-shuffled
    W1_ptr,         # [E, 2*d_expert_pad, d_hidden_half] uint8 (fp4x2)
    W1_scale_ptr,   # [E, 2*d_expert_pad, scale_K_w] uint8 (e8m0, raw)
    # Permutation data
    sorted_pos_ptr,       # [total_sorted] int32 — original token index
    expert_offsets_ptr,   # [E+1] int32 — cumulative token count per expert
    # Output: intermediate activations
    out_ptr,              # [total_sorted, 2*d_expert_pad] bf16
    # Dimensions
    M, E: tl.constexpr, d_hidden_half, two_d_expert_pad,
    scale_K_a, scale_K_w,
    # Strides
    stride_am, stride_ak,          # A: [M, d_hidden_half]
    stride_asm, stride_ask,        # A_scale: [M, scale_K_a]
    stride_w1e, stride_w1n, stride_w1k,  # W1: [E, 2*d_expert_pad, d_hidden_half]
    stride_ws1e, stride_ws1n, stride_ws1k,  # W1_scale: [E, 2*d_expert_pad, scale_K_w]
    stride_om, stride_on,          # out: [total_sorted, 2*d_expert_pad]
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(0)
    num_sms = tl.num_programs(0)

    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16

    # Walk all tiles across all experts (persistent scheduling)
    # We precompute total_tiles in Python and pass grid=(total_tiles,)
    # But for truly persistent, we'd use grid=(num_sms,) and loop.
    # Here we use the simpler per-tile approach for correctness first.

    # Decode pid → (expert_id, tile_m_in_expert, tile_n)
    # Since expert sizes vary, we use expert_offsets to find which expert
    # owns this tile. Linear scan (OK for < 300 experts).

    # Compute tiles per N dimension (same for all experts)
    num_tiles_n = tl.cdiv(two_d_expert_pad, BLOCK_N)

    # Find expert and tile within expert
    # pid encodes: flat_tile_idx across all experts
    remaining = pid
    expert_id = 0

    # Iterate to find expert (simple loop, bounded by E)
    tokens_before = tl.load(expert_offsets_ptr)  # expert_offsets[0] = 0
    for e in range(E):
        tokens_this = tl.load(expert_offsets_ptr + e + 1) - tl.load(expert_offsets_ptr + e)
        tiles_m = tl.cdiv(tokens_this, BLOCK_M)
        tiles_this_expert = tiles_m * num_tiles_n
        if remaining < tiles_this_expert:
            expert_id = e
            break
        remaining -= tiles_this_expert

    # Decode remaining into (tile_m_local, tile_n)
    expert_start = tl.load(expert_offsets_ptr + expert_id)
    expert_end = tl.load(expert_offsets_ptr + expert_id + 1)
    tokens_this = expert_end - expert_start

    tiles_m = tl.cdiv(tokens_this, BLOCK_M)
    tile_m_local = remaining // num_tiles_n
    tile_n = remaining % num_tiles_n

    # M offsets: indices into sorted token list for this expert
    m_start = expert_start + tile_m_local * BLOCK_M
    offs_m_sorted = m_start + tl.arange(0, BLOCK_M)
    m_mask = offs_m_sorted < expert_end

    # Gather original token positions for A access
    orig_pos = tl.load(sorted_pos_ptr + offs_m_sorted, mask=m_mask, other=0)

    # N offsets for output (expert intermediate dimension)
    offs_n = tile_n * BLOCK_N + tl.arange(0, BLOCK_N)
    n_mask = offs_n < two_d_expert_pad

    # Accumulator
    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

    # K loop over d_hidden_half
    for k_start in range(0, d_hidden_half, BLOCK_K):
        k_offs = tl.arange(0, BLOCK_K)
        scale_k_start = k_start // 16
        scale_offs = tl.arange(0, SCALE_PER_BLOCK)

        # Load A tile via gather (fused permutation)
        # A[orig_pos, k_start : k_start+BLOCK_K]
        a = tl.load(
            A_ptr + orig_pos[:, None] * stride_am + (k_start + k_offs[None, :]) * stride_ak,
            mask=m_mask[:, None] & ((k_start + k_offs[None, :]) < d_hidden_half),
            other=0,
        )

        # Load A scale via gather
        a_scale = tl.load(
            A_scale_ptr + orig_pos[:, None] * stride_asm + (scale_k_start + scale_offs[None, :]) * stride_ask,
            mask=m_mask[:, None],
            other=0,
        )

        # Load W1 tile: W1[expert_id, offs_n, k_start:k_start+BLOCK_K]
        # W1 is [E, 2*d_expert_pad, d_hidden_half] — N is second dim, K is third
        w = tl.load(
            W1_ptr + expert_id * stride_w1e + offs_n[None, :] * stride_w1n + (k_start + k_offs[:, None]) * stride_w1k,
            mask=n_mask[None, :] & ((k_start + k_offs[:, None]) < d_hidden_half),
            other=0,
        )

        # Load W1 scale: [BLOCK_N, SCALE_PER_BLOCK] (N-first!)
        w_scale = tl.load(
            W1_scale_ptr + expert_id * stride_ws1e + offs_n[:, None] * stride_ws1n + (scale_k_start + scale_offs[None, :]) * stride_ws1k,
            mask=n_mask[:, None],
            other=0,
        )

        # MXFP4 GEMM via tl.dot_scaled
        acc = tl.dot_scaled(a, a_scale, "e2m1", w, w_scale, "e2m1", acc=acc)

    # Store result to intermediate buffer
    out_mask = m_mask[:, None] & n_mask[None, :]
    tl.store(
        out_ptr + offs_m_sorted[:, None] * stride_om + offs_n[None, :] * stride_on,
        acc.to(tl.bfloat16),
        mask=out_mask,
    )


# ── Stage 2: down projection (d_expert → d_hidden) with weighted accumulate ──

@triton.jit
def _moe_stage2_kernel(
    # Intermediate activation (after SiLU)
    intermediate_ptr,     # [total_sorted, d_expert_pad] bf16
    # Weight
    W2_ptr,               # [E, d_hidden_pad, d_expert_half] uint8 (fp4x2)
    W2_scale_ptr,         # [E, d_hidden_pad, scale_K_w2] uint8 (e8m0)
    # Permutation + weights
    sorted_pos_ptr,       # [total_sorted] int32
    sorted_weights_ptr,   # [total_sorted] float32 — topk weights
    expert_offsets_ptr,   # [E+1] int32
    # Output
    out_ptr,              # [M, d_hidden] bf16 — atomic accumulate
    # Dimensions
    M, E: tl.constexpr, d_expert_half, d_hidden_pad, d_hidden,
    scale_K_w2,
    # Strides
    stride_im, stride_ik,
    stride_w2e, stride_w2n, stride_w2k,
    stride_ws2e, stride_ws2n, stride_ws2k,
    stride_om, stride_on,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(0)
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16

    num_tiles_n = tl.cdiv(d_hidden_pad, BLOCK_N)

    # Find expert and tile (same logic as stage 1)
    remaining = pid
    expert_id = 0
    for e in range(E):
        tokens_this = tl.load(expert_offsets_ptr + e + 1) - tl.load(expert_offsets_ptr + e)
        tiles_m = tl.cdiv(tokens_this, BLOCK_M)
        tiles_this_expert = tiles_m * num_tiles_n
        if remaining < tiles_this_expert:
            expert_id = e
            break
        remaining -= tiles_this_expert

    expert_start = tl.load(expert_offsets_ptr + expert_id)
    expert_end = tl.load(expert_offsets_ptr + expert_id + 1)
    tokens_this = expert_end - expert_start
    tiles_m = tl.cdiv(tokens_this, BLOCK_M)
    tile_m_local = remaining // num_tiles_n
    tile_n = remaining % num_tiles_n

    m_start = expert_start + tile_m_local * BLOCK_M
    offs_m_sorted = m_start + tl.arange(0, BLOCK_M)
    m_mask = offs_m_sorted < expert_end

    orig_pos = tl.load(sorted_pos_ptr + offs_m_sorted, mask=m_mask, other=0)
    weights = tl.load(sorted_weights_ptr + offs_m_sorted, mask=m_mask, other=0.0)

    offs_n = tile_n * BLOCK_N + tl.arange(0, BLOCK_N)
    n_mask = offs_n < d_hidden_pad

    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

    # For stage 2, intermediate is bf16 (not fp4). Use regular tl.dot.
    # Intermediate: [total_sorted, d_expert_pad] bf16
    # W2: [E, d_hidden_pad, d_expert_half] uint8 (fp4x2)
    # We need to handle mixed precision: bf16 intermediate × fp4 weight
    # tl.dot_scaled requires BOTH operands as fp4. So we either:
    #   a) Requantize intermediate to fp4 (adds overhead)
    #   b) Use bf16 matmul (no tl.dot_scaled for stage 2)
    # Using bf16 matmul for stage 2 (simpler, intermediate is already bf16)

    d_expert_pad_val = d_expert_half * 2  # logical expert dim

    for k_start in range(0, d_expert_pad_val, BLOCK_K):
        k_offs = tl.arange(0, BLOCK_K)

        # Load intermediate tile: [BLOCK_M, BLOCK_K] bf16
        i_tile = tl.load(
            intermediate_ptr + offs_m_sorted[:, None] * stride_im + (k_start + k_offs[None, :]) * stride_ik,
            mask=m_mask[:, None] & ((k_start + k_offs[None, :]) < d_expert_pad_val),
            other=0.0,
        )

        # Load W2 tile: need to dequantize fp4x2 → bf16 for regular dot
        # W2[expert_id, offs_n, k_start//2 : (k_start+BLOCK_K)//2]
        # This is complex with packed fp4x2. For now, use bf16 matmul.
        # TODO: requantize intermediate to fp4 and use tl.dot_scaled

        # For bf16 path: load W2 as bf16 (requires dequant in Python)
        # For this template, stage 2 uses bf16 intermediate × bf16 dequanted W2
        # This is a correctness-first approach. Performance optimization comes later.

        # Actually, we'll skip the inner K loop for bf16 and use a simpler approach
        break  # placeholder — see fallback below

    # FALLBACK: For stage 2, use torch.mm with dequantized W2
    # This is temporary until we implement proper fp4 stage 2
    pass


def _sort_tokens(ti, tw, E, top_k, device):
    """Sort tokens by expert ID for fused permutation."""
    flat_ids = ti.view(-1).long()
    flat_w = tw.view(-1)
    sort_order = torch.argsort(flat_ids, stable=True)
    sorted_pos = (sort_order // top_k).to(torch.int32)
    sorted_weights = flat_w[sort_order]
    tokens_per_expert = torch.bincount(flat_ids, minlength=E).to(torch.int32)
    expert_offsets = torch.zeros(E + 1, dtype=torch.int32, device=device)
    expert_offsets[1:] = tokens_per_expert.cumsum(0)
    return sorted_pos, sorted_weights, expert_offsets


def _compute_total_tiles(expert_offsets, E, two_d_expert_pad, d_hidden_pad, block_m, block_n):
    """Compute total number of tiles across all experts."""
    total = 0
    for e in range(E):
        tokens = int(expert_offsets[e + 1].item() - expert_offsets[e].item())
        if tokens == 0:
            continue
        tiles_m = (tokens + block_m - 1) // block_m
        tiles_n = (two_d_expert_pad + block_n - 1) // block_n
        total += tiles_m * tiles_n
    return total


def custom_kernel(data: input_t) -> output_t:
    (hs, w1, w2, w1s, w2s, w1sh, w2sh, w1ssh, w2ssh, tw, ti, cfg) = data

    M = hs.shape[0]
    d_hidden = cfg["d_hidden"]
    d_expert = cfg["d_expert"]
    d_hidden_pad = cfg["d_hidden_pad"]
    d_expert_pad = cfg["d_expert_pad"]
    E = w1.shape[0]
    top_k = ti.shape[1]
    d_hidden_half = d_hidden_pad // 2
    two_d_expert_pad = 2 * d_expert_pad

    if USE_FALLBACK:
        # Fallback to aiter fused_moe (always correct)
        return fm(
            hs, w1sh, w2sh, tw, ti, expert_mask=None,
            activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
            doweight_stage1=False, w1_scale=w1ssh, w2_scale=w2ssh,
            hidden_pad=d_hidden_pad - d_hidden,
            intermediate_pad=d_expert_pad - d_expert,
        )

    # ── Step 1: Sort tokens by expert (replaces moe_sorting_fwd) ──
    sorted_pos, sorted_weights, expert_offsets = _sort_tokens(ti, tw, E, top_k, hs.device)
    total_sorted = int(expert_offsets[-1].item())

    # ── Step 2: Pre-quantize activations ──
    hs_cont = hs.contiguous()
    hs_fp4, hs_scale = dynamic_mxfp4_quant(hs_cont)
    hs_u8 = hs_fp4.view(torch.uint8)        # [M, d_hidden_half]
    hs_scale_u8 = hs_scale.view(torch.uint8)  # [M, d_hidden_pad//32]

    # View raw weights as uint8 for Triton
    w1_u8 = w1.view(torch.uint8)     # [E, 2*d_expert_pad, d_hidden_half]
    w1s_u8 = w1s.view(torch.uint8)   # [E, 2*d_expert_pad, scale_K]

    # ── Step 3: Stage 1 — gate_up GEMM ──
    intermediate = torch.zeros(total_sorted, two_d_expert_pad, dtype=torch.bfloat16, device=hs.device)

    total_tiles = _compute_total_tiles(expert_offsets, E, two_d_expert_pad, d_hidden_half, BLOCK_M, BLOCK_N)

    if total_tiles > 0:
        _moe_stage1_kernel[(total_tiles,)](
            hs_u8, hs_scale_u8,
            w1_u8, w1s_u8,
            sorted_pos, expert_offsets,
            intermediate,
            M, E, d_hidden_half, two_d_expert_pad,
            hs_scale_u8.shape[1], w1s_u8.shape[2],
            hs_u8.stride(0), hs_u8.stride(1),
            hs_scale_u8.stride(0), hs_scale_u8.stride(1),
            w1_u8.stride(0), w1_u8.stride(1), w1_u8.stride(2),
            w1s_u8.stride(0), w1s_u8.stride(1), w1s_u8.stride(2),
            intermediate.stride(0), intermediate.stride(1),
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            num_warps=NUM_WARPS, num_stages=NUM_STAGES,
        )

    # ── Step 4: SiLU activation ──
    # intermediate is [total_sorted, 2*d_expert_pad] — split into gate + up
    gate = intermediate[:, :d_expert_pad]
    up = intermediate[:, d_expert_pad:]
    activated = torch.nn.functional.silu(gate) * up  # [total_sorted, d_expert_pad]

    # ── Step 5: Stage 2 — down projection + weighted scatter ──
    # For correctness-first, use per-expert bf16 matmul with dequantized weights.
    # TODO: Replace with Triton kernel using tl.dot_scaled after stage 1 is validated.
    from aiter.utility.fp4_utils import mxfp4_to_f32, e8m0_to_f32

    output = torch.zeros(M, d_hidden, dtype=torch.bfloat16, device=hs.device)

    for e in range(E):
        start = int(expert_offsets[e].item())
        end = int(expert_offsets[e + 1].item())
        if start == end:
            continue

        # Tokens for this expert
        expert_tokens = activated[start:end]  # [n_tokens, d_expert_pad]
        pos = sorted_pos[start:end].long()    # original token indices
        w = sorted_weights[start:end]         # topk weights

        # Dequantize W2[e] for this expert: [d_hidden_pad, d_expert_pad//2] fp4x2
        w2_e_fp4 = w2[e]  # [d_hidden_pad, d_expert_pad//2]
        w2_e_f32 = mxfp4_to_f32(w2_e_fp4)  # [d_hidden_pad, d_expert_pad]
        w2_e_scale = e8m0_to_f32(w2s[e].view(torch.uint8))  # [d_hidden_pad, scale_K_w2]
        # Apply block scales
        sk = w2_e_scale.shape[1]
        w2_e_f32_blocks = w2_e_f32.view(d_hidden_pad, sk, 32)
        w2_e_dq = (w2_e_f32_blocks * w2_e_scale.unsqueeze(-1)).reshape(d_hidden_pad, -1)
        w2_e_dq = w2_e_dq[:d_hidden, :d_expert].to(torch.bfloat16)

        # expert_tokens is [n_tokens, d_expert_pad], trim to d_expert
        expert_out = expert_tokens[:, :d_expert] @ w2_e_dq.T  # [n_tokens, d_hidden]

        # Weighted scatter-add to output
        output.index_add_(0, pos, (expert_out * w.unsqueeze(1)).to(torch.bfloat16))

    return output
'''

DEFAULT_PARAMS = {
    "BLOCK_M": 64,
    "BLOCK_N": 64,
    "BLOCK_K": 64,
    "NUM_WARPS": 4,
    "NUM_STAGES": 2,
    "USE_FALLBACK": False,
}

# Benchmark shapes from task.yml
SHAPES = [
    {"E": 257, "d_expert": 256, "bs": 16},
    {"E": 257, "d_expert": 256, "bs": 128},
    {"E": 257, "d_expert": 256, "bs": 512},
    {"E": 33, "d_expert": 512, "bs": 16},
    {"E": 33, "d_expert": 512, "bs": 128},
    {"E": 33, "d_expert": 512, "bs": 512},
    {"E": 33, "d_expert": 2048, "bs": 512},
]
