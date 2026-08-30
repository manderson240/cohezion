#!/usr/bin/env python3
"""Mypy debt ratchet — freeze the type backlog, allow only downward movement.

Sibling of ``ruff_ratchet.py``. The CI ``typecheck`` job runs mypy with
``continue-on-error: true`` because the repo carries a large pre-existing type
backlog, which makes that step toothless: a PR can add brand-new type errors and
CI stays green.

Until 2026-08-30 the step was worse than toothless — it was *dark*. Three
independent breakages stacked:

1. ``python_version = "3.11"`` in ``pyproject.toml`` while the project floor is
   3.13, so numpy's stubs (which use 3.12+ ``type`` statements) made mypy abort
   with ``errors prevented further checking`` **before reading any project file**.
2. Two skill ASSET directories with hyphens in their names
   (``skills/mcp-builder``, ``skills/kaggle/modules/{badge-collector,comp-report}``)
   made mypy refuse the whole run: a hyphen is not a legal Python identifier.
3. ``continue-on-error: true`` meant even a real failure did not gate.

With (1) and (2) fixed the gate finally runs: 1826 errors across 572 files, out
of 1583 checked. This ratchet handles (3) without demanding a 1826-error cleanup:
fail only when the count *exceeds* a committed baseline.

THE IMPORTANT INVARIANT: an aborted mypy run must NEVER be read as a low error
count. That is precisely how this gate stayed dark for months — a crash reports
"1 error", which any naive counter happily accepts as a massive improvement and
writes into the baseline. ``_parse_count`` refuses such output loudly.

Usage:
    python scripts/ci/mypy_ratchet.py             # gate: fail if count > baseline
    python scripts/ci/mypy_ratchet.py --update    # rewrite baseline (never upward)
    python scripts/ci/mypy_ratchet.py --self-test # prove the gate can still fail
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
BASELINE_FILE = Path(__file__).resolve().parent / "mypy_baseline.txt"
TARGET = "src/cohezion/"

_FOUND = re.compile(r"^Found (\d+) errors? in \d+ files?", re.M)
_SUCCESS = re.compile(r"^Success: no issues found", re.M)
# How many files mypy actually looked at. Tracked because a FALLING error count
# is only good news if coverage held: broadening `exclude` also lowers the count,
# and without this the gate would congratulate you for going blind.
# Matches BOTH summary shapes: "(checked N source files)" after an error summary,
# and "Success: no issues found in N source files" on a clean run. Matching only
# the first reports checked=0 for every clean run, which silently defeats the
# coverage guard below. (Found by glm-5.2 in multiperspective review.)
_CHECKED = re.compile(r"(?:\(checked |no issues found in )(\d+) source files?")

# Markers meaning mypy never completed a real check. Counting these is the bug.
# Deliberately NOT included: "Cannot find implementation or library stub for
# module named" — that is a NORMAL per-file error, not a run abort, so treating
# it as one would refuse legitimate runs the moment --ignore-missing-imports
# stopped suppressing it. (Raised by glm-5.2 in cross-family review.)
_ABORTED = (
    "errors prevented further checking",
    "is not a valid Python package name",
)


class MypyAbortedError(RuntimeError):
    """mypy failed to complete a check — the count is meaningless, not low."""


def _parse_count(output: str) -> tuple[int, int]:
    """Return (errors, files_checked), refusing output from an incomplete run."""
    for marker in _ABORTED:
        if marker in output:
            raise MypyAbortedError(
                f"mypy did not complete a real check (saw {marker!r}). "
                f"Refusing to treat this as an error count — a crashed type "
                f"checker is not a clean one. Fix the configuration first."
            )
    checked_match = _CHECKED.search(output)
    checked = int(checked_match.group(1)) if checked_match else 0

    match = _FOUND.search(output)
    if match:
        return int(match.group(1)), checked
    if _SUCCESS.search(output):
        return 0, checked
    raise MypyAbortedError(
        "mypy produced no recognisable summary line; refusing to guess a count.\n" + output[-2000:]
    )


def _current_count() -> tuple[int, int]:
    # --no-incremental: the count must not depend on whatever .mypy_cache the
    # runner happens to carry, or the gate fails on arrival in CI for reasons
    # unrelated to the PR. Determinism is the whole value of a baseline.
    # Always via `uv run` so the project's pinned mypy wins over any global one.
    cmd = ["uv", "run", "mypy", TARGET, "--ignore-missing-imports", "--no-incremental"]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return _parse_count(proc.stdout + proc.stderr)


def _read_baseline() -> tuple[int, int]:
    """Baseline must be 'errors checked'. Both fields are REQUIRED.

    A bare-int baseline is deliberately rejected rather than tolerated: it would
    set baseline_checked = 0, which makes the coverage guard's `if baseline_checked`
    falsy and silently disables it. This gate has never shipped a one-field
    baseline, so "backward compatibility" here would only ever be a way to disarm
    the coverage half by editing one file. (Found by kimi-k3 in multiperspective
    review.) Fail loudly instead — a malformed baseline is an operator error, not
    a reason to check less.
    """
    if not BASELINE_FILE.exists():
        raise SystemExit(f"mypy_ratchet: missing baseline file {BASELINE_FILE}")
    parts = BASELINE_FILE.read_text().split()
    if len(parts) != 2:
        raise SystemExit(
            f"mypy_ratchet: {BASELINE_FILE} must contain exactly two integers "
            f"'<errors> <files_checked>', got {parts!r}. A one-field baseline "
            f"would silently disable the coverage guard."
        )
    return int(parts[0]), int(parts[1])


def _verdict(
    current: int, baseline: int, checked: int = 0, baseline_checked: int = 0
) -> int:
    """Pure comparison, so --self-test can exercise it without running mypy.

    Coverage is checked BEFORE the count. A shrinking error count is only good
    news if mypy still looked at as many files: broadening `exclude` lowers the
    count too, and a naive ratchet would print "debt reduced — lock it in" and
    then bake that blindness into the baseline via --update. Concretely, widening
    the skills/ exclude to the whole package would silently drop 15 importable
    modules and look like a win. (Raised by kimi-k3 in cross-family review.)
    """
    # NO `and checked` term: with it, checked == 0 short-circuits the guard, so
    # excluding EVERYTHING (0 files, 0 errors) skipped straight to "debt reduced
    # — lock it in". The most complete blindness was the one case that passed.
    # (Found by glm-5.2 in multiperspective review; the --update path below was
    # already written correctly, which is what made the asymmetry visible.)
    if baseline_checked and checked < baseline_checked:
        print(
            f"❌ mypy_ratchet: coverage DROPPED — {checked} files checked vs "
            f"baseline {baseline_checked} (-{baseline_checked - checked}). A lower "
            f"error count here means mypy stopped looking, not that the code "
            f"improved. Usually a widened `exclude` in pyproject.toml. Restore "
            f"coverage; do not --update."
        )
        return 1
    if current > baseline:
        print(
            f"❌ mypy_ratchet: {current} errors > baseline {baseline} "
            f"(+{current - baseline}). This PR adds new type debt — fix the new "
            f"errors. Do NOT raise the baseline.\n"
            f"   See them: uv run mypy {TARGET} --ignore-missing-imports"
        )
        return 1
    if current < baseline:
        print(
            f"✅ mypy_ratchet: {current} < baseline {baseline} — debt reduced by "
            f"{baseline - current}! Lock it in: python scripts/ci/mypy_ratchet.py --update"
        )
        return 0
    print(f"✅ mypy_ratchet: {current} == baseline {baseline} (no new type debt)")
    return 0


def _self_test() -> int:
    """Prove the gate can still FAIL, and that it refuses aborted runs.

    Deliberately no `assert`: assertions are stripped under `python -O`, which
    would turn this proof-of-detection into a silent no-op — the same class of
    failure the gate itself exists to catch.
    """
    failures: list[str] = []

    def check(label: str, got: object, want: object) -> None:
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    check("increase must fail", _verdict(101, 100), 1)
    check("equal must pass", _verdict(100, 100), 0)
    check("decrease must pass", _verdict(99, 100), 0)

    # Coverage guard: a LOWER error count with FEWER files checked is blindness,
    # not improvement, and must fail even though the count went down.
    check("coverage drop must fail", _verdict(1000, 1826, 1200, 1583), 1)
    check("same coverage, fewer errors passes", _verdict(1000, 1826, 1583, 1583), 0)
    check("more coverage, fewer errors passes", _verdict(1000, 1826, 1600, 1583), 0)

    check(
        "parse found-many",
        _parse_count("Found 1826 errors in 572 files (checked 1583 source files)"),
        (1826, 1583),
    )
    check(
        "parse found-one",
        _parse_count("Found 1 error in 1 file (checked 3 source files)"),
        (1, 3),
    )
    # A clean run still reports how many files it looked at. Asserting (0, 0)
    # here is how the previous version of this self-test ENCODED the bug it was
    # supposed to catch: a green run reported zero coverage, disarming the guard.
    check(
        "parse success keeps the file count",
        _parse_count("Success: no issues found in 5 source files"),
        (0, 5),
    )
    # The extreme case: exclude everything. 0 errors over 0 files must FAIL as a
    # coverage collapse, never pass as "debt reduced by 1826".
    check("total exclusion must fail", _verdict(0, 1826, 0, 1583), 1)
    check("zero-error run at full coverage passes", _verdict(0, 1826, 1583, 1583), 0)
    # A normal missing-stub error is NOT an abort: refusing it would reject
    # legitimate runs the moment --ignore-missing-imports stopped hiding it.
    check(
        "missing-stub error is not an abort",
        _parse_count(
            "x.py:1: error: Cannot find implementation or library stub for module named 'q'\n"
            "Found 1 error in 1 file (checked 3 source files)"
        ),
        (1, 3),
    )

    # The defect this gate exists to prevent: a crashed run reports "1 error".
    # Counting it would silently ratchet the baseline down to 1 and disable the gate.
    crashed = (
        "numpy/__init__.pyi:737: error: Type statement is only supported in "
        "Python 3.12 and greater  [syntax]\n"
        "Found 1 error in 1 file (errors prevented further checking)\n"
    )
    try:
        _parse_count(crashed)
    except MypyAbortedError:
        pass
    else:  # pragma: no cover - self-test failure path
        failures.append("an aborted mypy run was accepted as a count of 1")

    try:
        _parse_count("mcp-builder contains __init__.py but is not a valid Python package name")
    except MypyAbortedError:
        pass
    else:  # pragma: no cover
        failures.append("an invalid-package-name abort was accepted as a count")

    if failures:
        for line in failures:
            print(f"SELF-TEST FAILED: {line}")
        return 1

    print(
        "SELF-TEST OK: ratchet flags an increase (red) and passes equal/decrease "
        "(green); aborted mypy runs are refused instead of counted as 1."
    )
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()

    try:
        current, checked = _current_count()
    except MypyAbortedError as exc:
        print(f"❌ mypy_ratchet: {exc}")
        return 1

    if "--update" in sys.argv:
        old, old_checked = _read_baseline() if BASELINE_FILE.exists() else (None, 0)
        if old is not None and current > old:
            sys.stderr.write(
                f"mypy_ratchet: refusing to RAISE baseline {old} -> {current}. "
                f"The ratchet only moves down.\n"
            )
            return 1
        if old_checked and checked < old_checked:
            sys.stderr.write(
                f"mypy_ratchet: refusing to record a baseline with LESS coverage "
                f"({checked} files vs {old_checked}). Locking this in would make "
                f"the gate permanently blind to the dropped files.\n"
            )
            return 1
        BASELINE_FILE.write_text(f"{current} {checked}\n")
        delta = "" if old is None else f" (was {old}, -{old - current})"
        print(f"mypy_ratchet: baseline set to {current} errors / {checked} files{delta}")
        return 0

    baseline, baseline_checked = _read_baseline()
    return _verdict(current, baseline, checked, baseline_checked)


if __name__ == "__main__":
    raise SystemExit(main())
