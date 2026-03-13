"""
MXFP4 GEMM — Probe: Discover available quantization and GEMM alternatives.

Tests:
  1. get_torch_quant with shuffle=True
  2. get_hip_quant existence and signature
  3. gemm_afp4wfp4 Triton kernel existence and signature
  4. Other GEMM functions in aiter
  5. Whether calling gemm_a4w4 through a dynamically-created module works
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
            import aiter
            from aiter import QuantType, dtypes
            import torch

            A, B, B_q, B_shuffle, B_scale_sh = data

            # 1. Test get_torch_quant with shuffle=True
            print("\n=== get_torch_quant test ===", file=sys.stderr)
            try:
                quant_func = aiter.get_torch_quant(QuantType.per_1x32)
                print(f"get_torch_quant returned: {type(quant_func)}", file=sys.stderr)
                sig = inspect.signature(quant_func)
                print(f"signature: {sig}", file=sys.stderr)

                # Test with shuffle=True
                A_test = A[:4].contiguous()
                try:
                    A_q, A_scale = quant_func(A_test, shuffle=True)
                    print(f"shuffle=True WORKS: A_q shape={A_q.shape} dtype={A_q.dtype}", file=sys.stderr)
                    print(f"A_scale shape={A_scale.shape} dtype={A_scale.dtype}", file=sys.stderr)
                except TypeError as e:
                    print(f"shuffle=True TypeError: {e}", file=sys.stderr)
                    # Try without shuffle
                    A_q, A_scale = quant_func(A_test)
                    print(f"no shuffle: A_q shape={A_q.shape} dtype={A_q.dtype}", file=sys.stderr)
                    print(f"A_scale shape={A_scale.shape} dtype={A_scale.dtype}", file=sys.stderr)
            except Exception as e:
                print(f"get_torch_quant error: {e}", file=sys.stderr)

            # 2. Test get_hip_quant
            print("\n=== get_hip_quant test ===", file=sys.stderr)
            try:
                hip_quant = aiter.get_hip_quant(QuantType.per_1x32)
                print(f"get_hip_quant returned: {type(hip_quant)}", file=sys.stderr)
                sig = inspect.signature(hip_quant)
                print(f"signature: {sig}", file=sys.stderr)
                try:
                    A_q_hip, A_scale_hip = hip_quant(A_test, shuffle=True)
                    print(f"hip shuffle=True: A_q shape={A_q_hip.shape}", file=sys.stderr)
                except Exception as e:
                    print(f"hip shuffle=True error: {e}", file=sys.stderr)
            except AttributeError:
                print("get_hip_quant not available", file=sys.stderr)
            except Exception as e:
                print(f"get_hip_quant error: {e}", file=sys.stderr)

            # 3. Test gemm_afp4wfp4
            print("\n=== gemm_afp4wfp4 test ===", file=sys.stderr)
            try:
                from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import gemm_afp4wfp4
                sig = inspect.signature(gemm_afp4wfp4)
                print(f"gemm_afp4wfp4 signature: {sig}", file=sys.stderr)
                src = inspect.getsource(gemm_afp4wfp4)
                # Print first 2000 chars
                print(f"source (first 2000 chars):", file=sys.stderr)
                print(src[:2000], file=sys.stderr)
            except ImportError as e:
                print(f"gemm_afp4wfp4 import error: {e}", file=sys.stderr)
                # Try alternative paths
                try:
                    from aiter.ops.triton.gemm import gemm_afp4wfp4
                    print(f"found at aiter.ops.triton.gemm", file=sys.stderr)
                except ImportError:
                    print("not found at aiter.ops.triton.gemm either", file=sys.stderr)
            except Exception as e:
                print(f"gemm_afp4wfp4 error: {e}", file=sys.stderr)

            # 4. List all GEMM-related functions in aiter
            print("\n=== aiter GEMM functions ===", file=sys.stderr)
            for name in sorted(dir(aiter)):
                if 'gemm' in name.lower() or 'a4w4' in name.lower():
                    obj = getattr(aiter, name)
                    try:
                        sig = inspect.signature(obj)
                        print(f"aiter.{name}{sig}", file=sys.stderr)
                    except (ValueError, TypeError):
                        print(f"aiter.{name} (type: {type(obj).__name__})", file=sys.stderr)

            # 5. List quant functions
            print("\n=== aiter quant functions ===", file=sys.stderr)
            for name in sorted(dir(aiter)):
                if 'quant' in name.lower():
                    print(f"aiter.{name}", file=sys.stderr)

            # 6. Check if dynamic_mxfp4_quant exists (from fused_moe path)
            print("\n=== dynamic_mxfp4_quant ===", file=sys.stderr)
            try:
                from aiter.fused_moe import dynamic_mxfp4_quant
                sig = inspect.signature(dynamic_mxfp4_quant)
                print(f"dynamic_mxfp4_quant{sig}", file=sys.stderr)
            except ImportError:
                print("not found in fused_moe", file=sys.stderr)
            except Exception as e:
                print(f"error: {e}", file=sys.stderr)

        except Exception as e:
            print(f"PROBE ERROR: {e}", file=sys.stderr)

    return ref_kernel(data)
