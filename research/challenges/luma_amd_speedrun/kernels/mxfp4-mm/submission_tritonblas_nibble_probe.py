"""Probe: Test nibble-swap hypothesis for get_hip_quant + tritonblas.

Hypothesis: get_hip_quant and dynamic_mxfp4_quant produce different nibble
ordering in fp4 packed bytes. If we swap nibbles, hip_quant output becomes
compatible with tritonblas. This would give us 15 µs quant + 30 µs GEMM
instead of 35 µs quant + 30 µs GEMM.
"""
import sys
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
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        import aiter
        from aiter import QuantType

        print(f"\n=== NIBBLE PROBE (m={m}, n={n}, k={k}) ===", file=sys.stderr)

        k_scale = k // 32
        B_scale = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)

        # Truth: dynamic_mxfp4_quant + tritonblas
        A_fp4_truth, A_scale_truth = dynamic_mxfp4_quant(A.contiguous())
        A_truth_u8 = A_fp4_truth.view(torch.uint8)

        # --- 1. Analyze byte-level differences ---
        # get_hip_quant
        hip_quant = aiter.get_hip_quant(QuantType.per_1x32)
        A_q_hip, A_scale_hip = hip_quant(A.contiguous())
        A_hip_u8 = A_q_hip.view(torch.uint8)

        # get_triton_quant(shuffle=False)
        triton_quant = aiter.get_triton_quant(QuantType.per_1x32)
        A_q_tri, A_scale_tri = triton_quant(A.contiguous(), shuffle=False)
        A_tri_u8 = A_q_tri.view(torch.uint8)

        # Show first 16 bytes comparison
        print("\n--- First 16 bytes (row 0) ---", file=sys.stderr)
        print(f"  truth:  {A_truth_u8[0, :16].tolist()}", file=sys.stderr)
        print(f"  hip:    {A_hip_u8[0, :16].tolist()}", file=sys.stderr)
        print(f"  triton: {A_tri_u8[0, :16].tolist()}", file=sys.stderr)

        # Nibble-swapped versions
        A_hip_swapped = ((A_hip_u8 & 0x0F) << 4) | ((A_hip_u8 >> 4) & 0x0F)
        A_tri_swapped = ((A_tri_u8 & 0x0F) << 4) | ((A_tri_u8 >> 4) & 0x0F)

        print(f"  hip_sw: {A_hip_swapped[0, :16].tolist()}", file=sys.stderr)
        print(f"  tri_sw: {A_tri_swapped[0, :16].tolist()}", file=sys.stderr)

        # Check which swap matches truth
        hip_direct_match = torch.equal(A_hip_u8, A_truth_u8)
        hip_swap_match = torch.equal(A_hip_swapped, A_truth_u8)
        tri_direct_match = torch.equal(A_tri_u8, A_truth_u8)
        tri_swap_match = torch.equal(A_tri_swapped, A_truth_u8)

        print(f"\n--- Match analysis ---", file=sys.stderr)
        print(f"  hip direct match: {hip_direct_match}", file=sys.stderr)
        print(f"  hip nibble-swap match: {hip_swap_match}", file=sys.stderr)
        print(f"  triton direct match: {tri_direct_match}", file=sys.stderr)
        print(f"  triton nibble-swap match: {tri_swap_match}", file=sys.stderr)

        # Partial match counts
        hip_direct_pct = (A_hip_u8 == A_truth_u8).float().mean().item()
        hip_swap_pct = (A_hip_swapped == A_truth_u8).float().mean().item()
        tri_direct_pct = (A_tri_u8 == A_truth_u8).float().mean().item()
        tri_swap_pct = (A_tri_swapped == A_truth_u8).float().mean().item()

        print(f"  hip direct match %: {hip_direct_pct:.4f}", file=sys.stderr)
        print(f"  hip nibble-swap match %: {hip_swap_pct:.4f}", file=sys.stderr)
        print(f"  triton direct match %: {tri_direct_pct:.4f}", file=sys.stderr)
        print(f"  triton nibble-swap match %: {tri_swap_pct:.4f}", file=sys.stderr)

        # --- 2. Check if hip and triton match each other ---
        hip_tri_match = torch.equal(A_hip_u8, A_tri_u8)
        hip_tri_pct = (A_hip_u8 == A_tri_u8).float().mean().item()
        print(f"\n  hip==triton: {hip_tri_match} ({hip_tri_pct:.4f})", file=sys.stderr)

        # --- 3. Try nibble-swapped hip with tritonblas GEMM ---
        print("\n--- Nibble-swap GEMM tests ---", file=sys.stderr)

        C_truth = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
        matmul_fp4(A_truth_u8, B_q.view(torch.uint8), C_truth,
                   A_scale_truth.view(torch.uint8), B_scale)
        torch.cuda.synchronize()

        # Test: hip direct + tritonblas
        C_hip_direct = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
        A_scale_hip_u8 = A_scale_hip.view(torch.uint8)[:m, :k_scale].contiguous()
        matmul_fp4(A_hip_u8, B_q.view(torch.uint8), C_hip_direct,
                   A_scale_hip_u8, B_scale)
        err_hip_direct = (C_hip_direct.float() - C_truth.float()).abs().max().item()
        print(f"  hip direct → err vs truth: {err_hip_direct:.4f}", file=sys.stderr)

        # Test: hip nibble-swapped + tritonblas
        C_hip_swap = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
        matmul_fp4(A_hip_swapped, B_q.view(torch.uint8), C_hip_swap,
                   A_scale_hip_u8, B_scale)
        err_hip_swap = (C_hip_swap.float() - C_truth.float()).abs().max().item()
        print(f"  hip nibble-swap → err vs truth: {err_hip_swap:.4f}", file=sys.stderr)

        # Test: triton direct + tritonblas
        C_tri_direct = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
        A_scale_tri_u8 = A_scale_tri.view(torch.uint8)[:m, :k_scale].contiguous()
        matmul_fp4(A_tri_u8, B_q.view(torch.uint8), C_tri_direct,
                   A_scale_tri_u8, B_scale)
        err_tri_direct = (C_tri_direct.float() - C_truth.float()).abs().max().item()
        print(f"  triton direct → err vs truth: {err_tri_direct:.4f}", file=sys.stderr)

        # Test: triton nibble-swapped + tritonblas
        C_tri_swap = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
        matmul_fp4(A_tri_swapped, B_q.view(torch.uint8), C_tri_swap,
                   A_scale_tri_u8, B_scale)
        err_tri_swap = (C_tri_swap.float() - C_truth.float()).abs().max().item()
        print(f"  triton nibble-swap → err vs truth: {err_tri_swap:.4f}", file=sys.stderr)

        # --- 4. Also test hip/triton against ref_kernel output ---
        ref_out = ref_kernel(data)
        err_truth_vs_ref = (C_truth.float() - ref_out.float()).abs().max().item()
        err_hip_direct_vs_ref = (C_hip_direct.float() - ref_out.float()).abs().max().item()
        err_hip_swap_vs_ref = (C_hip_swap.float() - ref_out.float()).abs().max().item()

        print(f"\n--- vs REFERENCE ---", file=sys.stderr)
        print(f"  truth (dynamic_mxfp4_quant) vs ref: {err_truth_vs_ref:.4f}", file=sys.stderr)
        print(f"  hip direct vs ref: {err_hip_direct_vs_ref:.4f}", file=sys.stderr)
        print(f"  hip nibble-swap vs ref: {err_hip_swap_vs_ref:.4f}", file=sys.stderr)

        # --- 5. Nibble pattern analysis ---
        print("\n--- Nibble pattern analysis ---", file=sys.stderr)
        # For each byte, extract high and low nibbles
        truth_hi = (A_truth_u8 >> 4) & 0x0F
        truth_lo = A_truth_u8 & 0x0F
        hip_hi = (A_hip_u8 >> 4) & 0x0F
        hip_lo = A_hip_u8 & 0x0F

        # Check if hip's nibbles are in opposite positions
        cross_match_1 = (truth_hi == hip_lo).float().mean().item()  # truth_hi matches hip_lo
        cross_match_2 = (truth_lo == hip_hi).float().mean().item()  # truth_lo matches hip_hi
        print(f"  truth_hi == hip_lo: {cross_match_1:.4f}", file=sys.stderr)
        print(f"  truth_lo == hip_hi: {cross_match_2:.4f}", file=sys.stderr)

        # --- 6. Timing: full pipeline with hip_quant if it works ---
        print("\n--- PIPELINE TIMING ---", file=sys.stderr)

        # Pipeline: dynamic_mxfp4_quant + tritonblas
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(10):
            A_fp4, A_sc = dynamic_mxfp4_quant(A.contiguous())
            B_sc = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)
            C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
            matmul_fp4(A_fp4.view(torch.uint8), B_q.view(torch.uint8), C,
                       A_sc.view(torch.uint8), B_sc)
        torch.cuda.synchronize()
        pipe_dyn = (time.perf_counter() - t0) / 10 * 1e6
        print(f"  dynamic_mxfp4_quant pipeline: {pipe_dyn:.1f} µs", file=sys.stderr)

        # Pipeline: hip_quant + nibble_swap + tritonblas
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(10):
            A_q_h, A_s_h = hip_quant(A.contiguous())
            A_h_u8 = A_q_h.view(torch.uint8)
            A_h_swapped = ((A_h_u8 & 0x0F) << 4) | ((A_h_u8 >> 4) & 0x0F)
            A_s_h_u8 = A_s_h.view(torch.uint8)[:m, :k_scale].contiguous()
            B_sc = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)
            C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
            matmul_fp4(A_h_swapped, B_q.view(torch.uint8), C,
                       A_s_h_u8, B_sc)
        torch.cuda.synchronize()
        pipe_hip = (time.perf_counter() - t0) / 10 * 1e6
        print(f"  hip_quant + nibble_swap pipeline: {pipe_hip:.1f} µs", file=sys.stderr)

    except Exception as e:
        print(f"PROBE ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return ref_kernel(data)
