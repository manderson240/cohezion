"""A per-order timeout is UNKNOWN, not a defect and not a failed gate (ops MINOR).

The gate took ~8 minutes at 8 jobs with a 180 s per-order timeout; on a contended box one
order timing out turned the whole landing gate red ("worker subprocess errors"). A
timeout says nothing about import cycles: it is retried once, then reported as UNKNOWN.
It must not count as a defect, and it must not make a baseline entry look "fixed"
(that would demand a --update that bakes a stale baseline in).
"""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "hidden_import_cycle_scan.py"


@pytest.fixture()
def scanmod():
    spec = importlib.util.spec_from_file_location("_hics", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _res(entries=(), unknown=0, errors=0, runs=20):
    return {
        "packages": 1,
        "runs": runs,
        "worker_errors": [{"order": ["x"], "error": "worker exit 1: boom"}] * errors,
        "unknown_orders": [
            {"order": [f"p{i}"], "unknown": "timeout after 180s"} for i in range(unknown)
        ],
        "counts": {},
        "entries": [{"key": k, "category": "defect"} for k in entries],
    }


def test_timeout_is_unknown_and_passes_the_gate(scanmod, monkeypatch):
    monkeypatch.setattr(scanmod, "_read_baseline", lambda: {"a:X"})
    assert scanmod.gate(_res(entries=["a:X"], unknown=1)) == 0


def test_timeout_does_not_make_a_baseline_entry_look_fixed(scanmod, monkeypatch):
    monkeypatch.setattr(scanmod, "_read_baseline", lambda: {"a:X", "b:Y"})
    assert scanmod.gate(_res(entries=["a:X"], unknown=2)) == 0


def test_new_defect_still_fails_despite_timeouts(scanmod, monkeypatch):
    monkeypatch.setattr(scanmod, "_read_baseline", lambda: {"a:X"})
    assert scanmod.gate(_res(entries=["a:X", "c:Z"], unknown=1)) == 1


def test_real_worker_crash_still_fails(scanmod, monkeypatch):
    monkeypatch.setattr(scanmod, "_read_baseline", lambda: {"a:X"})
    assert scanmod.gate(_res(entries=["a:X"], errors=1)) == 1


def test_mostly_unknown_measurement_is_not_a_pass(scanmod, monkeypatch):
    monkeypatch.setattr(scanmod, "_read_baseline", lambda: {"a:X"})
    assert scanmod.gate(_res(entries=["a:X"], unknown=15, runs=20)) == 1


def test_a_hanging_import_is_retried_then_recorded_as_unknown(scanmod, tmp_path):
    pkg = tmp_path / "zzslow"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        textwrap.dedent("""\
        import contextlib
        with contextlib.suppress(Exception):
            from zzslow.hang import H as H
        """)
    )
    (pkg / "hang.py").write_text("import time\ntime.sleep(60)\nclass H: pass\n")
    res = scanmod.scan(src=tmp_path, root_pkg="zzslow", hubs=(), jobs=1, timeout_s=1, retries=1)
    assert res["worker_errors"] == []
    assert len(res["unknown_orders"]) == 1
    assert res["unknown_orders"][0]["attempts"] == 2
    assert res["entries"] == []
