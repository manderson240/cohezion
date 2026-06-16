"""ImprovementExecutor — cloud-backed task executor for the autonomous loop."""

from __future__ import annotations

from typing import Any


class ImprovementExecutor:
    """Cloud executor: delegates task execution to a remote inference provider."""

    def __init__(self, config: Any = None) -> None:
        self._config = config
        self._started = False

    def start(self, worktree_path: str) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def execute_task(self, task: Any, worktree_path: str) -> dict[str, Any]:
        return {
            "success": False,
            "summary": "no inference provider configured",
            "tokens_used": 0,
            "output": "",
            "returncode": 1,
        }
