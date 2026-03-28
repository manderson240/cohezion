"""
MLA decode: matmul with 4D broadcasting — minimal overhead.

For qlen=1 decode, attention is just:
  scores = Q(bs,H,1,576) @ K(bs,1,576,S)  → (bs,H,1,S)  [broadcast]
  weights = softmax(scores)
  out = weights(bs,H,1,S) @ V(bs,1,S,512) → (bs,H,1,512) [broadcast]

torch.matmul handles the GQA broadcast (H=16 query heads, 1 KV head)
internally without materializing the expanded tensor.

Compared to einsum: matmul uses cuBLAS/hipBLAS batched GEMM backend,
while einsum goes through torch.tensordot path which may have overhead.

Compared to SDPA: no attention framework overhead, no mask checking,
no dropout path, no causal mask — just raw matmul + softmax.
"""
import torch
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

    # K^T: (bs, 1, 576, kvseqlen) — broadcasts over nheads
    k_t = kv.unsqueeze(1).transpose(2, 3)

    # Score: (bs, nheads, qseqlen, kvseqlen)
    scores = torch.matmul(q_4d, k_t).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)

    # V: (bs, 1, kvseqlen, 512) — broadcasts over nheads
    v = kv[:, :, :V_HEAD_DIM].unsqueeze(1)

    # Out: (bs, nheads, qseqlen, 512) → (bs*qseqlen, nheads, 512)
    out = torch.matmul(weights, v)
    return out.transpose(1, 2).reshape(-1, nheads, V_HEAD_DIM)
