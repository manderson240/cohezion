"""ImprovementExecutor — cloud-backed task executor for the autonomous loop.

Wires UnifiedHybridRouter (Tier 2 Ollama Cloud), TransitionController.enum_schema
for Markov agentic state transitions, and AutoHarnessPolicy for deterministic verification.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.inference.transition_controller import TransitionController


logger = logging.getLogger(__name__)

DEFAULT_TRANSITION_MATRIX: dict[str, list[str]] = {
    "start": ["plan", "abort"],
    "plan": ["code", "abort"],
    "code": ["verify", "abort"],
    "verify": ["commit", "code", "abort"],
    "commit": ["done"],
    "abort": ["done"],
    "done": [],
}


class ImprovementExecutor:
    """Cloud/hybrid executor: delegates task execution to remote or hybrid inference providers."""

    def __init__(
        self,
        config: Any = None,
        router: Any = None,
        transition_controller: TransitionController | None = None,
        autoharness: AutoHarnessPolicy | None = None,
    ) -> None:
        self._config = config
        self._router = router
        self._transition_controller = transition_controller or TransitionController(
            matrix=DEFAULT_TRANSITION_MATRIX
        )
        self._autoharness = autoharness or AutoHarnessPolicy("improvement_executor")
        self._started = False
        self._worktree_path: str = "/tmp/worktree"

    def start(self, worktree_path: str) -> None:
        self._started = True
        self._worktree_path = worktree_path

    def stop(self) -> None:
        self._started = False

    def execute_task(self, task: Any, worktree_path: str) -> dict[str, Any]:
        """Execute task across cloud/hybrid inference with Markov state transition control."""
        if not self._started:
            self.start(worktree_path)

        state_history = ["start"]
        current_state = "start"

        # Step 1: Query transition controller enum schema for valid next states
        _transition_schema = self._transition_controller.enum_schema(current_state)

        # Step 2: Ensure an inference router is available
        router = self._router
        if router is None and getattr(self._config, "use_cloud", False):
            try:
                from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter

                router = UnifiedHybridRouter(prefer_local=False)
                self._router = router
            except Exception as exc:
                logger.debug("Failed to instantiate default UnifiedHybridRouter: %s", exc)

        if router is None:
            return {
                "success": False,
                "summary": "no inference provider configured",
                "tokens_used": 0,
                "output": "",
                "returncode": 1,
                "task_id": getattr(task, "id", None),
                "state_transitions": state_history,
            }

        # Step 3: Advance state to plan -> code
        current_state = "plan"
        state_history.append(current_state)
        current_state = "code"
        state_history.append(current_state)

        task_desc = getattr(task, "description", str(task))
        verification_cmd = getattr(task, "verification", "")
        prompt = (
            f"Autonomous Loop Task Resolution:\n"
            f"Description: {task_desc}\n"
            f"Verification: {verification_cmd}\n"
            f"Provide the exact patch or solution."
        )

        tokens_used = 0
        output_text = ""
        try:
            if hasattr(router, "route_query"):
                route_res = router.route_query(prompt, force_cloud=True)
                output_text = route_res.content
                tokens_used = getattr(route_res, "tokens_used", 150)
            elif hasattr(router, "query"):
                res = router.query(prompt)
                output_text = str(res)
                tokens_used = 150
            else:
                output_text = str(router(prompt))
                tokens_used = 150
        except Exception as exc:
            logger.warning("Cloud inference execution failed: %s", exc)
            self._transition_controller.record_transition("code", "abort", -1.0)
            state_history.append("abort")
            state_history.append("done")
            return {
                "success": False,
                "summary": f"cloud inference error: {exc}",
                "tokens_used": tokens_used,
                "output": output_text,
                "returncode": 1,
                "task_id": getattr(task, "id", None),
                "state_transitions": state_history,
            }

        # Step 4: Advance to verify state & run AutoHarness
        current_state = "verify"
        state_history.append(current_state)

        # If code fences are detected, verify via AutoHarness
        code_snippets = []
        if "```python" in output_text:
            parts = output_text.split("```python")
            for p in parts[1:]:
                code = p.split("```")[0]
                code_snippets.append(code)

        for code in code_snippets:
            harness_res = self._autoharness.verify_code(code)
            if not harness_res.valid:
                logger.warning("AutoHarness AST violation: %s", harness_res.violations)
                self._transition_controller.record_transition("verify", "code", -0.5)
                state_history.append("abort")
                state_history.append("done")
                return {
                    "success": False,
                    "summary": f"AutoHarness verification failed: {harness_res.violations}",
                    "tokens_used": tokens_used,
                    "output": output_text,
                    "returncode": 1,
                    "task_id": getattr(task, "id", None),
                    "state_transitions": state_history,
                }

        # Step 5: Execute verification command if provided
        returncode = 0
        cmd_out = ""
        target_dir = worktree_path or self._worktree_path
        if verification_cmd and os.path.exists(target_dir):
            try:
                proc = subprocess.run(  # noqa: S602
                    verification_cmd,
                    shell=True,
                    cwd=target_dir,
                    capture_output=True,
                    text=True,
                    timeout=60.0,
                )
                returncode = proc.returncode
                cmd_out = proc.stdout + proc.stderr
            except Exception as exc:
                logger.warning("Verification command failed to execute: %s", exc)
                returncode = 1
                cmd_out = str(exc)

        success = (returncode == 0) and bool(output_text.strip())
        if success:
            self._transition_controller.record_transition("verify", "commit", 1.0)
            state_history.append("commit")
            state_history.append("done")
            summary = "ok"
        else:
            self._transition_controller.record_transition("verify", "abort", -0.8)
            state_history.append("abort")
            state_history.append("done")
            summary = f"verification failed (rc={returncode})"

        return {
            "success": success,
            "summary": summary,
            "tokens_used": tokens_used,
            "output": cmd_out if cmd_out else output_text,
            "returncode": returncode,
            "task_id": getattr(task, "id", None),
            "state_transitions": state_history,
        }
