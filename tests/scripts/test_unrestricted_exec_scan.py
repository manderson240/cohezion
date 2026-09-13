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


@pytest.mark.parametrize("gate", ["scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"])
def test_scanner_is_wired_into_the_gate(gate):
    """A scanner no gate runs is dormant — and one run without --self-test proves nothing."""
    text = (REPO / gate).read_text(encoding="utf-8")
    assert "unrestricted_exec_scan.py --self-test" in text, f"{gate} skips the self-test"
    runs_scan = any(
        "unrestricted_exec_scan.py" in line and "--self-test" not in line
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
    )
    assert runs_scan, f"{gate} runs only the self-test, never the actual scan"
