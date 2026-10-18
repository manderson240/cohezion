"""Polyglot Multi-Language Orchestration Subsystem.

Provides first-principles language mapping across Rust, TypeScript/Bun,
WebAssembly, C#/.NET, R, Clang/Assembly, and Free-Threaded Python 3.15+.
"""

from __future__ import annotations

from cohezion.polyglot.bun_bridge import BunBridge, BunExecutionResult
from cohezion.polyglot.runtime_audit import (
    HardwareSIMDCapabilities,
    LanguageRuntime,
    PolyglotCapabilities,
    audit_polyglot_capabilities,
)
from cohezion.polyglot.rust_bridge import (
    fast_kahn_topological_sort,
    fast_poincare_conformal_factor,
    fast_poincare_distance,
    fast_poincare_mobius_add,
    fast_poincare_pairwise_distances,
    fast_zobrist_hash_grid,
    is_rust_accelerated,
)
from cohezion.polyglot.wasm_runner import WasmExecutionResult, WasmSandboxRunner


__all__ = [
    "BunBridge",
    "BunExecutionResult",
    "HardwareSIMDCapabilities",
    "LanguageRuntime",
    "PolyglotCapabilities",
    "WasmExecutionResult",
    "WasmSandboxRunner",
    "audit_polyglot_capabilities",
    "fast_kahn_topological_sort",
    "fast_poincare_conformal_factor",
    "fast_poincare_distance",
    "fast_poincare_mobius_add",
    "fast_poincare_pairwise_distances",
    "fast_zobrist_hash_grid",
    "is_rust_accelerated",
]
