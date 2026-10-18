"""Unit and Integration Tests for Polyglot Architecture & Multi-Language Bridges."""

from __future__ import annotations

import math

from cohezion.polyglot.bun_bridge import BunBridge
from cohezion.polyglot.runtime_audit import audit_polyglot_capabilities
from cohezion.polyglot.rust_bridge import (
    fast_kahn_topological_sort,
    fast_poincare_conformal_factor,
    fast_poincare_distance,
    fast_zobrist_hash_grid,
    is_rust_accelerated,
)
from cohezion.polyglot.wasm_runner import WasmSandboxRunner


class TestPolyglotRuntimeAudit:
    """Test host hardware and compiler discovery."""

    def test_audit_detects_zen5_and_avx512(self):
        caps = audit_polyglot_capabilities()
        assert caps.simd.has_avx512f is True
        assert caps.simd.has_avx512_vpopcntdq is True
        assert caps.simd.total_uma_ram_gb > 64.0  # 128GB UMA on Strix Halo

    def test_audit_detects_installed_runtimes(self):
        caps = audit_polyglot_capabilities()
        # Rust and Bun/TypeScript are installed on host
        assert caps.is_available("rust") is True
        assert caps.is_available("typescript") is True
        assert caps.is_available("wasm") is True
        summary = caps.summary()
        assert "rust" in summary["available_runtimes"]
        assert "typescript" in summary["available_runtimes"]


class TestRustBridge:
    """Test high-performance Rust PyO3 acceleration bridge."""

    def test_rust_acceleration_or_fallback(self):
        # Either loaded or falling back cleanly
        accel = is_rust_accelerated()
        assert isinstance(accel, bool)

    def test_fast_poincare_distance_numerical_accuracy(self):
        # Origin to point
        u = [0.0, 0.0, 0.0]
        v = [0.5, 0.0, 0.0]
        # Exact: arcosh(1 + 2 * (0.25) / (1 * (1 - 0.25))) = arcosh(1 + 0.5 / 0.75) = arcosh(5/3) ≈ 1.098612
        dist = fast_poincare_distance(u, v)
        expected = math.acosh(5.0 / 3.0)
        assert abs(dist - expected) < 1e-5

    def test_fast_poincare_conformal_factor(self):
        coords = [0.0, 0.0, 0.0]
        factor = fast_poincare_conformal_factor(coords)
        assert abs(factor - 2.0) < 1e-6  # at origin, lambda = 2 / (1 - 0) = 2.0

        coords_half = [0.5, 0.0, 0.0]
        factor_half = fast_poincare_conformal_factor(coords_half)
        assert abs(factor_half - (2.0 / 0.75)) < 1e-6

    def test_fast_kahn_topological_sort(self):
        nodes = ["a", "b", "c"]
        edges = [("a", "b"), ("b", "c")]
        is_dag, order = fast_kahn_topological_sort(nodes, edges)
        assert is_dag is True
        assert order == ["a", "b", "c"]

    def test_fast_kahn_topological_sort_detects_cycles(self):
        nodes = ["a", "b"]
        edges = [("a", "b"), ("b", "a")]
        is_dag, _ = fast_kahn_topological_sort(nodes, edges)
        assert is_dag is False

    def test_fast_zobrist_hash_grid(self):
        grid = [[1, 2], [3, 4]]
        h1 = fast_zobrist_hash_grid(grid)
        h2 = fast_zobrist_hash_grid(grid)
        assert h1 == h2
        assert isinstance(h1, int)


class TestBunBridge:
    """Test TypeScript execution via Bun."""

    def test_bun_executes_typescript_arithmetic(self):
        bun = BunBridge()
        if not bun.is_available:
            return  # Skip if bun not present

        ts_code = """
interface Result {
    sum: number;
    vector: number[];
}
const res: Result = {
    sum: [1, 2, 3, 4].reduce((a, b) => a + b, 0),
    vector: [10, 20, 30]
};
console.log(JSON.stringify(res));
"""
        result = bun.run_typescript_snippet(ts_code)
        assert result.success is True
        assert result.data["sum"] == 10
        assert result.data["vector"] == [10, 20, 30]
        assert result.duration_ms < 500.0

    def test_bun_validates_json_schema(self):
        bun = BunBridge()
        if not bun.is_available:
            return

        payload = {"agent_id": "architect-1", "status": "active"}
        result = bun.validate_json_schema(payload, ["agent_id", "status"])
        assert result.success is True
        assert result.data["valid"] is True
        assert result.data["missing"] == []

        # Missing key
        result_missing = bun.validate_json_schema(payload, ["agent_id", "token_quota"])
        assert result_missing.data["valid"] is False
        assert "token_quota" in result_missing.data["missing"]


class TestWasmSandboxRunner:
    """Test WebAssembly sandbox execution and metering."""

    def test_validate_wasm_header(self):
        runner = WasmSandboxRunner()
        # Valid WASM binary magic header \0asm\1\0\0\0
        valid_wasm = b"\x00asm\x01\x00\x00\x00"
        assert runner.validate_wasm(valid_wasm) is True

        invalid_wasm = b"invalid_binary_header"
        assert runner.validate_wasm(invalid_wasm) is False

    def test_execute_metered_algorithm_sum_squares(self):
        runner = WasmSandboxRunner()
        res = runner.execute_pure_algorithm("sum_squares", [1, 2, 3, 4], max_fuel=1000)
        if not runner.bun.is_available:
            return

        assert res.success is True
        assert res.output == 1 + 4 + 9 + 16  # 30
        assert res.fuel_consumed > 0

    def test_execute_metered_algorithm_d4_rotate(self):
        runner = WasmSandboxRunner()
        grid = [
            [1, 2],
            [3, 4],
        ]
        res = runner.execute_pure_algorithm("d4_rotate", [grid], max_fuel=1000)
        if not runner.bun.is_available:
            return

        assert res.success is True
        # 90 deg clockwise of [[1,2],[3,4]] is [[3,1],[4,2]]
        assert res.output == [[3, 1], [4, 2]]
