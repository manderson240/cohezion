"""ImprovementExecutor — runs Claude Code subprocesses for autonomous improvement tasks.

Each task is executed as a fresh Claude Code process with:
- A specific prompt describing what to fix
- Allowed tools restricted to what's needed
- Output captured for verification
- Result parsed and returned to the coordinator

This is subprocess-based, so context never grows within any single process.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from typing import Any

from .coordinator import LoopConfig, LoopTask


logger = logging.getLogger(__name__)


class ImprovementExecutor:
    """Execute improvement tasks via Claude Code subprocesses."""

    def __init__(self, config: LoopConfig | None = None):
        self.config = config or LoopConfig()
        self._claude_cmd = self._find_claude()
        self._started = False

    def start(self, worktree_path: str) -> None:
        """Initialize the executor."""
        self._worktree_path = worktree_path
        self._started = True
        logger.info("ImprovementExecutor started at %s", worktree_path)

    def stop(self) -> None:
        """Clean up."""
        self._started = False
        logger.info("ImprovementExecutor stopped")

    def execute_task(self, task: LoopTask, worktree_path: str) -> dict[str, Any]:
        """Execute one improvement task via Claude Code subprocess.

        Returns dict with:
        - success: bool
        - summary: str
        - tokens_used: int (estimated)
        - output: str (last 2000 chars)
        """
        if not self._started:
            raise RuntimeError("Executor not started. Call start() first.")

        # Build the prompt for Claude Code
        prompt = self._build_prompt(task)

        # Run Claude Code in non-interactive mode
        result = self._run_claude(prompt, worktree_path, task)

        # Parse the result
        return self._parse_result(result, task)

    def _find_claude(self) -> str:
        """Find the claude binary."""
        # Try common locations
        for path in ["/usr/local/bin/claude", "/usr/bin/claude", "claude"]:
            try:
                subprocess.run([path, "--version"], capture_output=True, timeout=5)
                return path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        raise RuntimeError("claude CLI not found in PATH")

    def _build_prompt(self, task: LoopTask) -> str:
        """Build a Claude Code prompt for this task."""
        if task.category == "test_fix":
            return self._build_test_fix_prompt(task)
        elif task.category == "lint_fix":
            return self._build_lint_fix_prompt(task)
        elif task.category == "type_fix":
            return self._build_type_fix_prompt(task)
        elif task.category == "refactor":
            return self._build_refactor_prompt(task)
        else:
            return f"Fix this issue: {task.description}. Then verify with: {task.verification}"

    def _build_test_fix_prompt(self, task: LoopTask) -> str:
        return f"""You are fixing a test collection error.

TASK: {task.description}

VERIFICATION: Run this command to verify the fix:
```
{task.verification}
```

RULES:
1. Read the actual error from `uv run pytest {task.id.replace("test_fix_", "")} --collect-only -q 2>&1`
2. Fix the ROOT CAUSE — don't suppress errors, fix the code
3. If the import is wrong, fix the import or add the missing export
4. If there's a name collision, rename one of the files
5. After fixing, run the verification command
6. Report success/failure

IMPORTANT: Do NOT modify any files outside the test source or the module being imported.
Be surgical — touch only what's needed to fix the collection error.
"""

    def _build_lint_fix_prompt(self, task: LoopTask) -> str:
        return f"""You are fixing ruff lint issues.

TASK: {task.description}

VERIFICATION: Run this command to verify:
```
{task.verification}
```

RULES:
1. Run `uv run ruff check` first to see the exact errors
2. Fix each error — remove unused imports, fix formatting, etc.
3. After fixing, run the verification command
4. Report success/failure

Be surgical — touch only the lines that need fixing.
"""

    def _build_type_fix_prompt(self, task: LoopTask) -> str:
        return f"""You are fixing type errors.

TASK: {task.description}

VERIFICATION: Run this command to verify:
```
{task.verification}
```

RULES:
1. Run `uv run mypy` first to see the exact errors
2. Fix each type error with proper annotations
3. After fixing, run the verification command
4. Report success/failure
"""

    def _build_refactor_prompt(self, task: LoopTask) -> str:
        return f"""You are refactoring code.

TASK: {task.description}

VERIFICATION: Run this command to verify:
```
{task.verification}
```

RULES:
1. Read the file and understand the current code
2. Make the minimal change to address the issue
3. After fixing, run the verification command
4. Report success/failure
"""

    def _run_claude(
        self, prompt: str, worktree_path: str, task: LoopTask
    ) -> subprocess.CompletedProcess:
        """Run Claude Code with the given prompt."""
        # Build the command
        cmd = [
            self._claude_cmd,
            "-p",  # print mode (non-interactive)
            "--append-system-prompt",
            "You are an autonomous code improvement agent. Fix the issue described below. "
            "Be surgical — only touch files that need changing. "
            "Always verify your fix before reporting success.",
            prompt,
        ]

        env = {
            **__import__("os").environ,
            "CLAUDE_CODE_DISABLE_TELEMETRY": "1",
        }

        logger.info("Running Claude Code for task %s", task.id)
        start = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=worktree_path,
                env=env,
                timeout=300,  # 5 min per task
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                cmd=cmd, returncode=-1, stdout="", stderr="TIMEOUT after 5 minutes"
            )
        except Exception as exc:
            return subprocess.CompletedProcess(cmd=cmd, returncode=-2, stdout="", stderr=str(exc))

        elapsed = time.time() - start
        logger.info(
            "Task %s completed in %.1fs, return code=%d",
            task.id,
            elapsed,
            result.returncode,
        )

        return result

    def _parse_result(self, result: subprocess.CompletedProcess, task: LoopTask) -> dict[str, Any]:
        """Parse the Claude Code output to determine success/failure."""
        output = result.stdout + result.stderr

        # Estimate tokens from output length (rough heuristic)
        tokens_used = len(output.split()) * 2  # very rough estimate

        # Check for success indicators
        success = False
        summary = ""

        if result.returncode == 0:
            success = True
            summary = "Claude Code completed successfully"
        elif "TIMEOUT" in output:
            success = False
            summary = "Task timed out after 5 minutes"
        else:
            # Check output for success/failure signals
            if re.search(r"(success|fixed|resolved|passed|applied)", output, re.IGNORECASE):
                success = True
                summary = "Claude Code reports fix applied"
            elif re.search(r"(fail|error|cannot|unable|could not)", output, re.IGNORECASE):
                success = False
                summary = "Claude Code reports fix failed"
            else:
                # Default: assume success if Claude ran without error
                success = result.returncode != -1
                summary = output[-500:] if output else "No output"

        return {
            "success": success,
            "summary": summary[:200],
            "tokens_used": tokens_used,
            "output": output[-2000:],  # last 2000 chars
            "returncode": result.returncode,
        }
