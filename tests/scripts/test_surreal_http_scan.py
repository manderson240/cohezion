"""surreal_http_scan: classification is AST-true, the ratchet holds, and both gates run it."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ci"))
import surreal_http_scan as s  # noqa: E402


def test_self_test_passes():
    assert s.self_test() == 0


def test_no_new_unchecked_writers_vs_baseline():
    unchecked, candidates = s.scan()
    assert candidates > 0
    assert set(unchecked) - s.read_baseline() == set(), (
        "new unchecked /sql writer — use checked_statements"
    )


def test_the_originating_defects_are_now_clean():
    for f in (
        "src/cohezion/compound/journey_tracker.py",
        "src/cohezion/storage/surreal_client.py",
        "cloud-vault-mcp/src/mcp_server/surrealdb_sync.py",
    ):
        assert s.classify((REPO / f).read_text()) == "clean", f


def test_comment_claiming_a_check_does_not_count():
    src = 'import urllib.request\nurllib.request.urlopen("http://h/sql")\n# status == "ERR" is checked elsewhere\n'
    assert s.classify(src) == "unchecked"


@pytest.mark.parametrize("gate", ["scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"])
def test_t3_scanner_is_wired_into_the_gate(gate):
    text = (REPO / gate).read_text()
    assert "surreal_http_scan.py --self-test" in text
    assert text.count("surreal_http_scan.py") >= 2
