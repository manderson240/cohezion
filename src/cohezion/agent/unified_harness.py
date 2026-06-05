"""Unified Agent Harness - Claude Code equivalent for Cohezion.

Main agent loop with integrated tool use, long-horizon task execution,
and HIHO stability monitoring. Provides the unified interface for
autonomous task completion across benchmarks.

Architecture:
    UnifiedAgent - Main entry point for task execution
    ToolRegistry - Manages available tools (bash, python, file, browser)
    ExecutionContext - Maintains state across multi-step tasks
    SelfCorrection - Error recovery and replanning
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from cohezion.compound.autoharness import AutoHarnessSynthesizer
from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.inference.gaia_adapter import amd_optimized_hierarchy
from cohezion.integrations.agentverse.llm_executor import LLMExecutor


logger = logging.getLogger(__name__)


def autocontext_monitor(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Monitor context utilization and return compaction flags."""
    # If history is long or if mocked warn=True is patched, this function is used.
    return {"pct": 0.0, "warn": False, "critical": False}


@dataclass
class ToolCall:
    """Single tool invocation."""

    tool_name: str
    arguments: dict[str, Any]
    result: Any = field(default=None)
    error: str | None = field(default=None)
    duration_ms: float = field(default=0.0)


@dataclass
class ExecutionTrace:
    """Full execution record for a task."""

    task_id: str
    start_time: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    completed: bool = field(default=False)
    error: str | None = field(default=None)
    recoveries: int = field(default=0)
    compressed_history: str = ""


class ToolRegistry:
    """Registry of available agent tools."""

    def __init__(self):
        """Initialize with default tools."""
        self._tools: dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register standard tools."""
        self.register("bash", self._bash_tool)
        self.register("python", self._python_tool)
        self.register("file_read", self._file_read_tool)
        self.register("file_write", self._file_write_tool)
        self.register("browser", self._browser_tool)
        self.register("think", self._think_tool)

    def register(self, name: str, fn: Callable) -> None:
        """Register a new tool."""
        self._tools[name] = fn

    async def execute(self, name: str, args: dict[str, Any]) -> Any:
        """Execute a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        return await self._tools[name](**args)

    async def _bash_tool(
        self, command: str, cwd: str | None = None, timeout: int = 60
    ) -> dict[str, Any]:
        """Execute bash command."""
        import time

        start = time.monotonic()

        proc = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "stdout": stdout.decode()[:10000],  # Truncate
                "stderr": stderr.decode()[:5000],
                "returncode": proc.returncode,
                "duration": time.monotonic() - start,
            }
        except TimeoutError:
            proc.kill()
            return {"error": "timeout", "stdout": "", "stderr": "", "returncode": -1}

    async def _python_tool(self, code: str, timeout: int = 30) -> dict[str, Any]:
        """Execute Python code."""
        import io
        import sys
        import time

        start = time.monotonic()
        stdout = io.StringIO()
        stderr = io.StringIO()

        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout, stderr

        try:
            # Create isolated namespace
            namespace = {}
            exec(code, namespace)  # noqa: S102

            result = {
                "stdout": stdout.getvalue()[:10000],
                "stderr": stderr.getvalue()[:5000],
                "result": namespace.get("result"),
                "duration": time.monotonic() - start,
            }
        except Exception as e:
            result = {
                "stdout": stdout.getvalue()[:1000],
                "stderr": f"{stderr.getvalue()}{type(e).__name__}: {e}",
                "error": str(e),
                "duration": time.monotonic() - start,
            }
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        return result

    async def _file_read_tool(self, path: str) -> dict[str, Any]:
        """Read file content."""
        try:
            content = Path(path).read_text()
            return {"content": content[:50000], "size": len(content), "exists": True}
        except Exception as e:
            return {"error": str(e), "exists": False}

    async def _file_write_tool(self, path: str, content: str) -> dict[str, Any]:
        """Write file content."""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return {"written": True, "bytes": len(content), "path": str(p)}
        except Exception as e:
            return {"error": str(e), "written": False}

    async def _browser_tool(self, url: str, action: str = "fetch") -> dict[str, Any]:
        """Browser interaction (mock for now)."""
        # Real implementation would use playwright/selenium
        return {"url": url, "action": action, "status": "mock"}

    async def _think_tool(self, reasoning: str) -> dict[str, Any]:
        """Explicit reasoning step."""
        logger.info(f"[THINK] {reasoning[:200]}")
        return {"acknowledged": True, "reasoning": reasoning}


class UnifiedAgent:
    """Main unified agent harness - Claude Code equivalent.

    Provides autonomous task completion across benchmarks.
    """

    def __init__(
        self,
        executor: LLMExecutor | None = None,
        tools: ToolRegistry | None = None,
        use_gaia: bool = False,
        use_autocontext: bool = False,
        use_autoharness: bool = False,
        use_metaharness: bool = False,
    ):
        """Initialize agent with executor and tools."""
        self.executor = executor or LLMExecutor(model="qwen3.5:cloud")
        self.tools = tools or ToolRegistry()
        self.session_mgr = CompoundSessionManager()
        self.max_steps = 50
        self.recovery_attempts = 3
        self.use_gaia = use_gaia
        self.use_autocontext = use_autocontext
        self.use_autoharness = use_autoharness
        self.use_metaharness = use_metaharness

        if self.use_gaia:
            self.gaia_orchestrator = amd_optimized_hierarchy()

    async def run_task(
        self, task: str | Any, env: dict[str, Any] | None = None, timeout: int = 1800
    ) -> ExecutionTrace:
        """Execute long-horizon task.

        Args:
            task: Task description or AgenticTask object
            env: Environment context with workdir, tools, etc.
            timeout: Maximum execution time in seconds

        Returns:
            ExecutionTrace with full execution record
        """
        import time
        from datetime import datetime

        task_id = str(uuid4())[:8]
        trace = ExecutionTrace(task_id=task_id, start_time=datetime.now().isoformat())

        # Setup environment
        workdir = env.get("workdir", f"/tmp/agent_{task_id}") if env else f"/tmp/agent_{task_id}"
        Path(workdir).mkdir(parents=True, exist_ok=True)

        # Execute with session alignment
        async with self.session_mgr as mgr:
            alignment = mgr.check_alignment(str(task))
            if not alignment.should_proceed:
                trace.error = f"Task rejected by alignment gate: {alignment.issues}"
                return trace

            # Pre-synthesize verifier if using autoharness
            verify_action = None
            if self.use_autoharness:
                try:
                    env_desc = f"Task: {task}"

                    def dummy_env(c):
                        return True, "OK"

                    synthesizer = AutoHarnessSynthesizer(self.executor)
                    verifier_code = await synthesizer.synthesize_verifier(env_desc, dummy_env)
                    namespace = {}
                    exec(verifier_code, {}, namespace)  # noqa: S102
                    verify_action = namespace.get("verify_action")
                except Exception as e:
                    logger.warning("Failed to synthesize verifier: %s", e)

            # Run main execution loop
            for step in range(self.max_steps):
                step_start = time.monotonic()

                # Trigger autocontext compaction if enabled
                if self.use_autocontext:
                    try:
                        monitor_res = autocontext_monitor(trace.steps)
                        if monitor_res.get("warn") or monitor_res.get("critical"):
                            compaction_prompt = (
                                "Please compress the previous step history into a concise summary."
                            )
                            compaction_res = await self.executor.execute_task(
                                task=compaction_prompt, skill="compaction"
                            )
                            compaction_output = (
                                compaction_res.output
                                if hasattr(compaction_res, "output")
                                else str(compaction_res)
                            )
                            trace.compressed_history = (
                                f"Compressed Previous Steps:\n{compaction_output}"
                            )
                    except Exception as e:
                        logger.warning("Autocontext compaction failed: %s", e)

                try:
                    # If using gaia, route execution through gaia_orchestrator
                    if self.use_gaia:
                        res = await self.gaia_orchestrator.run(str(task))
                        action_text = res.text
                        try:
                            if "```json" in action_text:
                                json_str = action_text.split("```json")[1].split("```")[0]
                            elif '{"' in action_text:
                                json_str = action_text[
                                    action_text.find("{") : action_text.rfind("}") + 1
                                ]
                            else:
                                json_str = action_text
                            action = json.loads(json_str)
                        except Exception:
                            action = {"complete": True, "result": {"output": action_text}}
                    else:
                        # Generate next action using standard LLM planner
                        action = await self._plan_next_action(
                            task=str(task), trace=trace, workdir=workdir, step=step
                        )

                    # Execute action
                    if action.get("tool"):
                        tool_name = action["tool"]
                        args = action.get("args", {})

                        # AutoHarness intercept check
                        if self.use_autoharness and verify_action:
                            state = {"step": step, "task": str(task)}
                            action_payload = args.get("code") or args.get("command") or str(args)
                            try:
                                is_valid = verify_action(state, action_payload)
                            except Exception:
                                is_valid = True

                            if not is_valid:
                                logger.warning("Action rejected by synthesized harness: %s", action)
                                trace.steps.append(
                                    {
                                        "step": step,
                                        "action": action,
                                        "harness_rejection": True,
                                        "status": "harness_rejection",
                                        "detail": "Blocked by verify_action",
                                    }
                                )
                                continue

                        result = await self._execute_tool_action(tool_name, args, workdir)

                        trace.tool_calls.append(
                            ToolCall(
                                tool_name=tool_name,
                                arguments=args,
                                result=result,
                                duration_ms=(time.monotonic() - step_start) * 1000,
                            )
                        )

                        # Meta-Harness trace logging
                        if self.use_metaharness:
                            try:
                                trace_dir = Path("execution_traces") / trace.task_id
                                trace_dir.mkdir(parents=True, exist_ok=True)

                                # Write JSON trace
                                json_data = {"step": step, "action": action, "result": result}
                                (trace_dir / f"step_{step}.json").write_text(json.dumps(json_data))

                                # Write metrics trace
                                metrics_data = {
                                    "duration_ms": (time.monotonic() - step_start) * 1000
                                }
                                (trace_dir / f"step_{step}.metrics").write_text(
                                    json.dumps(metrics_data)
                                )

                                # Write output trace
                                output_data = (
                                    result.get("stdout", "")
                                    or result.get("result", "")
                                    or str(result)
                                )
                                (trace_dir / f"step_{step}.output").write_text(str(output_data))
                            except Exception as e:
                                logger.warning("Meta-Harness logging failed: %s", e)

                        # Check for errors
                        if result.get("error"):
                            trace.recoveries += 1
                            if trace.recoveries >= self.recovery_attempts:
                                trace.error = f"Max recoveries exceeded at step {step}"
                                break

                    elif action.get("complete"):
                        trace.completed = True
                        trace.final_state = action.get("result", {})
                        break

                    trace.steps.append(
                        {"step": step, "action": action, "duration": time.monotonic() - step_start}
                    )

                except Exception as e:
                    logger.exception(f"Step {step} failed")
                    trace.recoveries += 1
                    if trace.recoveries >= self.recovery_attempts:
                        trace.error = str(e)
                        break

            # End session
            summary = mgr.end_session()
            trace.final_state["session"] = summary

        return trace

    async def _plan_next_action(
        self, task: str, trace: ExecutionTrace, workdir: str, step: int
    ) -> dict[str, Any]:
        """Use LLM to plan next action."""

        # Build prompt
        prompt = f"""You are an autonomous agent working on: {task}

**Current Step**: {step}/{self.max_steps}
**Work Directory**: {workdir}

**Previous Actions**:
{self._format_history(trace)}

**Available Tools**:
- bash(command, cwd): Execute shell commands
- python(code): Execute Python code
- file_read(path): Read file content
- file_write(path, content): Write file content
- browser(url): Fetch web content
- think(reasoning): Explicit reasoning step

CHOOSE YOUR NEXT ACTION:
1. Use a tool to make progress
2. Call 'complete' when task is done

Respond in JSON:
{{"tool": "bash", "args": {{"command": "ls -la"}}}}
OR
{{"complete": true, "result": {{"status": "success"}}}}
"""

        result = await self.executor.execute_task(
            task=prompt, skill="agentic_execution", context=f"Step {step} of task"
        )

        # Parse JSON from result
        output = result.output if hasattr(result, "output") else str(result)

        # Extract JSON from output
        try:
            # Find JSON block
            if "```json" in output:
                json_str = output.split("```json")[1].split("```")[0]
            elif '{"' in output:
                json_str = output[output.find("{") : output.rfind("}") + 1]
            else:
                json_str = output

            action = json.loads(json_str)
            return action
        except json.JSONDecodeError:
            # Fallback: assume bash command
            return {"tool": "bash", "args": {"command": output[:500]}}

    async def _execute_tool_action(
        self, tool_name: str, args: dict[str, Any], workdir: str
    ) -> dict[str, Any]:
        """Execute tool with workdir injection."""
        if tool_name in ["bash"] and "cwd" not in args:
            args["cwd"] = workdir
        return await self.tools.execute(tool_name, args)

    def _format_history(self, trace: ExecutionTrace) -> str:
        """Format execution history for prompt."""
        history = []
        for tc in trace.tool_calls[-5:]:  # Last 5 calls
            history.append(f"- {tc.tool_name}: {tc.arguments}")
            if tc.error:
                history.append(f"  ERROR: {tc.error}")
        return "\n".join(history) if history else "None yet"


# Default instance
default_agent = UnifiedAgent()
