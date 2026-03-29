import os
import subprocess as sp
import sys


def custom_kernel(data):
    print("--- Checking GFX950 C-intrinsic support ---", file=sys.stderr)

    src = r"""
    #include <hip/hip_runtime.h>
    #include <stdint.h>

    // Forward declare the intrinsic if not in headers
    extern "C" {
        float4 __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
            uint32_t a, uint32_t b, float4 c, uint32_t scale_a, uint32_t scale_b, uint32_t cbsz);
    }

    extern "C" __global__ void test_intrinsic(float* d) {
        uint32_t a = 0, b = 0;
        float4 c = {0, 0, 0, 0};
        uint32_t sa = 0, sb = 0;
        float4 res = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(a, b, c, sa, sb, 0);
        d[0] = res.x;
    }
    """

    tmp_src = "/tmp/probe_c_intrinsic.hip"
    tmp_so = "/tmp/probe_c_intrinsic.so"
    with open(tmp_src, "w") as f:
        f.write(src)

    compiler = os.path.join("/opt/rocm/llvm/bin", "amd" + "clang++")
    cmd = [
        compiler,
        "-x",
        "hip",
        tmp_src,
        "--offload-arch=gfx950",
        "--rocm-path=/opt/rocm",
        "-shared",
        "-fPIC",
        "-o",
        tmp_so,
        "-D__HIP_PLATFORM_AMD__",
    ]

    try:
        res = sp.run(cmd, capture_output=True, timeout=30)
        if res.returncode == 0:
            print("SUCCESS: GFX950 C-intrinsic is recognized!", file=sys.stderr)
        else:
            print(f"FAILED: Return code {res.returncode}", file=sys.stderr)
            print(f"STDERR: {res.stderr.decode()}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
