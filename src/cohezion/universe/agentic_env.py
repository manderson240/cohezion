"""Agentic Task Environment for LLM Agent Evaluation.

Provides structured environments where LLM agents execute multi-step tasks
within sandboxed contexts. Unlike traditional RL environments (fixed action
spaces), agentic environments accept natural language actions and tool calls.

This bridges the gap between Cohezion's 12D universe simulation and
practical LLM agent evaluation — the core workflow for Anthropic's
Universes team.

Architecture:
    AgenticEnvironment
        ├── Maintains task state (files, shell, variables)
        ├── Accepts text actions and tool calls
        ├── Returns observations, rewards, and task completion status
        └── Integrates with ContainerizedUniverse for sandbox execution

    ToolRegistry
        ├── Registers available tools (bash, file_read, file_write, etc.)
        ├── Validates tool calls
        └── Executes tools within sandbox

    TaskScenario
        ├── Defines initial state (files, instructions)
        ├── Defines success criteria (file exists, test passes, output matches)
        └── Defines resource limits

    TrajectoryRecorder
        ├── Records full (observation, action, reward) sequences
        ├── Exports to LLM training formats (DPO, reward model)
        └── Integrates with llm_training_bridge.py

References:
    - SWE-bench: real-world coding task evaluation
    - Anthropic tool use: structured tool calling protocol
    - Smith's HIHO: agent coherence tracked through task execution
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool system
# ---------------------------------------------------------------------------


class ToolResult(StrEnum):
    """Outcome of a tool execution."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    DENIED = "denied"


@dataclass
class ToolCall:
    """A structured tool call from an agent."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: str = field(default_factory=lambda: uuid4().hex[:8])


@dataclass
class ToolResponse:
    """Response from a tool execution."""

    call_id: str
    tool_name: str
    result: ToolResult
    output: str
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolSpec:
    """Specification for an available tool.

    Parameters
    ----------
    name : str
        Tool name (e.g., "bash", "file_read").
    description : str
        Human-readable description for the agent.
    parameters : dict
        JSON Schema-like parameter specification.
    handler : callable
        Function that executes the tool. Signature: (args, env_state) -> str
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Any,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_schema(self) -> dict[str, Any]:
        """Convert to tool schema for agent prompt."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Registry of available tools for an agentic environment.

    Tools are executed within the environment's sandbox. The registry
    validates tool calls before execution and tracks usage.
    """

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}
        self._call_history: list[tuple[ToolCall, ToolResponse]] = []

    def register(self, tool: ToolSpec) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> ToolSpec | None:
        """Get tool by name."""
        return self._tools.get(name)

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        """Get schemas for all available tools."""
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, call: ToolCall, env_state: dict[str, Any]) -> ToolResponse:
        """Execute a tool call.

        Parameters
        ----------
        call : ToolCall
            The tool call to execute.
        env_state : dict
            Current environment state (filesystem, variables, etc.).

        Returns
        -------
        ToolResponse
            Execution result.
        """
        tool = self._tools.get(call.tool_name)
        if tool is None:
            response = ToolResponse(
                call_id=call.call_id,
                tool_name=call.tool_name,
                result=ToolResult.ERROR,
                output=f"Unknown tool: {call.tool_name}. Available: {list(self._tools.keys())}",
            )
            self._call_history.append((call, response))
            return response

        start = time.time()
        try:
            output = tool.handler(call.arguments, env_state)
            response = ToolResponse(
                call_id=call.call_id,
                tool_name=call.tool_name,
                result=ToolResult.SUCCESS,
                output=str(output),
                duration_seconds=time.time() - start,
            )
        except TimeoutError:
            response = ToolResponse(
                call_id=call.call_id,
                tool_name=call.tool_name,
                result=ToolResult.TIMEOUT,
                output="Tool execution timed out",
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            response = ToolResponse(
                call_id=call.call_id,
                tool_name=call.tool_name,
                result=ToolResult.ERROR,
                output=f"Error: {e}",
                duration_seconds=time.time() - start,
            )

        self._call_history.append((call, response))
        return response

    @property
    def call_count(self) -> int:
        return len(self._call_history)


# ---------------------------------------------------------------------------
# Task scenarios
# ---------------------------------------------------------------------------


class SuccessCriterionType(StrEnum):
    """Types of success criteria for task completion."""

    FILE_EXISTS = "file_exists"
    FILE_CONTAINS = "file_contains"
    OUTPUT_MATCHES = "output_matches"
    TEST_PASSES = "test_passes"
    CUSTOM = "custom"


@dataclass
class SuccessCriterion:
    """A single success criterion for task evaluation."""

    criterion_type: SuccessCriterionType
    target: str  # File path, regex pattern, test command, etc.
    weight: float = 1.0
    description: str = ""


@dataclass
class TaskScenario:
    """Defines an agentic task scenario.

    Parameters
    ----------
    scenario_id : str
        Unique identifier.
    name : str
        Human-readable name.
    instructions : str
        Task instructions given to the agent.
    initial_files : dict[str, str]
        Files to populate in the sandbox at start.
    success_criteria : list[SuccessCriterion]
        How to determine task completion.
    max_steps : int
        Maximum number of agent actions.
    max_time_seconds : int
        Maximum wall-clock time.
    allowed_tools : list[str] | None
        Tool whitelist (None = all tools).
    difficulty : str
        Difficulty level.
    tags : list[str]
        Searchable tags.
    """

    scenario_id: str
    name: str
    instructions: str
    initial_files: dict[str, str] = field(default_factory=dict)
    success_criteria: list[SuccessCriterion] = field(default_factory=list)
    max_steps: int = 50
    max_time_seconds: int = 600
    allowed_tools: list[str] | None = None
    difficulty: str = "medium"
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Environment state
# ---------------------------------------------------------------------------


@dataclass
class EnvObservation:
    """Observation returned to the agent after each step."""

    step_number: int
    tool_response: ToolResponse | None
    system_message: str
    available_tools: list[dict[str, Any]]
    files_changed: list[str]
    remaining_steps: int
    elapsed_seconds: float
    coherence: float  # HIHO coherence tracking


@dataclass
class StepRecord:
    """Record of a single environment step."""

    step_number: int
    action: ToolCall | str  # Tool call or free-text action
    observation: EnvObservation
    reward: float
    cumulative_reward: float
    timestamp: float


# ---------------------------------------------------------------------------
# Agentic environment
# ---------------------------------------------------------------------------


class AgenticEnvironment:
    """Environment for evaluating LLM agents on multi-step tasks.

    Maintains a virtual filesystem, tool registry, and task state.
    Agents interact via tool calls and receive observations including
    tool results, file changes, and coherence tracking.

    Parameters
    ----------
    scenario : TaskScenario
        The task scenario to run.
    tool_registry : ToolRegistry | None
        Available tools. If None, default tools are registered.
    """

    def __init__(
        self,
        scenario: TaskScenario,
        tool_registry: ToolRegistry | None = None,
    ):
        self.scenario = scenario
        self.tools = tool_registry or self._default_tools()

        # Environment state
        self._files: dict[str, str] = dict(scenario.initial_files)
        self._variables: dict[str, Any] = {}
        self._stdout_buffer: list[str] = []
        self._step_count = 0
        self._start_time = 0.0
        self._cumulative_reward = 0.0
        self._history: list[StepRecord] = []
        self._done = False
        self._success = False

        # HIHO coherence tracking
        self._coherence = 0.5  # Start at HIHO equilibrium

    def reset(self) -> EnvObservation:
        """Reset the environment to initial state.

        Returns
        -------
        EnvObservation
            Initial observation for the agent.
        """
        self._files = dict(self.scenario.initial_files)
        self._variables = {}
        self._stdout_buffer = []
        self._step_count = 0
        self._start_time = time.time()
        self._cumulative_reward = 0.0
        self._history = []
        self._done = False
        self._success = False
        self._coherence = 0.5

        return EnvObservation(
            step_number=0,
            tool_response=None,
            system_message=self._format_initial_prompt(),
            available_tools=self.tools.available_tools,
            files_changed=list(self._files.keys()),
            remaining_steps=self.scenario.max_steps,
            elapsed_seconds=0.0,
            coherence=self._coherence,
        )

    def step(self, action: ToolCall | str) -> tuple[EnvObservation, float, bool, dict[str, Any]]:
        """Execute an agent action in the environment.

        Parameters
        ----------
        action : ToolCall | str
            A tool call or free-text action.

        Returns
        -------
        tuple
            (observation, reward, done, info)
        """
        self._step_count += 1
        elapsed = time.time() - self._start_time
        files_before = set(self._files.keys())

        # Execute action
        tool_response = None
        if isinstance(action, ToolCall):
            env_state = {
                "files": self._files,
                "variables": self._variables,
                "stdout": self._stdout_buffer,
            }
            tool_response = self.tools.execute(action, env_state)
        elif isinstance(action, str):
            # Free-text action — interpret as a message
            self._stdout_buffer.append(action)

        # Detect file changes
        files_after = set(self._files.keys())
        files_changed = list(files_after - files_before)

        # Check termination conditions
        done = False
        info: dict[str, Any] = {}

        if self._step_count >= self.scenario.max_steps:
            done = True
            info["terminal_reason"] = "max_steps"

        if elapsed >= self.scenario.max_time_seconds:
            done = True
            info["terminal_reason"] = "timeout"

        # Check success criteria
        success_score = self._evaluate_success()
        if success_score >= 0.8:
            done = True
            self._success = True
            info["terminal_reason"] = "success"

        self._done = done

        # Compute reward
        reward = self._compute_reward(tool_response, success_score)
        self._cumulative_reward += reward

        # Update coherence
        self._update_coherence(tool_response)

        # Build observation
        observation = EnvObservation(
            step_number=self._step_count,
            tool_response=tool_response,
            system_message="" if not done else self._format_terminal_message(),
            available_tools=self.tools.available_tools,
            files_changed=files_changed,
            remaining_steps=self.scenario.max_steps - self._step_count,
            elapsed_seconds=elapsed,
            coherence=self._coherence,
        )

        # Record step
        record = StepRecord(
            step_number=self._step_count,
            action=action,
            observation=observation,
            reward=reward,
            cumulative_reward=self._cumulative_reward,
            timestamp=time.time(),
        )
        self._history.append(record)

        info["success_score"] = success_score
        info["coherence"] = self._coherence
        info["cumulative_reward"] = self._cumulative_reward
        info["tool_calls"] = self.tools.call_count

        return observation, reward, done, info

    def _compute_reward(self, tool_response: ToolResponse | None, success_score: float) -> float:
        """Compute step reward.

        Reward components:
        1. Tool success: +0.1 for successful tool call
        2. Progress: success_score improvement
        3. Coherence: bonus for staying near HIHO
        4. Efficiency: small penalty per step (encourages brevity)
        """
        reward = 0.0

        # Tool success
        if tool_response and tool_response.result == ToolResult.SUCCESS:
            reward += 0.1
        elif tool_response and tool_response.result == ToolResult.ERROR:
            reward -= 0.05

        # Progress toward success
        reward += success_score * 0.5

        # HIHO coherence bonus
        coherence_bonus = 1.0 - abs(self._coherence - 0.5) * 2
        reward += coherence_bonus * 0.1

        # Step cost (encourages efficiency)
        reward -= 0.02

        # Completion bonus
        if self._success:
            reward += 2.0

        return reward

    def _update_coherence(self, tool_response: ToolResponse | None) -> None:
        """Update HIHO coherence based on action outcomes."""
        if tool_response is None:
            # No tool call — slight drift toward center
            self._coherence += (0.5 - self._coherence) * 0.05
        elif tool_response.result == ToolResult.SUCCESS:
            # Success moves toward HIHO stability
            self._coherence += (0.5 - self._coherence) * 0.1
        elif tool_response.result == ToolResult.ERROR:
            # Errors destabilize coherence
            self._coherence *= 0.95
        self._coherence = max(0.0, min(1.0, self._coherence))

    def _evaluate_success(self) -> float:
        """Evaluate how well success criteria are met.

        Returns
        -------
        float
            Score 0.0-1.0 indicating criterion satisfaction.
        """
        if not self.scenario.success_criteria:
            return 0.0

        total_weight = sum(c.weight for c in self.scenario.success_criteria)
        if total_weight == 0:
            return 0.0

        weighted_score = 0.0
        for criterion in self.scenario.success_criteria:
            score = self._check_criterion(criterion)
            weighted_score += score * criterion.weight

        return weighted_score / total_weight

    def _check_criterion(self, criterion: SuccessCriterion) -> float:
        """Check a single success criterion."""
        if criterion.criterion_type == SuccessCriterionType.FILE_EXISTS:
            return 1.0 if criterion.target in self._files else 0.0

        elif criterion.criterion_type == SuccessCriterionType.FILE_CONTAINS:
            # target format: "filename:expected_content"
            parts = criterion.target.split(":", 1)
            if len(parts) != 2:
                return 0.0
            filename, expected = parts
            content = self._files.get(filename, "")
            return 1.0 if expected in content else 0.0

        elif criterion.criterion_type == SuccessCriterionType.OUTPUT_MATCHES:
            stdout = "\n".join(self._stdout_buffer)
            return 1.0 if criterion.target in stdout else 0.0

        elif criterion.criterion_type == SuccessCriterionType.TEST_PASSES:
            # Would run in sandbox; here we check if test file exists
            return 1.0 if criterion.target in self._files else 0.0

        return 0.0

    def _format_initial_prompt(self) -> str:
        """Format the initial system message for the agent."""
        lines = [
            f"Task: {self.scenario.name}",
            f"Instructions: {self.scenario.instructions}",
            f"Max steps: {self.scenario.max_steps}",
            f"Max time: {self.scenario.max_time_seconds}s",
            "",
        ]

        if self._files:
            lines.append("Initial files:")
            for name in self._files:
                lines.append(f"  - {name}")

        if self.tools.available_tools:
            lines.append(f"\nAvailable tools: {[t['name'] for t in self.tools.available_tools]}")

        return "\n".join(lines)

    def _format_terminal_message(self) -> str:
        """Format terminal state message."""
        if self._success:
            return "Task completed successfully."
        return f"Task ended (steps={self._step_count}, success={self._success})."

    def _default_tools(self) -> ToolRegistry:
        """Register default tools."""
        registry = ToolRegistry()

        registry.register(
            ToolSpec(
                name="file_read",
                description="Read the contents of a file.",
                parameters={"path": {"type": "string", "description": "File path to read"}},
                handler=self._tool_file_read,
            )
        )

        registry.register(
            ToolSpec(
                name="file_write",
                description="Write content to a file (creates or overwrites).",
                parameters={
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                handler=self._tool_file_write,
            )
        )

        registry.register(
            ToolSpec(
                name="file_list",
                description="List all files in the environment.",
                parameters={},
                handler=self._tool_file_list,
            )
        )

        registry.register(
            ToolSpec(
                name="bash",
                description="Execute a bash command (simulated).",
                parameters={"command": {"type": "string", "description": "Command to execute"}},
                handler=self._tool_bash,
            )
        )

        return registry

    def _tool_file_read(self, args: dict[str, Any], env_state: dict[str, Any]) -> str:
        """Read a file from the virtual filesystem."""
        path = args.get("path", "")
        files = env_state.get("files", {})
        if path in files:
            return str(files[path])
        raise FileNotFoundError(f"File not found: {path}")

    def _tool_file_write(self, args: dict[str, Any], env_state: dict[str, Any]) -> str:
        """Write to a file in the virtual filesystem."""
        path = args.get("path", "")
        content = args.get("content", "")
        self._files[path] = content
        env_state["files"][path] = content
        return f"Wrote {len(content)} bytes to {path}"

    def _tool_file_list(self, args: dict[str, Any], env_state: dict[str, Any]) -> str:
        """List files in the virtual filesystem."""
        files = env_state.get("files", {})
        return "\n".join(files.keys()) if files else "(empty)"

    def _tool_bash(self, args: dict[str, Any], env_state: dict[str, Any]) -> str:
        """Simulated bash execution (safe, no real shell)."""
        command = args.get("command", "")
        # Simple simulation for common commands
        if command.startswith("echo "):
            output: str = command[5:]
            env_state.get("stdout", []).append(output)
            return output
        elif command == "ls":
            return self._tool_file_list(args, env_state)
        elif command.startswith("cat "):
            return self._tool_file_read({"path": command[4:].strip()}, env_state)
        else:
            return f"(simulated) Command executed: {command}"

    @property
    def trajectory(self) -> list[StepRecord]:
        """Get the full action/observation trajectory."""
        return list(self._history)

    def export_trajectory(self) -> dict[str, Any]:
        """Export trajectory in a format compatible with llm_training_bridge."""
        return {
            "scenario_id": self.scenario.scenario_id,
            "scenario_name": self.scenario.name,
            "success": self._success,
            "total_steps": self._step_count,
            "cumulative_reward": self._cumulative_reward,
            "final_coherence": self._coherence,
            "steps": [
                {
                    "step": r.step_number,
                    "action": (
                        {"tool": r.action.tool_name, "args": r.action.arguments}
                        if isinstance(r.action, ToolCall)
                        else {"text": str(r.action)}
                    ),
                    "reward": r.reward,
                    "coherence": r.observation.coherence,
                }
                for r in self._history
            ],
        }


# ---------------------------------------------------------------------------
# Trajectory recorder for training signal extraction
# ---------------------------------------------------------------------------


class TrajectoryRecorder:
    """Records and exports agent trajectories for LLM training.

    Collects full interaction histories from AgenticEnvironment runs
    and converts them into training data formats compatible with
    llm_training_bridge.py.

    Parameters
    ----------
    output_dir : str | Path
        Directory for exported data.
    """

    def __init__(self, output_dir: str | Path = "data/agentic_trajectories"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._trajectories: list[dict[str, Any]] = []

    def record(self, env: AgenticEnvironment) -> None:
        """Record a completed environment trajectory."""
        trajectory = env.export_trajectory()
        self._trajectories.append(trajectory)

    def export_jsonl(self, filename: str = "trajectories.jsonl") -> Path:
        """Export all trajectories as JSONL."""
        path = self.output_dir / filename
        with open(path, "w") as f:
            for traj in self._trajectories:
                f.write(json.dumps(traj) + "\n")
        logger.info("Exported %d trajectories to %s", len(self._trajectories), path)
        return path

    def export_preference_pairs(self, filename: str = "agentic_preferences.jsonl") -> Path:
        """Export DPO preference pairs from trajectories.

        Pairs successful trajectories (chosen) with failed ones (rejected)
        for the same scenario.
        """
        path = self.output_dir / filename
        pairs_written = 0

        # Group by scenario
        by_scenario: dict[str, list[dict[str, Any]]] = {}
        for traj in self._trajectories:
            sid = traj["scenario_id"]
            by_scenario.setdefault(sid, []).append(traj)

        with open(path, "w") as f:
            for scenario_id, trajs in by_scenario.items():
                successful = [t for t in trajs if t["success"]]
                failed = [t for t in trajs if not t["success"]]

                for chosen in successful:
                    for rejected in failed:
                        pair = {
                            "scenario_id": scenario_id,
                            "prompt": chosen["scenario_name"],
                            "chosen": json.dumps(chosen["steps"]),
                            "rejected": json.dumps(rejected["steps"]),
                            "chosen_reward": chosen["cumulative_reward"],
                            "rejected_reward": rejected["cumulative_reward"],
                        }
                        f.write(json.dumps(pair) + "\n")
                        pairs_written += 1

        logger.info("Exported %d preference pairs to %s", pairs_written, path)
        return path

    @property
    def trajectory_count(self) -> int:
        return len(self._trajectories)

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate trajectory statistics."""
        if not self._trajectories:
            return {"count": 0}

        successes = sum(1 for t in self._trajectories if t["success"])
        rewards = [t["cumulative_reward"] for t in self._trajectories]
        steps = [t["total_steps"] for t in self._trajectories]

        return {
            "count": len(self._trajectories),
            "success_rate": successes / len(self._trajectories),
            "avg_reward": float(sum(rewards) / len(rewards)),
            "avg_steps": float(sum(steps) / len(steps)),
            "avg_coherence": float(
                sum(t["final_coherence"] for t in self._trajectories) / len(self._trajectories)
            ),
        }


# ---------------------------------------------------------------------------
# Built-in task scenarios
# ---------------------------------------------------------------------------


def build_coding_scenarios() -> list[TaskScenario]:
    """Build a set of coding task scenarios for agent evaluation."""
    return [
        TaskScenario(
            scenario_id="coding_001",
            name="Fix the Bug",
            instructions=(
                "The file `app.py` has a bug in the `calculate_average` function. "
                "It crashes on empty lists. Fix the bug so it returns 0.0 for empty lists."
            ),
            initial_files={
                "app.py": (
                    "def calculate_average(numbers):\n    return sum(numbers) / len(numbers)\n"
                ),
                "test_app.py": (
                    "from app import calculate_average\n\n"
                    "def test_normal():\n"
                    "    assert calculate_average([1, 2, 3]) == 2.0\n\n"
                    "def test_empty():\n"
                    "    assert calculate_average([]) == 0.0\n"
                ),
            },
            success_criteria=[
                SuccessCriterion(
                    SuccessCriterionType.FILE_CONTAINS,
                    "app.py:len(numbers) == 0",
                    description="Handles empty list case",
                ),
                SuccessCriterion(
                    SuccessCriterionType.FILE_CONTAINS,
                    "app.py:return 0",
                    description="Returns 0 for empty list",
                ),
            ],
            max_steps=10,
            difficulty="easy",
            tags=["python", "debugging"],
        ),
        TaskScenario(
            scenario_id="coding_002",
            name="Implement Feature",
            instructions=(
                "Add a `to_json` method to the `User` class in `models.py`. "
                "It should return a JSON string with keys 'name', 'email', and 'age'."
            ),
            initial_files={
                "models.py": (
                    "class User:\n"
                    "    def __init__(self, name: str, email: str, age: int):\n"
                    "        self.name = name\n"
                    "        self.email = email\n"
                    "        self.age = age\n"
                ),
            },
            success_criteria=[
                SuccessCriterion(
                    SuccessCriterionType.FILE_CONTAINS,
                    "models.py:def to_json",
                    description="Has to_json method",
                ),
                SuccessCriterion(
                    SuccessCriterionType.FILE_CONTAINS,
                    "models.py:json",
                    description="Uses json module",
                ),
            ],
            max_steps=15,
            difficulty="easy",
            tags=["python", "feature"],
        ),
        TaskScenario(
            scenario_id="coding_003",
            name="Write Tests",
            instructions=(
                "The file `utils.py` contains a `fibonacci` function. "
                "Write a comprehensive test file `test_utils.py` with at least 5 test cases "
                "covering edge cases (0, 1, negative, large numbers)."
            ),
            initial_files={
                "utils.py": (
                    "def fibonacci(n: int) -> int:\n"
                    "    if n < 0:\n"
                    "        raise ValueError('n must be non-negative')\n"
                    "    if n <= 1:\n"
                    "        return n\n"
                    "    a, b = 0, 1\n"
                    "    for _ in range(2, n + 1):\n"
                    "        a, b = b, a + b\n"
                    "    return b\n"
                ),
            },
            success_criteria=[
                SuccessCriterion(
                    SuccessCriterionType.FILE_EXISTS,
                    "test_utils.py",
                    description="Test file created",
                ),
                SuccessCriterion(
                    SuccessCriterionType.FILE_CONTAINS,
                    "test_utils.py:def test_",
                    description="Has test functions",
                ),
            ],
            max_steps=20,
            difficulty="medium",
            tags=["python", "testing"],
        ),
        TaskScenario(
            scenario_id="coding_004",
            name="Refactor for Performance",
            instructions=(
                "The `search` function in `search.py` is O(n^2). "
                "Refactor it to O(n) using a hash set approach. "
                "The function finds pairs in a list that sum to a target."
            ),
            initial_files={
                "search.py": (
                    "def find_pairs(numbers: list[int], target: int) -> list[tuple[int, int]]:\n"
                    "    pairs = []\n"
                    "    for i in range(len(numbers)):\n"
                    "        for j in range(i + 1, len(numbers)):\n"
                    "            if numbers[i] + numbers[j] == target:\n"
                    "                pairs.append((numbers[i], numbers[j]))\n"
                    "    return pairs\n"
                ),
            },
            success_criteria=[
                SuccessCriterion(
                    SuccessCriterionType.FILE_CONTAINS,
                    "search.py:set()",
                    description="Uses set for O(n) lookup",
                ),
            ],
            max_steps=15,
            difficulty="medium",
            tags=["python", "optimization", "algorithms"],
        ),
    ]
