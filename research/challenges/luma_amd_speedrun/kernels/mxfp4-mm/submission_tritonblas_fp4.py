"""Probe: tritonblas.matmul_fp4 signature + attempt MXFP4 GEMM."""
import sys
import os
import inspect
import torch
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    try:
        # 1. Get matmul_fp4 signature
        from tritonblas import matmul_fp4
        sig = inspect.signature(matmul_fp4)
        print(f"MATMUL_FP4 SIGNATURE: {sig}", file=sys.stderr)

        # 2. Read fp4_matmul source (from tritonblas.kernels)
        try:
            from tritonblas.kernels import fp4_matmul
            fp4_path = inspect.getfile(fp4_matmul)
            print(f"FP4_MATMUL PATH: {fp4_path}", file=sys.stderr)
            with open(fp4_path) as f:
                content = f.read()
            # Print first 100 lines to understand the kernel
            for i, line in enumerate(content.splitlines()[:100]):
                print(f"FP4_SRC[{i}]: {line}", file=sys.stderr)
        except Exception as e:
            print(f"FP4_MATMUL SOURCE ERROR: {type(e).__name__}: {e}", file=sys.stderr)

        # 3. Read matmul.py source (where matmul_fp4 is defined)
        try:
            matmul_path = inspect.getfile(matmul_fp4)
            print(f"MATMUL_FP4 PATH: {matmul_path}", file=sys.stderr)
            with open(matmul_path) as f:
                content = f.read()
            # Find matmul_fp4 definition
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if 'matmul_fp4' in line or 'fp4' in line.lower():
                    # Print surrounding context
                    start = max(0, i - 2)
                    end = min(len(lines), i + 15)
                    for j in range(start, end):
                        print(f"MATMUL_SRC[{j}]: {lines[j]}", file=sys.stderr)
                    print("---", file=sys.stderr)
                    break
        except Exception as e:
            print(f"MATMUL SOURCE ERROR: {type(e).__name__}: {e}", file=sys.stderr)

        # 4. Check OrigamiMatmulSelector
        try:
            from tritonblas import OrigamiMatmulSelector
            print(f"ORIGAMI: {dir(OrigamiMatmulSelector)}", file=sys.stderr)
            origami_path = inspect.getfile(OrigamiMatmulSelector)
            print(f"ORIGAMI PATH: {origami_path}", file=sys.stderr)
        except Exception as e:
            print(f"ORIGAMI ERROR: {type(e).__name__}: {e}", file=sys.stderr)

        # 5. Try calling matmul_fp4 with our data
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        from aiter import dtypes

        m, k = A.shape
        n = B.shape[0]

        # Quantize A
        A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())
        # B_q is already quantized fp4 data
        B_fp4 = B_q

        print(f"A_fp4: shape={A_fp4.shape}, dtype={A_fp4.dtype}", file=sys.stderr)
        print(f"A_scale: shape={A_scale.shape}, dtype={A_scale.dtype}", file=sys.stderr)
        print(f"B_fp4: shape={B_fp4.shape}, dtype={B_fp4.dtype}", file=sys.stderr)
        print(f"B_scale_sh: shape={B_scale_sh.shape}, dtype={B_scale_sh.dtype}", file=sys.stderr)

        # Pre-allocate output
        C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)

        # Try various call patterns based on what the signature tells us
        try:
            result = matmul_fp4(A_fp4, B_fp4, C)
            print(f"MATMUL_FP4 SUCCESS (no scales): result shape={result.shape if result is not None else 'None'}", file=sys.stderr)
        except Exception as e:
            print(f"MATMUL_FP4 ATTEMPT1 ERROR: {type(e).__name__}: {e}", file=sys.stderr)

        try:
            result = matmul_fp4(A_fp4, B_fp4, C, A_scale, B_scale_sh)
            print(f"MATMUL_FP4 SUCCESS (with scales): result shape={result.shape if result is not None else 'None'}", file=sys.stderr)
        except Exception as e:
            print(f"MATMUL_FP4 ATTEMPT2 ERROR: {type(e).__name__}: {e}", file=sys.stderr)

    except Exception as e:
        print(f"TRITONBLAS FP4 ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return ref_kernel(data)
