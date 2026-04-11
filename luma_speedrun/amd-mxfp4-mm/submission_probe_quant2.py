#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Compare inline quant vs aiter quant on actual data."""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import struct
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def my_e8m0_scale(max_abs_val: float) -> int:
    """My E8M0 computation (matching fused kernel)."""
    if max_abs_val == 0.0:
        return 0
    target = max_abs_val / 6.0
    bits = struct.unpack("I", struct.pack("f", target))[0]
    exp = (bits >> 23) & 0xFF
    if bits & 0x7FFFFF:
        exp += 1
    return min(max(exp, 1), 254)


def my_fp4_code(v: float) -> int:
    """My FP4 E2M1 with round-to-nearest-even."""
    sign = 8 if v < 0 else 0
    a = abs(v)
    if a <= 0.25:
        code = 0
    elif a < 0.75:
        code = 1
    elif a <= 1.25:
        code = 2
    elif a < 1.75:
        code = 3
    elif a <= 2.5:
        code = 4
    elif a < 3.5:
        code = 5
    elif a <= 5.0:
        code = 6
    else:
        code = 7
    return sign | code


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape

    # Quantize with aiter
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    aiter_fp4 = Aq.view(torch.uint8).cpu()
    aiter_scale = Asc.view(torch.uint8).cpu()

    # My quantization on CPU
    A_cpu = A.contiguous().cpu().float()
    ks = K // 32

    # Compare first 4 rows, first 2 scale groups
    for row in range(min(M, 2)):
        for sg in range(min(ks, 4)):
            start = sg * 32
            end = start + 32
            vals = A_cpu[row, start:end]

            # My scale
            max_abs = vals.abs().max().item()
            my_exp = my_e8m0_scale(max_abs)

            # Aiter scale
            aiter_exp = aiter_scale[row, sg].item()

            scale_match = "✓" if my_exp == aiter_exp else "✗"
            print(
                f"[CMP] row={row} sg={sg}: max_abs={max_abs:.6f} "
                f"my_exp={my_exp} aiter_exp={aiter_exp} {scale_match}"
            )

            if my_exp != aiter_exp:
                # Show the target computation details
                target = max_abs / 6.0
                bits = struct.unpack("I", struct.pack("f", target))[0]
                raw_exp = (bits >> 23) & 0xFF
                has_mantissa = bool(bits & 0x7FFFFF)
                print(f"  target={target:.10f} raw_exp={raw_exp} mantissa_bits={has_mantissa}")

            # Compare FP4 bytes for this group
            if my_exp == aiter_exp:
                inv_scale = 1.0 / (2.0 ** (my_exp - 127)) if my_exp > 0 else 0.0
                mismatches = 0
                for i in range(0, 32, 2):
                    v0 = vals[i].item() * inv_scale
                    v1 = vals[i + 1].item() * inv_scale
                    my_code0 = my_fp4_code(v0)
                    my_code1 = my_fp4_code(v1)
                    my_byte = (my_code1 << 4) | my_code0
                    aiter_byte = aiter_fp4[row, sg * 16 + i // 2].item()
                    if my_byte != aiter_byte:
                        mismatches += 1
                        if mismatches <= 3:
                            a_lo = aiter_byte & 0xF
                            a_hi = (aiter_byte >> 4) & 0xF
                            print(
                                f"  FP4 mismatch byte[{i // 2}]: "
                                f"my=0x{my_byte:02x}({my_code0},{my_code1}) "
                                f"aiter=0x{aiter_byte:02x}({a_lo},{a_hi}) "
                                f"scaled=({v0:.6f},{v1:.6f})"
                            )
                if mismatches > 0:
                    print(f"  {mismatches}/16 bytes mismatch in this group")

    # Actual GEMM
    N = B.shape[0]
    import aiter

    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
    )
