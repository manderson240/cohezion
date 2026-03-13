"""
MXFP4 GEMM — K-split probe: discover log2_k_split impact on timing.

Tests log2_k_split=1,2,3 for each benchmark shape by printing timing
to stderr. The log2_k_split parameter splits the K dimension across
multiple CU groups, potentially improving utilization for small M.

Shape analysis:
- m=8, k=7168: very small M, large K → K-split may help (more CUs active)
- m=16, k=1536: small M, medium K → K-split may help
- m=64, k=1536: medium M, medium K → K-split neutral or harmful
- m=256, k=512: large M, small K → K-split harmful (overhead > gain)
"""
import sys
import time
import aiter
from aiter import QuantType, dtypes
from task import input_t, output_t

_quant_func = None
_call_count = 0


def custom_kernel(data: input_t) -> output_t:
    global _quant_func, _call_count
    _call_count += 1
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    if _quant_func is None:
        _quant_func = aiter.get_torch_quant(QuantType.per_1x32)

    A_q, A_scale_sh = _quant_func(A, shuffle=True)
    m, k = A.shape
    n = B_shuffle.shape[0]

    # Only probe on first few calls to get timing data
    if _call_count <= 4:
        import torch
        torch.cuda.synchronize()

        results = []
        for log2_k in [None, 0, 1, 2, 3]:
            # Warmup
            for _ in range(3):
                _ = aiter.gemm_a4w4(A_q, B_shuffle, A_scale_sh, B_scale_sh,
                                    dtype=dtypes.bf16, bpreshuffle=True)
            torch.cuda.synchronize()

            # Time it
            t0 = time.perf_counter()
            for _ in range(10):
                out = aiter.gemm_a4w4(A_q, B_shuffle, A_scale_sh, B_scale_sh,
                                      dtype=dtypes.bf16, bpreshuffle=True)
            torch.cuda.synchronize()
            elapsed_us = (time.perf_counter() - t0) * 1e6 / 10
            results.append((log2_k, elapsed_us))

        print(f"\n=== Shape m={m}, k={k}, n={n} ===", file=sys.stderr)
        for log2_k, us in results:
            print(f"  log2_k_split={log2_k}: {us:.1f} us", file=sys.stderr)

    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
