"""V-model structural boundary test: local_executor → coordinator boundary.

Verifies that per-tier routing fields (node, elapsed_ms, fallback) survive
_record_result() intact. These fields were added in the 'local inference mastery'
sprint and must round-trip from execute_task() output through the RunReport.results
list. This is a V-model integration boundary test — not a unit test of either
component in isolation, but of the contract crossing the boundary.

All inference topology references use :13305 only (single OmniRouter — no per-tier
ports). See harness.md N3 and local-inference-default.md.
"""

from __future__ import annotations

from cohezion.compound.autonomous_loop.coordinator import (
    LoopConfig,
    LoopCoordinator,
    LoopTask,
    RunReport,
    SprintResult,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_task(task_id: str = "t-001", category: str = "test") -> LoopTask:
    return LoopTask(
        id=task_id,
        description="Boundary test task",
        category=category,
        priority=5,
        verification="Check boundary",
        estimated_tokens=100,
    )


def _make_config() -> LoopConfig:
    return LoopConfig(use_local_inference=False)


def _call_record_result(
    coordinator: LoopCoordinator,
    result: dict,
    task: LoopTask,
    is_cloud: bool = False,
) -> RunReport:
    report = RunReport()
    fail_counts: dict[str, int] = {}
    category_stats: dict[str, dict[str, int]] = {}
    sprint = SprintResult()
    coordinator._record_result(
        result,
        task,
        is_cloud,
        result.get("tokens_used", 0),
        report,
        fail_counts,
        category_stats,
        sprint,
    )
    return report


# ── Structural invariant tests ────────────────────────────────────────────────


class TestCoordinatorBoundary:
    """_record_result() passes per-tier fields through to RunReport.results."""

    def test_node_field_survives_boundary(self):
        coord = LoopCoordinator(_make_config())
        task = _make_task()
        result = {
            "task_id": task.id,
            "success": True,
            "tokens_used": 42,
            "node": "npu",
            "model": "llama3.2-1b-FLM",
            "elapsed_ms": 123.0,
            "tried_models": ["llama3.2-1b-FLM"],
        }
        report = _call_record_result(coord, result, task)
        assert len(report.results) == 1
        assert report.results[0]["node"] == "npu"

    def test_elapsed_ms_survives_boundary(self):
        coord = LoopCoordinator(_make_config())
        task = _make_task()
        result = {
            "task_id": task.id,
            "success": True,
            "tokens_used": 10,
            "node": "gpu",
            "model": "Gemma-4-E4B-it-GGUF",
            "elapsed_ms": 387.5,
            "tried_models": ["Gemma-4-E4B-it-GGUF"],
        }
        report = _call_record_result(coord, result, task)
        assert report.results[0]["elapsed_ms"] == 387.5

    def test_fallback_false_when_single_model(self):
        coord = LoopCoordinator(_make_config())
        task = _make_task()
        result = {
            "task_id": task.id,
            "success": True,
            "tokens_used": 20,
            "node": "npu",
            "model": "llama3.2-1b-FLM",
            "elapsed_ms": 50.0,
            "tried_models": ["llama3.2-1b-FLM"],
        }
        report = _call_record_result(coord, result, task)
        assert report.results[0]["fallback"] is False

    def test_fallback_true_when_npu_degraded_to_igpu(self):
        """NPU HTTP 500 → fallback to iGPU sets fallback=True in coordinator record."""
        coord = LoopCoordinator(_make_config())
        task = _make_task()
        result = {
            "task_id": task.id,
            "success": True,
            "tokens_used": 30,
            "node": "npu",
            "model": "Gemma-4-E4B-it-GGUF",  # final model after fallback
            "elapsed_ms": 210.0,
            "tried_models": ["llama3.2-1b-FLM", "Gemma-4-E4B-it-GGUF"],
        }
        report = _call_record_result(coord, result, task)
        assert report.results[0]["fallback"] is True

    def test_missing_tried_models_uses_model_field(self):
        """Legacy result without tried_models key: fallback=False (single model implied)."""
        coord = LoopCoordinator(_make_config())
        task = _make_task()
        result = {
            "task_id": task.id,
            "success": True,
            "tokens_used": 15,
            "node": "gpu",
            "model": "Gemma-4-E4B-it-GGUF",
            "elapsed_ms": 199.0,
            # No tried_models key — legacy executor result
        }
        report = _call_record_result(coord, result, task)
        assert report.results[0]["fallback"] is False

    def test_task_id_survives_boundary(self):
        coord = LoopCoordinator(_make_config())
        task = _make_task(task_id="skill-003-foobar")
        result = {
            "task_id": task.id,
            "success": True,
            "tokens_used": 5,
            "node": "cpu",
            "model": "Gemma-4-E2B-it-GGUF",
            "elapsed_ms": 800.0,
            "tried_models": ["Gemma-4-E2B-it-GGUF"],
        }
        report = _call_record_result(coord, result, task)
        assert report.results[0]["task_id"] == "skill-003-foobar"

    def test_success_true_increments_tasks_completed(self):
        coord = LoopCoordinator(_make_config())
        task = _make_task()
        result = {
            "task_id": task.id,
            "success": True,
            "tokens_used": 10,
            "node": "npu",
            "model": "llama3.2-1b-FLM",
            "elapsed_ms": 40.0,
            "tried_models": ["llama3.2-1b-FLM"],
        }
        report = _call_record_result(coord, result, task)
        assert report.tasks_completed == 1
        assert report.tasks_failed == 0

    def test_success_false_increments_tasks_failed(self):
        coord = LoopCoordinator(_make_config())
        task = _make_task()
        result = {
            "task_id": task.id,
            "success": False,
            "tokens_used": 0,
            "node": "npu",
            "model": "llama3.2-1b-FLM",
            "elapsed_ms": 3000.0,
            "tried_models": ["llama3.2-1b-FLM"],
        }
        report = _call_record_result(coord, result, task)
        assert report.tasks_completed == 0
        assert report.tasks_failed == 1

    def test_cloud_result_sets_node_to_cloud(self):
        coord = LoopCoordinator(_make_config())
        task = _make_task()
        result = {
            "task_id": task.id,
            "success": True,
            "tokens_used": 500,
            # Cloud executor doesn't emit node/elapsed_ms/tried_models
        }
        report = _call_record_result(coord, result, task, is_cloud=True)
        assert report.results[0]["node"] == "cloud"
        assert report.results[0]["is_cloud"] is True
