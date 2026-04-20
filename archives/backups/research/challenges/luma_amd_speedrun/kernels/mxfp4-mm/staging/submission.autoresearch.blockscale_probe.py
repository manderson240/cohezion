"""Probe: gemm_a4w4_blockscale — undiscovered kernel variant from recon."""

import sys

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


_probed = False


def custom_kernel(data: input_t) -> output_t:
    global _probed
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    if not _probed:
        _probed = True
        # Inspect gemm_a4w4_blockscale signature
        try:
            import inspect

            sig = inspect.signature(aiter.gemm_a4w4_blockscale)
            print(f"[PROBE] gemm_a4w4_blockscale signature: {sig}", file=sys.stderr)
        except Exception as e:
            print(f"[PROBE] gemm_a4w4_blockscale inspect failed: {e}", file=sys.stderr)

        # Inspect deepgemm and deepgemm_ck
        for name in ["deepgemm", "deepgemm_ck"]:
            fn = getattr(aiter, name, None)
            if fn:
                try:
                    sig = inspect.signature(fn)
                    print(f"[PROBE] {name} signature: {sig}", file=sys.stderr)
                except Exception as e:
                    print(f"[PROBE] {name} inspect failed: {e}", file=sys.stderr)
            else:
                print(f"[PROBE] {name}: NOT FOUND", file=sys.stderr)

        # Inspect gemm_a4w4_blockscale_tune
        fn = getattr(aiter, "gemm_a4w4_blockscale_tune", None)
        if fn:
            try:
                sig = inspect.signature(fn)
                print(f"[PROBE] gemm_a4w4_blockscale_tune signature: {sig}", file=sys.stderr)
            except Exception as e:
                print(f"[PROBE] gemm_a4w4_blockscale_tune inspect failed: {e}", file=sys.stderr)

        # Try calling gemm_a4w4_blockscale with same args as gemm_a4w4
        A_q_raw, A_scale_raw = dynamic_mxfp4_quant(A)
        A_scale_shuffled = e8m0_shuffle(A_scale_raw).view(dtypes.fp8_e8m0)
        A_q = A_q_raw.view(dtypes.fp4x2)
        try:
            C = aiter.gemm_a4w4_blockscale(
                A_q,
                B_shuffle,
                A_scale_shuffled,
                B_scale_sh,
                dtype=dtypes.bf16,
                bpreshuffle=True,
            )
            print(
                f"[PROBE] gemm_a4w4_blockscale SUCCEEDED: output shape={C.shape}, dtype={C.dtype}",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"[PROBE] gemm_a4w4_blockscale FAILED: {e}", file=sys.stderr)

    # Fallback to working gemm_a4w4
    A_q_raw, A_scale_raw = dynamic_mxfp4_quant(A)
    A_scale_shuffled = e8m0_shuffle(A_scale_raw).view(dtypes.fp8_e8m0)
    A_q = A_q_raw.view(dtypes.fp4x2)
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_shuffled,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
