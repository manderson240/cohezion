"""Popcorn-cli wrapper for kernel evaluation.

Handles test/benchmark/leaderboard submission modes,
output parsing for per-shape timings, and retry logic.
"""

from __future__ import annotations

import math
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


POPCORN_CLI = Path.home() / ".local" / "bin" / "popcorn-cli"
TIMEOUT_SECONDS = 720  # 12 min cap

# Leaderboard names from popcorn-cli skill
LEADERBOARD_NAMES = {
    "moe": "amd-moe-mxfp4",
    "gemm": "amd-mxfp4-mm",
    "mla": "amd-mixed-mla",
}

# Kernel directory names (for submission path)
KERNEL_DIRS = {
    "moe": "moe-mxfp4",
    "gemm": "mxfp4-mm",
    "mla": "mixed-mla",
}


@dataclass
class EvalResult:
    """Result of a popcorn-cli evaluation."""

    kernel: str
    mode: str  # test | benchmark | leaderboard
    success: bool
    geomean_us: float | None = None
    per_shape_us: dict[str, float] = field(default_factory=dict)
    raw_output: str = ""
    error: str = ""
    duration_s: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kernel": self.kernel,
            "mode": self.mode,
            "success": self.success,
            "geomean_us": self.geomean_us,
            "per_shape_us": self.per_shape_us,
            "error": self.error,
            "duration_s": self.duration_s,
            "timestamp": self.timestamp,
        }


def _parse_benchmark_output(output: str) -> tuple[float | None, dict[str, float]]:
    """Parse popcorn-cli benchmark output for timings.

    Popcorn-cli benchmark format (proven from autokernel.py):
        ⏱ 19.0 ± 0.02 µs
        ⚡ 18.0 µs 🐌 23.8 µs

    Tries multiple strategies in order:
    1. Explicit "geomean" or "geometric mean" line
    2. ⏱ timer emoji lines (popcorn-cli per-shape medians)
    3. "median:" style lines
    4. Tabular format fallback

    Returns (geomean_us, {shape_key: time_us})
    """
    per_shape: dict[str, float] = {}
    geomean: float | None = None

    # Strategy 1: Explicit geomean line
    for line in output.split("\n"):
        lower = line.lower()
        if "geomean" in lower or "geometric" in lower:
            match = re.search(r"(\d+\.?\d*)\s*(?:us|µs|microsec)", line, re.IGNORECASE)
            if match:
                geomean = float(match.group(1))
                break
            match = re.search(r":\s*(\d+\.?\d*)", line)
            if match:
                geomean = float(match.group(1))
                break

    # Strategy 2: Parse popcorn-cli timer emoji lines: "⏱ 19.0 ± 0.02 µs"
    medians: list[float] = []
    for line in output.split("\n"):
        match = re.search(r"⏱\s*(\d+\.?\d*)\s*±", line)
        if match:
            medians.append(float(match.group(1)))
            per_shape[f"shape_{len(per_shape)}"] = float(match.group(1))

    if medians and geomean is None:
        log_sum = sum(math.log(m) for m in medians)
        geomean = round(math.exp(log_sum / len(medians)), 2)

    # Strategy 3: Parse "median:" style lines
    if not medians:
        for line in output.split("\n"):
            lower = line.lower()
            if "median" in lower:
                match = re.search(r"median[:\s=]+(\d+\.?\d*)\s*(?:us|µs)?", lower)
                if match:
                    medians.append(float(match.group(1)))
                    per_shape[f"shape_{len(per_shape)}"] = float(match.group(1))

        if medians and geomean is None:
            log_sum = sum(math.log(m) for m in medians)
            geomean = round(math.exp(log_sum / len(medians)), 2)

    # Strategy 4: Tabular format fallback: "  4  2880   512   8.198"
    if not medians:
        for line in output.split("\n"):
            tab_match = re.search(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+([0-9.]+)\s*$", line)
            if tab_match:
                shape_key = f"{tab_match.group(1)}_{tab_match.group(2)}_{tab_match.group(3)}"
                per_shape[shape_key] = float(tab_match.group(4))

    return geomean, per_shape


def _run_popcorn(
    submission_path: Path,
    kernel: str,
    mode: str,
    timeout: int = TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess:
    """Run popcorn-cli submit command."""
    leaderboard = LEADERBOARD_NAMES[kernel]
    cmd = [
        str(POPCORN_CLI),
        "submit",
        "--no-tui",
        "--mode",
        mode,
        "--gpu",
        "MI355X",
        "--leaderboard",
        leaderboard,
        str(submission_path),
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def evaluate(
    submission_path: Path,
    kernel: str,
    mode: str = "test",
    retry_on_artifact_failure: bool = True,
) -> EvalResult:
    """Submit a kernel to popcorn-cli and parse results.

    Args:
        submission_path: Path to the submission.py file
        kernel: "moe", "gemm", or "mla"
        mode: "test", "benchmark", or "leaderboard"
        retry_on_artifact_failure: Retry once on transient artifact errors

    Returns:
        EvalResult with parsed timings or error info
    """
    if kernel not in LEADERBOARD_NAMES:
        raise ValueError(f"Unknown kernel: {kernel}")

    start = time.time()

    try:
        result = _run_popcorn(submission_path, kernel, mode)
        output = result.stdout + "\n" + result.stderr
        duration = time.time() - start

        # Check for transient artifact failures
        if retry_on_artifact_failure and "artifact" in output.lower() and result.returncode != 0:
            time.sleep(5)
            result = _run_popcorn(submission_path, kernel, mode)
            output = result.stdout + "\n" + result.stderr
            duration = time.time() - start

        if result.returncode != 0:
            # Check for correctness errors
            if "mismatch" in output.lower() or "incorrect" in output.lower():
                return EvalResult(
                    kernel=kernel,
                    mode=mode,
                    success=False,
                    raw_output=output,
                    error="Correctness check failed",
                    duration_s=duration,
                )
            return EvalResult(
                kernel=kernel,
                mode=mode,
                success=False,
                raw_output=output,
                error=f"Exit code {result.returncode}",
                duration_s=duration,
            )

        geomean, per_shape = _parse_benchmark_output(output)
        return EvalResult(
            kernel=kernel,
            mode=mode,
            success=True,
            geomean_us=geomean,
            per_shape_us=per_shape,
            raw_output=output,
            duration_s=duration,
        )

    except subprocess.TimeoutExpired:
        return EvalResult(
            kernel=kernel,
            mode=mode,
            success=False,
            error=f"Timeout after {TIMEOUT_SECONDS}s",
            duration_s=time.time() - start,
        )
    except Exception as e:
        return EvalResult(
            kernel=kernel,
            mode=mode,
            success=False,
            error=str(e),
            duration_s=time.time() - start,
        )


def test_then_benchmark(
    submission_path: Path,
    kernel: str,
) -> EvalResult:
    """Run test first, then benchmark if test passes."""
    test_result = evaluate(submission_path, kernel, mode="test")
    if not test_result.success:
        return test_result
    return evaluate(submission_path, kernel, mode="benchmark")
