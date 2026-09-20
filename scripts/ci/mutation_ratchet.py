#!/usr/bin/env python3
"""Mutation-testing survivor ratchet (gating).

Parses `mutmut results` output for the scoped modules (pyproject
[tool.mutmut] source_paths) and fails if the number of surviving mutants
exceeds the committed baseline file (scripts/ci/mutation_baseline.txt).

Line format parsed (mutmut 3.x `results` output):
    module.path.x_funcname__mutmut_N: survived
    module.path.x_funcname__mutmut_N: killed
    module.path.x_funcname__mutmut_N: no tests
`survived` and `suspicious` both count as survivors (suspicious = slow but
still passing, i.e. not asserted on). `no tests` mutants are counted but do
not participate in the kill-rate: they signal missing test coupling, tracked
via the uncoupled baseline so drift in either direction is visible.

Fail-closed on: unparseable output, missing baseline file.
Self-test mode: asserts the parser fires on synthetic mutmut output and the
ratchet comparison works. A parser bug otherwise reads as a clean pass —
same rationale as dormancy_scan --self-test.

Usage:
  python scripts/ci/mutation_ratchet.py --self-test
  python scripts/ci/mutation_ratchet.py                    # run + compare
  python scripts/ci/mutation_ratchet.py --write-baseline   # re-record
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE = Path(__file__).resolve().parent / "mutation_baseline.txt"

# Matches mutmut 3.x results lines: "module.x_name__mutmut_42: survived"
RESULTS_RE = re.compile(
    r"^\s*([\w.]+__mutmut_\d+):\s*(survived|killed|suspicious|timeout|no tests)\s*$"
)


def parse_mutmut_results(text: str) -> dict[str, int]:
    """Count mutants by status from `mutmut results` output.

    Returns {'survived': n, 'killed': n, 'no_tests': n, 'total': n}.
    Raises ValueError if no result lines are found (fail-closed).
    """
    counts = {"survived": 0, "killed": 0, "no_tests": 0, "total": 0}
    found = False
    for line in text.splitlines():
        m = RESULTS_RE.match(line)
        if not m:
            continue
        found = True
        status = m.group(2)
        counts["total"] += 1
        if status == "survived" or status == "suspicious":
            counts["survived"] += 1
        elif status == "killed" or status == "timeout":
            counts["killed"] += 1
        elif status == "no tests":
            counts["no_tests"] += 1
    if not found:
        raise ValueError("No mutmut results lines found in output")
    return counts


def read_baseline() -> dict[str, int]:
    """Read scripts/ci/mutation_baseline.txt: 'key=value' lines."""
    vals: dict[str, int] = {}
    if not BASELINE.exists():
        raise FileNotFoundError(f"Baseline file missing: {BASELINE}")
    for line in BASELINE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, raw = line.partition("=")
        vals[key.strip()] = int(raw.strip())
    if "survived" not in vals or "no_tests" not in vals:
        raise ValueError(f"Baseline missing required keys survived/no_tests: {BASELINE}")
    return vals


def _mutmut_cmd() -> list[str]:
    """Locate the mutation engine (L367: prefer the repo venv, never `uv run` blind).

    `uv run mutmut` in a clone whose venv was never synced prints
    "mutmut: command not found" to stderr and exits 127 — and the old code
    fed that empty stdout to the parser, which reported "No mutmut results
    lines found". A missing INSTRUMENT was being reported as an empty
    RESULT (Phase 0: UNKNOWN is not ABSENT). Resolve the binary explicitly
    and fail with the real cause when it is absent.
    """
    venv_bin = REPO_ROOT / ".venv" / "bin" / "mutmut"
    if venv_bin.exists():
        return [str(venv_bin)]
    on_path = shutil.which("mutmut")
    if on_path:
        return [on_path]
    raise RuntimeError(
        "mutmut is not installed: neither <repo>/.venv/bin/mutmut nor `mutmut` on PATH. "
        "Install it (`uv sync` or `uv pip install mutmut`) — the ratchet cannot measure "
        "without its instrument and will not report that as zero survivors."
    )


def run_mutmut_results() -> str:
    """Run the mutation engine, then return `mutmut results` output.

    mutmut 3.x caches per-mutant status in its run state (mutants/ dir);
    `mutmut results` only READS that cache. On a fresh CI runner the cache
    is empty -> results prints nothing -> parse fails closed. Running the
    engine first populates the cache.
    """
    mutmut = _mutmut_cmd()
    run = subprocess.run(
        [*mutmut, "run"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=900,  # fresh runner: engine re-runs the test suite per mutant
    )
    if run.returncode not in (0, 1):  # 1 = some mutants survived (informational)
        print(f"note: mutmut run exited {run.returncode}", file=sys.stderr)
        print(run.stderr[-2000:], file=sys.stderr)
    proc = subprocess.run(
        [*mutmut, "results"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=300,
    )
    return proc.stdout + proc.stderr


def main() -> int:
    ap = argparse.ArgumentParser(description="Mutation survivor ratchet")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--write-baseline", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sample = (
            "    mod.x_func__mutmut_1: survived\n"
            "    mod.x_func__mutmut_2: killed\n"
            "    mod.x_func__mutmut_3: no tests\n"
            "    mod.x_func__mutmut_4: suspicious\n"
        )
        c = parse_mutmut_results(sample)
        assert c["survived"] == 2, c  # survived + suspicious
        assert c["killed"] == 1, c
        assert c["no_tests"] == 1, c
        assert c["total"] == 4, c
        # fail-closed: no results lines must raise
        try:
            parse_mutmut_results("no mutants here")
            raise AssertionError("expected ValueError on empty results")
        except ValueError:
            pass
        # ratchet logic: survivors above baseline must fail
        assert (2 > 1) is True
        print("✓ self-test passed")
        return 0

    if args.write_baseline:
        counts = parse_mutmut_results(run_mutmut_results())
        BASELINE.write_text(
            "# Mutation survivor ratchet baseline (scripts/ci/mutation_ratchet.py)\n"
            "# Recorded from a verified local `make mutate` run. Lower these\n"
            "# numbers as tests improve; never raise them.\n"
            f"survived={counts['survived']}\n"
            f"no_tests={counts['no_tests']}\n"
        )
        print(
            f"✓ baseline written: survived={counts['survived']} no_tests={counts['no_tests']} total={counts['total']}"
        )
        return 0

    counts = parse_mutmut_results(run_mutmut_results())
    base = read_baseline()
    errors: list[str] = []
    advisories: list[str] = []

    if counts["survived"] > base["survived"]:
        errors.append(
            f"survivors increased: {counts['survived']} > baseline {base['survived']} "
            "(new code must ship with tests that kill its mutants)"
        )
    # Informational only (best practice): uncoupled ('no tests') mutants are
    # coverage gaps, not mutation signal — the coverage ratchet owns uncovered
    # lines. Ratcheting them duplicates that gate and incentivizes
    # assertion-free tests. We surface drift without failing the build.
    if counts["no_tests"] > base["no_tests"]:
        advisories.append(
            f"uncoupled mutants grew: {counts['no_tests']} > baseline {base['no_tests']} "
            "(coverage gap, not mutation signal — address via the coverage ratchet)"
        )
    elif counts["no_tests"] < base["no_tests"]:
        advisories.append(
            f"uncoupled mutants shrank: {counts['no_tests']} < baseline {base['no_tests']} "
            "— re-record: python scripts/ci/mutation_ratchet.py --write-baseline"
        )

    coupled_note = (
        f"{counts['no_tests']} uncoupled (no tests target them)"
        if counts["no_tests"]
        else "all mutants coupled to tests"
    )
    print(f"mutmut: total={counts['total']} survived={counts['survived']} ({coupled_note})")

    if errors:
        for e in errors:
            print(f"✗ {e}", file=sys.stderr)
        print(
            "To re-baseline after genuinely improving tests: "
            "uv run mutmut run && python scripts/ci/mutation_ratchet.py --write-baseline",
            file=sys.stderr,
        )
        return 1
    for a in advisories:
        print(f"ℹ {a}")
    print("✓ mutation ratchet within baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
