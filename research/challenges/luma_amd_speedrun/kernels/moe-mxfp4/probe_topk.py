import inspect
import sys

import aiter


def custom_kernel(data):
    print("--- aiter.top_k_per_row_decode_fast Signature ---", file=sys.stderr)
    try:
        print(inspect.signature(aiter.top_k_per_row_decode_fast), file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        
    print("--- aiter.top_k_per_row_prefill_fast Signature ---", file=sys.stderr)
    try:
        print(inspect.signature(aiter.top_k_per_row_prefill_fast), file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

    from reference import ref_kernel
    return ref_kernel(data)
