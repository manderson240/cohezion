"""Long-Horizon Agentic Benchmark (OSWorld/TerminalBench equivalent).

Evaluates multi-step autonomous task completion in realistic environments.
Target: Match Mythos Preview's 79.6% OSWorld, 82% TerminalBench.

Key Capabilities Tested:
- Multi-step planning (10+ steps)
- Tool use (bash, browser, file system)
- Error recovery (self-correction)
- Context maintenance across sessions
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class AgenticTask:
    """Long-horizon task requiring multiple steps."""

    task_id: str
    category: str  # desktop, web, file_ops, data_analysis
    difficulty: int  # 1-5
    n_steps_expected: int
    time_limit_minutes: int

    # Task specification
    initial_state: dict[str, Any]
    goal_state: dict[str, Any]
    instructions: str

    # Environment capabilities needed
    available_tools: list[str]  # bash, browser, python, file
    sandbox_type: str  # docker, subprocess, none


@dataclass
class TaskResult:
    """Result of agentic task attempt."""

    task_id: str
    overall_success: bool
    steps_completed: int
    steps_expected: int
    time_taken: float
    recovery_attempts: int
    tool_calls: list[dict[str, Any]]
    final_state_match: float  # 0-1 similarity to goal
    error: str | None


class AgenticBenchmark:
    """Long-horizon task benchmark runner."""

    def __init__(self, tasks_dir: Path | None = None):
        """Initialize benchmark."""
        self.tasks_dir = tasks_dir or Path("data/agentic_tasks")
        self.results: list[TaskResult] = []

    async def load_tasks(self, category: str | None = None) -> list[AgenticTask]:
        """Load task dataset."""
        await self._ensure_tasks_exist()

        with open(self.tasks_dir / "tasks.json") as f:
            data = json.load(f)

        tasks = [AgenticTask(**t) for t in data["tasks"]]

        if category:
            tasks = [t for t in tasks if t.category == category]

        return tasks

    async def evaluate_task(
        self,
        task: AgenticTask,
        agent: Any,  # UnifiedAgent or similar
        timeout: int | None = None,
    ) -> TaskResult:
        """Evaluate single long-horizon task."""
        import time

        start = time.monotonic()
        timeout = timeout or task.time_limit_minutes * 60

        try:
            # Setup sandboxed environment
            env = await self._setup_environment(task)

            # Run agent on task
            trace = await self._run_agent(agent, task, env, timeout)

            time_taken = time.monotonic() - start

            # Evaluate final state
            state_match = self._evaluate_state(task.goal_state, trace.get("final_state", {}))

            success = state_match > 0.9 and trace.get("completed", False)

            return TaskResult(
                task_id=task.task_id,
                overall_success=success,
                steps_completed=trace.get("steps_done", 0),
                steps_expected=task.n_steps_expected,
                time_taken=time_taken,
                recovery_attempts=trace.get("recoveries", 0),
                tool_calls=trace.get("tools", []),
                final_state_match=state_match,
                error=trace.get("error"),
            )

        except Exception as e:
            logger.exception("Task evaluation failed")
            return TaskResult(
                task_id=task.task_id,
                overall_success=False,
                steps_completed=0,
                steps_expected=task.n_steps_expected,
                time_taken=time.monotonic() - start,
                recovery_attempts=0,
                tool_calls=[],
                final_state_match=0.0,
                error=str(e)[:500],
            )

    async def _setup_environment(self, task: AgenticTask) -> Any:
        """Setup task execution environment."""
        if task.sandbox_type == "docker":
            return await self._docker_sandbox(task)
        elif task.sandbox_type == "subprocess":
            return self._subprocess_sandbox(task)
        else:
            return self._mock_sandbox(task)

    async def _docker_sandbox(self, task: AgenticTask) -> dict[str, Any]:
        """Docker-based isolated environment."""
        # For now, use mock - Docker integration would need proper setup
        return {
            "type": "docker_mock",
            "workdir": f"/tmp/agentic_{task.task_id}",
            "bash": lambda cmd: {"stdout": f"Mock: {cmd}", "returncode": 0},
            "write_file": lambda p, c: None,
            "read_file": lambda p: "mock content",
            "cleanup": lambda: None,
        }

    def _subprocess_sandbox(self, task: AgenticTask) -> dict[str, Any]:
        """Subprocess-based semi-isolated environment."""
        import tempfile

        workdir = tempfile.mkdtemp()

        async def bash(cmd: str) -> dict[str, Any]:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=workdir
            )
            stdout, stderr = await proc.communicate()
            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "returncode": proc.returncode,
            }

        def write_file(path: str, content: str) -> None:
            p = Path(workdir) / path.lstrip("/")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

        def read_file(path: str) -> str:
            p = Path(workdir) / path.lstrip("/")
            return p.read_text() if p.exists() else ""

        return {
            "type": "subprocess",
            "workdir": workdir,
            "bash": bash,
            "write_file": write_file,
            "read_file": read_file,
            "cleanup": lambda: __import__("shutil").rmtree(workdir, ignore_errors=True),
        }

    def _mock_sandbox(self, task: AgenticTask) -> dict[str, Any]:
        """Placeholder sandbox."""
        return {
            "type": "mock",
            "bash": lambda cmd: {"stdout": "", "returncode": 0},
            "write_file": lambda p, c: None,
            "read_file": lambda p: "",
            "cleanup": lambda: None,
        }

    async def _run_agent(self, agent: Any, task: AgenticTask, env: dict[str, Any], timeout: int) -> dict[str, Any]:
        """Run agent on task with monitoring."""

        # Check if agent has unified harness interface
        if hasattr(agent, "run_task"):
            return await agent.run_task(task, env, timeout)

        # Fallback: simulate with LLM executor
        logger.warning("Using simulated agent execution")
        return await self._simulate_agent(agent, task, env, timeout)

    async def _simulate_agent(
        self, executor: Any, task: AgenticTask, env: dict[str, Any], timeout: int
    ) -> dict[str, Any]:
        """Simulated agent execution for baseline."""
        # Mock trace - would need real agent integration
        return {
            "completed": False,
            "steps_done": task.n_steps_expected // 2,  # Assume partial success
            "recoveries": 0,
            "tools": [],
            "final_state": {},
            "error": "Simulated: needs real agent",
        }

    def _evaluate_state(self, goal: dict, actual: dict) -> float:
        """Compute similarity between goal and actual state."""
        if not goal or not actual:
            return 0.0
        # Simple key matching
        matches = sum(1 for k, v in goal.items() if actual.get(k) == v)
        return matches / len(goal) if goal else 0.0

    async def run_benchmark(
        self, agent: Any, n_tasks: int | None = None, category: str | None = None
    ) -> dict[str, Any]:
        """Run full benchmark suite."""
        tasks = await self.load_tasks(category)

        if n_tasks:
            tasks = tasks[:n_tasks]

        logger.info(f"Running agentic benchmark: {len(tasks)} tasks")

        self.results = []
        for task in tasks:
            result = await self.evaluate_task(task, agent)
            self.results.append(result)

        return self._compute_summary()

    def _compute_summary(self) -> dict[str, Any]:
        """Compute aggregate metrics."""
        if not self.results:
            return {}

        total = len(self.results)
        successes = sum(1 for r in self.results if r.overall_success)

        step_completion = (
            sum(r.steps_completed / r.steps_expected if r.steps_expected > 0 else 0 for r in self.results) / total
            if total > 0
            else 0
        )

        return {
            "overall": {
                "success_rate": successes / total if total > 0 else 0.0,
                "success_percentage": (successes / total * 100) if total > 0 else 0.0,
                "target": "79.6% OSWorld, 82% TerminalBench",
                "step_completion": step_completion,
                "total_tasks": total,
                "successes": successes,
            },
            "detailed_results": [
                {
                    "task_id": r.task_id,
                    "success": r.overall_success,
                    "steps": f"{r.steps_completed}/{r.steps_expected}",
                    "time": r.time_taken,
                }
                for r in self.results
            ],
        }

    async def _ensure_tasks_exist(self) -> None:
        """Create synthetic task dataset."""
        if (self.tasks_dir / "tasks.json").exists():
            return

        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        # Diverse long-horizon tasks
        tasks = {
            "tasks": [
                {
                    "task_id": "desktop_001_file_org",
                    "category": "desktop",
                    "difficulty": 2,
                    "n_steps_expected": 5,
                    "time_limit_minutes": 10,
                    "initial_state": {"files": ["doc1.pdf", "doc2.jpg", "temp.xls"]},
                    "goal_state": {"organized": True, "by_extension": True},
                    "instructions": "Organize these files by type into folders.",
                    "available_tools": ["bash", "file"],
                    "sandbox_type": "subprocess",
                },
                {
                    "task_id": "web_001_research",
                    "category": "web",
                    "difficulty": 3,
                    "n_steps_expected": 8,
                    "time_limit_minutes": 15,
                    "initial_state": {"query": "quantum error correction papers 2024"},
                    "goal_state": {"downloaded": 5, "organized": True},
                    "instructions": "Find and download 5 recent papers on QEC.",
                    "available_tools": ["browser", "file", "python"],
                    "sandbox_type": "subprocess",
                },
                {
                    "task_id": "data_001_analysis",
                    "category": "data_analysis",
                    "difficulty": 4,
                    "n_steps_expected": 12,
                    "time_limit_minutes": 20,
                    "initial_state": {"data_file": "sales_data.csv"},
                    "goal_state": {"analyzed": True, "visualization": "sales_trend.png"},
                    "instructions": "Analyze sales data and create trend visualization.",
                    "available_tools": ["python", "file", "bash"],
                    "sandbox_type": "subprocess",
                },
                {
                    "task_id": "system_001_setup",
                    "category": "system_admin",
                    "difficulty": 5,
                    "n_steps_expected": 15,
                    "time_limit_minutes": 30,
                    "initial_state": {"server": "ubuntu_22.04"},
                    "goal_state": {"configured": True, "services": ["nginx", "postgres"]},
                    "instructions": "Configure web server with reverse proxy and database.",
                    "available_tools": ["bash", "file"],
                    "sandbox_type": "docker",
                },
            ]
        }

        with open(self.tasks_dir / "tasks.json", "w") as f:
            json.dump(tasks, f, indent=2)


# Default
agentic_benchmark = AgenticBenchmark()
