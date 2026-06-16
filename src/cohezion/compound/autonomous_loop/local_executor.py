"""LocalImprovementExecutor — NPU/iGPU-backed task executor for the autonomous loop."""

from __future__ import annotations

from typing import Any


class LoopTickSweeper:
    """Periodically corrects the loop's course based on sprint statistics."""

    def course_correct(
        self, sprint_results: list[Any], category_stats: dict[str, Any]
    ) -> list[str]:
        return []


class LocalImprovementExecutor:
    """Local silicon executor: routes tasks through the Lemonade OmniRouter."""

    def __init__(self, base_url: str = "http://localhost:13305") -> None:
        self._base_url = base_url
        self._started = False
        self._sweeper = LoopTickSweeper()

    def start(self, worktree_path: str) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def execute_task(self, task: Any, worktree_path: str) -> dict[str, Any]:
        return {
            "success": False,
            "summary": "no local inference available",
            "tokens_used": 0,
            "output": "",
            "returncode": 1,
        }
