"""The provenance ratchet's contract: three outcomes, and a real consumer.

Two things are pinned here.

**"Could not measure" must never collapse into "measured fine."** That is the defect fixed
in `ruff_ratchet` on 2026-09-20 -- an empty stdout parsed as `[]` and reported 0 violations,
a PASS, from a run that never happened. This gate is written after that lesson, so the
lesson gets a test rather than a comment.

**The gate is the production CONSUMER of `loop_goal_graph`.** A module with no caller is
dormant however well tested. If this import is ever dropped, the graph module silently
becomes dead code again -- so the wiring is asserted structurally, the way `harness.md`
requires a consumption invariant rather than a declaration.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "provenance_ratchet.py"


def _load():
    spec = importlib.util.spec_from_file_location("provenance_ratchet_uut", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ratchet():
    return _load()


def test_gate_is_a_real_consumer_of_the_graph_module(ratchet) -> None:
    """Consumption invariant: drop these calls and loop_goal_graph is dormant again."""
    src = SCRIPT.read_text()
    names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)}
    assert "coverage_certificate" in names, "producer not called"
    assert "verify_coverage" in names, "INDEPENDENT checker not called"
    assert hasattr(ratchet, "coverage_certificate")


def test_unreachable_database_is_exit_2_not_a_pass(tmp_path: Path) -> None:
    """The load-bearing test. A fail-open gate would exit 0 here."""
    broken = SCRIPT.read_text().replace(
        'SURREAL_URL = "http://localhost:8001/sql"',
        'SURREAL_URL = "http://localhost:59999/sql"',
    )
    probe = tmp_path / "unreachable.py"
    probe.write_text(broken)
    r = subprocess.run([sys.executable, str(probe)], capture_output=True, text=True)
    assert r.returncode == 2, f"expected COULD-NOT-MEASURE, got {r.returncode}"
    assert "COULD NOT MEASURE" in r.stderr
    assert "0" not in r.stdout  # no coverage number invented from a failed read


class _FakeResponse:
    """Minimal stand-in for urlopen's context manager."""

    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> bool:
        return False


@pytest.mark.parametrize(
    "payload",
    [
        [{"status": "ERR", "result": "Parse error: bad idiom"}],
        [{"status": "OK", "result": "not-a-list"}],
        [],
    ],
    ids=["statement-error", "wrong-result-shape", "empty-envelope"],
)
def test_http_200_with_a_bad_body_is_not_read_as_zero_goals(ratchet, monkeypatch, payload) -> None:
    """SurrealDB reports statement errors with HTTP 200.

    Reading `result` regardless would turn a failed query into "no goals" -- and an empty
    goal set scores 100% coverage, the most dangerous possible wrong answer: a gate that
    goes green precisely because it learned nothing.
    """
    monkeypatch.setattr(ratchet.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload))
    with pytest.raises(ratchet.CouldNotMeasureError):
        ratchet.fetch_goal_graph()


def test_a_well_formed_response_is_parsed_into_goals_and_edges(ratchet, monkeypatch) -> None:
    """Discriminating partner: a fix that raised on EVERY body would pass the test above."""
    payload = [
        {
            "status": "OK",
            "result": [
                {"id": "g1", "origin_trace_ids": ["t1", "t2"]},
                {"id": "g2", "origin_trace_ids": []},
                {"id": "g3"},
            ],
        }
    ]
    monkeypatch.setattr(ratchet.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload))
    goal_ids, edges = ratchet.fetch_goal_graph()
    assert goal_ids == ["goal:g1", "goal:g2", "goal:g3"]
    assert edges == [("trace:t1", "goal:g1"), ("trace:t2", "goal:g1")]


def test_baseline_requires_a_measured_by_stamp(ratchet, tmp_path, monkeypatch) -> None:
    """A typed baseline is a number with no evidence; ruff_ratchet learned this first."""
    typed = tmp_path / "b.json"
    typed.write_text(json.dumps({"covered": 99, "coverage_pct": 1.0, "note": "by hand"}))
    monkeypatch.setattr(ratchet, "BASELINE_PATH", typed)
    _covered, _pct, measured = ratchet.read_baseline()
    assert measured is False


def test_missing_baseline_reads_as_zero_not_as_failure(ratchet, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ratchet, "BASELINE_PATH", tmp_path / "absent.json")
    covered, pct, measured = ratchet.read_baseline()
    assert (covered, pct, measured) == (0, 0.0, False)
