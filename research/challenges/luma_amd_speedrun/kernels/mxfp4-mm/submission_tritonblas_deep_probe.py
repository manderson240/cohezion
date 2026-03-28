"""Deep probe: tritonblas API exploration + timing breakdown.

Explores matmul_lt, matmul, OrigamiMatmulSelector internals,
and measures A quantization vs GEMM time to find the bottleneck.
"""
import sys
import inspect
import time
import torch
from task import input_t, output_t
from reference import ref_kernel


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B.shape[0]

    try:
        import tritonblas
        print(f"\n=== TRITONBLAS DEEP PROBE (m={m}, n={n}, k={k}) ===", file=sys.stderr)

        # 1. ALL exports and their types
        print("\n--- ALL EXPORTS ---", file=sys.stderr)
        for name in sorted(dir(tritonblas)):
            if not name.startswith('_'):
                obj = getattr(tritonblas, name)
                print(f"  {name}: {type(obj).__name__}", file=sys.stderr)

        # 2. matmul_lt signature and source
        print("\n--- matmul_lt ---", file=sys.stderr)
        try:
            from tritonblas import matmul_lt
            sig = inspect.signature(matmul_lt)
            print(f"  sig: {sig}", file=sys.stderr)
            try:
                src = inspect.getsource(matmul_lt)
                for i, line in enumerate(src.splitlines()[:60]):
                    print(f"  [{i}] {line}", file=sys.stderr)
            except Exception as e:
                print(f"  source error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"  import error: {e}", file=sys.stderr)

        # 3. matmul signature and source
        print("\n--- matmul ---", file=sys.stderr)
        try:
            from tritonblas import matmul
            sig = inspect.signature(matmul)
            print(f"  sig: {sig}", file=sys.stderr)
            try:
                src = inspect.getsource(matmul)
                for i, line in enumerate(src.splitlines()[:60]):
                    print(f"  [{i}] {line}", file=sys.stderr)
            except Exception as e:
                print(f"  source error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"  import error: {e}", file=sys.stderr)

        # 4. OrigamiMatmulSelector
        print("\n--- OrigamiMatmulSelector ---", file=sys.stderr)
        try:
            from tritonblas import OrigamiMatmulSelector
            print(f"  type: {type(OrigamiMatmulSelector)}", file=sys.stderr)
            print(f"  methods: {[m for m in dir(OrigamiMatmulSelector) if not m.startswith('_')]}", file=sys.stderr)
            try:
                src = inspect.getsource(OrigamiMatmulSelector)
                for i, line in enumerate(src.splitlines()[:80]):
                    print(f"  [{i}] {line}", file=sys.stderr)
            except Exception as e:
                print(f"  source error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"  import error: {e}", file=sys.stderr)

        # 5. Read tritonblas __init__.py source
        print("\n--- __init__.py (imports) ---", file=sys.stderr)
        try:
            init_file = inspect.getfile(tritonblas)
            with open(init_file) as f:
                for i, line in enumerate(f.readlines()[:40]):
                    print(f"  [{i}] {line.rstrip()}", file=sys.stderr)
        except Exception as e:
            print(f"  error: {e}", file=sys.stderr)

        # 6. List all tritonblas submodules/files
        print("\n--- tritonblas package files ---", file=sys.stderr)
        import os
        pkg_dir = os.path.dirname(inspect.getfile(tritonblas))
        for root, dirs, files in os.walk(pkg_dir):
            for f in sorted(files):
                if f.endswith('.py'):
                    rel = os.path.relpath(os.path.join(root, f), pkg_dir)
                    print(f"  {rel}", file=sys.stderr)

        # 7. Timing breakdown: quantization vs GEMM
        print("\n--- TIMING BREAKDOWN ---", file=sys.stderr)
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        from tritonblas import matmul_fp4

        # Warmup
        A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())
        C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)

        def e8m0_unshuffle(scale_shuffled, orig_m, orig_n):
            sm, sn = scale_shuffled.shape
            scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
            scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
            scale = scale.view(sm, sn)
            return scale[:orig_m, :orig_n]

        k_scale = k // 32
        B_scale = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)

        # Warmup GEMM
        matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C,
                   A_scale.view(torch.uint8), B_scale)
        torch.cuda.synchronize()

        # Time quantization (5 runs)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            A_fp4_t, A_scale_t = dynamic_mxfp4_quant(A.contiguous())
        torch.cuda.synchronize()
        quant_us = (time.perf_counter() - t0) / 5 * 1e6

        # Time GEMM only (5 runs)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C,
                       A_scale.view(torch.uint8), B_scale)
        torch.cuda.synchronize()
        gemm_us = (time.perf_counter() - t0) / 5 * 1e6

        # Time e8m0_shuffle for A_scale (our overhead)
        from aiter.utility.fp4_utils import e8m0_shuffle
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            _ = e8m0_shuffle(A_scale_t.view(torch.float8_e8m0fnu) if hasattr(torch, 'float8_e8m0fnu') else A_scale_t)
        torch.cuda.synchronize()
        shuffle_us = (time.perf_counter() - t0) / 5 * 1e6

        # Time unshuffle for B_scale
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            _ = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)
        torch.cuda.synchronize()
        unshuffle_us = (time.perf_counter() - t0) / 5 * 1e6

        # Time full pipeline
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            A_fp4_p, A_scale_p = dynamic_mxfp4_quant(A.contiguous())
            B_scale_p = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)
            C_p = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
            matmul_fp4(A_fp4_p.view(torch.uint8), B_q.view(torch.uint8), C_p,
                       A_scale_p.view(torch.uint8), B_scale_p)
        torch.cuda.synchronize()
        total_us = (time.perf_counter() - t0) / 5 * 1e6

        print(f"  A quant (dynamic_mxfp4_quant): {quant_us:.1f} µs", file=sys.stderr)
        print(f"  e8m0_shuffle (A_scale):        {shuffle_us:.1f} µs", file=sys.stderr)
        print(f"  e8m0_unshuffle (B_scale):      {unshuffle_us:.1f} µs", file=sys.stderr)
        print(f"  GEMM (matmul_fp4):             {gemm_us:.1f} µs", file=sys.stderr)
        print(f"  Full pipeline:                 {total_us:.1f} µs", file=sys.stderr)
        print(f"  Overhead (quant+shuffle):      {quant_us + shuffle_us:.1f} µs ({(quant_us+shuffle_us)/total_us*100:.0f}%)", file=sys.stderr)

        # 8. Try matmul_fp4 with custom tile sizes
        print("\n--- TILE SWEEP (matmul_fp4) ---", file=sys.stderr)
        configs = [
            (16, 16, 64), (16, 32, 64), (16, 64, 64), (16, 128, 64),
            (32, 32, 64), (32, 64, 64), (32, 128, 64), (32, 256, 64),
            (64, 64, 64), (64, 128, 64), (64, 256, 64),
            (128, 128, 64), (128, 256, 64),
            (16, 16, 128), (32, 32, 128), (64, 64, 128),
            (16, 64, 128), (32, 128, 128), (64, 256, 128),
        ]
        for bm, bn, bk in configs:
            try:
                C_t = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
                matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C_t,
                           A_scale.view(torch.uint8), B_scale,
                           block_m=bm, block_n=bn, block_k=bk)
                torch.cuda.synchronize()

                # Quick timing (3 runs)
                torch.cuda.synchronize()
                t0 = time.perf_counter()
                for _ in range(3):
                    matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C_t,
                               A_scale.view(torch.uint8), B_scale,
                               block_m=bm, block_n=bn, block_k=bk)
                torch.cuda.synchronize()
                tile_us = (time.perf_counter() - t0) / 3 * 1e6

                # Check correctness vs default
                C_ref = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
                matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C_ref,
                           A_scale.view(torch.uint8), B_scale)
                max_err = (C_t.float() - C_ref.float()).abs().max().item()

                print(f"  ({bm:3d},{bn:3d},{bk:3d}): {tile_us:8.1f} µs  err={max_err:.4f}", file=sys.stderr)
            except Exception as e:
                err_str = str(e)[:80]
                print(f"  ({bm:3d},{bn:3d},{bk:3d}): FAIL: {err_str}", file=sys.stderr)

        # 9. Also try num_warps and num_stages variations on best tile
        print("\n--- WARPS/STAGES SWEEP ---", file=sys.stderr)
        for nw in [2, 4, 8, 16]:
            for ns in [1, 2, 3, 4]:
                try:
                    C_t = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
                    matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C_t,
                               A_scale.view(torch.uint8), B_scale,
                               num_warps=nw, num_stages=ns)
                    torch.cuda.synchronize()
                    t0 = time.perf_counter()
                    for _ in range(3):
                        matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C_t,
                                   A_scale.view(torch.uint8), B_scale,
                                   num_warps=nw, num_stages=ns)
                    torch.cuda.synchronize()
                    ws_us = (time.perf_counter() - t0) / 3 * 1e6
                    print(f"  warps={nw:2d} stages={ns}: {ws_us:8.1f} µs", file=sys.stderr)
                except Exception as e:
                    print(f"  warps={nw:2d} stages={ns}: FAIL: {str(e)[:60]}", file=sys.stderr)

    except Exception as e:
        print(f"PROBE ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return ref_kernel(data)
