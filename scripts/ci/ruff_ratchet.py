#!/usr/bin/env python3
"""Ruff debt ratchet — freeze the lint backlog, allow only downward movement.

The CI ``lint`` job runs ``ruff check`` with ``continue-on-error: true`` because
the repo carries a large pre-existing ruff backlog (749 violations as of the
baseline). That makes the required ``lint`` check toothless: a PR can add brand-new
violations and CI stays green.

This ratchet restores teeth without forcing a 749-error cleanup first: it fails CI
only when the violation count *exceeds* a committed baseline. New lint debt is
blocked; legacy debt is tolerated but visible and monotonically shrinking. When a
PR reduces the count, lower the baseline (``--update``). When the baseline reaches
0, delete this script and make ``ruff check`` itself gating.

Usage:
    python scripts/ci/ruff_ratchet.py            # gate: fail if count > baseline
    python scripts/ci/ruff_ratchet.py --update   # rewrite baseline to current count
                                                  # (refuses to RAISE the baseline)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
# Note: NOT named ruff_*.txt — that pattern is .gitignore'd (ruff report outputs).
BASELINE_FILE = Path(__file__).resolve().parent / "lint_baseline.txt"
TARGETS = ["src/", "tests/"]


def _current_count() -> int:
    """Return the number of ruff-check violations across TARGETS (deterministic JSON count)."""
    cmd = ["ruff", "check", *TARGETS, "--output-format", "json"]
    try:
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    except FileNotFoundError:
        # ruff not directly on PATH — fall back to the project venv via uv.
        proc = subprocess.run(["uv", "run", *cmd], cwd=REPO, capture_output=True, text=True)
    try:
        return len(json.loads(proc.stdout or "[]"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(proc.stdout[:2000] + "\n" + proc.stderr[:2000] + "\n")
        raise SystemExit(f"ruff_ratchet: could not parse ruff JSON output: {exc}") from exc


def _read_baseline() -> int:
    if not BASELINE_FILE.exists():
        raise SystemExit(f"ruff_ratchet: missing baseline file {BASELINE_FILE}")
    return int(BASELINE_FILE.read_text().strip())


def main() -> int:
    current = _current_count()

    if "--update" in sys.argv:
        old = _read_baseline() if BASELINE_FILE.exists() else None
        if old is not None and current > old:
            sys.stderr.write(
                f"ruff_ratchet: refusing to RAISE baseline {old} -> {current}. "
                f"The ratchet only moves down.\n"
            )
            return 1
        BASELINE_FILE.write_text(f"{current}\n")
        delta = "" if old is None else f" (was {old}, -{old - current})"
        print(f"ruff_ratchet: baseline set to {current}{delta}")
        return 0

    baseline = _read_baseline()
    if current > baseline:
        print(
            f"❌ ruff_ratchet: {current} violations > baseline {baseline} "
            f"(+{current - baseline}). This PR adds new lint debt — fix the new "
            f"violations. Do NOT raise the baseline.\n"
            f"   See them: uv run ruff check {' '.join(TARGETS)}"
        )
        return 1
    if current < baseline:
        print(
            f"✅ ruff_ratchet: {current} < baseline {baseline} — debt reduced by "
            f"{baseline - current}! Lock it in: python scripts/ci/ruff_ratchet.py --update"
        )
        return 0
    print(f"✅ ruff_ratchet: {current} == baseline {baseline} (no new lint debt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
