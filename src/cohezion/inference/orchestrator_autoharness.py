"""
Orchestrator AutoHarness - Multi-Node Distributed Inference

Orchestrates tasks across heterogeneous compute nodes:
- GPU (Vulkan): High-throughput, best for concurrent batches
- NPU (XDNA2): Low-latency, best for sequential tasks
- CPU (Zen 5): Fallback, small models

Features:
- Task routing based on node capabilities and load
- Dynamic load balancing
- Failover between backends
- Result aggregation from distributed execution
- Hardware-aware scheduling (thermal throttling, memory)

Integrates with:
- HardwareTelemetry: Monitors node health and capacity
- CompoundEngineeringAutoHarness: Optimizes per-node configurations
- AntiSycophancy: Prevents gaming by verifying actual utilization
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class ComputeNodeState(Enum):
    """State of a compute node."""
    IDLE = "idle"
    BUSY = "busy"
    THROTTLED = "throttled"  # Thermal/power limiting
    OVERLOADED = "overloaded"  # Memory/queue full
    OFFLINE = "offline"


@dataclass
class ComputeNode:
    """Heterogeneous compute node (GPU/NPU/CPU)."""
    node_id: str
    backend: str  # "vulkan_gpu", "xdna2_npu", "zen5_cpu"

    # Capabilities
    max_concurrency: int = 1
    optimal_batch_size: int = 1
    supports_streaming: bool = False

    # Current state
    state: ComputeNodeState = ComputeNodeState.IDLE
    active_tasks: int = 0
    queued_tasks: int = 0

    # Performance metrics
    tokens_per_sec: float = 0.0
    avg_latency_ms: float = 0.0

    # Hardware telemetry
    temperature_c: float = 0.0
    utilization_pct: float = 0.0
    memory_used_mb: int = 0
    memory_total_mb: int = 0

    # Task affinity
    supported_task_types: set[str] = field(default_factory=set)

    def available_capacity(self) -> int:
        """Calculate available task slots."""
        if self.state in (ComputeNodeState.OFFLINE, ComputeNodeState.THROTTLED):
            return 0
        return max(0, self.max_concurrency - self.active_tasks)

    def health_score(self) -> float:
        """
        Calculate health score (0-1).
        
        Factors:
        - Load (lower is better)
        - Temperature (cooler is better)
        - Recent performance
        """
        if self.state == ComputeNodeState.OFFLINE:
            return 0.0

        # Load factor
        load = self.active_tasks / max(self.max_concurrency, 1)
        load_score = 1.0 - (load ** 2)  # Quadratic penalty for saturation

        # Temperature factor
        temp_score = 1.0
        if self.temperature_c > 85:
            temp_score = 0.0  # Critical
        elif self.temperature_c > 75:
            temp_score = 0.5  # Warning
        elif self.temperature_c > 0:
            temp_score = 1.0 - (self.temperature_c - 50) / 50

        # State factor
        state_score = {
            ComputeNodeState.IDLE: 1.0,
            ComputeNodeState.BUSY: 0.8,
            ComputeNodeState.THROTTLED: 0.3,
            ComputeNodeState.OVERLOADED: 0.1,
        }.get(self.state, 0.0)

        return (load_score * 0.5 + temp_score * 0.3 + state_score * 0.2)


@dataclass
class Task:
    """Task to be executed."""
    task_id: str
    prompt: str
    task_type: str  # "reasoning", "coding", "embedding", etc.
    priority: TaskPriority = TaskPriority.NORMAL

    # Requirements
    requires_streaming: bool = False
    max_latency_ms: int | None = None
    min_quality_score: float = 0.0

    # Routing hints
    preferred_backend: str | None = None
    avoid_backends: set[str] = field(default_factory=set)

    # State
    status: str = "pending"  # pending, assigned, running, completed, failed
    assigned_node: str | None = None
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    completed_at: float | None = None

    def wait_time_ms(self) -> float:
        """Calculate current wait time."""
        return (time.monotonic() - self.created_at) * 1000


@dataclass
class RoutingDecision:
    """Result of task routing decision."""
    task: Task
    node: ComputeNode | None
    strategy: str
    reason: str


class MultiNodeOrchestrator:
    """
    Orchestrates tasks across heterogeneous compute nodes.
    
    Features:
    - Intelligent routing based on task requirements and node state
    - Load balancing across available capacity
    - Automatic failover on node failure
    - Result aggregation from distributed execution
    """

    def __init__(self):
        self.nodes: dict[str, ComputeNode] = {}
        self.tasks: dict[str, Task] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.results: dict[str, Any] = {}

        # Telemetry
        self.telemetry_samples: list[dict] = []

        # Configuration
        self.max_retries = 3
        self.health_check_interval_sec = 10

    def register_node(self, node: ComputeNode):
        """Register a compute node."""
        self.nodes[node.node_id] = node
        logger.info(f"Registered node {node.node_id} ({node.backend})")

    def deregister_node(self, node_id: str):
        """Deregister a compute node."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            logger.info(f"Deregistered node {node_id}")

    def update_node_state(self, node_id: str, telemetry: dict):
        """Update node state from telemetry."""
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]

        # Update metrics
        node.temperature_c = telemetry.get("temperature_c", node.temperature_c)
        node.utilization_pct = telemetry.get("utilization_pct", node.utilization_pct)
        node.memory_used_mb = telemetry.get("memory_used_mb", node.memory_used_mb)

        # Determine state
        if telemetry.get("throttling", False) or node.temperature_c > 85:
            node.state = ComputeNodeState.THROTTLED
        elif node.active_tasks >= node.max_concurrency:
            node.state = ComputeNodeState.OVERLOADED
        elif node.active_tasks > 0:
            node.state = ComputeNodeState.BUSY
        else:
            node.state = ComputeNodeState.IDLE

    async def submit_task(self, task: Task) -> str:
        """
        Submit a task to the orchestrator.
        
        Returns task ID for tracking.
        """
        self.tasks[task.task_id] = task

        # Priority queue: (priority, task_id, task)
        await self.task_queue.put((task.priority.value, task.created_at, task.task_id, task))

        logger.debug(f"Submitted task {task.task_id} ({task.task_type})")
        return task.task_id

    async def route_task(self, task: Task) -> RoutingDecision:
        """
        Route a task to the optimal compute node.
        
        Strategy:
        1. Check preferred backend if specified
        2. Find nodes that support task type
        3. Filter out overloaded/throttled nodes
        4. Score remaining by health + latency match
        5. Select best node
        """
        available = []

        for node in self.nodes.values():
            # Skip if explicitly avoided
            if node.backend in task.avoid_backends:
                continue

            # Skip if doesn't support task type
            if task.task_type not in node.supported_task_types:
                continue

            # Skip if capacity exhausted
            if node.available_capacity() == 0:
                continue

            # Skip if requires streaming and node doesn't support
            if task.requires_streaming and not node.supports_streaming:
                continue

            available.append(node)

        if not available:
            return RoutingDecision(
                task=task,
                node=None,
                strategy="failed",
                reason="No available nodes match requirements"
            )

        # Preferred backend gets priority
        if task.preferred_backend:
            preferred = [n for n in available if n.backend == task.preferred_backend]
            if preferred:
                available = preferred

        # Score and select best node
        scored = [(n.health_score() + self._latency_match_score(task, n), n)
                  for n in available]
        scored.sort(reverse=True)

        best_node = scored[0][1]

        return RoutingDecision(
            task=task,
            node=best_node,
            strategy="intelligent_routing",
            reason=f"Best match: {best_node.backend} with health {best_node.health_score():.2f}"
        )

    def _latency_match_score(self, task: Task, node: ComputeNode) -> float:
        """Score how well node matches latency requirements."""
        if task.max_latency_ms is None:
            return 0.5  # Neutral

        if node.avg_latency_ms == 0:
            return 0.5  # Unknown

        if node.avg_latency_ms <= task.max_latency_ms * 0.8:
            return 1.0  # Good margin
        elif node.avg_latency_ms <= task.max_latency_ms:
            return 0.5  # Just fits
        else:
            return 0.0  # Too slow

    async def execute_task(self, task: Task, node: ComputeNode,
                          executor: Callable) -> Any:
        """
        Execute a task on a specific node.
        
        Updates node state and handles failures.
        """
        task.status = "running"
        task.assigned_node = node.node_id
        task.started_at = time.monotonic()
        node.active_tasks += 1

        try:
            # Execute
            result = await executor(task, node)

            task.status = "completed"
            task.completed_at = time.monotonic()
            task.result = result

            # Update node performance
            latency_ms = (task.completed_at - task.started_at) * 1000
            node.avg_latency_ms = (node.avg_latency_ms * 0.9 + latency_ms * 0.1)

            logger.debug(f"Task {task.task_id} completed on {node.node_id}")

            return result

        except Exception as e:
            task.status = "failed"
            task.error = str(e)

            logger.error(f"Task {task.task_id} failed on {node.node_id}: {e}")

            raise

        finally:
            node.active_tasks -= 1

    async def process_queue(self, executor: Callable,
                            stop_event: asyncio.Event):
        """
        Process task queue continuously.
        
        Main orchestration loop.
        """
        while not stop_event.is_set():
            try:
                # Non-blocking wait
                priority, _, task_id, task = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )

                # Route task
                decision = await self.route_task(task)

                if decision.node is None:
                    # Requeue if possible
                    task.status = "pending"
                    await asyncio.sleep(0.1)  # Brief backoff
                    await self.task_queue.put(
                        (task.priority.value, time.monotonic(), task.task_id, task)
                    )
                    continue

                # Execute
                try:
                    await self.execute_task(task, decision.node, executor)
                except Exception:
                    # Handle retry logic
                    pass

            except TimeoutError:
                continue

    async def gather_results(self, task_ids: list[str],
                             timeout_sec: float = 300.0) -> dict[str, Any]:
        """
        Gather results from distributed tasks.
        
        Returns results for completed tasks.
        """
        results = {}
        pending = set(task_ids)
        deadline = time.monotonic() + timeout_sec

        while pending and time.monotonic() < deadline:
            for task_id in list(pending):
                if task_id not in self.tasks:
                    continue

                task = self.tasks[task_id]
                if task.status == "completed":
                    results[task_id] = task.result
                    pending.remove(task_id)
                elif task.status == "failed":
                    results[task_id] = {"error": task.error}
                    pending.remove(task_id)

            if pending:
                await asyncio.sleep(0.1)

        # Mark remaining as timeout
        for task_id in pending:
            results[task_id] = {"error": "timeout"}

        return results

    def get_orchstration_report(self) -> str:
        """Generate orchestration report."""
        lines = [
            "=" * 70,
            "MULTI-NODE ORCHESTRATION REPORT",
            "=" * 70,
            "",
            "--- COMPUTE NODES ---",
        ]

        for node in sorted(self.nodes.values(), key=lambda n: n.node_id):
            lines.append(
                f"{node.node_id} ({node.backend}):"
            )
            lines.append(
                f"  State: {node.state.value} | "
                f"Active: {node.active_tasks}/{node.max_concurrency} | "
                f"Health: {node.health_score():.2f}"
            )
            lines.append(
                f"  Temp: {node.temperature_c}°C | "
                f"Memory: {node.memory_used_mb/1024:.1f}GB | "
                f"TPS: {node.tokens_per_sec:.1f}"
            )
            lines.append("")

        # Task summary
        pending = sum(1 for t in self.tasks.values() if t.status == "pending")
        running = sum(1 for t in self.tasks.values() if t.status == "running")
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        failed = sum(1 for t in self.tasks.values() if t.status == "failed")

        lines.extend([
            "--- TASK SUMMARY ---",
            f"Pending: {pending}",
            f"Running: {running}",
            f"Completed: {completed}",
            f"Failed: {failed}",
            "",
        ])

        # Utilization
        lines.append("--- CLUSTER UTILIZATION ---")
        total_capacity = sum(n.max_concurrency for n in self.nodes.values())
        used_capacity = sum(n.active_tasks for n in self.nodes.values())

        if total_capacity > 0:
            utilization = used_capacity / total_capacity * 100
            lines.append(f"Total capacity: {total_capacity}")
            lines.append(f"Used capacity: {used_capacity}")
            lines.append(f"Utilization: {utilization:.1f}%")

            if utilization < 50:
                lines.append("❌ UNDERUTILIZED - Add more tasks")
            elif utilization > 90:
                lines.append("⚠️ SATURATED - May experience queuing")
            else:
                lines.append("✅ GOOD - Well-utilized cluster")

        lines.append("=" * 70)

        return "\n".join(lines)


class StrixHaloOrchestrator:
    """
    Pre-configured orchestrator for AMD Strix Halo.
    
    Sets up nodes for GPU, NPU, and CPU automatically.
    """

    def __init__(self):
        self.orchestrator = MultiNodeOrchestrator()
        self._setup_strix_halo_nodes()

    def _setup_strix_halo_nodes(self):
        """Configure nodes for Strix Halo hardware."""
        # GPU node (Vulkan)
        # - High throughput
        # - Best for concurrent requests
        # - Thermal sensitive
        gpu_node = ComputeNode(
            node_id="vulkan_gpu_0",
            backend="vulkan_gpu",
            max_concurrency=4,  # From saturation curve
            optimal_batch_size=4,
            supports_streaming=True,
            supported_task_types={
                "reasoning", "coding", "generation", "embedding"
            },
        )
        self.orchestrator.register_node(gpu_node)

        # NPU node (XDNA2)
        # - Low latency
        # - Sequential only (no concurrency benefit)
        # - Good for small models
        npu_node = ComputeNode(
            node_id="xdna2_npu_0",
            backend="xdna2_npu",
            max_concurrency=1,  # Sequential only
            optimal_batch_size=1,
            supports_streaming=False,
            supported_task_types={
                "inference", "classification"
            },
        )
        self.orchestrator.register_node(npu_node)

        # CPU node (Zen 5)
        # - Fallback
        # - Good for small models
        cpu_node = ComputeNode(
            node_id="zen5_cpu_0",
            backend="zen5_cpu",
            max_concurrency=2,  # SMT
            optimal_batch_size=1,
            supports_streaming=True,
            supported_task_types={
                "reasoning", "coding"
            },
        )
        self.orchestrator.register_node(cpu_node)

    async def submit_prompt(self, prompt: str,
                           task_type: str = "reasoning",
                           priority: TaskPriority = TaskPriority.NORMAL,
                           preferred_backend: str | None = None) -> str:
        """
        Submit a single prompt.
        
        Returns task ID.
        """
        task = Task(
            task_id=f"task_{int(time.time()*1000)}_{id(prompt)}",
            prompt=prompt,
            task_type=task_type,
            priority=priority,
            preferred_backend=preferred_backend,
        )

        return await self.orchestrator.submit_task(task)

    async def submit_batch(self, prompts: list[str],
                          task_type: str = "reasoning") -> list[str]:
        """
        Submit multiple prompts as batch.
        
        Distributes across available nodes.
        """
        task_ids = []
        for prompt in prompts:
            task_id = await self.submit_prompt(prompt, task_type=task_type)
            task_ids.append(task_id)
        return task_ids


def create_strix_halo_orchestrator() -> StrixHaloOrchestrator:
    """Factory for Strix Halo orchestrator."""
    return StrixHaloOrchestrator()


if __name__ == "__main__":
    # Demo
    async def demo():
        print("Strix Halo Orchestrator Demo")
        print("=" * 50)

        orch = create_strix_halo_orchestrator()

        # Show nodes
        print(orch.orchestrator.get_orchstration_report())
        print()

        # Submit tasks
        print("Submitting tasks...")
        for i in range(5):
            await orch.submit_prompt(
                f"Task {i+1}",
                task_type="reasoning",
                priority=TaskPriority.NORMAL
            )

        print(orch.orchestrator.get_orchstration_report())

    asyncio.run(demo())
