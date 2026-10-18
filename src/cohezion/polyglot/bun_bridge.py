"""Bun / TypeScript Runtime Bridge.

Provides high-throughput asynchronous execution of TypeScript scripts,
FastMCP micro-services, and JSON Schema validation leveraging Bun's
zero-transpile JavaScriptCore runtime.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BunExecutionResult:
    """Outcome of a Bun / TypeScript execution."""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    data: Any = None
    duration_ms: float = 0.0


class BunBridge:
    """Bridge for executing TypeScript code via Bun."""

    def __init__(self, bun_executable: str | None = None):
        if bun_executable:
            self.bun_path: str | None = bun_executable
        else:
            # Check default path and user home
            extra_paths = [
                str(Path.home() / ".bun" / "bin"),
                str(Path.home() / ".local" / "bin"),
            ]
            path_env = os.environ.get("PATH", "") + ":" + ":".join(extra_paths)
            self.bun_path = shutil.which("bun", path=path_env)

    @property
    def is_available(self) -> bool:
        """True if Bun executable is found and runnable."""
        return self.bun_path is not None and os.path.isfile(self.bun_path)

    def run_typescript_snippet(
        self,
        ts_code: str,
        timeout_sec: float = 5.0,
    ) -> BunExecutionResult:
        """Execute inline TypeScript snippet and capture JSON or text output."""
        if not self.is_available or not self.bun_path:
            return BunExecutionResult(
                success=False,
                stdout="",
                stderr="Bun runtime not found on host",
                exit_code=-1,
            )

        import time

        start = time.perf_counter()

        try:
            proc = subprocess.run(
                [self.bun_path, "-e", ts_code],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            stdout = proc.stdout.strip()
            parsed_data = None
            if stdout:
                with contextlib.suppress(Exception):
                    parsed_data = json.loads(stdout)

            return BunExecutionResult(
                success=(proc.returncode == 0),
                stdout=stdout,
                stderr=proc.stderr.strip(),
                exit_code=proc.returncode,
                data=parsed_data,
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired:
            return BunExecutionResult(
                success=False,
                stdout="",
                stderr=f"TypeScript execution timed out after {timeout_sec}s",
                exit_code=-2,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as e:
            return BunExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-3,
                duration_ms=(time.perf_counter() - start) * 1000,
            )

    def validate_json_schema(
        self,
        data: dict[str, Any],
        required_keys: list[str],
    ) -> BunExecutionResult:
        """Validate JSON schema using TypeScript in Bun."""
        snippet = f"""
const payload = {json.dumps(data)};
const required = {json.dumps(required_keys)};
const missing = required.filter(k => !(k in payload));
console.log(JSON.stringify({{ valid: missing.length === 0, missing }}));
"""
        return self.run_typescript_snippet(snippet)
