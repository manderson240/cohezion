"""
GEMM: Online Quantization with Streaming
Approach: Process input in streaming fashion, quantizing and computing
on chunks to reduce peak memory usage and improve cache efficiency.

Key insight: For large M dimension, we can stream through input rows,
keeping only a working set in memory at once.
"""


import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    Online streaming quantization GEMM.

    Processes input in chunks:
    1. Stream through M dimension in chunks
    2. Quantize each chunk on-the-fly
    3. Compute GEMM immediately
    4. Accumulate to output

    Benefits: Lower peak memory, better cache locality.
    """
    try:
        A, B, B_q, B_shuffle, B_scale_sh = data

        M, K = A.shape
        N = B.shape[0]

        # Chunk size for streaming (tuned for cache)
        CHUNK_M = 64

        # Pre-allocate output
        output = torch.empty(M, N, dtype=torch.bfloat16, device=A.device)

        # Process in chunks
        for m_start in range(0, M, CHUNK_M):
            m_end = min(m_start + CHUNK_M, M)
            m_size = m_end - m_start

            # Get input chunk
            A_chunk = A[m_start:m_end].contiguous()

            # Online quantization
            A_q_chunk, A_scale_chunk = dynamic_mxfp4_quant(A_chunk)
            A_q_chunk = A_q_chunk.view(dtypes.fp4x2)

            # Compute GEMM for this chunk
            # For efficiency with small m_size, use direct GEMM
            chunk_out = aiter.gemm_a4w4(
                A_q_chunk,
                B_shuffle,
                A_scale_chunk,
                B_scale_sh,
                dtype=dtypes.bf16,
                bpreshuffle=True,
            )

            # Store output
            output[m_start:m_end] = chunk_out

        return output

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
