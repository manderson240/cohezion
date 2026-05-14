"""Coverage batch Z44: lemonade_provider, memory_barrier, flier_routing, bmad_cis_routes."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Module 1: physics/vliw_bridge.py
# ---------------------------------------------------------------------------


class TestVLIWBridge:
    def test_simd_mode_transition(self):
        from cohezion.physics.vliw_bridge import ExecutionMode, VLIWBridge

        bridge = VLIWBridge()
        assert bridge.state.mode == ExecutionMode.SIMD
        state = np.zeros(12, dtype=np.float32)
        delta = np.full(12, 0.1, dtype=np.float32)
        result = bridge.execute_state_transition(state, delta)
        assert result.shape == (12,)
        assert np.allclose(result, 0.1, atol=1e-5)

    def test_fallback_mode_transition(self):
        from cohezion.physics.vliw_bridge import ExecutionMode, VLIWBridge

        bridge = VLIWBridge(force_fallback=True)
        assert bridge.state.mode == ExecutionMode.FALLBACK_PYTHON
        state = np.zeros(12, dtype=np.float32)
        delta = np.full(12, 0.1, dtype=np.float32)
        result = bridge.execute_state_transition(state, delta)
        assert result.shape == (12,)
        assert np.allclose(result, 0.1, atol=1e-5)

    def test_simd_clips_to_bounds(self):
        from cohezion.physics.vliw_bridge import VLIWBridge

        bridge = VLIWBridge()
        state = np.full(12, 0.9, dtype=np.float32)
        delta = np.full(12, 0.5, dtype=np.float32)
        result = bridge.execute_state_transition(state, delta)
        assert np.all(result <= 1.0)

    def test_fallback_clips_to_bounds(self):
        from cohezion.physics.vliw_bridge import VLIWBridge

        bridge = VLIWBridge(force_fallback=True)
        state = np.full(12, -0.9, dtype=np.float32)
        delta = np.full(12, -0.5, dtype=np.float32)
        result = bridge.execute_state_transition(state, delta)
        assert np.all(result >= -1.0)

    def test_invalid_shape_raises(self):
        from cohezion.physics.vliw_bridge import VLIWBridge

        bridge = VLIWBridge()
        with pytest.raises(ValueError):
            bridge.execute_state_transition(np.zeros(6), np.zeros(12))

    def test_benchmark_transition(self):
        from cohezion.physics.vliw_bridge import VLIWBridge

        bridge = VLIWBridge()
        result = bridge.benchmark_transition(np.zeros(12), np.zeros(12))
        assert result.latency_ms >= 0.0
        assert result.transition_count == 1

    def test_state_property(self):
        from cohezion.physics.vliw_bridge import VLIWBridge

        bridge = VLIWBridge(compilation_error="test error")
        s = bridge.state
        assert s.is_degraded is True
        assert s.compilation_error == "test error"

    def test_fallback_both_modes_produce_same_result(self):
        from cohezion.physics.vliw_bridge import VLIWBridge

        state = np.array([0.1, 0.2, 0.3, 0.4, 0.5, -0.1, -0.2, -0.3, -0.4, -0.5, 0.0, 0.0], dtype=np.float32)
        delta = np.array([0.05] * 12, dtype=np.float32)
        simd_result = VLIWBridge()._simd_transition(state, delta)
        py_result = VLIWBridge(force_fallback=True)._python_transition(state, delta)
        assert np.allclose(simd_result, py_result, atol=1e-5)


# ---------------------------------------------------------------------------
# Module 2: security/memory_barrier.py
# ---------------------------------------------------------------------------


class TestMemoryMappedBarrier:
    def _make_barrier(self):
        from cohezion.security.memory_barrier import MemoryMappedBarrier

        return MemoryMappedBarrier()

    def test_gtt_allocation_contains(self):
        from cohezion.security.memory_barrier import GTTAllocation

        alloc = GTTAllocation(allocation_id="proc1", base_address=0x1000, size_bytes=0x500)
        assert alloc.contains(0x1000) is True
        assert alloc.contains(0x14FF) is True
        assert alloc.contains(0x1500) is False
        assert alloc.contains(0x0FFF) is False

    def test_gtt_allocation_end_address(self):
        from cohezion.security.memory_barrier import GTTAllocation

        alloc = GTTAllocation(allocation_id="p", base_address=0x2000, size_bytes=0x100)
        assert alloc.end_address == 0x2100

    def test_barrier_event_to_dict(self):
        from cohezion.security.memory_barrier import BarrierEvent

        ev = BarrierEvent(allocation_id="p1", attempted_address=0xDEAD, event_type="out_of_bounds_read")
        d = ev.to_dict()
        assert d["allocation_id"] == "p1"
        assert d["blocked"] is True

    def test_allocate_and_read_within_bounds(self):
        barrier = self._make_barrier()
        alloc = barrier.allocate("proc1", size_bytes=1024)
        assert isinstance(alloc.base_address, int)
        result = barrier.read("proc1", alloc.base_address)
        assert result is True

    def test_read_out_of_bounds_raises(self):
        from cohezion.security.memory_barrier import BarrierViolationError

        barrier = self._make_barrier()
        alloc = barrier.allocate("proc1", size_bytes=0x100)
        with pytest.raises(BarrierViolationError):
            barrier.read("proc1", alloc.end_address + 0x1000)

    def test_read_unknown_allocation_raises(self):
        barrier = self._make_barrier()
        with pytest.raises(KeyError):
            barrier.read("ghost", 0x1000)

    def test_deny_over_quota_allocation_raises(self):
        from cohezion.security.memory_barrier import BarrierViolationError

        barrier = self._make_barrier()
        with pytest.raises(BarrierViolationError):
            barrier.deny_over_quota_allocation("proc1", 2048, 1024)

    def test_barrier_events_logged(self):
        from cohezion.security.memory_barrier import BarrierViolationError

        barrier = self._make_barrier()
        alloc = barrier.allocate("p1", size_bytes=0x100)
        try:
            barrier.read("p1", alloc.end_address + 0x500)
        except BarrierViolationError:
            pass
        events = barrier.barrier_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "out_of_bounds_read"

    def test_quota_violation_also_logged(self):
        from cohezion.security.memory_barrier import BarrierViolationError

        barrier = self._make_barrier()
        try:
            barrier.deny_over_quota_allocation("p1", 2048, 1024)
        except BarrierViolationError:
            pass
        events = barrier.barrier_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "quota_exceeded"


# ---------------------------------------------------------------------------
# Module 3: physics/flier_routing.py
# ---------------------------------------------------------------------------


class TestFLIERRouter:
    def _make_router(self, num_qubits=6, bond_dim=4):
        from cohezion.physics.flier_routing import FLIERRouter

        return FLIERRouter(num_qubits=num_qubits, bond_dimension=bond_dim)

    def test_init_creates_qubits(self):
        router = self._make_router(num_qubits=6)
        assert len(router.qubits) == 6
        assert router.routing_path == list(range(6))

    def test_qubit_node_default(self):
        from cohezion.physics.flier_routing import QubitNode

        node = QubitNode(id=3)
        assert node.id == 3
        assert node.neighbors == []
        assert node.state_vector is None

    def test_build_dense_topology(self):
        router = self._make_router(num_qubits=6)
        router.build_dense_topology(density=1.0)  # all connected
        # With density=1.0, every qubit should have neighbors
        for q in router.qubits:
            assert len(q.neighbors) > 0

    def test_calculate_swap_overhead(self):
        router = self._make_router(num_qubits=4)
        router.build_dense_topology(density=1.0)
        swaps = router.calculate_swap_overhead(list(range(4)))
        assert isinstance(swaps, int)
        assert swaps >= 0

    def test_optimize_routing_returns_path(self):
        router = self._make_router(num_qubits=4)
        router.build_dense_topology(density=0.7)
        path = router.optimize_routing_path(iterations=5)
        assert len(path) == 4
        assert set(path) == set(range(4))

    def test_run_mps_simulation(self):
        router = self._make_router(num_qubits=4, bond_dim=8)
        result = router.run_mps_simulation(shots=100)
        assert "snr" in result
        assert "fidelity" in result
        assert result["fidelity"] == pytest.approx(0.99)

    def test_run_mps_simulation_bond_dimension(self):
        router = self._make_router(num_qubits=4, bond_dim=16)
        result = router.run_mps_simulation()
        assert result["bond_dimension"] == 16


# ---------------------------------------------------------------------------
# Module 4: mcp/servers/bmad/routes_cis.py
# ---------------------------------------------------------------------------


class TestBmadCisRoutes:
    def _make_request(self, data: dict):
        mock_req = MagicMock()
        mock_req.json = AsyncMock(return_value=data)
        return mock_req

    def test_brainstorming_tool(self):
        from cohezion.mcp.servers.bmad.routes_cis import tool_bmad_cis_brainstorming

        req = self._make_request({"topic": "AI innovation", "participants": 3, "timebox_minutes": 20})
        response = asyncio.run(tool_bmad_cis_brainstorming(req))
        data = response.body
        import json

        parsed = json.loads(data)
        assert parsed["tool"] == "bmad_cis_brainstorming"
        assert "techniques" in parsed

    def test_design_thinking_tool(self):
        from cohezion.mcp.servers.bmad.routes_cis import tool_bmad_cis_design_thinking

        req = self._make_request({"problem": "users can't find search bar"})
        response = asyncio.run(tool_bmad_cis_design_thinking(req))
        import json

        parsed = json.loads(response.body)
        assert parsed["tool"] == "bmad_cis_design_thinking"
        assert len(parsed["phases"]) == 5

    def test_cis_route_handles_empty_request(self):
        from cohezion.mcp.servers.bmad.routes_cis import tool_bmad_cis_brainstorming

        req = self._make_request({})
        response = asyncio.run(tool_bmad_cis_brainstorming(req))
        import json

        parsed = json.loads(response.body)
        assert parsed["tool"] == "bmad_cis_brainstorming"
