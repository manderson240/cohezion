"""Popcorn CLI integration for submitting kernels to AMD MI355X leaderboards.

Wraps popcorn-cli subprocess calls with structured output parsing.
Handles test/benchmark/leaderboard modes, timeouts, and rate limiting.
"""
from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)

POPCORN_CLI = Path.home() / ".local" / "bin" / "popcorn-cli"
LUMA_DIR = Path(__file__).parent.parent  # luma_speedrun/

# Kernel short name → (leaderboard name, submission directory)
KERNEL_MAP: dict[str, tuple[str, str]] = {
    "gemm": ("amd-mxfp4-mm", "amd-mxfp4-mm"),
    "moe": ("amd-moe-mxfp4", "amd-moe-mxfp4"),
    "mla": ("amd-mixed-mla", "amd-mixed-mla"),
}

# Timeout per mode (seconds). JIT builds can take 230s+ for MoE.
MODE_TIMEOUTS: dict[str, int] = {
    "test": 720,
    "benchmark": 720,
    "leaderboard": 720,
}


@dataclass
class SubmitResult:
    """Structured result from a popcorn-cli submission."""
    passed: bool
    score: float  # geomean µs for benchmark, 0.0 for test-only
    mode: str
    kernel: str
    stderr: str  # full stderr (contains discovery probe output)
    stdout: str  # full stdout
    error: str  # error message if failed
    elapsed_s: float  # wall clock time

    @property
    def discovered_kernels(self) -> list[str]:
        """Extract FOUND lines from stderr (probe discovery output)."""
        return [line for line in self.stderr.splitlines() if line.startswith("FOUND ")]


def submit(
    kernel: str,
    submission_path: str | Path,
    mode: str = "test",
) -> SubmitResult:
    """Submit a kernel to popcorn-cli and parse the result.

    Args:
        kernel: Short name ("gemm", "moe", "mla") or full leaderboard name
        submission_path: Path to submission.py file
        mode: "test", "benchmark", or "leaderboard"

    Returns:
        SubmitResult with parsed output
    """
    # Resolve leaderboard name
    if kernel in KERNEL_MAP:
        leaderboard, _ = KERNEL_MAP[kernel]
    else:
        leaderboard = kernel  # assume it's already a full leaderboard name

    submission_path = Path(submission_path)
    if not submission_path.exists():
        return SubmitResult(
            passed=False, score=0.0, mode=mode, kernel=kernel,
            stderr="", stdout="", error=f"File not found: {submission_path}",
            elapsed_s=0.0,
        )

    cmd = [
        str(POPCORN_CLI), "submit",
        "--no-tui",
        "--mode", mode,
        "--gpu", "MI355X",
        "--leaderboard", leaderboard,
        str(submission_path),
    ]

    timeout = MODE_TIMEOUTS.get(mode, 720)
    logger.info("Submitting: %s", " ".join(cmd))
    start = time.monotonic()

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start
        stdout, stderr = proc.stdout, proc.stderr
        logger.debug("stdout:\n%s", stdout[:2000])
        logger.debug("stderr:\n%s", stderr[:2000])
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return SubmitResult(
            passed=False, score=0.0, mode=mode, kernel=kernel,
            stderr="", stdout="", error=f"Timeout after {timeout}s",
            elapsed_s=elapsed,
        )
    except FileNotFoundError:
        return SubmitResult(
            passed=False, score=0.0, mode=mode, kernel=kernel,
            stderr="", stdout="",
            error=f"popcorn-cli not found at {POPCORN_CLI}",
            elapsed_s=0.0,
        )

    passed = _parse_passed(stdout, stderr, mode)
    score = _parse_score(stdout, stderr, mode)
    error = _parse_error(stdout, stderr, proc.returncode)

    return SubmitResult(
        passed=passed, score=score, mode=mode, kernel=kernel,
        stderr=stderr, stdout=stdout, error=error,
        elapsed_s=elapsed,
    )


def _parse_passed(stdout: str, stderr: str, mode: str) -> bool:
    """Determine if submission passed correctness checks."""
    combined = stdout + "\n" + stderr
    # Explicit pass indicators
    if re.search(r"(?i)(correctness|test).*pass", combined):
        return True
    if re.search(r"(?i)all\s+tests?\s+passed", combined):
        return True
    # Explicit fail indicators
    if re.search(r"(?i)(correctness|test).*fail", combined):
        return False
    if re.search(r"(?i)mismatch|incorrect|assertion", combined):
        return False
    # For benchmark mode, having a score means it passed
    if mode == "benchmark" and _parse_score(stdout, stderr, mode) > 0:
        return True
    return False


def _parse_score(stdout: str, stderr: str, mode: str) -> float:
    """Extract timing score (geomean µs) from output."""
    combined = stdout + "\n" + stderr
    # Look for geomean patterns
    for pattern in [
        r"geomean[:\s]+([0-9.]+)\s*[µu]s",
        r"geometric\s+mean[:\s]+([0-9.]+)\s*[µu]s",
        r"score[:\s]+([0-9.]+)\s*[µu]s",
        r"benchmark[:\s]+([0-9.]+)\s*[µu]s",
        r"([0-9.]+)\s*[µu]s\s*(?:geomean|geometric)",
        # Fallback: any µs value
        r"(\d+\.\d+)\s*[µu]s",
    ]:
        m = re.search(pattern, combined, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return 0.0


def _parse_error(stdout: str, stderr: str, returncode: int) -> str:
    """Extract error message from failed submission."""
    if returncode == 0:
        return ""
    combined = stdout + "\n" + stderr
    # Look for common error patterns
    for pattern in [
        r"(?i)error:\s*(.+)",
        r"(?i)traceback.*\n.*Error:\s*(.+)",
        r"(?i)(ModuleNotFoundError.+)",
        r"(?i)(ImportError.+)",
        r"(?i)(RuntimeError.+)",
    ]:
        m = re.search(pattern, combined)
        if m:
            return m.group(1).strip()[:500]
    if returncode != 0:
        return f"Exit code {returncode}"
    return ""


def get_submission_path(kernel: str, filename: str = "submission.py") -> Path:
    """Get the path to a submission file for a kernel."""
    if kernel in KERNEL_MAP:
        _, dirname = KERNEL_MAP[kernel]
    else:
        dirname = kernel
    return LUMA_DIR / dirname / filename


def write_submission(kernel: str, code: str, filename: str = "submission_candidate.py") -> Path:
    """Write generated code to a submission file."""
    path = get_submission_path(kernel, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code)
    logger.info("Wrote %d bytes to %s", len(code), path)
    return path
