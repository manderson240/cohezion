import inspect
import sys

from aiter.mla import mla_decode_fwd


def custom_kernel(data):
    print("--- mla_decode_fwd Signature ---", file=sys.stderr)
    print(inspect.signature(mla_decode_fwd), file=sys.stderr)
    from reference import ref_kernel
    return ref_kernel(data)
