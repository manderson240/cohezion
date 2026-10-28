"""declared_field_scan: AST-true, oracle-validated on real history, ratchet holds, both gates run it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ci"))
import declared_field_scan as s


def test_self_test_passes():
    assert s.self_test() == 0


def test_no_new_dropped_fields_vs_baseline():
    findings, files = s.scan()
    assert files > 0
    base = s.read_baseline()
    for f in findings:
        assert f.key in base, f"NEW dropped fields: {f.key} missing {f.missing}"
        assert set(f.missing) <= base[f.key], f"GREW: {f.key} +{set(f.missing) - base[f.key]}"


def _historical(ref: str) -> str:
    """journey_tracker.py at a real prior revision: an oracle nobody wrote to satisfy this scanner."""
    r = subprocess.run(
        ["git", "show", f"{ref}:src/cohezion/compound/journey_tracker.py"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    if r.returncode != 0:
        pytest.skip(f"revision {ref} not available in this checkout")
    return r.stdout


def test_oracle_pre_fix_revision_flags_exactly_the_historical_defect():
    """0890c6763~1: CREATE journey_transition dropped `action` (21,635 rows, NULL on all)."""
    found = {(f.cls, f.missing) for f in s.scan_source(_historical("0890c6763~1"))}
    assert ("TrajectoryPoint", ("timestamp", "action", "source", "transformation")) in found
    assert not any(cls == "Journey" for cls, _ in found)  # a second class must not bind


def test_oracle_current_journey_tracker_is_complete():
    src = (REPO / "src/cohezion/compound/journey_tracker.py").read_text()
    assert [f for f in s.scan_source(src) if f.cls == "TrajectoryPoint"] == []


def test_update_statements_are_not_candidates():
    src = (
        "from dataclasses import dataclass\n@dataclass\nclass P:\n    a: int\n    b: int\n    c: int\n"
        'def f(p):\n    q = f"UPDATE t SET a = {p.a}, b = {p.b};"\n'
    )
    assert s.scan_source(src) == []  # a partial UPDATE is by design


def test_serialising_through_a_method_is_not_a_candidate():
    src = (
        "from dataclasses import dataclass\n@dataclass\nclass P:\n    a: int\n    b: int\n"
        'def f(p: P):\n    q = f"CREATE t CONTENT {p.to_dict()};"\n'
    )
    assert s.scan_source(src) == []  # annotation alone never binds a write naming no fields


@pytest.mark.parametrize("gate", ["scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"])
def test_t3_scanner_is_wired_into_the_gate(gate):
    text = (REPO / gate).read_text()
    assert "declared_field_scan.py --self-test" in text
    assert text.count("declared_field_scan.py") >= 2
