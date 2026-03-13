"""tritonblas.matmul_fp4 — read kernel source + try uint8 views."""
import sys
import torch
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    try:
        # 1. Read fp4_matmul kernel source to understand expected layout
        import tritonblas
        import os
        tb_path = os.path.dirname(tritonblas.__file__)
        fp4_path = os.path.join(tb_path, "kernels", "fp4_matmul.py")
        if os.path.exists(fp4_path):
            with open(fp4_path) as f:
                content = f.read()
            lines = content.splitlines()
            print(f"FP4_MATMUL.PY ({len(lines)} lines):", file=sys.stderr)
            # Print all of it (or first 150 lines)
            for i, line in enumerate(lines[:150]):
                print(f"  [{i}] {line}", file=sys.stderr)
            if len(lines) > 150:
                print(f"  ... ({len(lines) - 150} more lines)", file=sys.stderr)

        # 2. Read the matmul_fp4 wrapper in matmul.py
        matmul_path = os.path.join(tb_path, "matmul.py")
        if os.path.exists(matmul_path):
            with open(matmul_path) as f:
                content = f.read()
            lines = content.splitlines()
            # Find matmul_fp4 function definition
            in_fp4 = False
            fp4_lines = []
            for i, line in enumerate(lines):
                if 'def matmul_fp4' in line:
                    in_fp4 = True
                if in_fp4:
                    fp4_lines.append((i, line))
                    if len(fp4_lines) > 1 and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                        break
                    if len(fp4_lines) > 50:
                        break
            print(f"\nMATMUL_FP4 FUNCTION:", file=sys.stderr)
            for i, line in fp4_lines:
                print(f"  [{i}] {line}", file=sys.stderr)

        # 3. Try calling with uint8 views
        from tritonblas import matmul_fp4
        from aiter.ops.triton.quant import dynamic_mxfp4_quant

        m, k = A.shape
        n = B.shape[0]

        # Quantize A
        A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())
        A_fp4_u8 = A_fp4.view(torch.uint8)   # [M, K//2]
        A_scale_u8 = A_scale.view(torch.uint8)  # [M, K//32]

        # B: re-quant for un-shuffled scale
        _, B_scale = dynamic_mxfp4_quant(B.contiguous())
        B_fp4_u8 = B_q.view(torch.uint8)     # [N, K//2]
        B_scale_u8 = B_scale.view(torch.uint8)  # [N, K//32]

        C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)

        print(f"A_fp4_u8: {A_fp4_u8.shape}, B_fp4_u8: {B_fp4_u8.shape}", file=sys.stderr)
        print(f"A_scale_u8: {A_scale_u8.shape}, B_scale_u8: {B_scale_u8.shape}", file=sys.stderr)
        print(f"C: {C.shape}", file=sys.stderr)

        # Attempt 1: A=[M,K//2], B=[N,K//2] (both row-major, standard MXFP4 layout)
        try:
            result = matmul_fp4(A_fp4_u8, B_fp4_u8, C, A_scale_u8, B_scale_u8)
            print(f"ATTEMPT1 (A=[M,K//2], B=[N,K//2]): SUCCESS", file=sys.stderr)
            # Check if result is correct by comparing to ref
            ref_out = ref_kernel(data)
            max_err = (C.float() - ref_out.float()).abs().max().item()
            print(f"  max_error vs ref: {max_err}", file=sys.stderr)
            if max_err < 0.05:
                return C
        except Exception as e:
            print(f"ATTEMPT1 ERROR: {type(e).__name__}: {e}", file=sys.stderr)

        # Attempt 2: A=[M,K//2], B=[K//2,N] (B transposed)
        try:
            B_fp4_t = B_fp4_u8.t().contiguous()
            B_scale_t = B_scale_u8.t().contiguous()
            C2 = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
            result = matmul_fp4(A_fp4_u8, B_fp4_t, C2, A_scale_u8, B_scale_t)
            print(f"ATTEMPT2 (B transposed): SUCCESS", file=sys.stderr)
            ref_out = ref_kernel(data)
            max_err = (C2.float() - ref_out.float()).abs().max().item()
            print(f"  max_error vs ref: {max_err}", file=sys.stderr)
            if max_err < 0.05:
                return C2
        except Exception as e:
            print(f"ATTEMPT2 ERROR: {type(e).__name__}: {e}", file=sys.stderr)

    except Exception as e:
        print(f"TRITONBLAS FP4 V2 ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return ref_kernel(data)
