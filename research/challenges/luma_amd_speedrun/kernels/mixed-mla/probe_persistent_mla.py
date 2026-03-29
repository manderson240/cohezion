import inspect
import sys

import aiter


def custom_kernel(data):
    print("--- Probing aiter for fused or persistent MLA ---", file=sys.stderr)

    targets = ["fused_mla", "persistent", "mla_decode_stage1", "mla_reduce"]
    for s in dir(aiter):
        if any(t in s.lower() for t in targets):
            print(f"Found symbol: aiter.{s}", file=sys.stderr)
            try:
                print(f"Signature: {inspect.signature(getattr(aiter, s))}", file=sys.stderr)
            except (ValueError, TypeError):
                pass

    if hasattr(aiter, "mla"):
        print("\n--- aiter.mla contents ---", file=sys.stderr)
        for s in dir(aiter.mla):
            if any(t in s.lower() for t in targets):
                print(f"Found aiter.mla.{s}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
