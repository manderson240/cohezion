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
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.integrations.agentverse.llm_executor import LLMExecutor


logger = logging.getLogger(__name__)


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
    """Full execution record for a task.

    Recursive: when an agent delegates a subtask to a nested agent run, the child's
    ExecutionTrace is attached via :meth:`add_child`, forming a tree. This lets
    retrospection (the A-Evolve "Diagnose" step) reason over the whole recursive call
    tree rather than a flat list — e.g. roll up tool calls / recoveries per subtree
    (see :meth:`aggregate`), or locate which subtree failed.
    """

    task_id: str
    start_time: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    completed: bool = field(default=False)
    error: str | None = field(default=None)
    recoveries: int = field(default=0)
    # --- recursive structure ---
    parent_task_id: str | None = field(default=None)
    depth: int = field(default=0)
    children: list[ExecutionTrace] = field(default_factory=list)

    def add_child(self, child: ExecutionTrace) -> ExecutionTrace:
        """Attach a sub-task trace, stamping its parent link and depth."""
        child.parent_task_id = self.task_id
        child.depth = self.depth + 1
        self.children.append(child)
        return child

    def walk(self) -> Iterator[ExecutionTrace]:
        """Pre-order traversal: yield this trace, then each descendant."""
        yield self
        for c in self.children:
            yield from c.walk()

    def aggregate(self) -> dict[str, Any]:
        """Recursively roll up metrics across the whole subtree (retrospection primitive)."""
        nodes = list(self.walk())
        return {
            "node_count": len(nodes),
            "max_depth": max(n.depth for n in nodes),
            "total_steps": sum(len(n.steps) for n in nodes),
            "total_tool_calls": sum(len(n.tool_calls) for n in nodes),
            "total_recoveries": sum(n.recoveries for n in nodes),
            "completed_subtree": all(n.completed for n in nodes),
            "failed_task_ids": [n.task_id for n in nodes if n.error],
        }


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
            exec(code, namespace)

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
                "error": str(e)[
                    :500
                ],  # bounded like stdout/stderr — may be ingested as a fault-guard
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
            return {"error": str(e)[:500], "exists": False}

    async def _file_write_tool(self, path: str, content: str) -> dict[str, Any]:
        """Write file content."""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return {"written": True, "bytes": len(content), "path": str(p)}
        except Exception as e:
            return {"error": str(e)[:500], "written": False}

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

    Provides autonomous task execution with:
    - Multi-step planning and execution
    - Tool use (bash, python, file, browser)
    - Error recovery and self-correction
    - HIHO stability monitoring via CompoundSession
    """

    def __init__(
        self,
        executor: LLMExecutor | None = None,
        tools: ToolRegistry | None = None,
        *,
        guidance: Any | None = None,
        guidance_min_trust: float = 0.6,
        guidance_max_facts: int = 5,
    ):
        """Initialize agent with executor and tools.

        ``guidance`` enables the READ half of the compound self-improvement loop: pass a
        ``GroundTruthHierarchy`` (or any object exposing ``inject_context(max_facts=, min_trust=,
        max_chars=) -> str``) that the orchestrator's ``adapt_skill`` writes accepted fault-guards
        into. The worker then reads trust-ranked guidance back into its planning prompt, so a fault
        attributed once can improve future tasks. NOTE: the loop is only LIVE when a driver constructs
        ``UnifiedAgent(guidance=H)`` AND calls ``run_with_reflection(..., trust=H)`` with the SAME
        hierarchy ``H`` — no such driver exists yet, so this is wired-but-not-joined (same honest
        residual as reflective_orchestrator). Defaults are deliberately conservative so the injection
        is bounded and recurrence-gated:
          * ``guidance_min_trust=0.6`` — a single occurrence of a fault sits at trust 0.5; 0.6 requires
            the guard to have RECURRED (been corroborated) before it is treated as ground truth, so
            one-off faults never flood unrelated tasks.
          * ``guidance_max_facts=5`` — the injected block is capped regardless of how many guards
            accumulate, bounding the per-step token cost on the local fleet.
        """
        self.executor = executor or LLMExecutor(model="qwen3.5:cloud")
        self.tools = tools or ToolRegistry()
        self.session_mgr = CompoundSessionManager()
        self.max_steps = 50
        self.recovery_attempts = 3
        if not 0.0 <= guidance_min_trust <= 1.0:
            raise ValueError(f"guidance_min_trust must be in [0,1], got {guidance_min_trust}")
        if guidance_max_facts < 0:
            raise ValueError(f"guidance_max_facts must be >= 0, got {guidance_max_facts}")
        self.guidance = guidance
        self.guidance_min_trust = guidance_min_trust
        self.guidance_max_facts = guidance_max_facts
        # Per-guard char cap: bounds the bytes of each injected fact so a single multi-KB error string
        # ingested as a guard cannot blow up the per-step prompt (count cap alone is not a token bound).
        self.guidance_max_chars = 200

    # Cap recursive delegation so a planner that keeps delegating cannot loop forever.
    max_delegation_depth: int = 3

    async def run_task(
        self,
        task: str | Any,
        env: dict[str, Any] | None = None,
        timeout: int = 1800,
        _depth: int = 0,
    ) -> ExecutionTrace:
        """Execute long-horizon task.

        Args:
            task: Task description or AgenticTask object
            env: Environment context with workdir, tools, etc.
            timeout: Maximum execution time in seconds
            _depth: recursion depth (set internally when a parent delegates a subtask).

        Returns:
            ExecutionTrace with full execution record. If the agent delegates subtasks,
            child traces are nested under this one (see ExecutionTrace.add_child / walk).
        """
        import time
        from datetime import datetime

        task_id = str(uuid4())[:8]
        trace = ExecutionTrace(task_id=task_id, start_time=datetime.now().isoformat(), depth=_depth)

        # Setup environment
        workdir = env.get("workdir", f"/tmp/agent_{task_id}") if env else f"/tmp/agent_{task_id}"
        Path(workdir).mkdir(parents=True, exist_ok=True)

        # Execute with session alignment
        async with self.session_mgr as mgr:
            alignment = mgr.check_alignment(str(task))
            if not alignment.should_proceed:
                trace.error = f"Task rejected by alignment gate: {alignment.issues}"
                return trace

            # Run main execution loop
            for step in range(self.max_steps):
                step_start = time.monotonic()

                try:
                    # Generate next action
                    action = await self._plan_next_action(
                        task=str(task), trace=trace, workdir=workdir, step=step
                    )

                    # Execute action
                    if action.get("tool"):
                        result = await self._execute_tool_action(
                            action["tool"], action.get("args", {}), workdir
                        )

                        trace.tool_calls.append(
                            ToolCall(
                                tool_name=action["tool"],
                                arguments=action.get("args", {}),
                                result=result,
                                duration_ms=(time.monotonic() - step_start) * 1000,
                            )
                        )

                        # Check for errors
                        if result.get("error"):
                            trace.recoveries += 1
                            if trace.recoveries >= self.recovery_attempts:
                                trace.error = f"Max recoveries exceeded at step {step}"
                                break

                    elif action.get("delegate") and _depth < self.max_delegation_depth:
                        # Recursive delegation: run a subtask in a nested agent and
                        # nest its trace under this one (depth-guarded).
                        subtask = action.get("subtask") or action.get("args", {}).get("subtask", "")
                        child = await self.run_task(
                            subtask, env=env, timeout=timeout, _depth=_depth + 1
                        )
                        trace.add_child(child)
                        trace.tool_calls.append(
                            ToolCall(
                                tool_name="delegate",
                                arguments={"subtask": subtask},
                                result={
                                    "child_task_id": child.task_id,
                                    "completed": child.completed,
                                },
                                error=child.error,
                                duration_ms=(time.monotonic() - step_start) * 1000,
                            )
                        )
                        if child.error:
                            trace.recoveries += 1

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

        # Build prompt. The guidance block (if any) carries trust-ranked guards learned from prior
        # faults — the read half of the compound self-improvement loop (see __init__ guidance=).
        guidance_block = self._prior_guidance_block()
        prompt = f"""You are an autonomous agent working on: {task}
{guidance_block}
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

    def _prior_guidance_block(self) -> str:
        """Render the trust-ranked guidance block for the planning prompt (read half of the loop).

        Returns "" when no guidance store is configured or it is empty (so the prompt is byte-identical
        to the un-guided path — additive). Injection is bounded (``guidance_max_facts``) and
        recurrence-gated (``guidance_min_trust``) so one-off faults from unrelated tasks never flood
        the prompt. Falls back to "" on any guidance-provider error — guidance is an enhancement,
        never a hard dependency of planning.
        """
        if self.guidance is None or not hasattr(self.guidance, "inject_context"):
            return ""
        try:
            block = self.guidance.inject_context(
                max_facts=self.guidance_max_facts,
                min_trust=self.guidance_min_trust,
                max_chars=self.guidance_max_chars,
            )
        except (ValueError, KeyError, RuntimeError, OSError):
            # Runtime failures of an optional enhancement degrade to "no guidance" (logged). A
            # TypeError/AttributeError (wrong signature / wiring bug) deliberately PROPAGATES so a
            # misconfigured provider fails loudly at integration time instead of silently never injecting.
            logger.warning("guidance provider raised in inject_context; planning without guidance")
            return ""
        return f"\n{block}\n" if block else ""

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
