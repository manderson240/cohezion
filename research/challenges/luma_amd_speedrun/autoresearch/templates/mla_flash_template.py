"""Flash Attention-style MLA decode template for gfx950.

Replaces the 3-stage pipeline (metadata build + stage1 ASM + reduce) with
a single-pass Flash Attention kernel adapted for MLA's asymmetric dimensions:
  Q: [bs, num_heads, 576] (QK dimension)
  K: [total_kv, 1, 576] (FP8)
  V: embedded in K as first 512 dims
  Output: [bs, num_heads, 512]

MLA input_t = (q, kv_data, qo_indptr, kv_indptr, config):
  q:          [total_q, num_heads, 576] bf16
  kv_data:    dict with "bf16", "fp8" (Tensor, scale), "mxfp4" (Tensor, scale)
  qo_indptr:  [batch_size+1] int32
  kv_indptr:  [batch_size+1] int32
  config:     dict with batch_size, num_heads, qk_head_dim(576), v_head_dim(512), etc.

Parameters (JSON):
  block_kv: int, KV sequence tile size
  num_warps: int
  num_stages: int
  kv_format: "fp8" or "bf16" — which KV cache to use
"""

TEMPLATE = """\
import os
import torch
import triton
import triton.language as tl
from task import input_t, output_t
from aiter import dtypes as dt
import aiter

os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

BLOCK_KV = $BLOCK_KV
NUM_WARPS = $NUM_WARPS
NUM_STAGES = $NUM_STAGES
KV_FORMAT = "$KV_FORMAT"

# ── MLA Flash Attention kernel ───────────────────────────────────────────────
# Single-pass decode attention for MLA with:
# - QK dim = 576, V dim = 512 (asymmetric)
# - 576 NOT power-of-2 → pad to 1024 for tl.arange (44% register waste)
# - FP8 KV cache with per-tensor scale
# - Online softmax (Flash Attention style)

# Pad dimensions to next power of 2 for Triton
QK_DIM = 576
V_DIM = 512
QK_PAD = 1024  # next power of 2 after 576
V_PAD = 512    # already power of 2
SM_SCALE = 1.0 / (576 ** 0.5)


@triton.jit
def _mla_flash_decode_kernel(
    # Query: [total_q, num_heads, 576] bf16
    Q_ptr,
    # KV cache: [total_kv, 1, 576] fp8 or bf16
    K_ptr,
    KV_scale_ptr,  # scalar float32 (for fp8) or None
    # Indices
    kv_indptr_ptr,  # [batch_size+1] int32
    # Output: [total_q, num_heads, 512] bf16
    O_ptr,
    # Dimensions
    batch_size, num_heads,
    total_kv,
    # Strides
    stride_qb, stride_qh, stride_qd,  # Q: [total_q, num_heads, 576]
    stride_kn, stride_k1, stride_kd,  # K: [total_kv, 1, 576]
    stride_ob, stride_oh, stride_od,  # O: [total_q, num_heads, 512]
    # Config
    BLOCK_KV: tl.constexpr,
    IS_FP8: tl.constexpr,
):
    # Program ID: one program per (batch, head) pair
    pid = tl.program_id(0)
    batch_id = pid // num_heads
    head_id = pid % num_heads

    # KV range for this batch element
    kv_start = tl.load(kv_indptr_ptr + batch_id)
    kv_end = tl.load(kv_indptr_ptr + batch_id + 1)
    kv_len = kv_end - kv_start

    # Load query vector: [576] bf16 → pad to QK_PAD
    q_offs = tl.arange(0, QK_PAD)
    q_mask = q_offs < QK_DIM
    q = tl.load(
        Q_ptr + batch_id * stride_qb + head_id * stride_qh + q_offs * stride_qd,
        mask=q_mask, other=0.0,
    ).to(tl.float32)

    # Load KV scale (for fp8)
    if IS_FP8:
        kv_scale = tl.load(KV_scale_ptr).to(tl.float32)
    else:
        kv_scale = 1.0

    # Online softmax variables
    m_prev = float("-inf")  # running max
    l_prev = 0.0            # running sum of exp
    acc = tl.zeros([V_PAD], dtype=tl.float32)  # running weighted sum

    # Iterate over KV sequence in tiles
    for kv_tile_start in range(0, kv_len, BLOCK_KV):
        kv_offs = kv_tile_start + tl.arange(0, BLOCK_KV)
        kv_mask = kv_offs < kv_len

        # Load K tile: [BLOCK_KV, 576] → pad K dim to QK_PAD
        # K is [total_kv, 1, 576], access K[kv_start + kv_offs, 0, :]
        k_tile = tl.load(
            K_ptr + (kv_start + kv_offs[:, None]) * stride_kn + q_offs[None, :] * stride_kd,
            mask=kv_mask[:, None] & q_mask[None, :],
            other=0.0,
        )
        if IS_FP8:
            k_f32 = k_tile.to(tl.float32) * kv_scale
        else:
            k_f32 = k_tile.to(tl.float32)

        # Compute attention scores: q · K^T → [BLOCK_KV]
        # q is [QK_PAD], k_f32 is [BLOCK_KV, QK_PAD]
        scores = tl.sum(q[None, :] * k_f32, axis=1) * SM_SCALE  # [BLOCK_KV]
        scores = tl.where(kv_mask, scores, float("-inf"))

        # Online softmax update
        m_new = tl.maximum(m_prev, tl.max(scores, axis=0))
        # Correction factor for previous accumulator
        alpha = tl.math.exp2((m_prev - m_new) * 1.4426950408889634)  # log2(e)
        # New exponentials
        p = tl.math.exp2((scores - m_new) * 1.4426950408889634)
        l_new = alpha * l_prev + tl.sum(p, axis=0)

        # Load V tile: [BLOCK_KV, 512] (first 512 dims of KV buffer)
        v_offs = tl.arange(0, V_PAD)
        v_mask = v_offs < V_DIM
        v_tile = tl.load(
            K_ptr + (kv_start + kv_offs[:, None]) * stride_kn + v_offs[None, :] * stride_kd,
            mask=kv_mask[:, None] & v_mask[None, :],
            other=0.0,
        )
        if IS_FP8:
            v_f32 = v_tile.to(tl.float32) * kv_scale
        else:
            v_f32 = v_tile.to(tl.float32)

        # Update accumulator: acc = alpha * acc + p @ V
        acc = alpha * acc + tl.sum(p[:, None] * v_f32, axis=0)

        m_prev = m_new
        l_prev = l_new

    # Normalize
    acc = acc / l_prev

    # Store output: [512] bf16
    o_offs = tl.arange(0, V_PAD)
    o_mask = o_offs < V_DIM
    tl.store(
        O_ptr + batch_id * stride_ob + head_id * stride_oh + o_offs * stride_od,
        acc.to(tl.bfloat16),
        mask=o_mask,
    )


# ── Cache for metadata (aiter fallback) ──────────────────────────────────────
_c, _o = {}, {}
_f1, _f2 = None, None


def _ea():
    global _f1, _f2
    if _f1:
        return
    try:
        from aiter.mla import mla_decode_stage1_asm_fwd as f1, mla_reduce_v1 as f2
        _f1, _f2 = f1, f2
    except Exception:
        pass


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    batch_size = config["batch_size"]
    num_heads = config["num_heads"]
    kv_seq_len = config["kv_seq_len"]
    total_q = q.shape[0]

    # Select KV format
    is_fp8 = KV_FORMAT == "fp8"
    if is_fp8:
        kv_buffer, kv_scale = kv_data["fp8"]
    else:
        kv_buffer = kv_data["bf16"]
        kv_scale = torch.tensor([1.0], dtype=torch.float32, device=q.device)

    total_kv = kv_buffer.shape[0]

    # Output tensor
    output = torch.empty(total_q, num_heads, 512, dtype=torch.bfloat16, device=q.device)

    # Launch kernel: one program per (batch, head)
    grid = (batch_size * num_heads,)

    _mla_flash_decode_kernel[grid](
        q,
        kv_buffer,
        kv_scale if is_fp8 else kv_scale,
        kv_indptr,
        output,
        batch_size, num_heads,
        total_kv,
        q.stride(0), q.stride(1), q.stride(2),
        kv_buffer.stride(0), kv_buffer.stride(1) if kv_buffer.dim() > 2 else 1, kv_buffer.stride(-1),
        output.stride(0), output.stride(1), output.stride(2),
        BLOCK_KV=BLOCK_KV,
        IS_FP8=is_fp8,
        num_warps=NUM_WARPS, num_stages=NUM_STAGES,
    )

    return output
"""

DEFAULT_PARAMS = {
    "BLOCK_KV": 64,
    "NUM_WARPS": 8,
    "NUM_STAGES": 1,
    "KV_FORMAT": "fp8",
}

# Benchmark shapes from task.yml
SHAPES = [
    {"bs": 4, "qseqlen": 1, "kvseqlen": 1024, "tp": 4},
    {"bs": 4, "qseqlen": 4, "kvseqlen": 8192, "tp": 4},
    {"bs": 32, "qseqlen": 1, "kvseqlen": 8192, "tp": 8},
    {"bs": 32, "qseqlen": 4, "kvseqlen": 1024, "tp": 8},
    {"bs": 32, "qseqlen": 1, "kvseqlen": 1024, "tp": 4},
    {"bs": 32, "qseqlen": 4, "kvseqlen": 8192, "tp": 4},
    {"bs": 128, "qseqlen": 1, "kvseqlen": 8192, "tp": 8},
    {"bs": 128, "qseqlen": 4, "kvseqlen": 8192, "tp": 8},
]
