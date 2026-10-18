"""Polyglot Runtime & Toolchain Auditor.

Inspects the host hardware capabilities (Zen 5 AVX-512, UMA memory aperture)
and detects available programming language runtimes (Rust, Bun/TypeScript,
WebAssembly, C#/.NET, R, Clang/GCC, Python Free-Threading).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LanguageRuntime:
    """Status and version information for a language runtime."""

    name: str
    available: bool
    version: str = ""
    executable_path: str = ""
    target_domains: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""


@dataclass(frozen=True)
class HardwareSIMDCapabilities:
    """Hardware vector and coprocessor capabilities on the host."""

    has_avx512f: bool = False
    has_avx512_vpopcntdq: bool = False
    has_avx512_vpclmulqdq: bool = False
    has_avx512_vbmi2: bool = False
    has_avx512_bf16: bool = False
    zen5_dual_512bit: bool = False
    xdna2_npu: bool = False
    total_uma_ram_gb: float = 0.0


@dataclass(frozen=True)
class PolyglotCapabilities:
    """Aggregated host polyglot capabilities."""

    simd: HardwareSIMDCapabilities
    runtimes: dict[str, LanguageRuntime]
    python_free_threading: bool = False

    def is_available(self, language: str) -> bool:
        """Check if language runtime is ready."""
        rt = self.runtimes.get(language.lower())
        return rt.available if rt else False

    def summary(self) -> dict[str, Any]:
        """Human-readable dictionary summary."""
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "python_free_threading": self.python_free_threading,
            "simd_avx512": self.simd.has_avx512f,
            "zen5_dual_512bit": self.simd.zen5_dual_512bit,
            "available_runtimes": [k for k, v in self.runtimes.items() if v.available],
        }


def _probe_cpu_simd() -> HardwareSIMDCapabilities:
    """Inspect /proc/cpuinfo for AVX-512 flags and Zen 5 architecture."""
    cpuinfo_path = Path("/proc/cpuinfo")
    if not cpuinfo_path.exists():
        return HardwareSIMDCapabilities()

    try:
        content = cpuinfo_path.read_text(errors="ignore")
        flags = set()
        model_name = ""
        for line in content.splitlines():
            if line.startswith("flags"):
                flags = set(line.split()[2:])
            elif line.startswith("model name") and not model_name:
                model_name = line.split(":", 1)[1].strip()

        is_zen5 = "Ryzen AI" in model_name or "Zen 5" in model_name or "395" in model_name
        has_avx512f = "avx512f" in flags

        # Total memory from /proc/meminfo
        total_ram_gb = 0.0
        meminfo = Path("/proc/meminfo")
        if meminfo.exists():
            for mline in meminfo.read_text(errors="ignore").splitlines():
                if mline.startswith("MemTotal:"):
                    kb = float(mline.split()[1])
                    total_ram_gb = kb / (1024.0 * 1024.0)
                    break

        return HardwareSIMDCapabilities(
            has_avx512f=has_avx512f,
            has_avx512_vpopcntdq="avx512_vpopcntdq" in flags,
            has_avx512_vpclmulqdq="vpclmulqdq" in flags or "avx512_vpclmulqdq" in flags,
            has_avx512_vbmi2="avx512_vbmi2" in flags,
            has_avx512_bf16="avx512_bf16" in flags,
            zen5_dual_512bit=is_zen5 and has_avx512f,
            xdna2_npu=is_zen5,  # AMD Ryzen AI MAX+ 395 integrates XDNA 2 NPU
            total_uma_ram_gb=round(total_ram_gb, 1),
        )
    except Exception as e:
        logger.debug(f"Failed to probe CPU SIMD: {e}")
        return HardwareSIMDCapabilities()


def _probe_executable(name: str, version_arg: str = "--version") -> tuple[bool, str, str]:
    """Find executable and query its version string."""
    # Also check ~/.cargo/bin and ~/.bun/bin explicitly if not in PATH
    extra_paths = [
        str(Path.home() / ".cargo" / "bin"),
        str(Path.home() / ".bun" / "bin"),
        str(Path.home() / ".local" / "bin"),
    ]
    path_env = os.environ.get("PATH", "") + ":" + ":".join(extra_paths)
    path = shutil.which(name, path=path_env)
    if not path:
        return False, "", ""

    try:
        proc = subprocess.run(
            [path, version_arg],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        out = (proc.stdout or proc.stderr).strip().splitlines()
        version = out[0] if out else "found"
        return True, version, path
    except Exception:
        return True, "unknown_version", path


def audit_polyglot_capabilities() -> PolyglotCapabilities:
    """Execute complete host language and hardware audit."""
    simd = _probe_cpu_simd()
    runtimes: dict[str, LanguageRuntime] = {}

    # 1. Rust
    rust_ok, rust_ver, rust_path = _probe_executable("rustc")
    runtimes["rust"] = LanguageRuntime(
        name="Rust",
        available=rust_ok,
        version=rust_ver,
        executable_path=rust_path,
        target_domains=("Poincaré Hyperbolic Math", "AutoHarness ZKFV", "Low-RSS Daemons (<2MB)"),
        notes="High-throughput AVX-512 compiled native cdylib and binary",
    )

    # 2. TypeScript / Bun
    bun_ok, bun_ver, bun_path = _probe_executable("bun")
    runtimes["typescript"] = LanguageRuntime(
        name="TypeScript (Bun)",
        available=bun_ok,
        version=bun_ver,
        executable_path=bun_path,
        target_domains=("FastMCP Protocol Gateway", "TypeBox Schema Validation", "Swarm HUD"),
        notes="Instant zero-compile TypeScript runtime on JavaScriptCore",
    )

    # 3. WebAssembly (WASM)
    wasm_ok = bun_ok or shutil.which("wasmtime") is not None
    runtimes["wasm"] = LanguageRuntime(
        name="WebAssembly",
        available=wasm_ok,
        version="WASM-32 Core (JSC/Wasmtime)",
        executable_path=bun_path if bun_ok else (shutil.which("wasmtime") or ""),
        target_domains=("AutoHarness Sandboxed Code Execution", "Gas-Metered Agent Actions"),
        notes="Deterministic capability-based isolation",
    )

    # 4. C# / .NET Native AOT
    dotnet_ok, dotnet_ver, dotnet_path = _probe_executable("dotnet")
    runtimes["csharp"] = LanguageRuntime(
        name="C# / .NET",
        available=dotnet_ok,
        version=dotnet_ver,
        executable_path=dotnet_path,
        target_domains=("ARC-AGI-3 Affordance Engine", "Interactive 2D/3D Grid Physics"),
        notes="Native AOT high-throughput SIMD simulation",
    )

    # 5. R
    r_ok, r_ver, r_path = _probe_executable("Rscript")
    runtimes["r"] = LanguageRuntime(
        name="R",
        available=r_ok,
        version=r_ver,
        executable_path=r_path,
        target_domains=("CASMI26 Mass Spec Cleavage", "RSNA Knee Rank-AUC & Survival"),
        notes="Isolated batch statistical verification via IPC",
    )

    # 6. Clang / AVX-512 Assembly
    clang_ok, clang_ver, clang_path = _probe_executable("clang")
    runtimes["assembly"] = LanguageRuntime(
        name="Clang / AVX-512 Assembly",
        available=clang_ok,
        version=clang_ver,
        executable_path=clang_path,
        target_domains=("VPOPCNTDQ Bitboards", "VPCLMULQDQ Galois Hashing", "VBMI2 Permutations"),
        notes="Cycle-exact Zen 5 dual 512-bit vector pipeline exploitation",
    )

    # 7. Python Free-Threading
    free_threaded = getattr(sys, "_is_gil_enabled", None) is not None and not sys._is_gil_enabled()

    return PolyglotCapabilities(
        simd=simd,
        runtimes=runtimes,
        python_free_threading=bool(free_threaded),
    )
