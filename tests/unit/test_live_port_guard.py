"""The live-port guard (tests/_live_port_guard.py) must actually fail a test that dials :13305.

Discriminating: a planted test that opens a raw socket to the router must FAIL under the guard
(a neutralised guard lets it pass and this test goes red), while the tolerated cases -- a
read-only probe, an ``integration``-marked test, and the ``router_offline`` fake -- must pass.
Nothing here reaches a real router: every planted connect is refused or stubbed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]

_PLANTED = """
import importlib.util
import socket
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import tests._live_port_guard as guard


def _dial():
    s = socket.socket()
    try:
        s.connect(("127.0.0.1", 13305))
    finally:
        s.close()


def test_raw_connect_from_test_code():
    try:
        _dial()
    except ConnectionRefusedError:
        pass  # swallowing the refusal must not hide the attempt


def test_read_only_probe_is_tolerated():
    path = Path(__file__).parents[2] / "src" / "cohezion" / "probe_mod.py"
    spec = importlib.util.spec_from_file_location("planted_probe_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.is_available() is False


@pytest.mark.integration
def test_integration_marked_is_not_guarded(monkeypatch):
    def stub(self, addr):
        raise LookupError("reached the real connect")

    monkeypatch.setattr(guard, "_orig_connect", stub)
    with pytest.raises(LookupError):
        _dial()


@pytest.mark.usefixtures("router_offline")
def test_router_offline_fake_opens_no_socket():
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen("http://localhost:13305/v1/models", timeout=1)
"""

_PROBE = """
import socket


def is_available():
    s = socket.socket()
    try:
        s.connect(("127.0.0.1", 13305))
        return True
    except OSError:
        return False
    finally:
        s.close()
"""


def test_guard_fails_a_test_that_dials_the_router(tmp_path: Path) -> None:
    (tmp_path / "tests/unit").mkdir(parents=True)
    (tmp_path / "src/cohezion").mkdir(parents=True)
    (tmp_path / "tests/unit/test_planted.py").write_text(textwrap.dedent(_PLANTED))
    (tmp_path / "src/cohezion/probe_mod.py").write_text(textwrap.dedent(_PROBE))
    env = {**os.environ, "PYTHONPATH": f"{REPO}{os.pathsep}{REPO / 'src'}"}
    env.pop("PYTEST_ADDOPTS", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "tests._live_port_guard",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            "--strict-markers",
            "-o",
            "markers=integration: live",
            "-rA",
            "tests/unit/test_planted.py",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    out = proc.stdout + proc.stderr
    assert "FAILED tests/unit/test_planted.py::test_raw_connect_from_test_code" in out, out
    assert "tried to reach the live inference router" in out, out
    for name in (
        "test_read_only_probe_is_tolerated",
        "test_integration_marked_is_not_guarded",
        "test_router_offline_fake_opens_no_socket",
    ):
        assert f"PASSED tests/unit/test_planted.py::{name}" in out, out
    assert "1 failed, 3 passed" in out, out
