"""Consumption tests for scripts/ci/check_stealth_excepts.py (Learning 359, issue #94).

The gate existed for weeks with no caller while a violation sat on main. These tests fail if
either gate stops invoking it, or if the real tree regresses.
"""

import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "ci" / "check_stealth_excepts.py"


@pytest.mark.parametrize("gate", [".github/workflows/ci.yml", "scripts/ci/automerge_guard.sh"])
def test_gate_is_wired_with_self_test(gate):
    text = (REPO / gate).read_text(encoding="utf-8")
    assert "check_stealth_excepts.py --self-test" in text, f"{gate} does not self-test the gate"
    assert text.count("check_stealth_excepts.py") >= 2, f"{gate} self-tests but never runs the scan"
    self_test = text.find("check_stealth_excepts.py --self-test")
    scan = text.rfind("check_stealth_excepts.py")
    assert self_test < scan, f"{gate}: self-test must run before the scan, or a broken detector passes"


def test_self_test_passes():
    r = subprocess.run(
        [sys.executable, str(GATE), "--self-test"], capture_output=True, text=True, timeout=300
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_real_tree_is_clean_including_scripts():
    r = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("root", ["src", "scripts"])
def test_each_root_is_in_scope(root, tmp_path, monkeypatch):
    """Discriminating per root: dropping either root from the scan loop turns its arm green.

    scripts/ was added 2026-10-20 after a src-only scan missed a live violation; the src arm
    keeps the original scope from silently regressing in the same way.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("cse", GATE)
    assert spec is not None and spec.loader is not None
    cse = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cse)
    (tmp_path / "src").mkdir()
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(cse, "REPO", tmp_path)
    assert cse.main([]) == 0, "empty roots must pass, or the arm below proves nothing"
    (tmp_path / root / "d.py").write_text(
        "try:\n    pass\nexcept (TimeoutError, Exception):\n    pass\n"
    )
    assert cse.main([]) == 1
