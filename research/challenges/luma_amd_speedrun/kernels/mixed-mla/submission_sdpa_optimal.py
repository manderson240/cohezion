"""
MLA decode: SDPA with enable_gqa — uses CK flash attention on AMD.

PyTorch SDPA on ROCm dispatches to Composable Kernel (CK) flash attention.
This bypasses ALL aiter overhead (metadata, JIT, ASM dispatch).

Handles both qseqlen=1 (decode) and qseqlen=4 (prefill) natively.
SDPA supports arbitrary query/key lengths with no special casing.

K uses all 576 dims, V uses first 512 dims.
enable_gqa=True handles 16-32 query heads sharing 1 KV head.
"""
import torch
import torch.nn.functional as F
from task import input_t, output_t

SM_SCALE = 1.0 / (576 ** 0.5)
V_HEAD_DIM = 512
QK_HEAD_DIM = 576


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]

    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)

    # Q: (bs, nheads, qseqlen, 576)
    q_4d = q.view(bs, qseqlen, nheads, QK_HEAD_DIM).transpose(1, 2)

    # K: (bs, 1, kvseqlen, 576), V: (bs, 1, kvseqlen, 512)
    k = kv.unsqueeze(1)
    v = kv[:, :, :V_HEAD_DIM].unsqueeze(1)

    out = F.scaled_dot_product_attention(
        q_4d, k, v, scale=SM_SCALE, enable_gqa=True,
    )
    # out: (bs, nheads, qseqlen, 512) -> (bs*qseqlen, nheads, 512)
    return out.transpose(1, 2).reshape(-1, nheads, V_HEAD_DIM)
