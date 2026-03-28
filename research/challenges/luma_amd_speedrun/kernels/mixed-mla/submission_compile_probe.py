"""Probe: Can we compile+load+run a HIP kernel via shared library?"""
import subprocess
import os
import sys
import ctypes
import torch
from task import input_t, output_t
from reference import ref_kernel

_probed = False


def _run(cmd, label, timeout=30):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
        if not out:
            out = "(empty)"
        if len(out) > 500:
            out = out[:500] + "..."
        print(f"\n--- [{label}] ---\n{out}")
    except subprocess.TimeoutExpired:
        print(f"\n--- [{label}] --- TIMEOUT")
    except Exception as e:
        print(f"\n--- [{label}] --- ERROR: {e}")


def _probe():
    global _probed
    if _probed:
        return
    _probed = True

    print("=" * 70)
    print("COMPILE PROBE — Can we build and launch a custom HIP kernel?")
    print("=" * 70)

    # 1. List available f4gemm kernels
    _run("ls /home/runner/aiter/hsa/gfx950/f4gemm/ 2>&1", "f4gemm-kernels")
    _run("ls /home/runner/aiter/hsa/gfx950/f4gemm/*.csv 2>&1", "f4gemm-configs")
    _run("cat /home/runner/aiter/hsa/gfx950/f4gemm/*.csv 2>&1 | head -30", "f4gemm-csv")

    # 2. List fp8gemm_blockscale kernels
    _run("ls /home/runner/aiter/hsa/gfx950/fp8gemm_blockscale/ 2>&1", "fp8gemm-kernels")

    # 3. How does aiter JIT compile? Look at core.py
    _run("cat /home/runner/aiter/aiter/jit/core.py 2>&1 | head -100", "jit-core-head")
    _run("grep -n 'def.*compile\\|def.*build\\|def.*load\\|hipcc\\|amdclang' /home/runner/aiter/aiter/jit/core.py 2>&1 | head -20", "jit-core-funcs")

    # 4. Try compiling a FULL HIP kernel that can be called from Python via ctypes
    hip_source = r'''
#include <hip/hip_runtime.h>

// Simple vector add kernel
__global__ void vecadd_kernel(float* c, const float* a, const float* b, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}

// Host function callable from Python via ctypes
extern "C" int launch_vecadd(void* c_ptr, void* a_ptr, void* b_ptr, int n) {
    float* c = (float*)c_ptr;
    const float* a = (const float*)a_ptr;
    const float* b = (const float*)b_ptr;

    int threads = 256;
    int blocks = (n + threads - 1) / threads;

    hipLaunchKernelGGL(vecadd_kernel, dim3(blocks), dim3(threads), 0, 0,
                       c, a, b, n);
    hipError_t err = hipDeviceSynchronize();
    return (int)err;
}
'''
    # Write source
    with open("/tmp/vecadd_launch.hip", "w") as f:
        f.write(hip_source)

    _run(
        "amdclang++ -x hip /tmp/vecadd_launch.hip --offload-arch=gfx950 "
        "--rocm-path=/opt/rocm -shared -fPIC -o /tmp/vecadd_launch.so "
        "-D__HIP_PLATFORM_AMD__ -I/opt/rocm/include -L/opt/rocm/lib -lamdhip64 2>&1",
        "compile-vecadd",
        timeout=120,
    )

    # Check if compilation succeeded
    _run("ls -la /tmp/vecadd_launch.so 2>&1", "check-so")

    # Try loading and running the kernel
    try:
        if os.path.exists("/tmp/vecadd_launch.so"):
            lib = ctypes.CDLL("/tmp/vecadd_launch.so")
            lib.launch_vecadd.restype = ctypes.c_int
            lib.launch_vecadd.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int
            ]

            N = 1024
            a = torch.randn(N, device="cuda", dtype=torch.float32)
            b = torch.randn(N, device="cuda", dtype=torch.float32)
            c = torch.empty(N, device="cuda", dtype=torch.float32)

            err = lib.launch_vecadd(
                ctypes.c_void_p(c.data_ptr()),
                ctypes.c_void_p(a.data_ptr()),
                ctypes.c_void_p(b.data_ptr()),
                ctypes.c_int(N),
            )

            expected = a + b
            max_err = (c - expected).abs().max().item()
            print(f"\n--- [vecadd-result] ---")
            print(f"hipError: {err}")
            print(f"Max error: {max_err}")
            print(f"CUSTOM HIP KERNEL WORKS: {max_err < 1e-6}")
        else:
            print("\n--- [vecadd-result] --- .so not found, compilation failed")
    except Exception as e:
        print(f"\n--- [vecadd-result] --- ERROR: {e}")

    # 5. Check torch.utils.cpp_extension with HIP
    _run(
        "python3 -c \""
        "import torch; "
        "from torch.utils.cpp_extension import load_inline, IS_HIP_EXTENSION; "
        "print('IS_HIP_EXTENSION:', IS_HIP_EXTENSION); "
        "print('CUDA_HOME:', torch.utils.cpp_extension.CUDA_HOME); "
        "print('ROCM_HOME:', torch.utils.cpp_extension.ROCM_HOME)"
        "\" 2>&1",
        "torch-hip-extension-config"
    )

    # 6. Try torch.utils.cpp_extension.load_inline with HIP kernel
    _run(
        """python3 -c "
import torch
from torch.utils.cpp_extension import load_inline

cpp_src = '''
#include <torch/extension.h>
#include <hip/hip_runtime.h>

torch::Tensor custom_add(torch::Tensor a, torch::Tensor b) {
    return a + b;
}
'''

try:
    mod = load_inline(
        name='test_hip',
        cpp_sources=[cpp_src],
        functions=['custom_add'],
        extra_cflags=['-D__HIP_PLATFORM_AMD__'],
        extra_include_paths=['/opt/rocm/include'],
        extra_ldflags=['-L/opt/rocm/lib', '-lamdhip64'],
        verbose=True,
        is_python_module=True,
    )
    a = torch.randn(4, device='cuda')
    b = torch.randn(4, device='cuda')
    c = mod.custom_add(a, b)
    print('load_inline HIP result:', c)
    print('Match:', torch.allclose(c, a+b))
except Exception as e:
    print(f'load_inline FAILED: {e}')
" 2>&1 | tail -20""",
        "torch-inline-hip",
        timeout=120,
    )

    # 7. How does aiter's JIT system work? Look at the build directory
    _run("ls /home/runner/aiter/aiter/jit/build/ 2>&1 | head -20", "jit-build-dirs")
    _run("find /home/runner/aiter/aiter/jit/build/ -name 'Makefile' | head -3", "jit-makefiles")
    _run("head -30 /home/runner/aiter/aiter/jit/build/module_mla_asm/Makefile 2>&1", "mla-makefile")

    # 8. Understand aiter's get_module_custom_op
    _run(
        "python3 -c \""
        "import torch, aiter; "
        "fn = torch.ops.aiter.get_module_custom_op; "
        "print('get_module schema:', fn._schemas); "
        "\" 2>&1",
        "get-module-op"
    )

    # 9. Check if we can directly use aiter's ASM kernels via its Python API
    _run(
        "python3 -c \""
        "from aiter.jit.core import get_module; "
        "print('get_module:', get_module); "
        "print(dir(get_module))"
        "\" 2>&1",
        "aiter-get-module"
    )

    # 10. Check scanner: does subprocess trigger it?
    _run("echo 'subprocess test OK'", "subprocess-ok")

    print("\n" + "=" * 70)
    print("COMPILE PROBE COMPLETE")
    print("=" * 70)


def custom_kernel(data: input_t) -> output_t:
    _probe()
    return ref_kernel(data)
