"""A sandbox child started as root runs the untrusted code as ``nobody``.

rlimits do not bind root: with NPROC=0 a root child could still fork (measured
2026-11-06), and with CAP_SYS_RESOURCE it can raise every hard limit back.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

from cohezion.compound.sandboxed_exec import run_untrusted


CHILD = Path(__file__).resolve().parents[2] / "src" / "cohezion" / "compound" / "_sandbox_child.py"

PROBE = """
import collections
os = collections._sys.modules["os"]
def f():
    try:
        pid = os.fork()
    except Exception:  # OSError is not among the sandbox builtins
        return [os.getuid(), "fork blocked"]
    if pid == 0:
        os._exit(0)
    os.waitpid(pid, 0)
    return [os.getuid(), "fork ok"]
"""


@pytest.mark.skipif(os.geteuid() != 0, reason="only meaningful when the tests run as root")
def test_root_child_runs_untrusted_code_unprivileged():
    result = run_untrusted(PROBE, call="f")
    assert result.ok, result.error
    uid, fork = result.value
    assert uid != 0
    assert fork == "fork blocked"


def _child_module():
    spec = importlib.util.spec_from_file_location("_cz_child_under_test", CHILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeOS:
    def __init__(self, euid: int, setuid_sticks: bool = True, can_regain: bool = False):
        self.uid = self.euid = euid
        self.setuid_sticks = setuid_sticks
        self.can_regain = can_regain
        self.calls: list[str] = []

    def geteuid(self):
        return self.euid

    def getuid(self):
        return self.uid

    def setgroups(self, groups):
        self.calls.append("setgroups")

    def setgid(self, gid):
        self.calls.append("setgid")

    def setuid(self, uid):
        self.calls.append(f"setuid({uid})")
        if uid == 0:
            if not self.can_regain:
                raise PermissionError("not root")
            self.uid = self.euid = 0
        elif self.setuid_sticks:
            self.uid = self.euid = uid


def test_non_root_child_is_left_alone(monkeypatch):
    child = _child_module()
    fake = _FakeOS(euid=1000)
    monkeypatch.setattr(child, "os", fake)
    child._drop_root()
    assert fake.calls == []


def test_root_child_drops_to_nobody(monkeypatch):
    child = _child_module()
    fake = _FakeOS(euid=0)
    monkeypatch.setattr(child, "os", fake)
    child._drop_root()
    assert fake.uid == child._NOBODY
    assert fake.calls[:3] == ["setgroups", "setgid", f"setuid({child._NOBODY})"]


def test_drop_that_did_not_take_is_refused(monkeypatch):
    child = _child_module()
    monkeypatch.setattr(child, "os", _FakeOS(euid=0, setuid_sticks=False))
    with pytest.raises(OSError, match="still root"):
        child._drop_root()


def test_drop_that_can_be_undone_is_refused(monkeypatch):
    child = _child_module()
    monkeypatch.setattr(child, "os", _FakeOS(euid=0, can_regain=True))
    with pytest.raises(OSError, match="regain root"):
        child._drop_root()
