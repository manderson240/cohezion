"""Probe: Read matmul.py wrapper + test fast quant paths with tritonblas.

Key hypothesis: dynamic_mxfp4_quant is 62-70 µs. get_triton_quant might be
much faster. If we can use get_triton_quant(shuffle=False) with tritonblas
(which needs un-shuffled scales), we bypass both the shuffle overhead AND
get a faster quantization.
"""
import sys
import inspect
import time
import torch
from task import input_t, output_t
from reference import ref_kernel


def e8m0_unshuffle(scale_shuffled, orig_m, orig_n):
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    scale = scale.view(sm, sn)
    return scale[:orig_m, :orig_n]


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B.shape[0]

    try:
        from tritonblas import matmul_fp4
        import aiter
        from aiter import QuantType
        from aiter.ops.triton.quant import dynamic_mxfp4_quant

        print(f"\n=== QUANT PROBE (m={m}, n={n}, k={k}) ===", file=sys.stderr)

        # --- 1. Read matmul.py source (matmul_fp4 function) ---
        print("\n--- matmul_fp4 source ---", file=sys.stderr)
        try:
            src = inspect.getsource(matmul_fp4)
            for i, line in enumerate(src.splitlines()[:80]):
                print(f"  [{i}] {line}", file=sys.stderr)
        except Exception as e:
            print(f"  source error: {e}", file=sys.stderr)

        # --- 2. Read _make_fp4_matmul_selector if it exists ---
        print("\n--- _make_fp4_matmul_selector / helper functions ---", file=sys.stderr)
        try:
            import tritonblas.matmul as tm
            for name in dir(tm):
                if 'fp4' in name.lower() or 'make' in name.lower() or 'selector' in name.lower():
                    obj = getattr(tm, name)
                    if callable(obj):
                        print(f"\n  --- {name} ---", file=sys.stderr)
                        try:
                            src = inspect.getsource(obj)
                            for i, line in enumerate(src.splitlines()[:40]):
                                print(f"    [{i}] {line}", file=sys.stderr)
                        except:
                            print(f"    sig: {inspect.signature(obj)}", file=sys.stderr)
        except Exception as e:
            print(f"  error: {e}", file=sys.stderr)

        # --- 3. Get truth output from tritonblas default ---
        k_scale = k // 32
        B_scale = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)

        A_fp4_truth, A_scale_truth = dynamic_mxfp4_quant(A.contiguous())
        C_truth = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
        matmul_fp4(A_fp4_truth.view(torch.uint8), B_q.view(torch.uint8), C_truth,
                   A_scale_truth.view(torch.uint8), B_scale)
        torch.cuda.synchronize()

        # --- 4. Test get_triton_quant(shuffle=False) with tritonblas ---
        print("\n--- get_triton_quant(shuffle=False) + tritonblas ---", file=sys.stderr)
        try:
            quant_func = aiter.get_triton_quant(QuantType.per_1x32)
            A_q_tri, A_scale_tri = quant_func(A.contiguous(), shuffle=False)

            print(f"  A_q_tri dtype={A_q_tri.dtype}, shape={A_q_tri.shape}", file=sys.stderr)
            print(f"  A_scale_tri dtype={A_scale_tri.dtype}, shape={A_scale_tri.shape}", file=sys.stderr)

            # Compare A_q: is it identical to dynamic_mxfp4_quant?
            a_data_match = torch.equal(A_q_tri.view(torch.uint8), A_fp4_truth.view(torch.uint8))
            print(f"  A data matches dynamic_mxfp4_quant: {a_data_match}", file=sys.stderr)

            # Compare A_scale
            a_scale_match = torch.equal(A_scale_tri.view(torch.uint8)[:m, :k_scale],
                                         A_scale_truth.view(torch.uint8)[:m, :k_scale])
            print(f"  A scale matches (trimmed): {a_scale_match}", file=sys.stderr)

            if not a_data_match:
                diff = (A_q_tri.view(torch.uint8).float() - A_fp4_truth.view(torch.uint8).float()).abs()
                print(f"  A data diff: max={diff.max():.0f}, nonzero={(diff > 0).sum()}/{diff.numel()}", file=sys.stderr)

            if not a_scale_match:
                diff = (A_scale_tri.view(torch.uint8)[:m,:k_scale].float() - A_scale_truth.view(torch.uint8)[:m,:k_scale].float()).abs()
                print(f"  A scale diff: max={diff.max():.0f}, nonzero={(diff > 0).sum()}/{diff.numel()}", file=sys.stderr)

            # Try using it with tritonblas
            C_tri = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
            A_scale_u8 = A_scale_tri.view(torch.uint8)[:m, :k_scale].contiguous()
            matmul_fp4(A_q_tri.view(torch.uint8), B_q.view(torch.uint8), C_tri,
                       A_scale_u8, B_scale)
            torch.cuda.synchronize()

            max_err_vs_truth = (C_tri.float() - C_truth.float()).abs().max().item()
            print(f"  Max error vs truth: {max_err_vs_truth:.6f}", file=sys.stderr)

            # Time it
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            for _ in range(5):
                A_q_t, A_s_t = quant_func(A.contiguous(), shuffle=False)
            torch.cuda.synchronize()
            tri_quant_us = (time.perf_counter() - t0) / 5 * 1e6
            print(f"  get_triton_quant(shuffle=False) time: {tri_quant_us:.1f} µs", file=sys.stderr)

        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)

        # --- 5. Test get_triton_quant(shuffle=True) + unshuffle ---
        print("\n--- get_triton_quant(shuffle=True) + e8m0_unshuffle ---", file=sys.stderr)
        try:
            A_q_sh, A_scale_sh = quant_func(A.contiguous(), shuffle=True)

            print(f"  A_q_sh dtype={A_q_sh.dtype}, shape={A_q_sh.shape}", file=sys.stderr)
            print(f"  A_scale_sh dtype={A_scale_sh.dtype}, shape={A_scale_sh.shape}", file=sys.stderr)

            # Unshuffle A_scale_sh to get un-shuffled A_scale
            A_scale_unsh = e8m0_unshuffle(A_scale_sh.view(torch.uint8), orig_m=m, orig_n=k_scale)

            a_unsh_match = torch.equal(A_scale_unsh, A_scale_truth.view(torch.uint8)[:m, :k_scale])
            print(f"  Unshuffled A scale matches truth: {a_unsh_match}", file=sys.stderr)

            # Need to also check if shuffled A data is different from unshuffled
            a_data_sh_match = torch.equal(A_q_sh.view(torch.uint8), A_fp4_truth.view(torch.uint8))
            print(f"  A data (shuffled) matches truth: {a_data_sh_match}", file=sys.stderr)

            # Time shuffle=True
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            for _ in range(5):
                A_q_t, A_s_t = quant_func(A.contiguous(), shuffle=True)
            torch.cuda.synchronize()
            tri_quant_sh_us = (time.perf_counter() - t0) / 5 * 1e6
            print(f"  get_triton_quant(shuffle=True) time: {tri_quant_sh_us:.1f} µs", file=sys.stderr)

        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)

        # --- 6. Test get_torch_quant ---
        print("\n--- get_torch_quant ---", file=sys.stderr)
        try:
            torch_quant = aiter.get_torch_quant(QuantType.per_1x32)
            A_q_torch, A_scale_torch = torch_quant(A.contiguous())

            print(f"  A_q_torch dtype={A_q_torch.dtype}, shape={A_q_torch.shape}", file=sys.stderr)
            print(f"  A_scale_torch dtype={A_scale_torch.dtype}, shape={A_scale_torch.shape}", file=sys.stderr)

            a_data_torch_match = torch.equal(A_q_torch.view(torch.uint8), A_fp4_truth.view(torch.uint8))
            print(f"  A data matches truth: {a_data_torch_match}", file=sys.stderr)

            # Try with tritonblas
            C_torch = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
            A_scale_torch_u8 = A_scale_torch.view(torch.uint8)[:m, :k_scale].contiguous()
            matmul_fp4(A_q_torch.view(torch.uint8), B_q.view(torch.uint8), C_torch,
                       A_scale_torch_u8, B_scale)
            torch.cuda.synchronize()
            max_err_torch = (C_torch.float() - C_truth.float()).abs().max().item()
            print(f"  Max error vs truth: {max_err_torch:.6f}", file=sys.stderr)

            torch.cuda.synchronize()
            t0 = time.perf_counter()
            for _ in range(5):
                A_q_t, A_s_t = torch_quant(A.contiguous())
            torch.cuda.synchronize()
            torch_quant_us = (time.perf_counter() - t0) / 5 * 1e6
            print(f"  get_torch_quant time: {torch_quant_us:.1f} µs", file=sys.stderr)

        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)

        # --- 7. Test get_hip_quant ---
        print("\n--- get_hip_quant ---", file=sys.stderr)
        try:
            hip_quant = aiter.get_hip_quant(QuantType.per_1x32)
            A_q_hip, A_scale_hip = hip_quant(A.contiguous())

            print(f"  A_q_hip dtype={A_q_hip.dtype}, shape={A_q_hip.shape}", file=sys.stderr)
            print(f"  A_scale_hip dtype={A_scale_hip.dtype}, shape={A_scale_hip.shape}", file=sys.stderr)

            a_data_hip_match = torch.equal(A_q_hip.view(torch.uint8), A_fp4_truth.view(torch.uint8))
            print(f"  A data matches truth: {a_data_hip_match}", file=sys.stderr)

            # Try with tritonblas
            C_hip = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
            A_scale_hip_u8 = A_scale_hip.view(torch.uint8)[:m, :k_scale].contiguous()
            matmul_fp4(A_q_hip.view(torch.uint8), B_q.view(torch.uint8), C_hip,
                       A_scale_hip_u8, B_scale)
            torch.cuda.synchronize()
            max_err_hip = (C_hip.float() - C_truth.float()).abs().max().item()
            print(f"  Max error vs truth: {max_err_hip:.6f}", file=sys.stderr)

            torch.cuda.synchronize()
            t0 = time.perf_counter()
            for _ in range(5):
                A_q_t, A_s_t = hip_quant(A.contiguous())
            torch.cuda.synchronize()
            hip_quant_us = (time.perf_counter() - t0) / 5 * 1e6
            print(f"  get_hip_quant time: {hip_quant_us:.1f} µs", file=sys.stderr)

        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)

        # --- 8. Time comparison: dynamic_mxfp4_quant ---
        print("\n--- dynamic_mxfp4_quant timing ---", file=sys.stderr)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            _, _ = dynamic_mxfp4_quant(A.contiguous())
        torch.cuda.synchronize()
        dyn_quant_us = (time.perf_counter() - t0) / 5 * 1e6
        print(f"  dynamic_mxfp4_quant time: {dyn_quant_us:.1f} µs", file=sys.stderr)

        # --- 9. Full pipeline timing comparison ---
        print("\n--- FULL PIPELINE COMPARISON ---", file=sys.stderr)

        # Pipeline A: dynamic_mxfp4_quant + tritonblas (current best)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            A_fp4, A_sc = dynamic_mxfp4_quant(A.contiguous())
            B_sc = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)
            C_out = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
            matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C_out,
                       A_sc.view(torch.uint8), B_sc)
        torch.cuda.synchronize()
        pipe_a_us = (time.perf_counter() - t0) / 5 * 1e6
        print(f"  Pipeline A (dynamic_mxfp4_quant + tritonblas): {pipe_a_us:.1f} µs", file=sys.stderr)

        # Pipeline B: get_triton_quant(shuffle=False) + tritonblas (if it works)
        try:
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            for _ in range(5):
                A_q_t, A_s_t = quant_func(A.contiguous(), shuffle=False)
                A_s_u8 = A_s_t.view(torch.uint8)[:m, :k_scale].contiguous()
                B_sc = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)
                C_out = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
                matmul_fp4(A_q_t.view(torch.uint8), B_q.view(torch.uint8), C_out,
                           A_s_u8, B_sc)
            torch.cuda.synchronize()
            pipe_b_us = (time.perf_counter() - t0) / 5 * 1e6
            print(f"  Pipeline B (get_triton_quant + tritonblas):  {pipe_b_us:.1f} µs", file=sys.stderr)
        except Exception as e:
            print(f"  Pipeline B FAILED: {e}", file=sys.stderr)

    except Exception as e:
        print(f"PROBE ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return ref_kernel(data)
