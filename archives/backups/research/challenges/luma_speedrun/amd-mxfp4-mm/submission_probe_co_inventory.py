#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X
import os

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle


def custom_kernel(data):
    A, B, B_q, B_shuffle, B_scale_sh = data
    # Print runner .co inventory
    for d in [
        "/home/runner/aiter/hsa/gfx950/f4gemm/",
        "/home/runner/aiter/hsa/gfx950/fmoe/",
        "/home/runner/aiter/hsa/gfx950/mla/",
    ]:
        if os.path.isdir(d):
            files = sorted(os.listdir(d))
            print(f"[PROBE] {d}: {len(files)} files")
            for f in files[:30]:
                print(f"  {f}")
    # Also check tritonblas
    try:
        import tritonblas

        print(f"[PROBE] tritonblas available: {dir(tritonblas)}")
        print(f"[PROBE] tritonblas.matmul_fp4: {tritonblas.matmul_fp4}")
    except Exception as e:
        print(f"[PROBE] tritonblas: {e}")
    # Also list aiter's full API
    moe_funcs = [x for x in dir(aiter) if "moe" in x.lower() or "fmoe" in x.lower()]
    mla_funcs = [x for x in dir(aiter) if "mla" in x.lower() or "pa_" in x.lower()]
    print(f"[PROBE] aiter MoE APIs: {moe_funcs}")
    print(f"[PROBE] aiter MLA APIs: {mla_funcs}")
    # Still return correct result
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
    )
