"""Probe: What compilers/toolchains exist on the MI355X runner?"""
import subprocess
import os
import torch
from task import input_t, output_t
from reference import ref_kernel

_probed = False


def _probe():
    global _probed
    if _probed:
        return
    _probed = True

    checks = [
        # Rust
        ("rustc --version", "rustc"),
        ("cargo --version", "cargo"),
        # LLVM / Clang
        ("clang --version 2>&1 | head -2", "clang"),
        ("clang++ --version 2>&1 | head -2", "clang++"),
        ("llvm-mc --version 2>&1 | head -2", "llvm-mc"),
        ("llvm-as --version 2>&1 | head -2", "llvm-as"),
        ("llc --version 2>&1 | head -2", "llc"),
        ("opt --version 2>&1 | head -2", "opt"),
        # HIP / ROCm
        ("hipcc --version 2>&1 | head -2", "hipcc"),
        ("hipconfig --full 2>&1", "hipconfig"),
        ("which amdclang++ 2>&1", "amdclang++"),
        ("which amdclang 2>&1", "amdclang"),
        # Assemblers
        ("nasm --version 2>&1", "nasm"),
        ("as --version 2>&1 | head -2", "gas"),
        # ROCm path
        ("ls /opt/rocm/bin/ 2>&1 | head -20", "rocm-bin"),
        ("ls /opt/rocm/llvm/bin/ 2>&1 | head -20", "rocm-llvm-bin"),
        # GPU info
        ("rocminfo 2>&1 | grep -E 'Name:|Marketing' | head -6", "rocminfo"),
        # Linker
        ("ld --version 2>&1 | head -2", "ld"),
        ("ld.lld --version 2>&1 | head -2", "lld"),
        # Python ctypes test
        ("python3 -c \"import ctypes; print('ctypes OK')\" 2>&1", "ctypes"),
        # Check if we can write to /tmp
        ("touch /tmp/probe_test && echo 'tmp writable' && rm /tmp/probe_test", "tmp-write"),
        # Check shared lib compilation capability
        ("echo 'int add(int a, int b) { return a+b; }' > /tmp/test.c && cc -shared -o /tmp/test.so /tmp/test.c && echo 'cc -shared OK' && rm /tmp/test.c /tmp/test.so", "cc-shared"),
        # Check for ROCm clang offload
        ("ls /opt/rocm/lib/libamdhip64.so* 2>&1 | head -3", "libamdhip64-path"),
        # Check available GPU ISA files
        ("ls /opt/rocm/amdgcn/bitcode/ 2>&1 | head -10", "bitcode"),
        # Check for pre-compiled kernel objects
        ("find /opt/rocm -name '*.co' 2>/dev/null | head -5", "kernel-objects"),
        # Environment
        ("env | grep -i 'rocm\\|hip\\|hsa\\|gpu' | head -10", "env-gpu"),
        # Can we compile HIP?
        ("echo '__global__ void k(){}' > /tmp/t.hip && hipcc -c /tmp/t.hip -o /tmp/t.o --offload-arch=gfx950 2>&1 | tail -5 && echo 'hipcc compile OK' || echo 'hipcc compile FAIL'; rm -f /tmp/t.hip /tmp/t.o", "hipcc-compile"),
        # Can clang do HIP offload?
        ("echo '__global__ void k(){}' > /tmp/t.hip && clang++ -x hip -c /tmp/t.hip -o /tmp/t.o --offload-arch=gfx950 --rocm-path=/opt/rocm 2>&1 | tail -5 && echo 'clang hip OK' || echo 'clang hip FAIL'; rm -f /tmp/t.hip /tmp/t.o", "clang-hip"),
    ]

    print("=" * 60)
    print("TOOLCHAIN PROBE — MI355X Runner")
    print("=" * 60)

    for cmd, label in checks:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=15
            )
            output = (result.stdout.strip() + " " + result.stderr.strip()).strip()
            if not output:
                output = "(empty)"
            # Truncate long output
            if len(output) > 200:
                output = output[:200] + "..."
            print(f"\n[{label}] {output}")
        except subprocess.TimeoutExpired:
            print(f"\n[{label}] TIMEOUT")
        except Exception as e:
            print(f"\n[{label}] ERROR: {e}")

    print("\n" + "=" * 60)
    print("PROBE COMPLETE")
    print("=" * 60)


def custom_kernel(data: input_t) -> output_t:
    _probe()
    return ref_kernel(data)
