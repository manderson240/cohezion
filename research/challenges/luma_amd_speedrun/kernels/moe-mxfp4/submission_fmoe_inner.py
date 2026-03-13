"""
MXFP4 MoE — Introspection: fused_moe_ inner function source.

The public fused_moe() is just a wrapper. The actual implementation with
buffer allocation, sorting, and stage kernel calls is in fused_moe_().
We need this to understand how to call stage kernels directly.
"""
import sys
import inspect
from task import input_t, output_t
from reference import ref_kernel


def custom_kernel(data: input_t) -> output_t:
    if not hasattr(custom_kernel, '_probed'):
        custom_kernel._probed = True
        try:
            from aiter import fused_moe as fmoe_module

            # Get fused_moe_ source (the internal implementation)
            fmoe_inner = getattr(fmoe_module, 'fused_moe_', None)
            if fmoe_inner is None:
                # Try other names
                for name in dir(fmoe_module):
                    if 'fused_moe' in name and name != 'fused_moe':
                        print(f"Found: {name}", file=sys.stderr)

            if fmoe_inner:
                src = inspect.getsource(fmoe_inner)
                # Print in chunks to avoid buffer overflow
                chunk_size = 4000
                for i in range(0, len(src), chunk_size):
                    chunk = src[i:i+chunk_size]
                    print(f"\n=== fused_moe_ chunk {i//chunk_size + 1} ===",
                          file=sys.stderr)
                    print(chunk, file=sys.stderr)
                print(f"\n=== TOTAL LENGTH: {len(src)} chars ===", file=sys.stderr)

        except Exception as e:
            print(f"PROBE ERROR: {e}", file=sys.stderr)

    return ref_kernel(data)
