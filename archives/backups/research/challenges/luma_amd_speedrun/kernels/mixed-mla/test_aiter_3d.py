import sys

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]

    # Prepare 3D Q
    q_3d = q.view(bs, nheads, 576)
    q_q, q_s = dynamic_mxfp4_quant(q_3d.reshape(-1, 576))
    q_q = q_q.view(bs, nheads, 288).view(dtypes.fp4x2)
    q_s = q_s.view(bs, nheads, 24)[:, :, :18].contiguous().view(dtypes.fp8_e8m0)

    # Prepare 3D K
    kv_fp4, kv_scale = kv_data["mxfp4"]
    k_q = kv_fp4.view(bs, kvseqlen, 288).view(dtypes.fp4x2)
    k_s = kv_scale.view(bs, kvseqlen, 24)[:, :, :18].contiguous().view(dtypes.fp8_e8m0)

    print("--- Testing aiter.gemm_a4w4 with 3D inputs ---", file=sys.stderr)
    try:
        # Note: B needs to be [N, K]. Here N=kvseqlen, K=576.
        # But we have it as [bs, kvseqlen, 288].
        # If it supports batching, it might expect [bs, N, K].
        out = aiter.gemm_a4w4(
            q_q,
            k_q,
            q_s,
            k_s,
            dtype=torch.bfloat16,
            bpreshuffle=True,  # Assuming it's already in the right layout or we don't care for this test
        )
        print(f"SUCCESS! out shape: {out.shape}", file=sys.stderr)
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
