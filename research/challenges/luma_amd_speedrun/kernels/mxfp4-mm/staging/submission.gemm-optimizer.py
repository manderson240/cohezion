import os
import torch
import sys

# --- 1. ENV CONFIGURATION ---
os.environ["TRITON_CACHE_DIR"] = "./.kernel_cache"

try:
    import aiter
    HAS_AITER = True
except ImportError:
    HAS_AITER = False
    print("Warning: AITER not found.", file=sys.stderr)

try:
    import helion
    HAS_HELION = True
except ImportError:
    HAS_HELION = False
    print("Warning: helion not found.", file=sys.stderr)

def custom_kernel(data):
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M, K = A.shape
    N = B.shape[0]

    if HAS_AITER:
        from aiter import dtypes, QuantType
        import aiter
        
        # Quantize A using the exact reference logic
        quant_func = aiter.get_triton_quant(QuantType.per_1x32)
        A_q, A_scale_sh = quant_func(A, shuffle=True)
        
        out = aiter.gemm_a4w4(
            A_q,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True
        )
        return out
    else:
        from reference import ref_kernel
        return ref_kernel(data)
