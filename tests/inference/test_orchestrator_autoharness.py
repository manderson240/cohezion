"""Unit tests for orchestrator_autoharness — multi-node compute scheduling."""

from __future__ import annotations

from cohezion.inference.orchestrator_autoharness import (
    ComputeNode,
    ComputeNodeState,
    Task,
    TaskPriority,
)


# ── ComputeNode.available_capacity ────────────────────────────────────────────


class TestComputeNodeCapacity:
    def test_idle_node_full_capacity(self):
        """Idle node with no active tasks → max_concurrency slots available."""
        node = ComputeNode(
            node_id="npu-0",
            backend="xdna2_npu",
            max_concurrency=4,
            active_tasks=0,
            state=ComputeNodeState.IDLE,
        )
        assert node.available_capacity() == 4

    def test_offline_node_zero_capacity(self):
        """Offline node → 0 capacity regardless of active tasks."""
        node = ComputeNode(
            node_id="gpu-0",
            backend="vulkan_gpu",
            max_concurrency=8,
            active_tasks=0,
            state=ComputeNodeState.OFFLINE,
        )
        assert node.available_capacity() == 0

    def test_throttled_node_zero_capacity(self):
        """Throttled node (thermal limiting) → 0 capacity."""
        node = ComputeNode(
            node_id="cpu-0",
            backend="zen5_cpu",
            max_concurrency=16,
            active_tasks=3,
            state=ComputeNodeState.THROTTLED,
        )
        assert node.available_capacity() == 0

    def test_partially_loaded_node(self):
        """Node with 2 active / 4 max → 2 slots available."""
        node = ComputeNode(
            node_id="npu-0",
            backend="xdna2_npu",
            max_concurrency=4,
            active_tasks=2,
            state=ComputeNodeState.BUSY,
        )
        assert node.available_capacity() == 2

    def test_fully_loaded_node_zero_capacity(self):
        """Node saturated: active == max → 0 available."""
        node = ComputeNode(
            node_id="gpu-0",
            backend="vulkan_gpu",
            max_concurrency=4,
            active_tasks=4,
            state=ComputeNodeState.BUSY,
        )
        assert node.available_capacity() == 0

    def test_capacity_never_negative(self):
        """Active tasks > max_concurrency (overload) → 0, not negative."""
        node = ComputeNode(
            node_id="cpu-0",
            backend="zen5_cpu",
            max_concurrency=4,
            active_tasks=10,
            state=ComputeNodeState.OVERLOADED,
        )
        assert node.available_capacity() == 0


# ── ComputeNode.health_score ──────────────────────────────────────────────────


class TestComputeNodeHealth:
    def test_offline_node_zero_health(self):
        """Offline node → 0.0 health score."""
        node = ComputeNode(
            node_id="npu-0",
            backend="xdna2_npu",
            state=ComputeNodeState.OFFLINE,
        )
        assert node.health_score() == 0.0

    def test_idle_cool_node_high_health(self):
        """Idle node at normal temperature → high health score."""
        node = ComputeNode(
            node_id="npu-0",
            backend="xdna2_npu",
            state=ComputeNodeState.IDLE,
            active_tasks=0,
            max_concurrency=4,
            temperature_c=45.0,
        )
        score = node.health_score()
        assert score > 0.7, f"Idle cool node should have high health: {score}"

    def test_critical_temperature_low_health(self):
        """Temperature > 85°C → temp_score=0, reducing overall health."""
        node = ComputeNode(
            node_id="gpu-0",
            backend="vulkan_gpu",
            state=ComputeNodeState.IDLE,
            active_tasks=0,
            max_concurrency=4,
            temperature_c=90.0,  # critical
        )
        score = node.health_score()
        # temp_score=0 → health = load_score * 0.5 + 0 + state_score * 0.2
        assert score < 0.75, f"Critical temp should reduce health: {score}"

    def test_throttled_state_low_health(self):
        """Throttled state → state_score=0.3, reducing health."""
        node = ComputeNode(
            node_id="npu-0",
            backend="xdna2_npu",
            state=ComputeNodeState.THROTTLED,
            active_tasks=0,
            max_concurrency=4,
            temperature_c=50.0,
        )
        idle_node = ComputeNode(
            node_id="npu-1",
            backend="xdna2_npu",
            state=ComputeNodeState.IDLE,
            active_tasks=0,
            max_concurrency=4,
            temperature_c=50.0,
        )
        assert node.health_score() < idle_node.health_score()

    def test_health_score_bounded_0_to_1(self):
        """Health score must always be in [0, 1]."""
        scenarios = [
            ComputeNode("n", "x", state=ComputeNodeState.IDLE, temperature_c=0.0),
            ComputeNode(
                "n",
                "x",
                state=ComputeNodeState.BUSY,
                active_tasks=4,
                max_concurrency=4,
                temperature_c=80.0,
            ),
            ComputeNode("n", "x", state=ComputeNodeState.OFFLINE),
        ]
        for node in scenarios:
            s = node.health_score()
            assert 0.0 <= s <= 1.0, f"Health score {s} out of bounds for {node.state}"


# ── Task dataclass ────────────────────────────────────────────────────────────


class TestTask:
    def test_task_defaults(self):
        t = Task(task_id="t1", prompt="hello", task_type="reasoning")
        assert t.priority == TaskPriority.NORMAL
        assert t.status == "pending"
        assert t.assigned_node is None
        assert t.result is None

    def test_task_priority_ordering(self):
        """CRITICAL < HIGH < NORMAL < LOW < BACKGROUND (lower value = higher priority)."""
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.LOW.value
        assert TaskPriority.LOW.value < TaskPriority.BACKGROUND.value

    def test_task_preferred_backend(self):
        """Tasks can specify preferred backend for routing."""
        t = Task(
            task_id="code-task",
            prompt="Write a function",
            task_type="coding",
            preferred_backend="vulkan_gpu",
        )
        assert t.preferred_backend == "vulkan_gpu"

    def test_npu_task_for_classification(self):
        """Short classification tasks should prefer NPU backend."""
        t = Task(
            task_id="clf-1",
            prompt="Classify: POSITIVE or NEGATIVE?",
            task_type="classification",
            priority=TaskPriority.HIGH,
            preferred_backend="xdna2_npu",
            max_latency_ms=500,
        )
        assert t.preferred_backend == "xdna2_npu"
        assert t.max_latency_ms == 500
