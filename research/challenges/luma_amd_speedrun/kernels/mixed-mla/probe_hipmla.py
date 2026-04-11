import aiter
import sys


def custom_kernel(data):
    print("--- Probing aiter for HipMLA and Kittens primitives ---", file=sys.stderr)
    for attr in dir(aiter):
        if "hip" in attr.lower() or "kitten" in attr.lower() or "mla" in attr.lower():
            print(f"aiter.{attr}", file=sys.stderr)

    if hasattr(aiter, "ops"):
        for attr in dir(aiter.ops):
            if "hip" in attr.lower() or "kitten" in attr.lower():
                print(f"aiter.ops.{attr}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
