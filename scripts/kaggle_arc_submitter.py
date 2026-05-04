#!/usr/bin/env python3
"""
Kaggle ARCPrize Submission Bridge

Builds a Kaggle kernel from a local ARC solver variant, pushes it,
watches execution, and returns the leaderboard score.

Usage:
    python scripts/kaggle_arc_submitter.py --solver path/to/solver.py --competition arc-prize-2026-arc-agi-3
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
import uuid
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="[KAGGLE] %(asctime)s %(levelname)s: %(message)s")
_LOGGER = logging.getLogger("kaggle_arc")

COHEZION_ROOT = Path.home() / "dev" / "cohezion"
KAGGLE_KERNEL_DIR = Path.home() / ".cohezion-research" / "kaggle_kernels"

# Competition configs
COMPETITIONS = {
    "arc-prize-2026-arc-agi-3": {
        "ref": "arc-prize-2026-arc-agi-3",
        "metric": "accuracy",
        "direction": "maximize",
    },
    "arc-prize-2026-arc-agi-2": {
        "ref": "arc-prize-2026-arc-agi-2",
        "metric": "accuracy",
        "direction": "maximize",
    },
}


def build_kernel(solver_path: Path, kernel_name: str) -> Path:
    """Build a Kaggle kernel directory from solver code."""
    kdir = KAGGLE_KERNEL_DIR / kernel_name
    kdir.mkdir(parents=True, exist_ok=True)

    # Write solver as arc_solver.py in kernel dir
    solver_code = solver_path.read_text()
    (kdir / "arc_solver.py").write_text(solver_code)

    # Write submission builder
    submission_code = '''
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arc_solver

def main():
    # Kaggle data paths
    data_dir = Path("/kaggle/input/arc-prize-2026")
    with open(data_dir / "arc-agi_test_challenges.json") as f:
        challenges = json.load(f)

    submission = {}
    for task_id, task in sorted(challenges.items()):
        try:
            program = arc_solver.search_program(task["train"], max_depth=3, budget=5000)
            if program is not None:
                preds = []
                for test_ex in task.get("test", []):
                    pred = arc_solver.apply_program(arc_solver.deepcopy_grid(test_ex["input"]), program)
                    preds.append(pred)
                submission[task_id] = preds
        except Exception:
            submission[task_id] = []  # No prediction on error

    with open("/kaggle/working/submission.json", "w") as f:
        json.dump(submission, f)

    print("Submission written to /kaggle/working/submission.json")
    print(f"Tasks predicted: {len(submission)} / {len(challenges)}")

if __name__ == "__main__":
    main()
'''
    (kdir / "submission.py").write_text(submission_code)

    # Write kernel metadata
    metadata = {
        "id": f"manderson240/{kernel_name}",
        "title": f"ARC AutoResearch {kernel_name}",
        "code_file": "submission.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": False,
        "enable_gpu": False,
        "enable_internet": False,
        "dataset_sources": [
            "fchollet/arc-prize-2024",  # ARC data
        ],
        "competition_sources": [
            "arc-prize-2026-arc-agi-3",
        ],
    }
    (kdir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))

    return kdir


def push_kernel(kernel_dir: Path) -> str:
    """Push kernel to Kaggle, return kernel ID."""
    proc = subprocess.run(
        ["kaggle", "kernels", "push", "-p", str(kernel_dir)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        _LOGGER.error(f"Push failed: {proc.stderr}")
        return ""

    # Extract kernel ID from output
    m = re.search(r"([\w-]+/[\w-]+)", proc.stdout)
    if m:
        return m.group(1)

    # Fallback: use metadata id
    meta = json.loads((kernel_dir / "kernel-metadata.json").read_text())
    return meta.get("id", "")


def wait_for_score(kernel_id: str, competition: str, timeout: int = 600) -> tuple[float, str]:
    """Poll Kaggle for kernel completion and score."""
    start = time.time()
    while time.time() - start < timeout:
        proc = subprocess.run(
            ["kaggle", "kernels", "status", kernel_id],
            capture_output=True,
            text=True,
        )
        status = proc.stdout.lower()

        if "complete" in status and "error" not in status:
            # Kernel finished — check submissions
            time.sleep(10)  # Let leaderboard update
            sub_proc = subprocess.run(
                ["kaggle", "competitions", "submissions", "-c", competition],
                capture_output=True,
                text=True,
            )
            lines = sub_proc.stdout.strip().split("\n")
            if len(lines) > 1:
                # Last submission = most recent
                last = lines[-1]
                # Parse score from table
                parts = [p.strip() for p in last.split() if p.strip()]
                try:
                    # Score is typically column 5
                    score = float(parts[-2])
                    return score, "complete"
                except ValueError:
                    return 0.0, "score_parse_error"

        elif "error" in status:
            return 0.0, f"error: {status}"

        elif "cancel" in status:
            return 0.0, "cancelled"

        time.sleep(30)

    return 0.0, "timeout"


def submit_and_score(solver_path: Path, competition: str = "arc-prize-2026-arc-agi-3") -> tuple[float, str, str]:
    """
    Full pipeline: build kernel, push, wait for score.

    Returns:
        (score_float, status_str, kernel_id_str)
    """
    kernel_name = f"arc-auto-{uuid.uuid4().hex[:8]}"
    _LOGGER.info(f"Building kernel: {kernel_name}")
    kdir = build_kernel(solver_path, kernel_name)

    _LOGGER.info("Pushing kernel to Kaggle...")
    kernel_id = push_kernel(kdir)
    if not kernel_id:
        return 0.0, "push_failed", ""

    _LOGGER.info(f"Kernel pushed: {kernel_id}. Waiting for execution...")
    score, status = wait_for_score(kernel_id, competition, timeout=900)
    _LOGGER.info(f"Score: {score}, Status: {status}")

    return score, status, kernel_id


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver", type=Path, required=True, help="Path to arc_solver.py variant")
    parser.add_argument("--competition", default="arc-prize-2026-arc-agi-3")
    args = parser.parse_args()

    score, status, kernel_id = submit_and_score(args.solver, args.competition)
    print(f"SCORE: {score}")
    print(f"STATUS: {status}")
    print(f"KERNEL: {kernel_id}")


if __name__ == "__main__":
    main()
