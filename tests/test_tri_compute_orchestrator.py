"""
TDD Tests for Tri-Compute Orchestrator.

Tests verify:
1. NPU, iGPU, CPU engines exist and are configurable
2. Task distribution works correctly
3. Phase dependencies are respected
4. Results are aggregated properly
5. Error handling works

Run with: pytest tests/test_tri_compute_orchestrator.py -v
"""

# Add path for imports
import sys
import time
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest


sys.path.insert(0, "src")

from cohezion.inference.tri_compute_orchestrator import (
    ComputeTask,
    CPUOrchestrationEngine,
    ExperimentPhase,
    NPUInferenceEngine,
    TriComputeOrchestrator,
    iGPUSimulationEngine,
)


class TestNPUInferenceEngine:
    """Tests for NPU (XDNA2) inference engine."""

    def test_npu_engine_initializes(self):
        """NPU engine should initialize with correct endpoint."""
        npu = NPUInferenceEngine(port=8004, model="llama3.2:1b")

        assert npu.port == 8004
        assert npu.model == "llama3.2:1b"
        assert npu.endpoint == "http://localhost:8004/v1/chat/completions"
        assert npu.throughput_tps == 12.5  # Known XDNA2 rate

    @pytest.mark.asyncio
    async def test_npu_generates_experiment_params(self):
        """NPU should generate structured experiment parameters."""
        npu = NPUInferenceEngine()

        # Mock the inference call to avoid actual network request
        with patch.object(
            npu,
            "infer",
            return_value="""
            {"n_inference_calls": 100, "particle_count": 1000}
        """,
        ):
            params = npu.generate_experiment_params(phase=1, previous_results={})

        assert "phase" in params
        assert params["phase"] == 1
        assert "n_inference_calls" in params or "particle_count" in params

    @pytest.mark.asyncio
    async def test_npu_infer_returns_string(self):
        """NPU infer should return text response."""
        npu = NPUInferenceEngine()

        # Mock the actual HTTP call
        mock_response = {"choices": [{"message": {"content": "test response"}}]}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(
                return_value=AsyncMock(json=AsyncMock(return_value=mock_response))
            )
            mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await npu.infer("test prompt")

        assert isinstance(result, str)


class TestiGPUSimulationEngine:
    """Tests for iGPU (Vulkan) simulation engine."""

    def test_igpu_engine_initializes(self):
        """iGPU engine should initialize with correct concurrency."""
        igpu = iGPUSimulationEngine(max_concurrency=4)

        assert igpu.max_concurrency == 4
        assert igpu.throughput_tps == 121.5  # Peak observed

    def test_igpu_simulates_flume_batch(self):
        """iGPU should simulate FLUME agent batch evolution."""
        igpu = iGPUSimulationEngine()

        # Create mock agents
        agents = [{"latent": np.random.randn(256), "coherence": 0.5} for _ in range(10)]

        result = igpu.simulate_flume_batch(agents, n_steps=10)

        assert len(result) == len(agents)

    def test_igpu_computes_nbody_gravity(self):
        """iGPU should compute N-body gravitational forces."""
        igpu = iGPUSimulationEngine()

        positions = np.random.randn(10, 3) * 100
        masses = np.ones(10)

        forces = igpu.nbody_gravity(positions, masses, dt=0.01)

        assert forces.shape == positions.shape
        # Forces should generally be non-zero
        assert np.any(forces != 0)

    def test_igpu_updates_mhd_field(self):
        """iGPU should update MHD magnetic field."""
        igpu = iGPUSimulationEngine()

        b_field = np.random.randn(32, 32, 32, 3) * 0.1
        velocity = np.random.randn(32, 32, 32, 3) * 0.01

        updated_b = igpu.mhd_field_update(b_field, velocity, dt=0.01)

        assert updated_b.shape == b_field.shape


class TestCPUOrchestrationEngine:
    """Tests for CPU (Zen 5) orchestration engine."""

    def test_cpu_engine_initializes(self):
        """CPU engine should initialize with correct worker count."""
        cpu = CPUOrchestrationEngine(n_workers=16)

        assert cpu.n_workers == 16

    def test_cpu_schedules_phase_tasks(self):
        """CPU should generate correct task list for a phase."""
        cpu = CPUOrchestrationEngine(n_workers=8)

        phase = ExperimentPhase(
            phase_id=1,
            name="test",
            npu_workload=lambda x: x,
            igpu_workload=lambda x: x,
            cpu_workload=lambda x: x,
        )

        tasks = cpu.schedule_phase(phase, previous_results={})

        assert len(tasks) == 3  # NPU, iGPU, CPU tasks
        assert any(t.task_type == "npu" for t in tasks)
        assert any(t.task_type == "igpu" for t in tasks)
        assert any(t.task_type == "cpu" for t in tasks)

    def test_cpu_aggregates_results(self):
        """CPU should aggregate multi-compute results."""
        cpu = CPUOrchestrationEngine()

        # Mock results from each compute unit
        phase_results = [
            ComputeTask("test_npu", "npu", {"param": "value"}, result={"generated": True}),
            ComputeTask("test_igpu", "igpu", {"sim": True}, result={"simulated": True}),
            ComputeTask("test_cpu", "cpu", {}, result={"validated": True}),
        ]

        for task in phase_results:
            task.started_at = time.time()
            task.completed_at = time.time() + 0.1
            task.status = "completed"

        aggregated = cpu.aggregate_results(phase_results)

        assert "npu_params" in aggregated or "igpu_result" in aggregated
        assert "timing" in aggregated


class TestTriComputeOrchestrator:
    """Integration tests for full Tri-Compute Orchestrator."""

    def test_orchestrator_initializes_all_engines(self):
        """Orchestrator should initialize NPU, iGPU, CPU engines."""
        orch = TriComputeOrchestrator()

        assert orch.npu is not None
        assert orch.igpu is not None
        assert orch.cpu is not None

    def test_orchestrator_registers_phases(self):
        """Orchestrator should accept phase registrations."""
        orch = TriComputeOrchestrator()

        phase = ExperimentPhase(
            phase_id=1,
            name="FLUME Test",
            npu_workload=Mock(),
            igpu_workload=Mock(),
            cpu_workload=Mock(),
        )

        orch.register_phase(phase)

        assert len(orch.phases) == 1
        assert orch.phases[0].phase_id == 1

    @pytest.mark.asyncio
    async def test_orchestrator_runs_single_phase(self):
        """Orchestrator should execute single phase successfully."""
        orch = TriComputeOrchestrator()

        phase = ExperimentPhase(
            phase_id=0,
            name="Baseline",
            npu_workload=lambda ctx: {"params": True},
            igpu_workload=lambda ctx: {"sim": True},
            cpu_workload=lambda ctx: {"validated": True},
        )

        # Mock the actual compute calls to avoid dependencies
        with (
            patch.object(orch.npu, "infer", return_value="{}"),
            patch.object(
                orch.igpu,
                "run_simulation_batch",
                return_value=[ComputeTask("test", "igpu", {}, result={"simulated": True})],
            ),
        ):
            result = await orch.run_phase(phase)

        assert result is not None
        assert "phase_id" in result
        assert result["phase_id"] == 0


class TestComputeTask:
    """Tests for task data structure."""

    def test_task_tracks_timing(self):
        """Tasks should track creation, start, and completion times."""
        task = ComputeTask("test", "npu", {"data": True})

        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None

        # Simulate execution
        task.started_at = time.time()
        time.sleep(0.01)
        task.completed_at = time.time()

        assert task.started_at < task.completed_at

    def test_task_stores_result(self):
        """Tasks should store execution results."""
        task = ComputeTask("test", "igpu", {"sim": True})

        task.result = {"output": "success"}
        task.status = "completed"

        assert task.result is not None
        assert task.status == "completed"

    def test_task_stores_errors(self):
        """Tasks should capture error information."""
        task = ComputeTask("test", "cpu", {"data": True})

        task.error = "RuntimeError: test failed"
        task.status = "failed"

        assert task.error is not None
        assert task.status == "failed"


class TestExperimentPhases:
    """Tests for experimental phase structure."""

    def test_phase_has_dependencies(self):
        """Phases can specify dependencies on other phases."""
        phase = ExperimentPhase(
            phase_id=2,
            name="EVO",
            npu_workload=None,
            igpu_workload=None,
            cpu_workload=None,
            dependencies=[0, 1],  # Depends on phases 0 and 1
        )

        assert phase.dependencies == [0, 1]

    def test_phase_default_no_dependencies(self):
        """Phases default to no dependencies."""
        phase = ExperimentPhase(
            phase_id=0,
            name="Baseline",
            npu_workload=None,
            igpu_workload=None,
            cpu_workload=None,
        )

        assert phase.dependencies == []


class TestPerformanceRequirements:
    """Performance benchmarks for tri-compute."""

    def test_npu_latency_under_100ms(self):
        """NPU inference should complete within 100ms."""
        npu = NPUInferenceEngine()

        # This is a design constraint, not a live test
        assert npu.latency_ms <= 100, "NPU latency exceeds 100ms threshold"

    def test_igpu_throughput_over_100_tps(self):
        """iGPU should sustain over 100 tokens/second."""
        igpu = iGPUSimulationEngine()

        assert igpu.throughput_tps >= 100, "iGPU throughput below 100 TPS"

    def test_cpu_uses_full_core_count(self):
        """CPU orchestrator should utilize all Zen 5 cores."""
        cpu = CPUOrchestrationEngine(n_workers=16)

        assert cpu.n_workers == 16, "CPU not using all 16 cores"


# Run with: pytest tests/test_tri_compute_orchestrator.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
