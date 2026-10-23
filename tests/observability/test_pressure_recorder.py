"""pressure_recorder: raw lemond cgroup counters + GTT, so pressure is readable without a host shell.

Fixture values are a real lemond snapshot (2026-10-22 22:33) taken while an FLM NPU model was
resident: its 7.21 GiB of buffers appeared in BOTH shmem and file_mapped. The recorder must keep
the raw counters and must NOT publish a derived working set (anon+shmem+file_mapped read 22.6 GiB
against a 20.12 GiB memory.current — a sum that double-counts mapped shmem).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cohezion.observability import pressure_recorder as pr


GIB = 2**30


def _cgroup(tmp_path: Path, high: str = str(30 * GIB)) -> Path:
    cg = tmp_path / "lemond.service"
    cg.mkdir()
    stat = {
        "anon": 6.25,
        "file": 13.79,
        "shmem": 7.21,
        "file_mapped": 9.13,
        "active_file": 10.0,
        "inactive_file": 3.79,
        "slab": 0.5,
    }
    (cg / "memory.stat").write_text("".join(f"{k} {int(v * GIB)}\n" for k, v in stat.items()))
    (cg / "memory.current").write_text(f"{int(20.12 * GIB)}\n")
    (cg / "memory.high").write_text(f"{high}\n")
    (cg / "memory.events").write_text("low 0\nhigh 3237\nmax 0\noom 0\noom_kill 0\n")
    return cg


def test_cgroup_counters_are_raw_and_preserved(tmp_path: Path) -> None:
    got = pr._cgroup_mem(_cgroup(tmp_path))
    assert got["anon"] == pytest.approx(6.25, abs=0.01)
    assert got["shmem"] == pytest.approx(7.21, abs=0.01)
    assert got["file_mapped"] == pytest.approx(9.13, abs=0.01)
    assert got["current"] == pytest.approx(20.12, abs=0.01)
    assert got["high"] == pytest.approx(30.0, abs=0.01)
    assert got["high_events"] == 3237
    assert "slab" not in got  # only the fields pressure analysis needs


def test_no_derived_working_set_is_published(tmp_path: Path) -> None:
    got = pr._cgroup_mem(_cgroup(tmp_path))
    # A recorder that summed anon+shmem+file_mapped would report more than memory.current:
    # physically impossible, and exactly the gate defect this guards against re-encoding.
    assert not {"working_set", "working_set_gb"} & set(got)
    assert got["anon"] + got["shmem"] + got["file_mapped"] > got["current"]


def test_unlimited_memory_high_is_omitted(tmp_path: Path) -> None:
    assert "high" not in pr._cgroup_mem(_cgroup(tmp_path, high="max"))


def test_missing_cgroup_yields_empty(tmp_path: Path) -> None:
    assert pr._cgroup_mem(tmp_path / "absent.service") == {}


def test_gtt_sums_every_card(tmp_path: Path) -> None:
    for i, used in enumerate((0.72, 0.05)):
        dev = tmp_path / f"card{i}" / "device"
        dev.mkdir(parents=True)
        (dev / "mem_info_gtt_used").write_text(f"{int(used * GIB)}\n")
    assert pr._gtt_used_gb(tmp_path) == pytest.approx(0.77, abs=0.01)


def test_gtt_absent_is_none(tmp_path: Path) -> None:
    assert pr._gtt_used_gb(tmp_path) is None


def test_sample_carries_new_fields_and_survives_missing_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pr, "LEMOND_CGROUP", _cgroup(tmp_path))
    monkeypatch.setattr(pr, "DRM", tmp_path / "no-drm")
    row = pr.sample()
    assert row["lemond_cg"]["shmem"] == pytest.approx(7.21, abs=0.01)
    assert "gtt_used_gb" not in row  # absent source: omitted, not a fake zero
    json.dumps(row)  # stays one JSON line

    monkeypatch.setattr(pr, "LEMOND_CGROUP", tmp_path / "gone")
    assert pr.sample()["lemond_cg"] == {}  # never raises
