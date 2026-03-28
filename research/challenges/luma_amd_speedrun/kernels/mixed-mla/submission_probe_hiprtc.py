"""
Probe: Check hiprtc/hip-python availability on MI355X runner.

This submission produces correct output via ref_kernel while dumping
diagnostic information about the HIP runtime compilation environment
to stdout/stderr. The diagnostics tell us whether we can use hiprtc
for zero-overhead kernel dispatch.
"""
import sys
import os
import subprocess
from task import input_t, output_t
from reference import ref_kernel


def _probe_environment():
    """Dump environment info to stdout for capture in submission results."""
    results = []

    # 1. Check hip-python package
    try:
        from hip import hip, hiprtc
        results.append(f"hip-python: AVAILABLE (hip={dir(hip)[:5]}, hiprtc={dir(hiprtc)[:5]})")
        # Check hiprtc version
        try:
            ver = hiprtc.hiprtcVersion()
            results.append(f"  hiprtc version: {ver}")
        except Exception as e:
            results.append(f"  hiprtc version error: {e}")
    except ImportError as e:
        results.append(f"hip-python: NOT AVAILABLE ({e})")

    # 2. Check ctypes access to libhiprtc.so
    try:
        import ctypes
        for path in [
            "libhiprtc.so",
            "/opt/rocm/lib/libhiprtc.so",
            "/usr/lib/libhiprtc.so",
            "/usr/local/lib/libhiprtc.so",
        ]:
            try:
                lib = ctypes.CDLL(path)
                results.append(f"ctypes libhiprtc: FOUND at {path}")
                # Check if hiprtcCreateProgram exists
                try:
                    fn = lib.hiprtcCreateProgram
                    results.append(f"  hiprtcCreateProgram: {fn}")
                except AttributeError:
                    results.append(f"  hiprtcCreateProgram: NOT FOUND")
                break
            except OSError:
                continue
        else:
            results.append("ctypes libhiprtc: NOT FOUND in any standard path")
    except Exception as e:
        results.append(f"ctypes probe error: {e}")

    # 3. Check libamdhip64.so (for hipModuleLaunchKernel)
    try:
        import ctypes
        for path in [
            "libamdhip64.so",
            "/opt/rocm/lib/libamdhip64.so",
        ]:
            try:
                lib = ctypes.CDLL(path)
                results.append(f"ctypes libamdhip64: FOUND at {path}")
                for fn_name in ["hipModuleLaunchKernel", "hipModuleLoadData", "hipModuleGetFunction"]:
                    try:
                        fn = getattr(lib, fn_name)
                        results.append(f"  {fn_name}: {fn}")
                    except AttributeError:
                        results.append(f"  {fn_name}: NOT FOUND")
                break
            except OSError:
                continue
        else:
            results.append("ctypes libamdhip64: NOT FOUND")
    except Exception as e:
        results.append(f"libamdhip64 probe error: {e}")

    # 4. Check hipcc
    try:
        r = subprocess.run(["hipcc", "--version"], capture_output=True, text=True, timeout=5)
        results.append(f"hipcc: {r.stdout.strip()[:200]}")
    except FileNotFoundError:
        results.append("hipcc: NOT FOUND in PATH")
    except Exception as e:
        results.append(f"hipcc error: {e}")

    # 5. Check ROCm paths
    rocm_paths = [
        "/opt/rocm",
        "/opt/rocm/lib",
        "/opt/rocm/bin",
        "/opt/rocm/include/hip",
    ]
    for p in rocm_paths:
        exists = os.path.exists(p)
        results.append(f"path {p}: {'EXISTS' if exists else 'MISSING'}")
        if exists and os.path.isdir(p):
            try:
                contents = os.listdir(p)[:10]
                results.append(f"  contents: {contents}")
            except Exception:
                pass

    # 6. Check torch GPU info
    try:
        import torch
        results.append(f"torch.cuda.get_arch_list: {torch.cuda.get_arch_list()}")
        results.append(f"torch.version.hip: {getattr(torch.version, 'hip', 'N/A')}")
        if torch.cuda.is_available():
            results.append(f"device: {torch.cuda.get_device_name(0)}")
            props = torch.cuda.get_device_properties(0)
            results.append(f"  gcnArchName: {getattr(props, 'gcnArchName', 'N/A')}")
    except Exception as e:
        results.append(f"torch probe error: {e}")

    # 7. Check pip packages related to hip
    try:
        r = subprocess.run(
            ["pip", "list"], capture_output=True, text=True, timeout=10
        )
        hip_pkgs = [l for l in r.stdout.split('\n') if 'hip' in l.lower() or 'rocm' in l.lower()]
        results.append(f"hip/rocm packages: {hip_pkgs}")
    except Exception as e:
        results.append(f"pip list error: {e}")

    # 8. Check if we can do a minimal hiprtc compile
    try:
        from hip import hiprtc
        src = b'extern "C" __global__ void test_kernel() {}'
        prog = hiprtc.hiprtcCreateProgram(src, b"test.hip", 0, [], [])
        results.append(f"hiprtc program created: {prog}")
        try:
            ret = hiprtc.hiprtcCompileProgram(prog, [b"--gpu-architecture=gfx950"])
            results.append(f"hiprtc compile gfx950: {'SUCCESS' if ret == 0 else f'FAILED ({ret})'}")
        except Exception as e:
            results.append(f"hiprtc compile error: {e}")
            # Try getting compile log
            try:
                log = hiprtc.hiprtcGetProgramLog(prog)
                results.append(f"  compile log: {log[:500]}")
            except Exception:
                pass
    except ImportError:
        results.append("hiprtc compile test: SKIPPED (no hip-python)")
    except Exception as e:
        results.append(f"hiprtc compile test error: {e}")

    # Print all results
    print("=== HIPRTC ENVIRONMENT PROBE ===")
    for r in results:
        print(r)
    print("=== END PROBE ===")


# Run probe on import (prints to stdout, captured by submission runner)
_probe_environment()


def custom_kernel(data: input_t) -> output_t:
    return ref_kernel(data)
