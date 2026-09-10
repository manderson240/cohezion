"""Leaf Minimalist Typed Harness with SurrealDB Telemetry.
==========================================================
Inspired by Microsoft Research's FrogNano technical report (arXiv:2026 / debug-gym):
1. Five Minimal Typed Tools:
   - read(path, start_line, end_line)
   - write(path, content)
   - edit(path, target, replacement)
   - glob(pattern, directory)
   - bash(command, cwd, timeout)
2. Natural Termination Rule:
   An assistant generation containing tool calls continues the episode;
   an assistant generation with NO tool calls is treated as the final answer
   and terminates the rollout immediately.
3. Log-Length Penalty:
   Penalizes token verbosity to enforce concise reasoning.
4. Native SurrealDB Integration:
   Rollout trajectories, tool sequences, and tokens are persisted directly
   into the SurrealDB `harness_rollout` table, linked to associative knowledge neurons.
"""

from __future__ import annotations

import base64
import fnmatch
import json
import logging
import math
import os
import subprocess
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LeafToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class LeafToolResult:
    tool_name: str
    output: str
    success: bool


@dataclass(frozen=True, slots=True)
class LeafRolloutStep:
    turn: int
    thought: str
    tool_calls: list[LeafToolCall]
    tool_results: list[LeafToolResult]
    tokens_generated: int


@dataclass(frozen=True, slots=True)
class LeafTrajectoryResult:
    task_id: str
    turns_used: int
    total_tokens: int
    log_length_penalty: float
    resolved: bool
    final_answer: str
    trajectory: list[LeafRolloutStep] = field(default_factory=list)
    surreal_record_id: str | None = None


class LeafHarness:
    """Minimalist 5-tool typed harness with natural termination and SurrealDB logging."""

    def __init__(
        self,
        workspace_dir: Path | str,
        surreal_url: str = "http://localhost:8001/sql",
        max_turns: int = 50,
        token_penalty_weight: float = 0.05,
    ) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        self.surreal_url = surreal_url
        self.max_turns = max_turns
        self.token_penalty_weight = token_penalty_weight
        self._tools: dict[str, Callable[..., str]] = {
            "read": self._tool_read,
            "write": self._tool_write,
            "edit": self._tool_edit,
            "glob": self._tool_glob,
            "bash": self._tool_bash,
        }

    # -------------------------------------------------------------------------
    # 5 Typed Tools (Leaf Protocol)
    # -------------------------------------------------------------------------

    def _tool_read(self, path: str, start_line: int = 1, end_line: int | None = None) -> str:
        """Read lines from a file."""
        target = (self.workspace_dir / path).resolve()
        if not target.is_relative_to(self.workspace_dir):
            return "Error: Path traversal outside workspace denied."
        if not target.exists():
            return f"Error: File '{path}' does not exist."
        if not target.is_file():
            return f"Error: '{path}' is not a regular file."

        try:
            with open(target, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            start_idx = max(0, start_line - 1)
            end_idx = end_line if end_line is not None else len(lines)
            selected = lines[start_idx:end_idx]
            numbered = [f"{start_idx + i + 1}: {line}" for i, line in enumerate(selected)]
            return "".join(numbered) if numbered else "[Empty range]"
        except Exception as e:
            return f"Error reading file '{path}': {e}"

    def _tool_write(self, path: str, content: str) -> str:
        """Write content to a file, creating parent directories if needed."""
        target = (self.workspace_dir / path).resolve()
        if not target.is_relative_to(self.workspace_dir):
            return "Error: Path traversal outside workspace denied."

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} bytes to '{path}'."
        except Exception as e:
            return f"Error writing file '{path}': {e}"

    def _tool_edit(self, path: str, target: str, replacement: str) -> str:
        """Replace target string with replacement in the specified file."""
        p = (self.workspace_dir / path).resolve()
        if not p.is_relative_to(self.workspace_dir):
            return "Error: Path traversal outside workspace denied."
        if not p.exists():
            return f"Error: File '{path}' does not exist."

        try:
            with open(p, encoding="utf-8") as f:
                text = f.read()
            if target not in text:
                return f"Error: Target text not found in '{path}'."
            count = text.count(target)
            if count > 1:
                return f"Error: Target text occurs {count} times in '{path}'. Must be unique."
            new_text = text.replace(target, replacement, 1)
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_text)
            return f"Successfully edited '{path}' (replaced 1 occurrence)."
        except Exception as e:
            return f"Error editing '{path}': {e}"

    def _tool_glob(self, pattern: str, directory: str = ".") -> str:
        """Search for files matching glob pattern."""
        search_root = (self.workspace_dir / directory).resolve()
        if not search_root.is_relative_to(self.workspace_dir):
            return "Error: Path traversal outside workspace denied."
        if not search_root.exists():
            return f"Error: Directory '{directory}' does not exist."

        matches = []
        for root, _, files in os.walk(search_root):
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), self.workspace_dir)
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(f, pattern):
                    matches.append(rel_path)
                    if len(matches) >= 50:
                        break
            if len(matches) >= 50:
                break

        return "\n".join(matches) if matches else f"No files matched pattern '{pattern}'."

    def _tool_bash(self, command: str, cwd: str = ".", timeout: float = 30.0) -> str:
        """Execute a bash command deterministically within workspace."""
        exec_cwd = (self.workspace_dir / cwd).resolve()
        if not exec_cwd.is_relative_to(self.workspace_dir):
            return "Error: Path traversal outside workspace denied."

        # Filter high-danger commands
        blocked = ["rm -rf /", ":(){ :|:& };:", "dd if="]
        if any(b in command for b in blocked):
            return "Error: Command violates harness safety policy."

        try:
            proc = subprocess.run(
                ["bash", "-c", command],
                cwd=exec_cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            combined = []
            if out:
                combined.append(out)
            if err:
                combined.append(f"[stderr]\n{err}")
            res_str = "\n".join(combined) if combined else "[Command exited with 0 and no output]"
            if proc.returncode != 0:
                res_str += f"\n[Exit code: {proc.returncode}]"
            return res_str
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds."
        except Exception as e:
            return f"Error executing bash: {e}"

    def execute_tool(self, call: LeafToolCall) -> LeafToolResult:
        """Execute a single Leaf typed tool call."""
        fn = self._tools.get(call.name)
        if not fn:
            return LeafToolResult(
                tool_name=call.name,
                output=f"Error: Unknown tool '{call.name}'. Available: {list(self._tools.keys())}",
                success=False,
            )
        try:
            output = fn(**call.arguments)
            success = not output.startswith("Error:")
            return LeafToolResult(tool_name=call.name, output=output, success=success)
        except Exception as e:
            return LeafToolResult(
                tool_name=call.name,
                output=f"Error executing '{call.name}': {e}",
                success=False,
            )

    # -------------------------------------------------------------------------
    # SurrealDB Persistence
    # -------------------------------------------------------------------------

    def persist_rollout_to_surreal(self, result: LeafTrajectoryResult) -> str | None:
        """Persist the rollout telemetry, token metrics, and penalty into SurrealDB."""
        try:
            auth = base64.b64encode(b"root:root").decode()
            record_id = f"rollout_{int(time.time() * 1000)}"
            data = {
                "task_id": result.task_id,
                "turns_used": result.turns_used,
                "total_tokens": result.total_tokens,
                "log_length_penalty": result.log_length_penalty,
                "resolved": result.resolved,
                "final_answer": result.final_answer[:500],
                "step_count": len(result.trajectory),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

            surql = f"CREATE harness_rollout:{record_id} CONTENT {json.dumps(data)};"
            req = urllib.request.Request(  # noqa: S310
                self.surreal_url,
                data=surql.encode("utf-8"),
                headers={
                    "surreal-ns": "cohezion",
                    "surreal-db": "vault",
                    "Authorization": f"Basic {auth}",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:  # noqa: S310
                if resp.status == 200:
                    logger.info("Persisted Leaf rollout '%s' to SurrealDB", record_id)
                    return f"harness_rollout:{record_id}"
        except Exception as e:
            logger.warning("Failed to persist Leaf rollout to SurrealDB: %s", e)
        return None

    def compute_log_length_penalty(self, total_tokens: int) -> float:
        """FrogNano log-length penalty: encourages concise reasoning and tool calls."""
        if total_tokens <= 0:
            return 0.0
        return round(self.token_penalty_weight * math.log(1.0 + total_tokens), 4)
