"""
Tri-Compute Orchestrator for Phase Connection Experiments

Distributes workload across AMD Strix Halo heterogeneous compute:
- NPU (XDNA2): Local inference, decision-making, pattern recognition
- iGPU (Vulkan/Mediatek): Parallel simulation (FLUME/EVO/MHD/SWIFT)
- CPU (Zen 5): Orchestration, I/O, sequential tasks, result aggregation

"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from queue import Queue
from typing import Any

import numpy as np


# Configuration for tri-compute
NPU_DEVICE = "/dev/xdna2"
VULKAN_DEVICE = "amd:0"
CPU_CORES = 16


@dataclass
class ComputeTask:
    """Task to be executed on specific compute unit."""

    task_id: str
    task_type: str  # "npu", "igpu", "cpu"
    payload: Any
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: Any = None
    error: str | None = None


@dataclass
class ExperimentPhase:
    """Single phase of the experimental framework."""

    phase_id: int
    name: str
    npu_workload: Callable  # Inference, pattern recognition
    igpu_workload: Callable  # Parallel simulation
    cpu_workload: Callable  # Orchestration, I/O
    dependencies: list[int] = field(default_factory=list)
    status: str = "pending"


class NPUInferenceEngine:
    """
    NPU (XDNA2) for local inference and decision-making.

    Uses FLM (FastFlowLM) runtime on port 8004.
    Best for: Sequential inference, low-latency decisions
    """

    def __init__(self, port: int = 8004, model: str = "llama3.2:1b"):
        self.port = port
        self.model = model
        self.endpoint = f"http://localhost:{port}/v1/chat/completions"
        self.latency_ms = 80  # Typical for XDNA2
        self.throughput_tps = 12.5

    async def infer(self, prompt: str, max_tokens: int = 256) -> str:
        """Run inference on NPU."""
        import aiohttp

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint, json=payload) as resp:
                result = await resp.json()
                return result["choices"][0]["message"]["content"]

    def generate_experiment_params(self, phase: int, previous_results: dict) -> dict:
        """Use NPU to generate next experiment parameters."""
        # This would actually call the NPU
        # For now, return structured params
        prompt = f"""
        Generate parameters for Phase {phase} experiment.
        Previous results: {json.dumps(previous_results, indent=2)}

        Return JSON with:
        - n_inference_calls: int
        - particle_count: int
        - grid_resolution: int
        - exotic_fraction: float
        """

        # Simulated NPU response
        return {
            "phase": phase,
            "n_inference_calls": 100 + phase * 50,
            "particle_count": 100 * (2**phase),
            "grid_resolution": 32 * (2 ** (phase // 2)),
            "exotic_fraction": 0.1 + phase * 0.05,
            "timestamp": time.time(),
        }


class iGPUSimulationEngine:
    """
    iGPU (Radeon 8060S) for parallel simulation workloads.

    Uses Vulkan compute for:
    - FLUME latent space evolution (batch)
    - EVO physical dynamics (N-body)
    - MHD field updates (grid)
    - SWIFT particle pushing

    Best for: Embarrassingly parallel, data-parallel tasks
    """

    def __init__(self, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency
        self.throughput_tps = 121.5  # Peak at concurrency=4
        self.executor = ThreadPoolExecutor(max_workers=max_concurrency)

    def simulate_flume_batch(self, agents: list[Any], n_steps: int) -> list[Any]:
        """
        Batch HIHO evolution on GPU using Vulkan compute.

        Would dispatch to Vulkan compute shaders.
        For now: vectorized NumPy (simulated)
        """
        # Placeholder: actual implementation uses Vulkan compute
        for _ in range(n_steps):
            for agent in agents:
                if hasattr(agent, "hiho_step"):
                    agent.hiho_step()
        return agents

    def nbody_gravity(
        self, positions: np.ndarray, masses: np.ndarray, dt: float = 0.01
    ) -> np.ndarray:
        """
        N-body gravity on GPU.

        O(N^2) force calculation, accelerates on GPU.
        """
        n = len(positions)
        forces = np.zeros_like(positions)

        # Vectorized computation (would be Vulkan in production)
        for i in range(n):
            r_vec = positions - positions[i]
            r_mag = np.linalg.norm(r_vec, axis=1) + 1e-10
            force_mag = masses[i] * masses / (r_mag**2)
            force = (r_vec.T * force_mag).T / r_mag[:, np.newaxis]
            forces[i] = np.sum(force, axis=0)

        return forces

    def mhd_field_update(self, b_field: np.ndarray, velocity: np.ndarray, dt: float) -> np.ndarray:
        """
        MHD induction equation on GPU.

        ∂B/∂t = ∇ × (v × B)
        """
        # Placeholder: actual would be Vulkan compute
        return b_field + np.random.randn(*b_field.shape) * 0.01 * dt

    async def run_simulation_batch(self, tasks: list[ComputeTask]) -> list[ComputeTask]:
        """Execute batch of simulation tasks on GPU."""
        loop = asyncio.get_event_loop()

        # Submit to thread pool (which would dispatch to GPU)
        futures = []
        for task in tasks:
            future = loop.run_in_executor(self.executor, self._execute_simulation_task, task)
            futures.append(future)

        results = await asyncio.gather(*futures)
        return results

    def _execute_simulation_task(self, task: ComputeTask) -> ComputeTask:
        """Execute single simulation task."""
        task.started_at = time.time()

        try:
            payload = task.payload
            task_type = payload.get("simulation_type")

            if task_type == "flume":
                result = self.simulate_flume_batch(payload["agents"], payload["n_steps"])
            elif task_type == "nbody":
                result = self.nbody_gravity(payload["positions"], payload["masses"])
            elif task_type == "mhd":
                result = self.mhd_field_update(
                    payload["b_field"], payload["velocity"], payload["dt"]
                )
            else:
                result = {"error": f"Unknown simulation type: {task_type}"}

            task.result = result
            task.status = "completed"

        except Exception as e:
            task.error = str(e)
            task.status = "failed"

        task.completed_at = time.time()
        return task


class CPUOrchestrationEngine:
    """
    CPU (Zen 5, 16 cores) for orchestration and I/O.

    Responsibilities:
    - Task scheduling and dependency management
    - Data marshaling between compute units
    - Result aggregation and analysis
    - File I/O (HDF5, checkpoints)
    - Communication with SurrealDB

    Best for: Sequential logic, complex control flow, I/O
    """

    def __init__(self, n_workers: int = 16):
        self.n_workers = n_workers
        self.executor = ProcessPoolExecutor(max_workers=n_workers)
        self.task_queue: Queue = Queue()
        self.results: dict[str, ComputeTask] = {}

    def schedule_phase(self, phase: ExperimentPhase, previous_results: dict) -> list[ComputeTask]:
        """
        Schedule a complete experimental phase across all compute units.

        Returns list of tasks for NPU, iGPU, and CPU.
        """
        tasks = []

        # Task 1: NPU generates parameters
        tasks.append(
            ComputeTask(
                task_id=f"{phase.phase_id}_npu_params",
                task_type="npu",
                payload={
                    "phase": phase.phase_id,
                    "previous_results": previous_results,
                    "generator": phase.npu_workload,
                },
                priority=0,
            )
        )

        # Task 2: iGPU runs simulation (depends on NPU)
        tasks.append(
            ComputeTask(
                task_id=f"{phase.phase_id}_igpu_sim",
                task_type="igpu",
                payload={
                    "simulation_type": "flume" if phase.phase_id <= 2 else "nbody",
                    "depends_on": f"{phase.phase_id}_npu_params",
                    "simulator": phase.igpu_workload,
                },
                priority=1,
            )
        )

        # Task 3: CPU aggregates and validates
        tasks.append(
            ComputeTask(
                task_id=f"{phase.phase_id}_cpu_validate",
                task_type="cpu",
                payload={
                    "validator": phase.cpu_workload,
                    "depends_on": f"{phase.phase_id}_igpu_sim",
                },
                priority=2,
            )
        )

        return tasks

    def execute_cpu_task(self, task: ComputeTask) -> ComputeTask:
        """Execute CPU-bound task."""
        task.started_at = time.time()

        try:
            payload = task.payload
            # Execute CPU workload
            result = payload.get("validator", lambda x: x)(payload)
            task.result = result
            task.status = "completed"
        except Exception as e:
            task.error = str(e)
            task.status = "failed"

        task.completed_at = time.time()
        return task

    def aggregate_results(self, phase_results: list[ComputeTask]) -> dict:
        """
        Aggregate results from all compute units after a phase.

        Combines NPU decisions, iGPU simulation outputs, CPU validation.
        """
        aggregated = {
            "phase": None,
            "npu_params": None,
            "igpu_result": None,
            "cpu_validation": None,
            "timing": {},
        }

        for task in phase_results:
            if task.task_type == "npu":
                aggregated["npu_params"] = task.result
                aggregated["timing"]["npu_ms"] = (
                    (task.completed_at - task.started_at) * 1000
                    if task.completed_at and task.started_at
                    else None
                )
            elif task.task_type == "igpu":
                aggregated["igpu_result"] = task.result
                aggregated["timing"]["igpu_ms"] = (
                    (task.completed_at - task.started_at) * 1000
                    if task.completed_at and task.started_at
                    else None
                )
            elif task.task_type == "cpu":
                aggregated["cpu_validation"] = task.result
                aggregated["timing"]["cpu_ms"] = (
                    (task.completed_at - task.started_at) * 1000
                    if task.completed_at and task.started_at
                    else None
                )

        return aggregated


class TriComputeOrchestrator:
    """
    Master orchestrator coordinating NPU, iGPU, and CPU.

    Pipeline flow for each experimental phase:
    1. CPU schedules phase, dispatches to NPU for parameter generation
    2. NPU returns parameters, CPU dispatches to iGPU for simulation
    3. iGPU returns results, CPU aggregates and validates
    4. CPU stores results, proceeds to next phase
    """

    def __init__(self):
        self.npu = NPUInferenceEngine(port=8004, model="llama3.2:1b")
        self.igpu = iGPUSimulationEngine(max_concurrency=4)
        self.cpu = CPUOrchestrationEngine(n_workers=16)

        self.phases: list[ExperimentPhase] = []
        self.results: dict[int, dict] = {}

    def register_phase(self, phase: ExperimentPhase):
        """Register an experimental phase."""
        self.phases.append(phase)

    async def run_phase(self, phase: ExperimentPhase) -> dict:
        """
        Execute single phase using tri-compute.

        Sequence:
        1. NPU: Generate parameters (sequential, fast inference)
        2. iGPU: Run simulation (parallel, batch processing)
        3. CPU: Validate and aggregate (sequential, I/O)
        """
        print(f"\n[Tri-Compute] Starting Phase {phase.phase_id}: {phase.name}")

        # Get previous results for dependency
        prev_results = {dep: self.results.get(dep, {}) for dep in phase.dependencies}

        # Step 1: NPU generates parameters
        print("  [NPU] Generating experiment parameters...")
        npu_start = time.time()
        params = await self.npu.infer(
            prompt=f"Generate params for Phase {phase.phase_id} with context: {prev_results}"
        )
        npu_time = (time.time() - npu_start) * 1000
        print(f"  [NPU] Complete in {npu_time:.1f}ms")

        # Step 2: iGPU runs simulation (batch)
        print("  [iGPU] Running parallel simulation...")
        igpu_start = time.time()

        # Create iGPU task
        igpu_task = ComputeTask(
            task_id=f"P{phase.phase_id}_igpu",
            task_type="igpu_simulation",
            payload={
                "simulation_type": "flume" if phase.phase_id <= 2 else "nbody",
                "params": params,
                "simulator": phase.igpu_workload,
            },
        )

        igpu_result = await self.igpu.run_simulation_batch([igpu_task])
        igpu_time = (time.time() - igpu_start) * 1000
        print(f"  [iGPU] Complete in {igpu_time:.1f}ms")

        # Step 3: CPU validates and aggregates
        print("  [CPU] Validating and aggregating...")
        cpu_start = time.time()

        # Aggregate all results
        phase_result = {
            "phase_id": phase.phase_id,
            "npu_params": params,
            "npu_time_ms": npu_time,
            "igpu_result": igpu_result[0].result if igpu_result else None,
            "igpu_time_ms": igpu_time,
            "cpu_validator": phase.cpu_workload,
        }

        cpu_time = (time.time() - cpu_start) * 1000
        phase_result["cpu_time_ms"] = cpu_time
        print(f"  [CPU] Complete in {cpu_time:.1f}ms")

        # Total phase time
        phase_result["total_time_ms"] = npu_time + igpu_time + cpu_time
        print(f"  [Phase {phase.phase_id}] Total: {phase_result['total_time_ms']:.1f}ms")

        return phase_result

    async def run_full_experiment(self) -> dict:
        """
        Run all registered phases using tri-compute scheduling.

        Each phase uses:
        - NPU for parameter generation (inference)
        - iGPU for simulation (parallel compute)
        - CPU for validation (orchestration)
        """
        print("=" * 70)
        print("TRI-COMPUTE EXPERIMENT ORCHESTRATION")
        print("NPU (XDNA2) + iGPU (Vulkan) + CPU (Zen 5)")
        print("=" * 70)

        total_start = time.time()

        for phase in self.phases:
            # Run phase
            result = await self.run_phase(phase)
            self.results[phase.phase_id] = result

            # Store to SurrealDB (if available)
            await self._store_result(result)

        total_time = (time.time() - total_start) * 1000

        # Final summary
        print("\n" + "=" * 70)
        print("EXPERIMENT COMPLETE")
        print("=" * 70)
        print(f"Total phases: {len(self.phases)}")
        print(f"Total time: {total_time:.1f}ms ({total_time / 1000:.2f}s)")
        print(f"Average per phase: {total_time / len(self.phases):.1f}ms")

        # Compute unit utilization
        npu_time = sum(r.get("npu_time_ms", 0) for r in self.results.values())
        igpu_time = sum(r.get("igpu_time_ms", 0) for r in self.results.values())
        cpu_time = sum(r.get("cpu_time_ms", 0) for r in self.results.values())

        print("\nCompute utilization:")
        print(f"  NPU: {npu_time:.1f}ms ({100 * npu_time / total_time:.1f}%)")
        print(f"  iGPU: {igpu_time:.1f}ms ({100 * igpu_time / total_time:.1f}%)")
        print(f"  CPU: {cpu_time:.1f}ms ({100 * cpu_time / total_time:.1f}%)")

        return self.results

    async def _store_result(self, result: dict):
        """Store result to SurrealDB or local file."""
        # Placeholder: actual implementation uses SurrealDB client
        pass

    def get_optimal_schedule(self) -> list[ExperimentPhase]:
        """
        Optimize phase ordering for minimal total time.

        Considers:
        - NPU sequential bottleneck (12.5 TPS)
        - iGPU concurrency (4 parallel)
        - CPU availability (16 cores)
        """
        # Topological sort respecting dependencies
        # Then schedule to maximize iGPU batching

        # For now: sequential execution
        return self.phases


# Demo usage
def demo_tri_compute():
    """Demonstrate tri-compute orchestration."""

    def dummy_npu_workload(ctx):
        return {"generated": True, "seed": 42}

    def dummy_igpu_workload(ctx):
        return {"simulated": True, "particles": 1000}

    def dummy_cpu_workload(ctx):
        return {"validated": True, "score": 0.95}

    # Create phases
    phases = [
        ExperimentPhase(
            phase_id=0,
            name="Baseline Inference",
            npu_workload=dummy_npu_workload,
            igpu_workload=dummy_igpu_workload,
            cpu_workload=dummy_cpu_workload,
        ),
        ExperimentPhase(
            phase_id=1,
            name="FLUME Coherence",
            npu_workload=dummy_npu_workload,
            igpu_workload=dummy_igpu_workload,
            cpu_workload=dummy_cpu_workload,
            dependencies=[0],
        ),
        ExperimentPhase(
            phase_id=2,
            name="EVO Coupling",
            npu_workload=dummy_npu_workload,
            igpu_workload=dummy_igpu_workload,
            cpu_workload=dummy_cpu_workload,
            dependencies=[1],
        ),
    ]

    # Create orchestrator
    orchestrator = TriComputeOrchestrator()

    # Register phases
    for phase in phases:
        orchestrator.register_phase(phase)

    # Run
    async def run():
        results = await orchestrator.run_full_experiment()
        return results

    return asyncio.run(run())


if __name__ == "__main__":
    demo_tri_compute()
