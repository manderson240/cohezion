"""Tests for ImprovementExecutor in the compound autonomous loop."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

from cohezion.compound.autonomous_loop.executor import ImprovementExecutor


@dataclass
class _DummyTask:
    id: str = "task-001"
    description: str = "Refactor trace parser"
    verification: str = ""


class TestImprovementExecutor:
    def test_lifecycle(self) -> None:
        executor = ImprovementExecutor()
        assert not executor._started
        executor.start("/tmp/test-wt")
        assert executor._started
        assert executor._worktree_path == "/tmp/test-wt"
        executor.stop()
        assert not executor._started

    def test_execute_task_no_provider(self) -> None:
        executor = ImprovementExecutor()
        task = _DummyTask()
        res = executor.execute_task(task, "/tmp/test-wt")
        assert not res["success"]
        assert res["summary"] == "no inference provider configured"
        assert res["returncode"] == 1
        assert res["task_id"] == "task-001"
        assert res["state_transitions"] == ["start"]

    def test_execute_task_success_with_router(self, tmp_path) -> None:
        mock_router = MagicMock()
        mock_route_res = MagicMock()
        mock_route_res.content = "```python\ndef solve() -> int:\n    return 42\n```"
        mock_route_res.tokens_used = 120
        mock_router.route_query.return_value = mock_route_res

        executor = ImprovementExecutor(router=mock_router)
        task = _DummyTask(verification="python3 -c 'exit(0)'")

        res = executor.execute_task(task, str(tmp_path))
        assert res["success"]
        assert res["summary"] == "ok"
        assert res["returncode"] == 0
        assert res["tokens_used"] == 120
        assert res["state_transitions"] == [
            "start",
            "plan",
            "code",
            "verify",
            "commit",
            "done",
        ]

    def test_execute_task_autoharness_violation(self, tmp_path) -> None:
        mock_router = MagicMock()
        mock_route_res = MagicMock()
        # Illegal eval call triggers AutoHarness rule
        mock_route_res.content = "```python\ndef solve():\n    return eval('2 + 2')\n```"
        mock_route_res.tokens_used = 80
        mock_router.route_query.return_value = mock_route_res

        executor = ImprovementExecutor(router=mock_router)
        task = _DummyTask(verification="python3 -c 'exit(0)'")

        res = executor.execute_task(task, str(tmp_path))
        assert not res["success"]
        assert "AutoHarness verification failed" in res["summary"]
        assert res["returncode"] == 1
        assert res["state_transitions"] == [
            "start",
            "plan",
            "code",
            "verify",
            "abort",
            "done",
        ]

    def test_execute_task_verification_failure(self, tmp_path) -> None:
        mock_router = MagicMock()
        mock_route_res = MagicMock()
        mock_route_res.content = "```python\ndef solve() -> int:\n    return 42\n```"
        mock_route_res.tokens_used = 90
        mock_router.route_query.return_value = mock_route_res

        executor = ImprovementExecutor(router=mock_router)
        task = _DummyTask(verification="python3 -c 'exit(1)'")

        res = executor.execute_task(task, str(tmp_path))
        assert not res["success"]
        assert "verification failed" in res["summary"]
        assert res["returncode"] == 1
        assert res["state_transitions"] == [
            "start",
            "plan",
            "code",
            "verify",
            "abort",
            "done",
        ]
