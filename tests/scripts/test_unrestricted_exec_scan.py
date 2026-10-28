"""unrestricted_exec_scan: self-test green, repo clean, and BOTH gates actually invoke it."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "unrestricted_exec_scan", REPO / "scripts/ci/unrestricted_exec_scan.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # @dataclass resolves its class module via sys.modules
    spec.loader.exec_module(mod)
    return mod


ues = _load()


def test_self_test_passes():
    assert ues.self_test() == 0


def test_historical_defect_is_red_and_fix_is_green(tmp_path):
    """The literal pre-fix dual_loop_optimizer shape, then the fixed shape."""
    before = tmp_path / "before.py"
    before.write_text(
        "def f(verifier_code):\n    local_namespace = {}\n    exec(verifier_code, local_namespace)\n"
    )
    after = tmp_path / "after.py"
    after.write_text(
        "def f(verifier_code):\n"
        "    local_namespace = safe_exec_globals()\n"
        "    exec(verifier_code, local_namespace)\n"
    )
    assert len(ues.scan_file(before)) == 1
    assert ues.scan_file(after) == []


def test_repo_src_is_currently_clean():
    assert [str(f) for f in ues.scan([REPO / "src"])] == []


_INVOKE = "python scripts/ci/unrestricted_exec_scan.py"


def wiring_problems(text: str) -> list[str]:
    """Why ``text`` (a gate file) does NOT genuinely run the scanner; empty means wired.

    Only uncommented lines that actually INVOKE the interpreter on the script count — an
    ``echo ... unrestricted_exec_scan.py`` or a commented-out line must not satisfy it — and a
    GitHub step marked ``continue-on-error`` is not a gate.
    """
    live = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    invocations = [ln for ln in live if _INVOKE in ln]
    problems = []
    if not any(ln.rstrip().endswith("--self-test") for ln in invocations):
        problems.append("never runs --self-test")
    if not any("--self-test" not in ln for ln in invocations):
        problems.append("never runs the actual scan")
    first = next((i for i, ln in enumerate(live) if _INVOKE in ln), None)
    if first is not None:
        step_start = max((i for i in range(first + 1) if "- name:" in live[i]), default=0)
        step_end = next((i for i in range(first + 1, len(live)) if "- name:" in live[i]), len(live))
        if any("continue-on-error: true" in ln for ln in live[step_start:step_end]):
            problems.append("step is continue-on-error (non-gating)")
    return problems


@pytest.mark.parametrize("gate", ["scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"])
def test_scanner_is_wired_into_the_gate(gate):
    """A scanner no gate runs is dormant — and one run without --self-test proves nothing."""
    assert wiring_problems((REPO / gate).read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "neutralised",
    [
        # commented out + echo mentioning the file (adversarial review of a25cc4a88)
        "  - name: Unrestricted exec/eval scan (gating)\n    continue-on-error: false\n"
        "    run: |\n      # uv run python scripts/ci/unrestricted_exec_scan.py --self-test\n"
        "      echo skipping unrestricted_exec_scan.py\n",
        # present but non-gating
        "  - name: Unrestricted exec/eval scan (gating)\n    continue-on-error: true\n"
        "    run: |\n      uv run python scripts/ci/unrestricted_exec_scan.py --self-test\n"
        "      uv run python scripts/ci/unrestricted_exec_scan.py\n",
        # self-test only
        "  - name: Unrestricted exec/eval scan (gating)\n"
        "    run: uv run python scripts/ci/unrestricted_exec_scan.py --self-test\n",
    ],
)
def test_wiring_check_rejects_neutralised_gates(neutralised):
    assert wiring_problems(neutralised), "wiring check accepted a gate that does not gate"
