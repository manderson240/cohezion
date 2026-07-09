"""Kaggle MCP Server — expose Kaggle CLI operations as MCP tools.

A stdio FastMCP bridge for Kaggle competition workflows: kernel management,
competition submission, leaderboard queries, GPU quota, and benchmark tasks
(new in kaggle 2.2.2).

Environment:
    KAGGLE_CLI      Path to kaggle binary (default: searches PATH then venv)
    MCP_TRANSPORT   "stdio" or "http" (default: stdio)
    MCP_PORT        HTTP server port when transport=http (default: 8363)

Usage:
    uv run python -m cohezion.mcp.kaggle_server_mcp
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("kaggle-mcp")

app = FastMCP("kaggle")

_VENV_KAGGLE = Path(__file__).parents[3] / ".venv" / "bin" / "kaggle"


def _kaggle_bin() -> str:
    """Resolve kaggle binary: env override → venv → PATH."""
    if override := os.getenv("KAGGLE_CLI"):
        return override
    if _VENV_KAGGLE.exists():
        return str(_VENV_KAGGLE)
    return "kaggle"


def _run(args: list[str], *, timeout: int = 60) -> dict[str, Any]:
    """Run kaggle CLI and return {stdout, stderr, returncode}."""
    cmd = [_kaggle_bin(), *args]
    logger.info("kaggle %s", " ".join(args))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "ok": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"kaggle command timed out after {timeout}s", "ok": False}
    except FileNotFoundError:
        return {"error": "kaggle CLI not found — install via: uv tool install kaggle", "ok": False}


# ── Kernels ───────────────────────────────────────────────────────────────────

@app.tool()
def kaggle_kernel_status(kernel_id: str) -> dict[str, Any]:
    """Check the run status of a Kaggle kernel.

    Args:
        kernel_id: Kernel identifier in the form username/kernel-slug
                   (e.g. manderson240/neurogolf-baseline-20260623-1030)
    """
    return _run(["kernels", "status", kernel_id])


@app.tool()
def kaggle_kernel_push(path: str) -> dict[str, Any]:
    """Push a kernel notebook directory to Kaggle.

    The directory must contain a kernel-metadata.json file.

    Args:
        path: Absolute path to the kernel directory containing kernel-metadata.json
    """
    return _run(["kernels", "push", "-p", path], timeout=120)


@app.tool()
def kaggle_kernel_logs(kernel_id: str) -> dict[str, Any]:
    """Fetch execution logs for a running or completed kernel.

    Args:
        kernel_id: Kernel identifier in the form username/kernel-slug
    """
    return _run(["kernels", "logs", kernel_id], timeout=30)


# ── Competitions ──────────────────────────────────────────────────────────────

@app.tool()
def kaggle_competition_submit(
    competition: str,
    kernel_id: str,
    message: str,
    version: int = 1,
) -> dict[str, Any]:
    """Submit a kernel output as a competition entry.

    Args:
        competition: Competition slug (e.g. neurogolf-2026, nvidia-nemotron-model-reasoning-challenge)
        kernel_id:   Kernel identifier in the form username/kernel-slug
        message:     Submission description shown on the leaderboard
        version:     Kernel output version number to submit (default: 1)
    """
    return _run([
        "competitions", "submit", competition,
        "-k", kernel_id,
        "-v", str(version),
        "-f", "submission.zip",
        "-m", message,
    ], timeout=60)


@app.tool()
def kaggle_competition_leaderboard(competition: str, show_all: bool = False) -> dict[str, Any]:
    """Fetch the current leaderboard for a competition.

    Args:
        competition: Competition slug (e.g. neurogolf-2026)
        show_all:    Return all entries, not just the first page
    """
    args = ["competitions", "leaderboard", competition, "--show"]
    if show_all:
        args.append("--all")
    return _run(args, timeout=30)


@app.tool()
def kaggle_competition_submissions(competition: str) -> dict[str, Any]:
    """List your own submissions for a competition.

    Args:
        competition: Competition slug
    """
    return _run(["competitions", "submissions", competition], timeout=30)


# ── Quota & Config ────────────────────────────────────────────────────────────

@app.tool()
def kaggle_quota() -> dict[str, Any]:
    """Show your remaining weekly GPU and TPU accelerator quota."""
    return _run(["quota"])


@app.tool()
def kaggle_config_view() -> dict[str, Any]:
    """Show current Kaggle CLI configuration (username, key path, etc.)."""
    return _run(["config", "view"])


# ── Benchmark Tasks (new in kaggle 2.2.2) ─────────────────────────────────────

@app.tool()
def kaggle_benchmark_tasks_list(
    status: str = "",
    name_regex: str = "",
) -> dict[str, Any]:
    """List Kaggle benchmark tasks owned by the current user.

    Benchmark tasks are standardized evaluation pipelines distinct from
    competitions — useful for ARC-AGI and NeuroGolf custom eval loops.

    Args:
        status:     Filter by status: queued, running, completed, errored (empty = all)
        name_regex: Filter task names by regex pattern
    """
    args = ["benchmarks", "tasks", "list", "--all"]
    if status:
        args += ["--status", status]
    if name_regex:
        args += ["--name-regex", name_regex]
    return _run(args, timeout=30)


@app.tool()
def kaggle_benchmark_tasks_status(task_ref: str) -> dict[str, Any]:
    """Show details and per-model run status for a benchmark task.

    Args:
        task_ref: Task reference (name or ID as shown by benchmark_tasks_list)
    """
    return _run(["benchmarks", "tasks", "status", task_ref], timeout=30)


@app.tool()
def kaggle_benchmark_tasks_run(task_ref: str, model_handle: str) -> dict[str, Any]:
    """Run a benchmark task against a specific model.

    Args:
        task_ref:     Task reference (name or ID)
        model_handle: Model handle to evaluate (e.g. google/gemma/transformers/gemma-2-2b-it/2)
    """
    return _run(["benchmarks", "tasks", "run", task_ref, "--model", model_handle], timeout=60)


@app.tool()
def kaggle_benchmark_models() -> dict[str, Any]:
    """List models available for benchmark evaluation."""
    return _run(["benchmarks", "tasks", "models"], timeout=30)


@app.tool()
def kaggle_benchmark_tasks_download(task_ref: str, output_path: str = ".") -> dict[str, Any]:
    """Download output files for a completed benchmark run.

    Args:
        task_ref:    Task reference
        output_path: Local directory to save output files (default: current dir)
    """
    return _run(["benchmarks", "tasks", "download", task_ref, "-p", output_path], timeout=120)


@app.tool()
def kaggle_benchmark_tasks_logs(task_ref: str) -> dict[str, Any]:
    """Fetch execution logs for a benchmark task run.

    Args:
        task_ref: Task reference
    """
    return _run(["benchmarks", "tasks", "logs", task_ref], timeout=30)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        port = int(os.getenv("MCP_PORT", "8363"))
        app.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        app.run(transport="stdio")
