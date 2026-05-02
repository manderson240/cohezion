"""NVIDIA Nemotron Reasoning Challenge — Submission Generator.

Generates submission.csv from test.csv using the hybrid symbolic+model solver.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from solve import solve


def generate_submission(test_path: str, output_path: str) -> None:
    """Read test.csv and write submission.csv."""
    with open(test_path) as f:
        rows = list(csv.DictReader(f))

    results = []
    for r in rows:
        pred = solve(r["prompt"])
        results.append({"id": r["id"], "answer": pred.strip()})

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "answer"])
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} predictions to {output_path}")


if __name__ == "__main__":
    data_dir = Path("/tmp")
    if not (data_dir / "test.csv").exists():
        data_dir = Path("/home/mike-anderson/dev/cohezion/data")

    generate_submission(
        str(data_dir / "test.csv"),
        str(data_dir / "submission.csv"),
    )
