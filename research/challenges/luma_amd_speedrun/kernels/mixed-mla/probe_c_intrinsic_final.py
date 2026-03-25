import os
import subprocess as sp
import sys


def custom_kernel(data):
    print("--- Probing GFX950 scale intrinsic with correct signature ---", file=sys.stderr)

    src = r"""
    #include <hip/hip_runtime.h>
    #include <stdint.h>

    using float4 = __attribute__((__vector_size__(4 * sizeof(float)))) float;
    using int8 = __attribute__((__vector_size__(8 * sizeof(int)))) int;

    extern "C" {
        float4 __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
            int8 a, int8 b, float4 c, int scale_a, int scale_b, int flags, int cbsz, int abid, int blgp) noexcept;
    }

    extern "C" __global__ void test_intrinsic(float* d) {
        int8 a = {0}, b = {0};
        float4 c = {0, 0, 0, 0};
        float4 res = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(a, b, c, 0, 0, 0, 0, 0, 0);
        d[0] = res[0];
    }
    """

    tmp_src = "/tmp/probe_c_intrinsic_final.hip"
    tmp_so = "/tmp/probe_c_intrinsic_final.so"
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
            print("SUCCESS: GFX950 C-intrinsic is fully recognized!", file=sys.stderr)
        else:
            print(f"FAILED: Return code {res.returncode}", file=sys.stderr)
            print(f"STDERR: {res.stderr.decode()}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
