"""Kaggle MCP Server — expose Kaggle CLI operations as MCP tools.

A stdio FastMCP bridge for Kaggle competition workflows: kernel management,
competition submission (kernel-mode and file-mode), submission monitoring
(limits, episodes, replay, agent logs), competition pages, leaderboard
queries, GPU quota, and benchmark tasks (new in kaggle 2.2.2).

Tools:
    kaggle_kernel_status / kaggle_kernel_push / kaggle_kernel_logs
    kaggle_competition_submit              kernel-mode submit (-k)
    kaggle_competition_submit_file         file-mode submit (-f), simulation comps
    kaggle_competition_submission_limits   remaining daily submissions
    kaggle_competition_episodes            episodes of one submission
    kaggle_competition_replay              download an episode replay
    kaggle_competition_logs                download one agent's episode logs
    kaggle_competition_pages               list / read competition pages
    kaggle_watch_submission                poll until a submission leaves PENDING
    kaggle_competition_leaderboard / kaggle_competition_submissions
    kaggle_quota / kaggle_config_view
    kaggle_benchmark_*                     benchmark tasks (kaggle 2.2.2+)

Environment:
    KAGGLE_CLI      Path to kaggle binary (default: repo .venv/bin/kaggle, then PATH)
    MCP_TRANSPORT   "stdio" or "http" (default: stdio)
    MCP_PORT        HTTP server port when transport=http (default: 8363)

Usage:
    uv run python -m cohezion.mcp.kaggle_server_mcp
"""

from __future__ import annotations

import csv
import io
import logging
import os
import subprocess
import sys
import time
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
    return _run(
        [
            "competitions",
            "submit",
            competition,
            "-k",
            kernel_id,
            "-v",
            str(version),
            "-f",
            "submission.zip",
            "-m",
            message,
        ],
        timeout=60,
    )


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


# ── Competitions: file-mode submit + simulation monitoring ────────────────────

# tmpfs roots: a submission source under /tmp was lost on 2026-08-28. Refuse them.
_TMPFS_ROOTS = (Path("/tmp"),)
_WATCH_POLL_SECONDS = 30
# MCP clients time out a sync tool call at ~60 s: keep a single watch short and let
# the caller re-invoke (long watches = repeated short calls).
_WATCH_DEFAULT_MINUTES = 1.0
_WATCH_MAX_MINUTES = 1.5
_WATCH_SLACK_SECONDS = 10
_WATCH_RUN_TIMEOUT = 120


def _refuse_tmpfs(path: Path) -> str | None:
    """Return an error string when *path* lives under a tmpfs root, else None."""
    for root in _TMPFS_ROOTS:
        if path == root or path.is_relative_to(root):
            return (
                f"refusing submission source under {root}: tmpfs is wiped on reboot "
                f"(lost a submission source 2026-08-28). Move {path} to a durable location."
            )
    return None


def _refuse_flag_like(name: str, value: str) -> str | None:
    """Return an error when *value* is a single token starting with '-' (would parse as a flag)."""
    token = value.strip()
    if token.startswith("-") and len(token.split()) == 1:
        return (
            f"{name} {token!r} looks like a CLI flag; pass a plain value (e.g. prefix it with text)"
        )
    return None


def _submission_status(csv_text: str, submission_ref: str) -> tuple[str, str, str | None]:
    """Locate *submission_ref* in `competitions submissions --csv` output.

    Returns (status_line, STATUS, error). status_line is the matching row
    re-serialised with csv.writer (quoted descriptions with commas survive);
    STATUS is the upper-cased ``status`` column. When the ref is not listed all
    three are empty/None. When the header has no ``status`` column, error is set
    rather than guessing from the raw line.
    """
    rows = list(csv.reader(io.StringIO(csv_text)))
    if not rows:
        return "", "", None
    header = [h.strip().lower() for h in rows[0]]
    status_idx = header.index("status") if "status" in header else None
    for row in rows[1:]:
        if not row or row[0].strip() != submission_ref:
            continue
        buf = io.StringIO()
        csv.writer(buf, lineterminator="").writerow(row)
        line = buf.getvalue()
        if status_idx is None or status_idx >= len(row):
            return line, "", "status column missing from `competitions submissions --csv` output"
        return line, row[status_idx].strip().upper(), None
    return "", "", None


def _bounded_timeout(remaining_seconds: float) -> int:
    """Shrink a `_run` timeout so the whole watch finishes by deadline + slack."""
    return max(1, int(min(_WATCH_RUN_TIMEOUT, remaining_seconds + _WATCH_SLACK_SECONDS)))


@app.tool()
def kaggle_competition_submit_file(
    competition: str, file_path: str, message: str
) -> dict[str, Any]:
    """Submit a local FILE as a competition entry (file-mode, e.g. simulation comps).

    Use this instead of kaggle_competition_submit when the competition takes an
    uploaded artifact (submission.tar.gz, .py agent, .csv) rather than a kernel.

    Args:
        competition: Competition slug (positional in kaggle 2.2.x — no -c flag)
        file_path:   Absolute path to the file to upload; must exist, be a regular
                     file, and NOT live under /tmp (tmpfs is wiped on reboot)
        message:     Submission description shown on the submissions page
    """
    if err := _refuse_flag_like("message", message):
        return {"error": err, "ok": False}
    path = Path(file_path).expanduser().resolve()
    if err := _refuse_tmpfs(path):
        return {"error": err, "ok": False}
    if not path.is_file():
        return {"error": f"submission file not found or not a regular file: {path}", "ok": False}
    return _run(
        ["competitions", "submit", competition, "-f", str(path), "-m", message],
        timeout=300,
    )


@app.tool()
def kaggle_competition_submission_limits(competition: str) -> dict[str, Any]:
    """Show remaining daily submission allowance for a competition.

    Args:
        competition: Competition slug
    """
    return _run(["competitions", "submission-limits", "-c", competition], timeout=30)


@app.tool()
def kaggle_competition_episodes(submission_id: str) -> dict[str, Any]:
    """List simulation episodes (validation + ladder games) for one submission.

    Args:
        submission_id: Numeric submission reference as shown by kaggle_competition_submissions
    """
    return _run(["competitions", "episodes", submission_id], timeout=60)


@app.tool()
def kaggle_competition_replay(episode_id: str, out_dir: str) -> dict[str, Any]:
    """Download the replay JSON for a simulation episode.

    Args:
        episode_id: Numeric episode id as shown by kaggle_competition_episodes
        out_dir:    Local directory to save the replay into
    """
    return _run(["competitions", "replay", episode_id, "-p", out_dir], timeout=120)


@app.tool()
def kaggle_competition_logs(episode_id: str, agent_index: int, out_dir: str) -> dict[str, Any]:
    """Download one agent's stdout/stderr logs for a simulation episode.

    Args:
        episode_id:  Numeric episode id
        agent_index: Agent slot within the episode (0 = first agent)
        out_dir:     Local directory to save the logs into
    """
    return _run(
        ["competitions", "logs", episode_id, str(agent_index), "-p", out_dir],
        timeout=120,
    )


@app.tool()
def kaggle_competition_pages(competition: str, page_name: str = "") -> dict[str, Any]:
    """List a competition's pages (Overview, Rules, Evaluation, ...) or read one.

    Args:
        competition: Competition slug
        page_name:   When given, fetch that page's content instead of listing pages
    """
    args = ["competitions", "pages", "-c", competition]
    if page_name:
        if err := _refuse_flag_like("page_name", page_name):
            return {"error": err, "ok": False}
        args += ["--content", "--page-name", page_name]
    return _run(args, timeout=60)


@app.tool()
def kaggle_watch_submission(
    competition: str,
    submission_ref: str,
    max_minutes: float = _WATCH_DEFAULT_MINUTES,
    allow_long: bool = False,
) -> dict[str, Any]:
    """Poll a submission every 30 s until it leaves PENDING, then fetch its episodes.

    The next-day status check nobody ran in June: a simulation submission can sit
    PENDING for minutes and then ERROR on validation (illegal deck, bad agent).

    This is a SYNC tool call and MCP clients time out at ~60 s, so one call is
    short by design: long watches = repeated short calls. On timeout the result
    carries ``next_poll_after_s`` — re-invoke after that many seconds. Total
    wall-clock is bounded by max_minutes + 10 s (poll timeouts shrink to fit).

    Args:
        competition:    Competition slug
        submission_ref: Numeric submission reference (first CSV column)
        max_minutes:    Give up after this many minutes (default 1.0, hard-capped
                        at 1.5 unless allow_long=True)
        allow_long:     Lift the 1.5-minute cap (only for clients with long tool timeouts)

    Returns:
        {status_line, status, episodes, ok, timed_out[, next_poll_after_s][, error]}
        — ok is True only when the final status is COMPLETE; episodes is None when
        the watch timed out.
    """
    if not allow_long:
        max_minutes = min(max_minutes, _WATCH_MAX_MINUTES)
    deadline = time.monotonic() + max_minutes * 60
    line, status = "", ""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        listing = _run(
            ["competitions", "submissions", "-c", competition, "--csv"],
            timeout=_bounded_timeout(remaining),
        )
        line, status, err = _submission_status(listing.get("stdout", ""), submission_ref)
        if err:
            return {
                "status_line": line,
                "status": status,
                "episodes": None,
                "ok": False,
                "timed_out": False,
                "error": err,
            }
        if line and "PENDING" not in status:
            break
        if time.monotonic() + _WATCH_POLL_SECONDS >= deadline:
            break
        time.sleep(_WATCH_POLL_SECONDS)

    if not line or "PENDING" in status:
        return {
            "status_line": line or "not found",
            "status": "PENDING",
            "episodes": None,
            "ok": False,
            "timed_out": True,
            "next_poll_after_s": _WATCH_POLL_SECONDS,
        }
    episodes = _run(
        ["competitions", "episodes", submission_ref],
        timeout=_bounded_timeout(deadline - time.monotonic()),
    )
    return {
        "status_line": line,
        "status": status,
        "episodes": episodes,
        "ok": "COMPLETE" in status and "ERROR" not in status,
        "timed_out": False,
    }


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
