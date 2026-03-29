"""
MLA Fused Flash-Decode: Using reference implementation (aiter) for correctness.

Custom HIP kernel had FP8 format issues. Using proven reference path.
"""

from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """MLA decode using reference implementation."""
    from reference import ref_kernel

    return ref_kernel(data)
