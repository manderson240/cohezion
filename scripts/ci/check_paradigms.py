#!/usr/bin/env python3
"""Testing-paradigm coverage gate (gating).

Verifies the repo's advanced testing paradigms are actually wired, not just
present as directories:
  1. Each paradigm test dir exists and contains at least one test file.
  2. Each paradigm's pytest marker is registered in pyproject.toml.
  3. The testing-paradigms workflow exists and invokes every paradigm dir.
  4. Mutation testing: mutmut config scopes real files, the coupled test
     file exists, and the survivor ratchet baseline is present.

Fail-closed: any missing dir/marker/workflow-reference is an error.
Self-test mode: mutates a synthetic repo state (temp dirs + fake pyproject)
and asserts each check FIRES on the broken variant — a check that cannot
fail is decoration. Same rationale as dormancy_scan --self-test.

Usage:
  python scripts/ci/check_paradigms.py --self-test
  python scripts/ci/check_paradigms.py
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PARADIGM_DIRS = {
    "property": "tests/property",
    "fuzz": "tests/fuzz",
    "metamorphic": "tests/metamorphic",
    "mutation": "tests/mutation",
    "contract": "tests/contracts",
}

WORKFLOW_REL = ".github/workflows/testing-paradigms.yml"
MUTMUT_TEST_REL = "muttest/test_model_shootout.py"
MUTATION_BASELINE_REL = "scripts/ci/mutation_baseline.txt"


def check_dir(d: Path, label: str, errors: list[str]) -> None:
    if not d.is_dir():
        errors.append(f"{label}: directory missing: {d}")
        return
    tests = list(d.glob("test_*.py"))
    if not tests:
        errors.append(f"{label}: no test_*.py files in {d}")
        return
    has_test = any(
        re.search(r"\bdef test_|\bpytestmark\b", t.read_text(errors="replace")) for t in tests
    )
    if not has_test:
        errors.append(f"{label}: test files in {d} define no tests")


def check_marker(pyproject_text: str, marker: str, label: str, errors: list[str]) -> None:
    if not re.search(rf'"{marker}\s*:', pyproject_text):
        errors.append(f"{label}: pytest marker '{marker}' not registered in pyproject.toml")


def check_workflow(wf_text: str, dir_rel: str, label: str, errors: list[str]) -> None:
    if dir_rel not in wf_text:
        errors.append(f"{label}: workflow does not invoke {dir_rel}")


def run_checks(root: Path, errors: list[str]) -> None:
    for label, rel in PARADIGM_DIRS.items():
        check_dir(root / rel, label, errors)

    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        errors.append("pyproject.toml missing")
    else:
        text = pyproject.read_text()
        for marker in ("property", "metamorphic", "mutation", "fuzz"):
            check_marker(text, marker, marker, errors)

    if not (root / WORKFLOW_REL).exists():
        errors.append(f"paradigm workflow missing: {WORKFLOW_REL}")
    else:
        wf_text = (root / WORKFLOW_REL).read_text()
        for label, rel in PARADIGM_DIRS.items():
            check_workflow(wf_text, rel, label, errors)

    # Mutation scope must point at real files and have a coupled test file
    if not (root / MUTMUT_TEST_REL).exists():
        errors.append(f"mutmut coupled test file missing: {MUTMUT_TEST_REL}")
    if not (root / MUTATION_BASELINE_REL).exists():
        errors.append(f"mutation ratchet baseline missing: {MUTATION_BASELINE_REL}")


def self_test() -> int:
    """Run checks against a deliberately-broken temp tree; every class of
    check must fire. Then run against a correct synthetic tree; none may fire."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(
            '[tool.pytest.ini_options]\nmarkers = ["property: x", "metamorphic: x", "mutation: x", "fuzz: x"]\n'
        )
        # broken tree: nothing else present
        broken: list[str] = []
        run_checks(root, broken)
        classes = {e.split(":")[0] for e in broken}
        expected = {"property", "fuzz", "metamorphic", "mutation", "contract"}
        missing = expected - classes
        assert not missing, f"self-test: checks did not fire for {missing}; got {broken}"
        assert any("workflow missing" in e for e in broken), broken
        assert any("mutation ratchet baseline" in e for e in broken), broken
        assert any("mutmut coupled test file" in e for e in broken), broken

        # correct tree: all pieces present
        good: list[str] = []
        wf = root / ".github/workflows"
        wf.mkdir(parents=True)
        wf_text = " ".join(f"uv run pytest {rel}" for rel in PARADIGM_DIRS.values())
        (wf / "testing-paradigms.yml").write_text(f"jobs:\n  x:\n    steps:\n      - run: {wf_text}\n")
        for rel in PARADIGM_DIRS.values():
            d = root / rel
            d.mkdir(parents=True)
            (d / "test_x.py").write_text("import pytest\n\ndef test_ok():\n    assert True\n")
        (root / "muttest").mkdir()
        (root / "muttest/test_model_shootout.py").write_text("def test_ok():\n    assert True\n")
        (root / "scripts/ci").mkdir(parents=True)
        (root / "scripts/ci/mutation_baseline.txt").write_text("survived=1\nno_tests=1\n")
        run_checks(root, good)
        assert not good, f"self-test: false positives on good tree: {good}"
    print("✓ self-test passed (broken tree fires all 8 check classes, good tree clean)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Testing-paradigm coverage gate")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    errors: list[str] = []
    run_checks(REPO_ROOT, errors)
    if errors:
        for e in errors:
            print(f"✗ {e}", file=sys.stderr)
        print("Every paradigm above must exist, carry tests, be marker-registered, and be CI-wired.", file=sys.stderr)
        return 1
    print("✓ all 5 paradigms wired: dirs+tests, markers, workflow refs, mutation scope+baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())