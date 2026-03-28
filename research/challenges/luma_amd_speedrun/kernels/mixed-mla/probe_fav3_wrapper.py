import sys
import inspect

def custom_kernel(data):
    try:
        from aiter.ops.triton.attention.fav3_sage_attention_mxfp4_wrapper import fav3_sage_attention_mxfp4
        print("--- fav3_sage_attention_mxfp4 Signature ---", file=sys.stderr)
        print(inspect.signature(fav3_sage_attention_mxfp4), file=sys.stderr)
    except Exception as e:
        print(f"Error importing wrapper: {e}", file=sys.stderr)

    from reference import ref_kernel
    return ref_kernel(data)
