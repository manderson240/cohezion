"""lineage_scan: reflex roots load by path within budget and without the deliberative stack.

T2 discriminating: a planted leak goes red (self-test), a leak in the registry is reported,
and the CONSUMPTION invariant -- both gates invoke the scanner -- fails if either stops.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "ci" / "lineage_scan.py"
sys.path.insert(0, str(SCRIPT.parent))
import lineage_scan as ls


def test_self_test_passes():
    assert ls.self_test() == 0


def test_every_registered_reflex_is_clean():
    """The gate itself. Measured 2026-09-19: 2-88 ms, 9-18 MB, 0 leaks per root."""
    assert ls.scan(ls.REFLEX_ROOTS) == []


def test_planted_leak_is_reported_with_the_leaked_module(tmp_path):
    leaky = tmp_path / "leaky.py"
    leaky.write_text(
        "import sys\nsys.path.insert(0, 'src')\nimport cohezion.inference.orchestrator\n"
    )
    bad = ls.verdicts(str(leaky), ls.probe(str(leaky)))
    assert any("cohezion.inference.orchestrator" in b for b in bad), bad


def test_probe_never_runs_in_the_test_interpreter():
    """A probe that imported into THIS process would poison later measurements."""
    before = {m for m in sys.modules if m.startswith("lineage_probe_")}
    ls.probe("src/cohezion/compound/safe_exec.py")
    assert {m for m in sys.modules if m.startswith("lineage_probe_")} == before


@pytest.mark.parametrize("gate", ["scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"])
def test_t3_scanner_is_wired_into_the_gate(gate):
    """CONSUMPTION invariant: neutralising the consumer turns this red."""
    text = (REPO / gate).read_text()
    assert "lineage_scan.py --self-test" in text, f"{gate} does not run the self-test"
    assert text.count("lineage_scan.py") >= 2, f"{gate} does not run the scan after the self-test"


def test_cli_exit_codes():
    assert subprocess.run([sys.executable, str(SCRIPT), "--self-test"], cwd=REPO).returncode == 0
    assert subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO).returncode == 0
