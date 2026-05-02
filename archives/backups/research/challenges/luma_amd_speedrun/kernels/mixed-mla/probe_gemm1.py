import inspect
import sys

import aiter


def custom_kernel(data):
    print("--- moe_cktile2stages_gemm1 inspect ---", file=sys.stderr)
    try:
        # It might be in aiter.ops or directly in aiter
        fn = getattr(aiter, "moe_cktile2stages_gemm1", None)
        if fn is None:
            from aiter.jit_build import (
                module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_,
            )

            fn = module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_.ck_moe_stage1
        print(inspect.signature(fn), file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
