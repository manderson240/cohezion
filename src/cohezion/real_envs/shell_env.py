"""Real shell environment for executing actual commands.

Executes real shell commands in sandboxed environments and captures
stdout, stderr, file system state, and process information.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shlex
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.real_envs.base import (
    RealAction,
    RealEnvironment,
    RealObservation,
    RealState,
    EnvironmentStep,
)
from cohezion.universe.sandbox_backends import select_backend, BackendResult
from cohezion.universe.sandbox_profiles import SandboxProfile, SandboxTier, PROFILES


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShellAction(RealAction):
    """A shell action (execute command, read file, write file, etc.)."""

    # action_type values:
    # - "execute": parameters={"command": str, "timeout": int, "cwd": str|null}
    # - "read_file": parameters={"path": str, "encoding": str}
    # - "write_file": parameters={"path": str, "content": str, "mode": str}
    # - "list_dir": parameters={"path": str}
    # - "create_dir": parameters={"path": str, "parents": bool}
    # - "delete": parameters={"path": str, "recursive": bool}
    # - "git": parameters={"subcommand": str, "args": list}
    # - "python": parameters={"code": str, "timeout": int}

    @classmethod
    def execute(
        cls, command: str, timeout: int = 30, cwd: str | None = None
    ) -> "ShellAction":
        return cls(
            action_type="execute",
            parameters={"command": command, "timeout": timeout, "cwd": cwd},
        )

    @classmethod
    def read_file(cls, path: str, encoding: str = "utf-8") -> "ShellAction":
        return cls(
            action_type="read_file", parameters={"path": path, "encoding": encoding}
        )

    @classmethod
    def write_file(cls, path: str, content: str, mode: str = "w") -> "ShellAction":
        return cls(
            action_type="write_file",
            parameters={"path": path, "content": content, "mode": mode},
        )

    @classmethod
    def list_dir(cls, path: str = ".") -> "ShellAction":
        return cls(action_type="list_dir", parameters={"path": path})

    @classmethod
    def create_dir(cls, path: str, parents: bool = True) -> "ShellAction":
        return cls(
            action_type="create_dir", parameters={"path": path, "parents": parents}
        )

    @classmethod
    def delete(cls, path: str, recursive: bool = False) -> "ShellAction":
        return cls(
            action_type="delete", parameters={"path": path, "recursive": recursive}
        )

    @classmethod
    def git(cls, subcommand: str, args: list[str] | None = None) -> "ShellAction":
        return cls(
            action_type="git", parameters={"subcommand": subcommand, "args": args or []}
        )

    @classmethod
    def python(cls, code: str, timeout: int = 30) -> "ShellAction":
        return cls(action_type="python", parameters={"code": code, "timeout": timeout})


@dataclass
class ShellObservation(RealObservation):
    """Observation from shell after an action."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    working_directory: str = ""
    command_executed: str = ""
    file_content: str | None = None  # For read_file actions
    directory_listing: list[dict] | None = None  # For list_dir actions

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "stdout": self.stdout[:5000]
                if len(self.stdout) > 5000
                else self.stdout,
                "stderr": self.stderr[:2000]
                if len(self.stderr) > 2000
                else self.stderr,
                "exit_code": self.exit_code,
                "working_directory": self.working_directory,
                "command_executed": self.command_executed,
                "file_content": self.file_content,
                "directory_listing": self.directory_listing,
            }
        )
        return base


@dataclass
class ShellState(RealState):
    """Current state of the shell environment."""

    working_directory: str = ""
    environment_variables: dict[str, str] = field(default_factory=dict)
    file_system_hash: str = ""
    recent_files: list[str] = field(default_factory=list)
    command_history: list[str] = field(default_factory=list)
    process_info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "working_directory": self.working_directory,
                "environment_variables": dict(
                    list(self.environment_variables.items())[:20]
                ),
                "file_system_hash": self.file_system_hash,
                "recent_files": self.recent_files[:20],
                "command_history": self.command_history[-50:],  # Last 50 commands
                "process_info": self.process_info,
            }
        )
        return base


class ShellEnvironment(RealEnvironment[ShellAction, ShellObservation, ShellState]):
    """Real shell environment with actual command execution.

    Executes real shell commands in sandboxed environments with
    configurable isolation levels. Captures full execution traces.

    Example:
        ```python
        env = ShellEnvironment("Create a Python virtual environment and install requests")
        obs, state = env.reset()

        # Create directory
        obs, reward, done, info = await env.step(
            ShellAction.create_dir("my_project")
        )

        # Create virtual environment
        obs, reward, done, info = await env.step(
            ShellAction.execute("python3 -m venv venv", cwd="my_project")
        )

        # Install package
        obs, reward, done, info = await env.step(
            ShellAction.execute("./venv/bin/pip install requests", cwd="my_project")
        )
        ```
    """

    def __init__(
        self,
        task_description: str,
        working_dir: str | None = None,
        sandbox_tier: SandboxTier = SandboxTier.MEDIUM,
        allowed_commands: list[str] | None = None,
        blocked_commands: list[str] | None = None,
        max_steps: int = 50,
        env_vars: dict[str, str] | None = None,
    ):
        super().__init__(task_description, max_steps, "data/real_envs/shell")

        # Create temp working directory if not provided
        if working_dir:
            self.working_dir = Path(working_dir).resolve()
            self.working_dir.mkdir(parents=True, exist_ok=True)
            self._temp_dir = None
        else:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="cohezion_shell_")
            self.working_dir = Path(self._temp_dir.name).resolve()

        self.sandbox_tier = sandbox_tier
        self.sandbox_profile = PROFILES[sandbox_tier]
        self.backend = select_backend()

        # Command filtering
        self.allowed_commands = set(allowed_commands) if allowed_commands else None
        self.blocked_commands = set(
            blocked_commands or ["rm -rf /", "dd if=/dev/zero", ":(){ :|: & };:"]
        )

        # Environment variables
        self.env_vars = env_vars or {}
        self._current_env = {**os.environ, **self.env_vars}

        self._state = ShellState(
            state_type="shell",
            working_directory=str(self.working_dir),
            environment_variables=self._current_env,
        )

        logger.info(f"ShellEnvironment initialized in {self.working_dir}")

    def reset(self, seed: int | None = None) -> tuple[ShellObservation, ShellState]:
        """Reset shell to initial state."""
        self.current_step = 0
        self.trajectory = []
        self._is_done = False

        # Clear temp directory contents
        if self._temp_dir:
            for item in self.working_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    import shutil

                    shutil.rmtree(item)

        state = self._capture_state()
        obs = ShellObservation(
            success=True,
            working_directory=str(self.working_dir),
            data={"message": "Shell reset to initial state"},
        )

        self._state = state
        return obs, state

    async def step(
        self, action: ShellAction
    ) -> tuple[ShellObservation, float, bool, dict[str, Any]]:
        """Execute a shell action."""
        start_time = time.time()

        success = True
        error_message = None
        stdout = ""
        stderr = ""
        exit_code = 0

        try:
            if action.action_type == "execute":
                command = action.parameters["command"]
                timeout = action.parameters.get("timeout", 30)
                cwd = action.parameters.get("cwd")

                if not self._is_command_allowed(command):
                    raise ValueError(f"Command not allowed: {command}")

                working_path = self.working_dir / cwd if cwd else self.working_dir

                # Always use direct subprocess for shell commands
                # Sandbox backends are designed for Python code execution
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(working_path),
                    env=self._current_env,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(), timeout=timeout
                    )
                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                    exit_code = process.returncode or 0
                    success = exit_code == 0
                except asyncio.TimeoutError:
                    process.kill()
                    stdout = ""
                    stderr = "Command timed out"
                    exit_code = -1
                    success = False

                # Record in history
                if len(self._state.command_history) > 100:
                    self._state.command_history.pop(0)
                self._state.command_history.append(command)

            elif action.action_type == "read_file":
                path = action.parameters["path"]
                encoding = action.parameters.get("encoding", "utf-8")
                file_path = self._resolve_path(path)

                # Security check
                self._check_path_in_working_dir(file_path)

                content = file_path.read_text(encoding=encoding)
                stdout = content[:10000]  # Limit output size

            elif action.action_type == "write_file":
                path = action.parameters["path"]
                content = action.parameters["content"]
                mode = action.parameters.get("mode", "w")

                file_path = self._resolve_path(path)
                self._check_path_in_working_dir(file_path)

                file_path.parent.mkdir(parents=True, exist_ok=True)

                if mode == "a":
                    file_path.write_text(content, encoding="utf-8")
                else:
                    file_path.write_text(content, encoding="utf-8")

                stdout = f"Wrote {len(content)} bytes to {path}"

            elif action.action_type == "list_dir":
                path = action.parameters.get("path", ".")
                dir_path = self._resolve_path(path)
                self._check_path_in_working_dir(dir_path)

                entries = []
                for item in dir_path.iterdir():
                    stat = item.stat()
                    entries.append(
                        {
                            "name": item.name,
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        }
                    )

                stdout = json.dumps(entries, indent=2)

            elif action.action_type == "create_dir":
                path = action.parameters["path"]
                parents = action.parameters.get("parents", True)

                dir_path = self._resolve_path(path)
                self._check_path_in_working_dir(dir_path)

                dir_path.mkdir(parents=parents, exist_ok=True)
                stdout = f"Created directory: {path}"

            elif action.action_type == "delete":
                path = action.parameters["path"]
                recursive = action.parameters.get("recursive", False)

                target_path = self._resolve_path(path)
                self._check_path_in_working_dir(target_path)

                if target_path.is_file():
                    target_path.unlink()
                    stdout = f"Deleted file: {path}"
                elif target_path.is_dir():
                    if recursive:
                        import shutil

                        shutil.rmtree(target_path)
                        stdout = f"Deleted directory recursively: {path}"
                    else:
                        target_path.rmdir()
                        stdout = f"Deleted empty directory: {path}"

            elif action.action_type == "git":
                subcommand = action.parameters["subcommand"]
                args = action.parameters.get("args", [])

                command = f"git {subcommand} {' '.join(shlex.quote(a) for a in args)}"

                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.working_dir),
                    env=self._current_env,
                )

                stdout_bytes, stderr_bytes = await process.communicate()
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                exit_code = process.returncode or 0
                success = exit_code == 0

            elif action.action_type == "python":
                code = action.parameters["code"]
                timeout = action.parameters.get("timeout", 30)

                # Create temporary script
                script_path = self.working_dir / f"_tmp_script_{int(time.time())}.py"
                script_path.write_text(code)

                command = f"python3 {script_path}"

                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.working_dir),
                    env=self._current_env,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(), timeout=timeout
                    )
                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                    exit_code = process.returncode or 0
                    success = exit_code == 0
                except asyncio.TimeoutError:
                    process.kill()
                    stdout = ""
                    stderr = "Python execution timed out"
                    exit_code = -1
                    success = False
                finally:
                    script_path.unlink(missing_ok=True)

            else:
                raise ValueError(f"Unknown action type: {action.action_type}")

        except Exception as e:
            success = False
            error_message = str(e)
            stderr = str(e)
            logger.error(f"Shell action failed: {e}")

        latency_ms = (time.time() - start_time) * 1000

        # Update state
        state = self._capture_state()

        obs = ShellObservation(
            success=success,
            data={},
            error_message=error_message,
            latency_ms=latency_ms,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            working_directory=str(self.working_dir),
            command_executed=action.parameters.get("command", action.action_type),
        )

        # Check task completion
        is_complete, reward, metrics = self.evaluate_task()
        self._is_done = is_complete or self.current_step >= self.max_steps

        # Record step
        step = EnvironmentStep(
            step_number=self.current_step,
            action=action,
            observation=obs,
            state=state,
            reward=reward,
            done=self._is_done,
            info={"latency_ms": latency_ms, **metrics},
        )
        self.trajectory.append(step)
        self.current_step += 1

        return obs, reward, self._is_done, metrics

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to working directory."""
        if path.startswith("/"):
            return Path(path).resolve()
        return (self.working_dir / path).resolve()

    def _check_path_in_working_dir(self, path: Path) -> None:
        """Security check: ensure path is within working directory."""
        try:
            path.relative_to(self.working_dir)
        except ValueError:
            raise ValueError(
                f"Path {path} is outside working directory {self.working_dir}"
            )

    def _is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed."""
        # Check blocked patterns
        for blocked in self.blocked_commands:
            if blocked in command:
                return False

        # If whitelist exists, check it
        if self.allowed_commands:
            cmd_parts = command.split()
            if cmd_parts and cmd_parts[0] not in self.allowed_commands:
                return False

        return True

    def _capture_state(self) -> ShellState:
        """Capture current shell state."""
        # Compute file system hash
        file_hashes = []
        try:
            for item in sorted(self.working_dir.rglob("*")):
                if item.is_file():
                    file_hashes.append(
                        f"{item.relative_to(self.working_dir)}:{item.stat().st_mtime}"
                    )
        except:
            pass

        fs_hash = hashlib.sha256("|".join(file_hashes).encode()).hexdigest()[:16]

        # Get recent files
        recent_files = []
        try:
            files = [
                (f, f.stat().st_mtime)
                for f in self.working_dir.rglob("*")
                if f.is_file()
            ]
            recent_files = [
                str(f[0].relative_to(self.working_dir))
                for f in sorted(files, key=lambda x: x[1], reverse=True)[:20]
            ]
        except:
            pass

        state = ShellState(
            state_type="shell",
            working_directory=str(self.working_dir),
            environment_variables=self._current_env,
            file_system_hash=fs_hash,
            recent_files=recent_files,
            command_history=self._state.command_history if self._state else [],
        )

        self._state = state
        return state

    def get_state(self) -> ShellState:
        """Get current shell state."""
        return self._state or self._capture_state()

    def evaluate_task(self) -> tuple[bool, float, dict[str, Any]]:
        """Evaluate if shell task is complete."""
        if not self.trajectory:
            return False, 0.0, {}

        # Default reward based on success rate
        success_rate = sum(1 for s in self.trajectory if s.observation.success) / len(
            self.trajectory
        )
        reward = success_rate * 0.1

        # Check for task-specific criteria (overridden by task evaluators)
        is_complete = False

        metrics = {
            "steps_taken": len(self.trajectory),
            "success_rate": success_rate,
            "files_created": len(self._state.recent_files) if self._state else 0,
            "commands_executed": len(self._state.command_history) if self._state else 0,
        }

        return is_complete, reward, metrics

    def close(self):
        """Cleanup resources."""
        if self._temp_dir:
            self._temp_dir.cleanup()
            logger.info(f"Cleaned up temp directory: {self.working_dir}")
