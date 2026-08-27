#!/usr/bin/env python3
"""Ruff debt ratchet — freeze the lint backlog, allow only downward movement.

The CI ``lint`` job runs ``ruff check`` with ``continue-on-error: true`` because
the repo carries a pre-existing ruff backlog. That makes the required ``lint``
check toothless: a PR can add brand-new violations and CI stays green.

This ratchet restores teeth without forcing a full cleanup first: it fails CI only
when the violation count *exceeds* a committed baseline. New lint debt is blocked;
legacy debt is tolerated but visible and monotonically shrinking. When a PR reduces
the count, lower the baseline (``--update``). When the baseline reaches 0, delete
this script and make ``ruff check`` itself gating.

The baseline carries a provenance stamp, because a baseline nobody measured is
worse than no gate at all -- see ``_PROVENANCE`` for the incident that motivated it.

Usage:
    python scripts/ci/ruff_ratchet.py            # gate: fail if count > baseline
    python scripts/ci/ruff_ratchet.py --update   # rewrite baseline to measured count
                                                  # (refuses to RAISE a measured one)
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
    # Prefer `uv run ruff` so the locked ruff version (uv.lock) is used — a
    # standalone ruff on PATH (e.g. ~/.local/bin/ruff) can be a different
    # version and produce a different violation count, causing CI/local skew.
    try:
        proc = subprocess.run(["uv", "run", *cmd], cwd=REPO, capture_output=True, text=True)
    except FileNotFoundError:
        # uv not available — fall back to bare ruff on PATH.
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    try:
        return len(json.loads(proc.stdout or "[]"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(proc.stdout[:2000] + "\n" + proc.stderr[:2000] + "\n")
        raise SystemExit(f"ruff_ratchet: could not parse ruff JSON output: {exc}") from exc


# Written by --update so the gate can tell a MEASURED baseline from a typed one.
# History (2026-08-27): commit 66f5186d5 hand-edited the baseline 749 -> 471 while the
# tree actually held 683 -> 758 violations. --update can only ever write the measured
# count, so that number came from a text editor, not a measurement. The gate then failed
# unconditionally and reported "this PR adds new lint debt" to every author -- false and
# unactionable, so it was ignored, and with policing gone the count drifted to 1302.
# This stamp makes an unmeasured baseline self-declaring. It is accident-proof, not
# tamper-proof: someone can copy the comment. Accident is the failure mode we had.
_PROVENANCE = "# measured-by: ruff_ratchet.py --update"


def _read_baseline() -> tuple[int, bool]:
    """Return ``(count, was_measured)`` for the committed baseline.

    ``was_measured`` is False when the file carries no provenance stamp, which
    means the number was typed rather than produced by a real ruff run.
    """
    if not BASELINE_FILE.exists():
        raise SystemExit(f"ruff_ratchet: missing baseline file {BASELINE_FILE}")
    text = BASELINE_FILE.read_text()
    counts = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not counts:
        raise SystemExit(f"ruff_ratchet: no count found in {BASELINE_FILE}")
    return int(counts[0]), _PROVENANCE in text


def main() -> int:
    current = _current_count()

    if "--update" in sys.argv:
        old, old_measured = _read_baseline() if BASELINE_FILE.exists() else (None, False)
        # "Only moves down" is right for a real baseline and wrong for a fictitious
        # one: it left NO sanctioned way to repair a typed number, so the only route
        # out of a permanently-red gate was to hand-edit the file again -- the very
        # act that broke it. Replacing an unverified value with a measurement is
        # establishing ground truth, not inflating debt, so it is allowed once.
        if old is not None and current > old and old_measured:
            sys.stderr.write(
                f"ruff_ratchet: refusing to RAISE baseline {old} -> {current}. "
                f"The ratchet only moves down.\n"
            )
            return 1
        if old is not None and current > old and not old_measured:
            print(
                f"ruff_ratchet: replacing UNVERIFIED baseline {old} with the first "
                f"measured value {current}. Subsequent updates may only move down."
            )
        BASELINE_FILE.write_text(f"{current}\n{_PROVENANCE}\n")
        delta = "" if old is None else f" (was {old}, {current - old:+d})"
        print(f"ruff_ratchet: baseline set to {current}{delta}")
        return 0

    baseline, was_measured = _read_baseline()
    if current > baseline and not was_measured:
        # Do NOT blame the author. An unmeasured baseline can sit below anything
        # the tree has ever achieved, in which case this gate fails for everyone
        # forever and teaches the team to ignore it.
        print(
            f"❌ ruff_ratchet: baseline {baseline} is UNVERIFIED — it carries no "
            f"provenance stamp, so it was typed rather than measured, and the tree "
            f"may never have met it (current: {current}).\n"
            f"   This is a gate misconfiguration, not new debt in your change.\n"
            f"   Re-measure it: python scripts/ci/ruff_ratchet.py --update"
        )
        return 1
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
