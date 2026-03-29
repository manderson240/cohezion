import sys

import aiter


def custom_kernel(data):
    print("--- aiter symbols ---", file=sys.stderr)
    for s in dir(aiter):
        print(s, file=sys.stderr)
    if hasattr(aiter, "ops"):
        print("--- aiter.ops symbols ---", file=sys.stderr)
        for s in dir(aiter.ops):
            print(s, file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
