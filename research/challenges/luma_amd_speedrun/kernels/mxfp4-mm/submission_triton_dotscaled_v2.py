"""
MXFP4 GEMM via Triton tl.dot_scaled — probes e8m0_shuffle reversibility.
If we can un-shuffle B_scale_sh, we avoid re-quantizing B entirely.
"""
import sys
import torch
from task import input_t, output_t
from reference import ref_kernel


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    try:
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        from aiter.utility.fp4_utils import e8m0_shuffle

        m, k = A.shape
        n = B.shape[0]

        # 1) Re-quantize B from bf16 to get ground truth un-shuffled scale
        B_fp4_truth, B_scale_truth = dynamic_mxfp4_quant(B.contiguous())

        # 2) Try to un-shuffle B_scale_sh
        # e8m0_shuffle rearranges within each row of the scale tensor.
        # If it's a permutation, we can reverse it.
        B_scale_sh_u8 = B_scale_sh.view(torch.uint8)
        B_scale_truth_u8 = B_scale_truth.view(torch.uint8)

        # Print shapes and check if B_q matches B_fp4_truth
        B_q_match = torch.equal(B_q.view(torch.uint8), B_fp4_truth.view(torch.uint8))
        print(f"B_q matches dynamic_mxfp4_quant output: {B_q_match}", file=sys.stderr)

        # Check if e8m0_shuffle(B_scale_truth) matches B_scale_sh
        B_scale_shuffled = e8m0_shuffle(B_scale_truth.view(torch.float8_e8m0fnu))
        B_scale_shuffled_u8 = B_scale_shuffled.view(torch.uint8)
        shuffle_match = torch.equal(B_scale_shuffled_u8, B_scale_sh_u8)
        print(f"e8m0_shuffle(dynamic_mxfp4_quant_scale) matches B_scale_sh: {shuffle_match}",
              file=sys.stderr)

        # Check shapes
        print(f"B_q shape: {B_q.shape}, dtype: {B_q.dtype}", file=sys.stderr)
        print(f"B_scale_sh shape: {B_scale_sh.shape}, dtype: {B_scale_sh.dtype}", file=sys.stderr)
        print(f"B_scale_truth shape: {B_scale_truth.shape}, dtype: {B_scale_truth.dtype}",
              file=sys.stderr)
        print(f"B_scale_shuffled shape: {B_scale_shuffled.shape}, dtype: {B_scale_shuffled.dtype}",
              file=sys.stderr)

        # Try to find the permutation pattern by checking first row
        if not shuffle_match and n > 0:
            row0_truth = B_scale_truth_u8[0]
            row0_sh = B_scale_sh_u8[0]
            print(f"First row truth (first 16): {row0_truth[:16].tolist()}", file=sys.stderr)
            print(f"First row shuffled (first 16): {row0_sh[:16].tolist()}", file=sys.stderr)

        # If B_q matches, try using B_q + B_scale_truth (skip B re-quant in future)
        if B_q_match:
            print("OPTIMIZATION: Can use input B_q directly!", file=sys.stderr)

    except Exception as e:
        print(f"PROBE ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return ref_kernel(data)
