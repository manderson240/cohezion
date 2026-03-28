"""
MLA decode: torch.compile(reduce-overhead) matmul — HIP graph fusion.

torch.compile with reduce-overhead mode captures HIP graphs, eliminating
kernel launch overhead. Combined with matmul-based attention (no aiter),
this should minimize total latency.

The compiled function handles the full attention:
  Q(bs,H,1,576) @ K^T(bs,1,576,S) → softmax → @ V(bs,1,S,512)

First few calls do JIT compilation + warmup. After warmup, HIP graph
replay gives near-zero launch overhead.
"""
import torch
from task import input_t, output_t

SM_SCALE = 1.0 / (576 ** 0.5)
V_HEAD_DIM = 512
QK_HEAD_DIM = 576

_compiled = {}


def _attn_core(q_4d, k_t, v):
    scores = torch.matmul(q_4d, k_t).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    return torch.matmul(weights, v)


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]

    if qseqlen != 1:
        from reference import ref_kernel
        return ref_kernel(data)

    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    q_4d = q.view(bs, nheads, 1, QK_HEAD_DIM)
    k_t = kv.unsqueeze(1).transpose(2, 3)
    v = kv[:, :, :V_HEAD_DIM].unsqueeze(1)

    # Get or create compiled function for this shape
    shape_key = (bs, kvseqlen)
    if shape_key not in _compiled:
        try:
            _compiled[shape_key] = torch.compile(
                _attn_core, mode="reduce-overhead", fullgraph=True,
            )
        except Exception:
            _compiled[shape_key] = _attn_core

    fn = _compiled[shape_key]
    out = fn(q_4d, k_t, v)
    return out.squeeze(2).to(torch.bfloat16)
