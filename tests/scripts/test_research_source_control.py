"""Hermetic tests for scripts/ops/research_source_control.py (the Phase 0 control-query instrument).

Every probe here targets a local stdlib server, so a failure means the PROBE is wrong, never that
arxiv/huggingface/github was down or the sandbox had no network.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "research_source_control.py"


def _load():
    spec = importlib.util.spec_from_file_location("research_source_control", _PATH)
    assert spec is not None and spec.loader is not None, f"cannot load {_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rsc = _load()


def _local(base: str, path: str, extract) -> dict:
    return rsc.probe(path, f"{base}{path}", extract, opener=rsc.LOCAL_OPENER, retry_delay=0)


def test_self_test_passes() -> None:
    assert rsc.self_test() == 0


def test_self_test_is_immune_to_a_proxy_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # A dead proxy in the environment must not turn every local case into UNREACHABLE.
    for var in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.setenv(var, "http://127.0.0.1:9")
    for var in ("no_proxy", "NO_PROXY"):
        monkeypatch.delenv(var, raising=False)
    # Load a fresh instance INSIDE the env: openers read the proxy env when constructed, so the
    # module-level instance (built before setenv) could not tell a proxy-honouring opener apart.
    assert _load().self_test() == 0


@pytest.mark.parametrize(
    ("status", "want"),
    [(406, "REFUSED"), (404, "NOT FOUND"), (418, "CLIENT ERROR"), (429, "THROTTLED")],
)
def test_4xx_is_never_an_unexplained_status(status: int, want: str) -> None:
    got = rsc._cause(status)
    assert want in got
    assert got != f"HTTP {status}"


def test_persistent_refusal_is_dead_retried_and_carries_evidence() -> None:
    with rsc._local_source() as base:
        r = _local(base, "/refuse", rsc._json_list())
    assert r["live"] is False
    assert r["status"] == 406
    assert r["attempts"] == 2
    assert r["evidence"]["headers"]["Server"].startswith("planted-refuser")
    assert "planted refusal" in r["evidence"]["body_head"]


@pytest.mark.parametrize(
    ("path", "want"),
    [("/errdict", "UNPARSEABLE"), ("/redir", "REDIRECTED")],
)
def test_200_that_is_not_the_answer_is_never_live(path: str, want: str) -> None:
    with rsc._local_source() as base:
        r = _local(base, path, rsc._json_list())
    assert r["live"] is False
    assert want in r["cause"]


def test_missing_known_answer_is_wrong_answer() -> None:
    with rsc._local_source() as base:
        r = _local(base, "/ok", rsc._known("1706.03762", rsc._json_list()))
    assert r["live"] is False
    assert "WRONG ANSWER" in r["cause"]


def test_main_exits_nonzero_and_names_the_dead_source(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    with rsc._local_source() as base:
        monkeypatch.setattr(
            rsc,
            "SOURCES",
            [
                ("ok", f"{base}/ok", rsc._json_list(), None),
                ("errdict", f"{base}/errdict", rsc._json_list(), None),
            ],
        )
        monkeypatch.setattr(rsc.sys, "argv", ["research_source_control.py"])
        code = rsc.main()
    out = capsys.readouterr().out
    assert code == 1
    assert "[OK  ] ok" in out
    assert "NOT verified: errdict" in out
