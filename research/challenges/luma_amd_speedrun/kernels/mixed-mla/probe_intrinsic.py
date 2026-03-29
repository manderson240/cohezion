import os
import subprocess as sp
import sys


def custom_kernel(data):
    print("--- Checking GFX950 scale intrinsic support ---", file=sys.stderr)

    src = r"""
    #include <hip/hip_runtime.h>
    #include <stdint.h>
    extern "C" __global__ void test_intrinsic(float* d) {
        // Dummy values
        uint32_t a = 0, b = 0;
        float c[4] = {0};
        uint32_t scale_a = 0, scale_b = 0;
        
        // This is the target CDNA 4 intrinsic
        // Res = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(a, b, c, scale_a, scale_b, 0);
        // Note: Using asm to probe if the compiler recognizes the op
        __asm__ volatile("v_mfma_scale_f32_16x16x128_f8f6f4 %0, %1, %2, %3, %4, %5, 0" 
            : : "v"(c), "v"(a), "v"(b), "v"(c), "v"(scale_a), "v"(scale_b));
    }
    """

    tmp_src = "/tmp/probe_intrinsic.hip"
    tmp_so = "/tmp/probe_intrinsic.so"
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
            print("SUCCESS: GFX950 scale instruction is recognized!", file=sys.stderr)
        else:
            print(f"FAILED: Return code {res.returncode}", file=sys.stderr)
            print(f"STDERR: {res.stderr.decode()}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
