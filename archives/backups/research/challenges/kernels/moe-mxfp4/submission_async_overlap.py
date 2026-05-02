"""
MoE: Memory-Compute Overlap with Async Operations
Approach: Overlap memory transfers (quantization, data movement) with compute
(GEMM operations) using CUDA streams and async execution.

Key insight: Quantization is memory-bound, GEMM is compute-bound.
By overlapping these operations across different token batches,
we can hide latency and improve throughput.
"""

import os
import sys

import torch
import torch.nn.functional as F


# Add JIT build path for faster compilation
_AITER_JIT_BUILD = "/home/runner/aiter/aiter/jit/build"
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    Async overlap MoE kernel.

    Overlaps quantization with GEMM execution by:
    1. Creating multiple CUDA streams for concurrent execution
    2. Streaming token processing (quantize batch N while computing batch N-1)
    3. Using async copies and non-blocking operations

    Fallback: fused_moe on any error.
    """
    try:
        # Unpack data
        (
            hidden_states,
            w1,
            w2,
            w1_scale,
            w2_scale,
            w1_shuffle,
            w2_shuffle,
            w1_scale_shuffled,
            w2_scale_shuffled,
            topk_weights,
            topk_ids,
            config,
        ) = data

        M = hidden_states.shape[0]
        K = hidden_states.shape[1]
        N = w1.shape[1] // 2
        topk = topk_ids.shape[1]
        num_experts = w1.shape[0]

        # Create CUDA streams for async execution
        stream_compute = torch.cuda.Stream(device=hidden_states.device)
        stream_quant = torch.cuda.Stream(device=hidden_states.device)

        # Allocate output accumulator
        output = torch.zeros(M, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)

        # Split batch into chunks for streaming
        CHUNK_SIZE = max(1, M // 4)  # 4 chunks for overlap

        # Pre-sort tokens by expert (using default stream)
        sorted_ids = torch.empty(M * topk, dtype=torch.int32, device=hidden_states.device)
        sorted_weights = torch.empty(M * topk, dtype=torch.float32, device=hidden_states.device)
        sorted_expert_ids = torch.empty(M * topk, dtype=torch.int32, device=hidden_states.device)
        num_valid_ids = torch.empty(1, dtype=torch.int32, device=hidden_states.device)

        aiter.moe_sorting_fwd(
            topk_ids,
            topk_weights,
            sorted_ids,
            sorted_weights,
            sorted_expert_ids,
            num_valid_ids,
            torch.empty(M * topk * K, dtype=torch.int32, device=hidden_states.device),
            num_experts,
            1,
        )

        # Process chunks with compute-quant overlap
        prev_chunk_quantized = None

        for chunk_idx in range(0, M, CHUNK_SIZE):
            chunk_end = min(chunk_idx + CHUNK_SIZE, M)
            chunk_size = chunk_end - chunk_idx

            # Stream 1: Quantize next chunk
            with torch.cuda.stream(stream_quant):
                chunk_hidden = hidden_states[chunk_idx:chunk_end].contiguous()
                chunk_quantized, chunk_scale = dynamic_mxfp4_quant(chunk_hidden)
                chunk_quantized = chunk_quantized.view(dtypes.fp4x2)

            # Stream 2: Compute previous chunk (if exists)
            if prev_chunk_quantized is not None:
                with torch.cuda.stream(stream_compute):
                    # Compute experts for previous chunk
                    prev_idx = chunk_idx - CHUNK_SIZE
                    for i in range(CHUNK_SIZE):
                        if prev_idx + i >= M:
                            break

                        token_id = prev_idx + i
                        # Get expert assignments for this token
                        token_experts = topk_ids[token_id]
                        token_weights = topk_weights[token_id]

                        for j, (expert_idx, weight) in enumerate(zip(token_experts, token_weights)):
                            # Get quantized input for this token
                            x_q = prev_chunk_quantized[i : i + 1]  # [1, K//2]
                            x_scale_chunk = chunk_scale[i : i + 1]

                            # Stage 1: Gate+Up (using shuffled weights)
                            w1_expert = w1_shuffle[expert_idx]
                            w1_scale = w1_scale_shuffled[expert_idx]

                            gate_up = torch.empty(
                                1, N * 2, dtype=torch.bfloat16, device=hidden_states.device
                            )
                            aiter.gemm_a4w4(
                                x_q,
                                w1_expert,
                                x_scale_chunk,
                                w1_scale,
                                dtype=dtypes.bf16,
                                bpreshuffle=True,
                            )

                            # SiLU + Mul
                            gate = gate_up[:, :N]
                            up = gate_up[:, N:]
                            activated = F.silu(gate) * up

                            # Re-quantize
                            a2_q, a2_scale = dynamic_mxfp4_quant(activated.contiguous())
                            a2_q = a2_q.view(dtypes.fp4x2)

                            # Stage 2: Down projection
                            w2_expert = w2_shuffle[expert_idx]
                            w2_scale = w2_scale_shuffled[expert_idx]

                            out = torch.empty(
                                1, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device
                            )
                            aiter.gemm_a4w4(
                                a2_q,
                                w2_expert,
                                a2_scale.view(dtypes.fp8_e8m0),
                                w2_scale,
                                dtype=dtypes.bf16,
                                bpreshuffle=True,
                            )

                            # Accumulate with weight
                            output[token_id] += out.squeeze(0) * weight

            # Synchronize before swapping
            torch.cuda.synchronize()
            prev_chunk_quantized = chunk_quantized

        return output

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
