import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t


# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────
MXFP4_BLOCK_SIZE = 32
PAD_ALIGN = 256
CK_BLOCK_GEMM = 1  # Enable block GEMM dispatch


def _pad_to(x: int, align: int) -> int:
    return (x + align - 1) // align * align


# ──────────────────────────────────────────────────────────────────────
# Adaptive KSPLIT selection per-shape
# ──────────────────────────────────────────────────────────────────────
def _select_ksplit(n_routed_experts: int, total_top_k: int) -> int:
    # For sparse MoE (many experts), use higher KSPLIT; otherwise use minimal
    return 4 if n_routed_experts > 200 else 2


def custom_kernel(data: input_t) -> output_t:
    # Unpack input
    hidden_states = data.hidden_states  # [M, d_hidden], bfloat16
    router_logits = data.router_logits  # [M, n_routed_experts], bfloat16
    w1 = data.w1  # [E, 2*intermediate, hidden], uint8 (MXFP4)
    w2 = data.w2  # [E, hidden, intermediate], uint8 (MXFP4)
    w3 = data.w3  # [E, 2*intermediate, hidden], uint8 (MXFP4) [optional if G1U1]
    router_weights = data.router_weights  # [M, total_top_k], float32
    expert_ids = data.expert_ids  # [M, total_top_k], int32
    n_routed_experts = data.n_routed_experts
    n_shared_experts = data.n_shared_experts
    total_top_k = data.total_top_k
    d_hidden = data.d_hidden
    d_expert = data.d_expert
    d_hidden_pad = data.d_hidden_pad
    d_expert_pad = data.d_expert_pad
    n_experts_per_token = data.n_experts_per_token
    M = hidden_states.shape[0]

    # ── Adaptive KSPLIT selection ──
    ksplit = _select_ksplit(n_routed_experts, total_top_k)

    # ── Handle MXFP4 layout: ensure uint8 view and correct shape ──
    # w1/w2/w3: [E, ..., ...] as uint8 (packed MXFP4)
    # Ensure contiguous and expected shape
    w1 = w1.contiguous()
    w2 = w2.contiguous()
    if w3 is not None:
        w3 = w3.contiguous()

    # ── Preprocess weights: shuffle for optimal GEMM layout ──
    # Use aiter's shuffle_weight to align weights for block GEMM
    w1_shuf = shuffle_weight(w1, block_size=MXFP4_BLOCK_SIZE)
    w2_shuf = shuffle_weight(w2, block_size=MXFP4_BLOCK_SIZE)
    w3_shuf = shuffle_weight(w3, block_size=MXFP4_BLOCK_SIZE) if w3 is not None else None

    # ── Fused MoE call with optimized config ──
    out = fused_moe(
        hidden_states,
        w1_shuf,
        w2_shuf,
        w3_shuf,
        router_weights,
        expert_ids,
        n_routed_experts=n_routed_experts,
        n_shared_experts=n_shared_experts,
        top_k=n_experts_per_token,
        total_top_k=total_top_k,
        use_fp4=True,
        block_size=MXFP4_BLOCK_SIZE,
        activation=ActivationType.GELU,
        quant_type=QuantType.MXFP4,
        ck_block_gemm=CK_BLOCK_GEMM,
        ksplit=ksplit,
        pad_align=PAD_ALIGN,
    )

    # ── Ensure output matches expected shape ──
    assert out.shape == (M, d_hidden), f"Output shape mismatch: {out.shape}"
    assert out.dtype == torch.bfloat16, f"Output dtype mismatch: {out.dtype}"

    return output_t(
        hidden_states=hidden_states,
        router_logits=router_logits,
        w1=w1,
        w2=w2,
        w3=w3 if w3 is not None else None,
        router_weights=router_weights,
        expert_ids=expert_ids,
        output=out,
    )