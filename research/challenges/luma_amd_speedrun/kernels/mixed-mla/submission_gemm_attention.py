import torch
from aiter import ActivationType, QuantType, dtypes
from aiter.fused_moe import fused_moe
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


# SM_SCALE for DeepSeek R1 MLA
SM_SCALE = 1.0 / (576**0.5)
V_HEAD_DIM = 512
QK_HEAD_DIM = 576

# Cache for routing IDs and weights
_routing_cache: dict = {}


def _get_routing(bs, nheads, device):
    key = (bs, nheads)
    if key not in _routing_cache:
        # Each head in a batch item belongs to the same batch item (expert)
        # topk_ids: [bs * nheads, 1]
        topk_ids = (
            torch.arange(bs, device=device).repeat_interleave(nheads).unsqueeze(1).to(torch.int32)
        )
        # topk_weights: [bs * nheads, 1]
        topk_weights = torch.ones((bs * nheads, 1), device=device, dtype=torch.float32)
        _routing_cache[key] = (topk_ids, topk_weights)
    return _routing_cache[key]


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]
    device = q.device

    # 1. Prepare Q: Quantize to MXFP4
    # q is [bs, nheads, 576]
    q_flat = q.view(bs * nheads, QK_HEAD_DIM)
    q_q, q_s = dynamic_mxfp4_quant(q_flat)

    # 2. Prepare K: from mxfp4 KV buffer
    kv_fp4, kv_scale = kv_data["mxfp4"]
    # kv_fp4 is [bs * kvseqlen, 1, 288]
    # kv_scale is [bs * kvseqlen, 24]

    # Reshape KV for fused_moe
    # fused_moe weights W1: [E, N, K]
    # Here E=bs, N=kvseqlen, K=576
    w1 = kv_fp4.view(bs, kvseqlen, 288).view(dtypes.fp4x2)
    # Scales: [bs, kvseqlen, 24] -> slice to 18
    w1_s = kv_scale.view(bs, kvseqlen, 24)[:, :, :18].contiguous().view(dtypes.fp8_e8m0)

    # Routing: each head to its batch item
    topk_ids, topk_weights = _get_routing(bs, nheads, device)

    # 3. Compute Scores = Q @ K.T
    # Result: [bs * nheads, kvseqlen]
    scores = fused_moe(
        q_flat,
        w1,
        None,  # No W2 needed for scores
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.No,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=w1_s,
        # Other params
        hidden_pad=0,
        intermediate_pad=0,
    )

    # 4. Softmax
    scores.mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)

    # 5. Compute Out = Weights @ V
    # V is the first 512 dims of the same KV cache
    # This is another GEMM: [bs * nheads, kvseqlen] @ [bs, kvseqlen, 512]
    # We can use fused_moe again!
    # Weights are the 'activations' [bs * nheads, kvseqlen]
    # V is the 'weights' [bs, 512, kvseqlen]

    # Prepare V: slice first 512 dims (256 bytes)
    # v_fp4: [bs, kvseqlen, 256]
    v_fp4 = kv_fp4.view(bs, kvseqlen, 288)[:, :, :256].contiguous().view(dtypes.fp4x2)
    # v_s: first 16 groups (512 / 32 = 16)
    v_s = kv_scale.view(bs, kvseqlen, 24)[:, :, :16].contiguous().view(dtypes.fp8_e8m0)

    # Weights for fused_moe must have d_model divisible by 32
    # d_model here is kvseqlen. If kvseqlen is not multiple of 32, we need padding.
    # But for now, let's assume it works or use a fallback.

    # Note: Weights @ V is A16W4 GEMM. fused_moe might not support bf16 input with fp4 weights directly?
    # Actually it does (QuantType.per_1x32).

    out = fused_moe(
        weights,
        v_fp4,
        None,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.No,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=v_s,
        hidden_pad=0,
        intermediate_pad=0,
    )

    return out.view(-1, nheads, V_HEAD_DIM)
