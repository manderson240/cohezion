"""Hermetic tests for scripts/ops/research_source_control.py (the Phase 0 control-query instrument).

Every probe here targets a local stdlib server, so a failure means the PROBE is wrong, never that
arxiv/huggingface/github was down or the sandbox had no network.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "research_source_control.py"
_spec = importlib.util.spec_from_file_location("research_source_control", _PATH)
assert _spec is not None and _spec.loader is not None, f"cannot load {_PATH}"
rsc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rsc)


def test_self_test_passes() -> None:
    assert rsc.self_test() == 0


@pytest.mark.parametrize(
    ("status", "want"),
    [(406, "REFUSED"), (404, "NOT FOUND"), (418, "CLIENT ERROR"), (429, "THROTTLED")],
)
def test_4xx_is_never_an_unexplained_status(status: int, want: str) -> None:
    got = rsc._cause(status)
    assert want in got
    assert got != f"HTTP {status}"


def test_refusal_is_dead_and_carries_evidence() -> None:
    with rsc._local_source() as base:
        r = rsc.probe("refused", f"{base}/refuse", rsc._json_len(None))
    assert r["live"] is False
    assert r["status"] == 406
    assert r["evidence"]["headers"]["Server"].startswith("planted-refuser")
    assert "planted refusal" in r["evidence"]["body_head"]


def test_main_exits_nonzero_and_prints_evidence_when_a_source_refuses(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with rsc._local_source() as base:
        monkeypatch.setattr(
            rsc,
            "SOURCES",
            [
                ("ok", f"{base}/ok", rsc._json_len(None), None),
                ("refused", f"{base}/refuse", rsc._json_len(None), None),
            ],
        )
        monkeypatch.setattr(rsc.sys, "argv", ["research_source_control.py"])
        code = rsc.main()
    out = capsys.readouterr().out
    assert code == 1
    assert "server=planted-refuser" in out
    assert "NOT verified: refused" in out
