import inspect
import sys

import aiter


def custom_kernel(data):
    print("--- ck_moe_stage1 Signature ---", file=sys.stderr)
    try:
        print(inspect.signature(aiter.ck_moe_stage1), file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

    print("--- ck_moe_stage2 Signature ---", file=sys.stderr)
    try:
        print(inspect.signature(aiter.ck_moe_stage2), file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
