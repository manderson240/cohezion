"""Tests for the file-mode / simulation-monitoring tools of the Kaggle MCP server.

`_run` is monkeypatched everywhere — the real kaggle CLI is never invoked. Each
test asserts the exact argv the tool builds, because the kaggle 2.2.x CLI is
picky about positional-vs-flag competition arguments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cohezion.mcp import kaggle_server_mcp as server


# A real, durable (non-/tmp) regular file for the happy-path submit test.
_THIS_FILE = str(Path(__file__).resolve())

# Exact column order of `kaggle competitions submissions --csv` (kaggle 2.2.x submission_fields).
_CSV_HEADER = "ref,fileName,date,description,status,publicScore,privateScore"


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Capture every argv handed to `_run`; return a canned ok result."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, timeout: int = 60) -> dict[str, Any]:
        seen.append(list(args))
        return {"stdout": "", "stderr": "", "returncode": 0, "ok": True}

    monkeypatch.setattr(server, "_run", fake_run)
    return seen


# ── submit_file ───────────────────────────────────────────────────────────────


def test_submit_file_builds_positional_competition_argv(calls: list[list[str]]) -> None:
    result = server.kaggle_competition_submit_file("kaggriculture", _THIS_FILE, "v1 agent")
    assert result["ok"] is True
    assert calls == [
        ["competitions", "submit", "kaggriculture", "-f", _THIS_FILE, "-m", "v1 agent"],
    ]
    assert "-c" not in calls[0]


def test_submit_file_refuses_tmpfs_path(calls: list[list[str]]) -> None:
    result = server.kaggle_competition_submit_file("kaggriculture", "/tmp/submission.tar.gz", "x")
    assert result["ok"] is False
    assert "tmpfs" in result["error"]
    assert calls == []


def test_submit_file_refuses_missing_file(calls: list[list[str]]) -> None:
    missing = str(Path(__file__).parent / "does-not-exist-submission.tar.gz")
    result = server.kaggle_competition_submit_file("kaggriculture", missing, "x")
    assert result["ok"] is False
    assert "not found" in result["error"]
    assert calls == []


def test_submit_file_refuses_directory(calls: list[list[str]]) -> None:
    result = server.kaggle_competition_submit_file("kaggriculture", str(Path(__file__).parent), "x")
    assert result["ok"] is False
    assert calls == []


# ── thin wrappers ─────────────────────────────────────────────────────────────


def test_submission_limits_uses_c_flag(calls: list[list[str]]) -> None:
    server.kaggle_competition_submission_limits("kaggriculture")
    assert calls == [["competitions", "submission-limits", "-c", "kaggriculture"]]


def test_episodes_argv(calls: list[list[str]]) -> None:
    server.kaggle_competition_episodes("55844550")
    assert calls == [["competitions", "episodes", "55844550"]]


def test_replay_uses_p_flag(calls: list[list[str]]) -> None:
    server.kaggle_competition_replay("123456", "/home/u/replays")
    assert calls == [["competitions", "replay", "123456", "-p", "/home/u/replays"]]


def test_logs_uses_p_flag_and_stringifies_agent_index(calls: list[list[str]]) -> None:
    server.kaggle_competition_logs("123456", 1, "/home/u/logs")
    assert calls == [["competitions", "logs", "123456", "1", "-p", "/home/u/logs"]]


def test_pages_list_uses_c_flag(calls: list[list[str]]) -> None:
    server.kaggle_competition_pages("kaggriculture")
    assert calls == [["competitions", "pages", "-c", "kaggriculture"]]


def test_pages_with_name_adds_content_flags(calls: list[list[str]]) -> None:
    server.kaggle_competition_pages("kaggriculture", page_name="rules")
    assert calls == [
        ["competitions", "pages", "-c", "kaggriculture", "--content", "--page-name", "rules"],
    ]


# ── watch_submission ──────────────────────────────────────────────────────────


class _FakeClock:
    """Deterministic monotonic clock advanced only by (patched) time.sleep."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    fake = _FakeClock()
    monkeypatch.setattr(server.time, "monotonic", fake.monotonic)
    monkeypatch.setattr(server.time, "sleep", fake.sleep)
    return fake


def _scripted_run(
    monkeypatch: pytest.MonkeyPatch,
    statuses: list[str],
    ref: str = "55844550",
) -> list[list[str]]:
    """Patch `_run` so successive `submissions --csv` polls report *statuses* in order.

    The final status repeats forever (so a never-resolving PENDING can time out).
    Any other argv (e.g. `episodes`) returns a canned ok result.
    """
    seen: list[list[str]] = []
    polls = iter(statuses)
    last = statuses[-1]

    def fake_run(args: list[str], *, timeout: int = 60) -> dict[str, Any]:
        seen.append(list(args))
        if args[:2] == ["competitions", "submissions"]:
            status = next(polls, last)
            csv_text = f"{_CSV_HEADER}\n{ref},agent.tar.gz,2026-09-02,v1,{status},,"
            return {"stdout": csv_text, "stderr": "", "returncode": 0, "ok": True}
        return {"stdout": f"episodes for {args[-1]}", "stderr": "", "returncode": 0, "ok": True}

    monkeypatch.setattr(server, "_run", fake_run)
    return seen


def test_watch_returns_ok_after_pending_then_complete(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    seen = _scripted_run(monkeypatch, ["PENDING", "PENDING", "COMPLETE"])
    result = server.kaggle_watch_submission("kaggriculture", "55844550", max_minutes=20)

    assert result["ok"] is True
    assert result["status"] == "COMPLETE"
    assert result["timed_out"] is False
    assert result["status_line"].startswith("55844550,")
    assert result["episodes"]["stdout"] == "episodes for 55844550"
    assert clock.sleeps == [30, 30]
    assert seen[0] == ["competitions", "submissions", "-c", "kaggriculture", "--csv"]
    assert seen[-1] == ["competitions", "episodes", "55844550"]


def test_watch_returns_not_ok_on_error(monkeypatch: pytest.MonkeyPatch, clock: _FakeClock) -> None:
    seen = _scripted_run(monkeypatch, ["PENDING", "ERROR"])
    result = server.kaggle_watch_submission("kaggriculture", "55844550", max_minutes=20)

    assert result["ok"] is False
    assert result["status"] == "ERROR"
    assert result["timed_out"] is False
    # Episodes are still fetched so the validation failure can be diagnosed.
    assert seen[-1] == ["competitions", "episodes", "55844550"]


def test_watch_times_out_while_pending(monkeypatch: pytest.MonkeyPatch, clock: _FakeClock) -> None:
    seen = _scripted_run(monkeypatch, ["PENDING"])
    result = server.kaggle_watch_submission("kaggriculture", "55844550", max_minutes=2)

    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["status"] == "PENDING"
    assert result["episodes"] is None
    # 2 minutes / 30 s = 4 sleeps before the deadline check trips.
    assert clock.sleeps == [30, 30, 30, 30]
    assert all(argv[:2] == ["competitions", "submissions"] for argv in seen)


def test_watch_times_out_when_ref_never_listed(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    _scripted_run(monkeypatch, ["COMPLETE"], ref="99999999")  # a different submission
    result = server.kaggle_watch_submission("kaggriculture", "55844550", max_minutes=1)

    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["status_line"] == "not found"
    assert result["episodes"] is None
