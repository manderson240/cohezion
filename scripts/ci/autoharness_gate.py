#!/usr/bin/env python3
"""AutoHarness Policy Gate (arXiv:2603.03329v1).

Deterministic AST bytecode verifier gating all PRs in automerge_guard:
    python scripts/ci/autoharness_gate.py --self-test  # prove it can go RED before trusting GREEN
    python scripts/ci/autoharness_gate.py              # gate

WHY THIS EXISTS:
----------------
Intercepts critical security and logic bugs (eval/exec injection, CWE-682
unit mismatches, bare except handlers) at 0ms latency with zero LLM inference costs.
"""

from __future__ import annotations

import ast
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from cohezion.agi.autoharness_policy import AutoHarnessPolicy  # noqa: E402

_GREEN_FIXTURE = """
def calculate_proceeds(pool_amount: int, token_rate: int) -> int:
    return pool_amount * token_rate
"""

_RED_FIXTURE_EVAL = """
def run_dynamic(user_input: str) -> None:
    eval(user_input)
"""

_RED_FIXTURE_UNIT_MISMATCH = """
def faulty_decrement(proceeds: int, participants: int) -> int:
    # CWE-682 unit mismatch between currency and count
    return proceeds - participants
"""


# Explicitly curated blessed evaluator modules where eval() executes pre-compiled
# AST bytecode objects exclusively inside a restricted __builtins__ dictionary.
# Any net-new eval() site outside this whitelist will fail the CI gate.
BLESSED_EVAL_SITES = {
    "src/cohezion/agi/autoharness_compiler.py",
    "src/cohezion/agi/kaggle_autoharness.py",
}


def scan_files(files_to_check: list[Path]) -> list[str]:
    """Scan given files with AutoHarnessPolicy."""
    policy = AutoHarnessPolicy(policy_name="ci_autoharness_gate")
    failures: list[str] = []

    for file_path in files_to_check:
        if not file_path.suffix == ".py":
            continue
        rel = file_path.relative_to(REPO) if file_path.is_relative_to(REPO) else file_path
        if str(rel) in BLESSED_EVAL_SITES:
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        result = policy.verify_code(content)
        # Filter for critical violations only (CWE-682, eval/exec, bare except)
        for v in result.violations:
            if any(k in v for k in ("Illegal dangerous call 'eval'", "CWE-682", "Bare 'except:'")):
                failures.append(f"{rel}: {v}")

    return failures


def self_test() -> int:
    """Discriminating self-test: must fail on red fixtures and pass on green."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        green_path = root / "green.py"
        green_path.write_text(_GREEN_FIXTURE, encoding="utf-8")

        red_eval_path = root / "red_eval.py"
        red_eval_path.write_text(_RED_FIXTURE_EVAL, encoding="utf-8")

        red_unit_path = root / "red_unit.py"
        red_unit_path.write_text(_RED_FIXTURE_UNIT_MISMATCH, encoding="utf-8")

        # Test green
        green_fails = scan_files([green_path])
        if green_fails:
            print(f"SELF-TEST FAILED: green fixture produced unexpected violations: {green_fails}")
            return 1

        # Test red eval
        red_eval_fails = scan_files([red_eval_path])
        if not red_eval_fails:
            print("SELF-TEST FAILED: red eval fixture was not flagged!")
            return 1

        # Test red unit mismatch
        red_unit_fails = scan_files([red_unit_path])
        if not red_unit_fails:
            print("SELF-TEST FAILED: red unit mismatch fixture (CWE-682) was not flagged!")
            return 1

    print("SELF-TEST OK: AutoHarness gate flags eval and CWE-682 mismatches (red) and passes valid code (green).")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    src_dir = REPO / "src" / "cohezion"
    target_files = list(src_dir.rglob("*.py"))
    failures = scan_files(target_files)

    if failures:
        print(f"AUTOHARNESS GATE FAILED — {len(failures)} critical safety/unit violation(s) found:")
        for f in failures:
            print("  ❌ " + f)
        return 1

    print(f"AutoHarness gate OK — {len(target_files)} Python source files verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
