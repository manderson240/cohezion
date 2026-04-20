"""
Runner Probe: Identifying the S500 Stream Fault Culprit

We will test four different execution paths to isolate exactly where
the "Work on another stream" error occurs.
"""
#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

import torch
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]

    # PROBE 1: Pure PyTorch
    # This should always pass.
    out_torch = torch.zeros((m, n), dtype=torch.bfloat16, device=A.device)
    out_torch += 1.0

    # PROBE 2: Triton (The Quantization Path)
    # If this fails, the S500 is triggered by Triton, not the GEMM kernel.
    try:
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        from aiter.utility.fp4_utils import e8m0_shuffle

        A_fp4, A_scale = dynamic_mxfp4_quant(A)
        A_scale_u8 = A_scale.view(
            torch.float8_e4m3fn if hasattr(torch, "float8_e4m3fn") else torch.float32
        ).contiguous()
        _ = e8m0_shuffle(A_scale_u8)
        print("PROBE 2 (Triton) SUCCESS")
    except Exception as e:
        print(f"PROBE 2 (Triton) FAILED: {e}")
        return out_torch

    # PROBE 3: aiter Wrapper without Triton
    # Use pre-quantized inputs to see if the wrapper itself is the problem.
    try:
        import aiter

        # Use B_q as a dummy A_q since it's already quantized
        # This bypasses the Triton path.
        A_q = B_q.view(torch.float32)  # dummy view
        # We don't actually care about the result, just the launch.
        # Using a very small size to avoid timeouts.
        _ = aiter.f4gemm_bf16_per1x32Fp4(
            A_q[:1, :1], B_shuffle[:1, :1], B_scale_sh[:1, :1], B_scale_sh[:1, :1], m=1, n=1, k=k
        )
        print("PROBE 3 (aiter Wrapper) SUCCESS")
    except Exception as e:
        print(f"PROBE 3 (aiter Wrapper) FAILED: {e}")
        return out_torch

    # PROBE 4: Full Pipeline
    try:
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        from aiter.utility.fp4_utils import e8m0_shuffle

        A_fp4, A_scale = dynamic_mxfp4_quant(A)
        A_scale_u8 = A_scale.view(
            torch.float8_e4m3fn if hasattr(torch, "float8_e4m3fn") else torch.float32
        ).contiguous()
        A_scale_sh = e8m0_shuffle(A_scale_u8)
        A_q = A_fp4.view(torch.float32)  # dummy

        import aiter

        _ = aiter.f4gemm_bf16_per1x32Fp4(A_q, B_shuffle, A_scale_sh, B_scale_sh, m=m, n=n, k=k)
        print("PROBE 4 (Full) SUCCESS")
    except Exception as e:
        print(f"PROBE 4 (Full) FAILED: {e}")
        return out_torch

    return out_torch
