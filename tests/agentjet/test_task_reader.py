"""Tests for JourneyTaskReader."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cohezion.agentjet.task_reader import JourneyTaskReader


def _make_jsonl_record(skill: str, phi: float, instruction: str = "do task") -> dict:
    return {
        "instruction": instruction,
        "output": "done",
        "metadata": {
            "skill": skill,
            "phi_score": phi,
            "mission": "m1",
            "trajectory_12d": [0.1] * 12,
        },
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def test_read_missing_jsonl_falls_back_to_collector(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.jsonl"
    reader = JourneyTaskReader(jsonl_path=missing)

    fake_normalised = [
        {
            "instruction": "x",
            "output": "",
            "phi_score": 0.9,
            "skill_name": "coding",
            "mission_id": "m1",
            "trajectory_12d": [],
            "metadata": {},
        }
    ]

    # Patch _load_from_collector directly — ExperienceCollector is imported
    # inside the method body, so we patch at the method level.
    with patch.object(reader, "_load_from_collector", return_value=fake_normalised):
        tasks = reader.read(min_phi=0.7)

    assert len(tasks) == 1
    assert tasks[0]["skill_name"] == "coding"


def test_read_existing_jsonl_returns_records(tmp_path: Path) -> None:
    jsonl = tmp_path / "journeys.jsonl"
    records = [
        _make_jsonl_record("research", 0.8),
        _make_jsonl_record("coding", 0.9),
    ]
    _write_jsonl(jsonl, records)

    reader = JourneyTaskReader(jsonl_path=jsonl)
    tasks = reader.read(min_phi=0.7)

    assert len(tasks) == 2
    assert {t["skill_name"] for t in tasks} == {"research", "coding"}


def test_read_min_phi_filters_low_scores(tmp_path: Path) -> None:
    jsonl = tmp_path / "journeys.jsonl"
    records = [
        _make_jsonl_record("research", 0.9),
        _make_jsonl_record("coding", 0.5),  # below threshold
        _make_jsonl_record("writing", 0.75),
    ]
    _write_jsonl(jsonl, records)

    reader = JourneyTaskReader(jsonl_path=jsonl)
    tasks = reader.read(min_phi=0.7)

    assert len(tasks) == 2
    phi_scores = [t["phi_score"] for t in tasks]
    assert all(p >= 0.7 for p in phi_scores)


def test_read_skill_filter_returns_matching_only(tmp_path: Path) -> None:
    jsonl = tmp_path / "journeys.jsonl"
    records = [
        _make_jsonl_record("coding", 0.8),
        _make_jsonl_record("research", 0.85),
        _make_jsonl_record("Coding", 0.9),  # case-insensitive match
    ]
    _write_jsonl(jsonl, records)

    reader = JourneyTaskReader(jsonl_path=jsonl)
    tasks = reader.read(skill_filter="coding", min_phi=0.7)

    assert len(tasks) == 2
    assert all(t["skill_name"].lower() == "coding" for t in tasks)


def test_group_by_skill_groups_correctly(tmp_path: Path) -> None:
    jsonl = tmp_path / "journeys.jsonl"
    records = [
        _make_jsonl_record("coding", 0.8),
        _make_jsonl_record("coding", 0.9),
        _make_jsonl_record("research", 0.85),
    ]
    _write_jsonl(jsonl, records)

    reader = JourneyTaskReader(jsonl_path=jsonl)
    groups = reader.group_by_skill(min_phi=0.7)

    assert "coding" in groups
    assert "research" in groups
    assert len(groups["coding"]) == 2
    assert len(groups["research"]) == 1


def test_empty_jsonl_returns_empty_list(tmp_path: Path) -> None:
    jsonl = tmp_path / "empty.jsonl"
    jsonl.write_text("", encoding="utf-8")

    reader = JourneyTaskReader(jsonl_path=jsonl)
    tasks = reader.read()

    assert tasks == []


def test_read_normalises_jsonl_record_fields(tmp_path: Path) -> None:
    jsonl = tmp_path / "journeys.jsonl"
    records = [_make_jsonl_record("analysis", 0.8, instruction="Analyse X")]
    _write_jsonl(jsonl, records)

    reader = JourneyTaskReader(jsonl_path=jsonl)
    tasks = reader.read(min_phi=0.7)

    assert len(tasks) == 1
    task = tasks[0]
    assert "phi_score" in task
    assert "skill_name" in task
    assert "instruction" in task
    assert "output" in task
    assert task["instruction"] == "Analyse X"
    assert task["phi_score"] == pytest.approx(0.8)
