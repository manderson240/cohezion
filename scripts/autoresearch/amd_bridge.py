#!/usr/bin/env python3
"""Bridge between andyluo7/autoresearch (AMD fork) and Cohezion compound engineering.

Wraps the autoresearch experiment loop with Cohezion tracking:
- Logs each experiment to Cohezion's compound metrics
- Tracks via Entire checkpoints (commits trigger checkpoints)
- Feeds val_bpb improvements into the compound knowledge base
- Follows the program.md protocol (5-min fixed time budget, modify train.py, iterate)

Usage:
    # Set up a new experiment run
    python scripts/autoresearch/amd_bridge.py setup --tag apr9

    # Run a single experiment (for agent use)
    python scripts/autoresearch/amd_bridge.py run --repo ~/dev/autoresearch-amd

    # Parse results from run.log
    python scripts/autoresearch/amd_bridge.py parse --log ~/dev/autoresearch-amd/run.log

Requires: andyluo7/autoresearch cloned at ~/dev/autoresearch-amd
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

AUTORESEARCH_DIR = Path.home() / "dev" / "autoresearch-amd"
COHEZION_DIR = Path.home() / "dev" / "cohezion"
RESULTS_FILE = "results.tsv"


@dataclass
class ExperimentResult:
    """Result from a single autoresearch experiment."""

    commit: str
    val_bpb: float
    memory_gb: float
    status: str  # keep, discard, crash
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    duration_seconds: float = 0.0
    mfu_percent: float = 0.0
    total_tokens_m: float = 0.0
    num_params_m: float = 0.0


def parse_run_log(log_path: Path) -> dict[str, float]:
    """Parse the summary block from train.py's run.log output."""
    metrics: dict[str, float] = {}
    if not log_path.exists():
        return metrics

    text = log_path.read_text()
    # Parse key: value pairs from the summary block
    patterns = {
        "val_bpb": r"^val_bpb:\s+([\d.]+)",
        "training_seconds": r"^training_seconds:\s+([\d.]+)",
        "total_seconds": r"^total_seconds:\s+([\d.]+)",
        "peak_vram_mb": r"^peak_vram_mb:\s+([\d.]+)",
        "mfu_percent": r"^mfu_percent:\s+([\d.]+)",
        "total_tokens_M": r"^total_tokens_M:\s+([\d.]+)",
        "num_steps": r"^num_steps:\s+(\d+)",
        "num_params_M": r"^num_params_M:\s+([\d.]+)",
        "depth": r"^depth:\s+(\d+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            metrics[key] = float(match.group(1))

    return metrics


def log_to_tsv(result: ExperimentResult, repo_dir: Path) -> None:
    """Append experiment result to results.tsv (following program.md format)."""
    tsv_path = repo_dir / RESULTS_FILE
    if not tsv_path.exists():
        tsv_path.write_text("commit\tval_bpb\tmemory_gb\tstatus\tdescription\n")

    line = f"{result.commit}\t{result.val_bpb:.6f}\t{result.memory_gb:.1f}\t{result.status}\t{result.description}\n"
    with open(tsv_path, "a") as f:
        f.write(line)
    logger.info(f"Logged to {tsv_path}: {result.status} val_bpb={result.val_bpb:.6f}")


def log_to_cohezion(result: ExperimentResult) -> None:
    """Append experiment result to Cohezion's autoresearch.jsonl for compound learning."""
    jsonl_path = COHEZION_DIR / "autoresearch.jsonl"
    entry = {
        "type": "autoresearch_experiment",
        "source": "andyluo7/autoresearch-amd",
        **asdict(result),
    }
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info(f"Logged to {jsonl_path}")


def get_current_commit(repo_dir: Path) -> str:
    """Get short commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_dir,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def setup_experiment(tag: str) -> None:
    """Set up a new experiment branch following program.md protocol."""
    branch = f"autoresearch/{tag}"
    logger.info(f"Setting up experiment branch: {branch}")

    # Check data exists
    cache_dir = Path.home() / ".cache" / "autoresearch"
    if not cache_dir.exists():
        logger.warning(
            f"Data not found at {cache_dir}. Run: cd {AUTORESEARCH_DIR} && uv run prepare.py"
        )

    # Create branch
    subprocess.run(
        ["git", "checkout", "-b", branch],
        cwd=AUTORESEARCH_DIR,
        check=True,
    )

    # Initialize results.tsv
    tsv_path = AUTORESEARCH_DIR / RESULTS_FILE
    if not tsv_path.exists():
        tsv_path.write_text("commit\tval_bpb\tmemory_gb\tstatus\tdescription\n")
        logger.info(f"Initialized {tsv_path}")

    logger.info(f"Ready. Run baseline: cd {AUTORESEARCH_DIR} && uv run train.py > run.log 2>&1")


def run_experiment(repo_dir: Path, timeout: int = 600) -> dict[str, float]:
    """Run a single autoresearch experiment (5-min time budget + startup overhead)."""
    log_path = repo_dir / "run.log"
    logger.info(f"Running experiment (timeout={timeout}s)...")

    start = time.time()
    try:
        with open(log_path, "w") as log_file:
            subprocess.run(
                ["uv", "run", "train.py"],
                cwd=repo_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
    except subprocess.TimeoutExpired:
        logger.warning(f"Experiment timed out after {timeout}s")
        return {}

    elapsed = time.time() - start
    logger.info(f"Experiment finished in {elapsed:.1f}s")

    metrics = parse_run_log(log_path)
    if metrics:
        logger.info(
            f"val_bpb={metrics.get('val_bpb', 'N/A')}, "
            f"peak_vram={metrics.get('peak_vram_mb', 'N/A')}MB"
        )
    else:
        logger.error("No metrics found — experiment likely crashed")
        # Show tail of log
        text = log_path.read_text()
        tail = "\n".join(text.strip().splitlines()[-20:])
        logger.error(f"Last 20 lines:\n{tail}")

    return metrics


def parse_only(log_path: Path) -> None:
    """Parse and display results from an existing run.log."""
    metrics = parse_run_log(log_path)
    if metrics:
        print(json.dumps(metrics, indent=2))
    else:
        print("No metrics found in log file.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cohezion <-> autoresearch AMD bridge")
    sub = parser.add_subparsers(dest="command")

    # setup
    setup_p = sub.add_parser("setup", help="Set up a new experiment branch")
    setup_p.add_argument("--tag", required=True, help="Experiment tag (e.g., apr9)")

    # run
    run_p = sub.add_parser("run", help="Run a single experiment")
    run_p.add_argument("--repo", type=Path, default=AUTORESEARCH_DIR)
    run_p.add_argument("--timeout", type=int, default=600)
    run_p.add_argument("--description", default="experiment")

    # parse
    parse_p = sub.add_parser("parse", help="Parse results from run.log")
    parse_p.add_argument("--log", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "setup":
        setup_experiment(args.tag)

    elif args.command == "run":
        metrics = run_experiment(args.repo, args.timeout)
        if metrics:
            commit = get_current_commit(args.repo)
            result = ExperimentResult(
                commit=commit,
                val_bpb=metrics.get("val_bpb", 0.0),
                memory_gb=metrics.get("peak_vram_mb", 0.0) / 1024,
                status="keep",  # Agent decides keep/discard
                description=args.description,
                duration_seconds=metrics.get("total_seconds", 0.0),
                mfu_percent=metrics.get("mfu_percent", 0.0),
                total_tokens_m=metrics.get("total_tokens_M", 0.0),
                num_params_m=metrics.get("num_params_M", 0.0),
            )
            log_to_tsv(result, args.repo)
            log_to_cohezion(result)

    elif args.command == "parse":
        parse_only(args.log)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
