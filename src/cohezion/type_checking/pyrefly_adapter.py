"""Pyrefly Type Checking Adapter and Agentic Diagnostic Engine.

Adopts Google and Meta's open-source Rust-based Python type checker (Pyrefly)
for Cohezion's agentic inner development loops, continuous CI ratchets, and
automated self-healing type repairs.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PyreflyDiagnostic:
    """Structured diagnostic representation of a Pyrefly compiler error or warning."""

    file: str
    line: int
    column: int
    severity: str
    error_code: str
    message: str
    offending_code: str | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializes the diagnostic to a dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "error_code": self.error_code,
            "message": self.message,
            "offending_code": self.offending_code,
            "suggestion": self.suggestion,
        }


@dataclass
class PyreflyResult:
    """Execution result from Pyrefly type checking."""

    returncode: int
    passed: bool
    errors_count: int
    warnings_count: int
    diagnostics: list[PyreflyDiagnostic] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serializes the result to a dictionary."""
        return {
            "returncode": self.returncode,
            "passed": self.passed,
            "errors_count": self.errors_count,
            "warnings_count": self.warnings_count,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "duration_ms": self.duration_ms,
        }


class PyreflyAdapter:
    """Adapter for running Pyrefly type checks and parsing Rust-style compiler diagnostics."""

    DIAGNOSTIC_HEADER_PATTERN = re.compile(
        r"(?P<severity>ERROR|WARNING)\s+(?P<message>.*?)\s+\[(?P<code>[a-zA-Z0-9\-_]+)\]\s*\n\s*-->\s*(?P<file>[^:\n]+):(?P<line>\d+):(?P<col>\d+)",
        re.DOTALL,
    )

    SUGGESTION_PATTERN = re.compile(
        r"(?:(?:The declared type|Expected|Note)[^\n]*\.\s*)?(?P<hint>(?:Consider|Did you mean)[^\n]+)",
        re.IGNORECASE,
    )

    def __init__(self, executable: str = "pyrefly") -> None:
        self.executable = executable

    def is_available(self) -> bool:
        """Checks if the Pyrefly binary is installed and executable in PATH."""
        return shutil.which(self.executable) is not None

    def check_files(
        self,
        paths: Sequence[str | Path],
        threads: int = 0,
        cwd: str | Path | None = None,
    ) -> PyreflyResult:
        """Executes full type checking over specific file paths or directories.

        Parameters
        ----------
        paths : Sequence[str | Path]
            Paths to files or directories to check.
        threads : int
            Number of worker threads (0 = auto-detect hardware concurrency).
        cwd : str | Path | None
            Working directory for execution.

        Returns
        -------
        PyreflyResult
            Parsed execution result and structured diagnostics.
        """
        if not self.is_available():
            return PyreflyResult(
                returncode=-1,
                passed=False,
                errors_count=1,
                warnings_count=0,
                stderr="Pyrefly executable not found in environment.",
            )

        cmd = [self.executable, "check", "--color", "never", "-j", str(threads)]
        for p in paths:
            cmd.append(str(p))

        t0 = time.perf_counter()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        diagnostics = self.parse_diagnostics(proc.stdout + "\n" + proc.stderr)
        errors = sum(1 for d in diagnostics if d.severity == "ERROR")
        warnings = sum(1 for d in diagnostics if d.severity == "WARNING")

        return PyreflyResult(
            returncode=proc.returncode,
            passed=(proc.returncode == 0 and errors == 0),
            errors_count=errors,
            warnings_count=warnings,
            diagnostics=diagnostics,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=round(elapsed_ms, 2),
        )

    def check_snippet(self, code_snippet: str) -> PyreflyResult:
        """Executes instant in-memory type checking on a raw Python code snippet.

        Parameters
        ----------
        code_snippet : str
            Python source string to type check.

        Returns
        -------
        PyreflyResult
            Parsed diagnostic result.
        """
        if not self.is_available():
            return PyreflyResult(
                returncode=-1,
                passed=False,
                errors_count=1,
                warnings_count=0,
                stderr="Pyrefly executable not found.",
            )

        cmd = [self.executable, "snippet", "--color", "never", code_snippet]
        t0 = time.perf_counter()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        diagnostics = self.parse_diagnostics(proc.stdout + "\n" + proc.stderr)
        errors = sum(1 for d in diagnostics if d.severity == "ERROR")
        warnings = sum(1 for d in diagnostics if d.severity == "WARNING")

        return PyreflyResult(
            returncode=proc.returncode,
            passed=(proc.returncode == 0 and errors == 0),
            errors_count=errors,
            warnings_count=warnings,
            diagnostics=diagnostics,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=round(elapsed_ms, 2),
        )

    def parse_diagnostics(self, output: str) -> list[PyreflyDiagnostic]:
        """Parses Rust-style compiler error output from Pyrefly into structured diagnostics."""
        diagnostics: list[PyreflyDiagnostic] = []
        if not output:
            return diagnostics

        blocks = re.split(r"(?=(?:ERROR|WARNING)\s+)", output)
        for block in blocks:
            match = self.DIAGNOSTIC_HEADER_PATTERN.search(block)
            if not match:
                continue

            severity = match.group("severity").strip()
            message = " ".join(match.group("message").split())
            code = match.group("code").strip()
            file_path = match.group("file").strip()
            line = int(match.group("line"))
            col = int(match.group("col"))

            # Extract offending line from snippet block
            offending_code = None
            code_line_match = re.search(r"\|\s*\d+\s*\|\s*(.*)", block)
            if code_line_match:
                offending_code = code_line_match.group(1).strip()

            # Extract actionable compiler suggestion
            suggestion = None
            sugg_match = self.SUGGESTION_PATTERN.search(block)
            if sugg_match:
                suggestion = sugg_match.group("hint").strip()

            diagnostics.append(
                PyreflyDiagnostic(
                    file=file_path,
                    line=line,
                    column=col,
                    severity=severity,
                    error_code=code,
                    message=message,
                    offending_code=offending_code,
                    suggestion=suggestion,
                )
            )

        return diagnostics

    def generate_remediation_prompt(self, diagnostic: PyreflyDiagnostic) -> str:
        """Constructs an unambiguous, deterministic prompt for agentic self-repair.

        Parameters
        ----------
        diagnostic : PyreflyDiagnostic
            The compiler diagnostic to remediate.

        Returns
        -------
        str
            A structured instruction prompting the agent or verifier to fix the type mismatch.
        """
        lines = [
            f"Pyrefly Type Error in {diagnostic.file}:{diagnostic.line}:{diagnostic.column} [{diagnostic.error_code}]:",
            f"Message: {diagnostic.message}",
        ]
        if diagnostic.offending_code:
            lines.append(f"Offending Code: {diagnostic.offending_code}")
        if diagnostic.suggestion:
            lines.append(f"Compiler Actionable Suggestion: {diagnostic.suggestion}")
            lines.append(
                "Instruction: Apply the exact compiler recommendation to narrow the type or fix parameter annotations."
            )
        else:
            lines.append(
                "Instruction: Correct the type signature or narrow the type with runtime type checks."
            )
        return "\n".join(lines)
