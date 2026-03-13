"""
MXFP4 MoE — Phase 12: Direct cktile stage kernel calls.

Bypass fused_moe dispatch to call cktile_moe_gemm1/gemm2 directly with
per-shape-optimized block_m and split_k values. This eliminates the
dispatch overhead and allows fine-grained control over kernel parameters.

Step 1: Introspect fused_moe to understand exactly how it calls
cktile_moe_gemm1/gemm2, what intermediate buffers it allocates, and
how sorting/scattering works. Print the full cktile call code to stderr.
"""
import sys
import os
import inspect
from task import input_t, output_t
from reference import ref_kernel


def custom_kernel(data: input_t) -> output_t:
    if not hasattr(custom_kernel, '_probed'):
        custom_kernel._probed = True
        try:
            from aiter.fused_moe import fused_moe as fmoe_fn
            src = inspect.getsource(fmoe_fn)

            # Print the FULL fused_moe function source — we need to understand
            # buffer allocation, sorting, and stage call patterns
            # Limit to ~8000 chars to avoid stderr overflow
            print("=== fused_moe FULL SOURCE (first 8000 chars) ===", file=sys.stderr)
            print(src[:8000], file=sys.stderr)

            if len(src) > 8000:
                print(f"\n=== TRUNCATED ({len(src)} total chars) ===", file=sys.stderr)
                # Print the last 3000 chars (likely contains the cktile calls)
                print("\n=== fused_moe TAIL (last 3000 chars) ===", file=sys.stderr)
                print(src[-3000:], file=sys.stderr)

        except Exception as e:
            print(f"PROBE ERROR: {e}", file=sys.stderr)

    return ref_kernel(data)
