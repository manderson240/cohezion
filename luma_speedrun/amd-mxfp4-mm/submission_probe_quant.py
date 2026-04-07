#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Extract aiter's FP4 quantization details for matching in custom kernel."""

import os
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
import inspect
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Probe 1: Print dynamic_mxfp4_quant source
    try:
        src = inspect.getsource(dynamic_mxfp4_quant)
        print(f"[PROBE] dynamic_mxfp4_quant source:\n{src[:2000]}")
    except Exception as e:
        print(f"[PROBE] Cannot get source: {e}")

    # Probe 2: Test quantization on known values
    test_vals = torch.tensor([
        [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0,
         -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0, 0.25,
         0.3, 0.7, 0.8, 1.2, 1.3, 1.7, 1.8, 2.4,
         2.6, 3.4, 3.6, 4.9, 5.1, 7.0, 0.1, 0.0]
    ], dtype=torch.bfloat16, device="cuda")

    fp4_data, scale = dynamic_mxfp4_quant(test_vals)
    fp4_bytes = fp4_data.view(torch.uint8)
    scale_bytes = scale.view(torch.uint8)

    print(f"[PROBE] Input shape: {test_vals.shape}, K={test_vals.shape[1]}")
    print(f"[PROBE] FP4 bytes ({fp4_bytes.shape}): {fp4_bytes.cpu().tolist()}")
    print(f"[PROBE] Scale bytes ({scale_bytes.shape}): {scale_bytes.cpu().tolist()}")

    # Probe 3: Decode the FP4 bytes to see exact quantization
    for i in range(16):
        byte_val = fp4_bytes[0, i].item()
        lo = byte_val & 0xF
        hi = (byte_val >> 4) & 0xF
        orig0 = test_vals[0, 2*i].item()
        orig1 = test_vals[0, 2*i+1].item()
        print(f"[PROBE] byte[{i}]=0x{byte_val:02x}: "
              f"elem[{2*i}]={orig0:.4f}→{lo:04b}({lo}), "
              f"elem[{2*i+1}]={orig1:.4f}→{hi:04b}({hi})")

    # Probe 4: Check E8M0 scale value
    print(f"[PROBE] E8M0 scale raw: {scale_bytes[0, 0].item()}")
    scale_exp = scale_bytes[0, 0].item()
    if scale_exp > 0:
        scale_val = 2.0 ** (scale_exp - 127)
        print(f"[PROBE] Scale = 2^({scale_exp}-127) = {scale_val}")
        print(f"[PROBE] Max input abs = {test_vals.abs().max().item()}")
        print(f"[PROBE] Max/scale = {test_vals.abs().max().item() / scale_val}")

    # Probe 5: Check module path for Triton kernel source
    try:
        import aiter.ops.triton.quant as qmod
        print(f"[PROBE] quant module file: {qmod.__file__}")
    except Exception as e:
        print(f"[PROBE] Cannot find quant module: {e}")

    # Do the actual GEMM for the test to pass
    import aiter
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh,
                           dtype=dtypes.bf16, bpreshuffle=True)
