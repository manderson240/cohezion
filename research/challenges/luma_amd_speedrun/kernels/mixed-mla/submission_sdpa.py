"""
MLA decode: bf16 SDPA — bypasses aiter mla_decode_fwd entirely.

The aiter pipeline has ~130us of fixed overhead:
  1. fp8 quantization of Q (~5us)
  2. get_mla_metadata_v1 (~30us JIT + compute)
  3. mla_decode_fwd multi-kernel dispatch (~90us)

For DeepSeek MLA with absorbed Q and compressed KV, the attention
is just batched matmul + softmax:
  Score: Q(bs,H,qlen,576) @ K(bs,1,kvlen,576).T  -> (bs,H,qlen,kvlen)
  Value: softmax(Score) @ V(bs,1,kvlen,512)       -> (bs,H,qlen,512)

With num_kv_heads=1, this is MQA — all query heads share one KV head.
PyTorch SDPA handles this via enable_gqa=True with fused flash attention.

Falls back to manual matmul if SDPA/GQA not available.
"""
import torch
import torch.nn.functional as F
from task import input_t, output_t

SM_SCALE = 1.0 / (576 ** 0.5)

_mode = "sdpa"  # "sdpa" -> "matmul" on failure


def custom_kernel(data: input_t) -> output_t:
    global _mode
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]

    kv = kv_data["bf16"].view(bs, kvseqlen, 576)

    # (bs, nheads, qseqlen, 576)
    q_4d = q.view(bs, qseqlen, nheads, 576).transpose(1, 2)

    if _mode == "sdpa":
        try:
            # K: (bs, 1, kvseqlen, 576), V: (bs, 1, kvseqlen, 512)
            k = kv.unsqueeze(1)
            v = kv[:, :, :512].contiguous().unsqueeze(1)
            out = F.scaled_dot_product_attention(
                q_4d, k, v, scale=SM_SCALE, enable_gqa=True,
            )
            return out.transpose(1, 2).reshape(-1, nheads, 512)
        except Exception:
            _mode = "matmul"

    # Manual matmul fallback
    # Score: (bs, nheads, qseqlen, 576) @ (bs, 1, 576, kvseqlen)
    k = kv.unsqueeze(1).transpose(-2, -1)
    scores = torch.matmul(q_4d, k) * SM_SCALE
    attn = torch.softmax(scores, dim=-1)

    # Value: (bs, nheads, qseqlen, kvseqlen) @ (bs, 1, kvseqlen, 512)
    v = kv[:, :, :512].unsqueeze(1)
    out = torch.matmul(attn, v)
    return out.transpose(1, 2).reshape(-1, nheads, 512)
