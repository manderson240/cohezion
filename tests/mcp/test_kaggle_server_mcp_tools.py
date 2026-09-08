"""Tests for the file-mode / simulation-monitoring tools of the Kaggle MCP server.

`_run` is monkeypatched everywhere — the real kaggle CLI is never invoked. Each
test asserts the exact argv the tool builds, because the kaggle 2.2.x CLI is
picky about positional-vs-flag competition arguments.
"""

from __future__ import annotations

import csv
import io
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


def test_submit_file_refuses_flag_like_message(calls: list[list[str]]) -> None:
    result = server.kaggle_competition_submit_file("kaggriculture", _THIS_FILE, "-v")
    assert result["ok"] is False
    assert "flag" in result["error"]
    assert calls == []


def test_submit_file_allows_dash_inside_multi_token_message(calls: list[list[str]]) -> None:
    # A leading dash in a real sentence is fine; only single tokens are refused.
    server.kaggle_competition_submit_file("kaggriculture", _THIS_FILE, "-- retry after fix")
    assert calls and calls[0][-1] == "-- retry after fix"


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


def test_pages_refuses_flag_like_page_name(calls: list[list[str]]) -> None:
    result = server.kaggle_competition_pages("kaggriculture", page_name="--all")
    assert result["ok"] is False
    assert "flag" in result["error"]
    assert calls == []


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


_DESCRIPTION = "v1"


def _scripted_run(
    monkeypatch: pytest.MonkeyPatch,
    statuses: list[str],
    ref: str = "55844550",
    header: str = _CSV_HEADER,
    description: str = _DESCRIPTION,
) -> tuple[list[list[str]], list[int]]:
    """Patch `_run` so successive `submissions --csv` polls report *statuses* in order.

    The final status repeats forever (so a never-resolving PENDING can time out).
    Any other argv (e.g. `episodes`) returns a canned ok result. Rows are built
    with csv.writer so quoted descriptions match the real CLI output shape.
    Returns (argv list, timeout list) in call order.
    """
    seen: list[list[str]] = []
    timeouts: list[int] = []
    polls = iter(statuses)
    last = statuses[-1]

    def fake_run(args: list[str], *, timeout: int = 60) -> dict[str, Any]:
        seen.append(list(args))
        timeouts.append(timeout)
        if args[:2] == ["competitions", "submissions"]:
            status = next(polls, last)
            buf = io.StringIO()
            csv.writer(buf).writerow(
                [ref, "agent.tar.gz", "2026-09-02", description, status, "", ""]
            )
            csv_text = f"{header}\n{buf.getvalue()}"
            return {"stdout": csv_text, "stderr": "", "returncode": 0, "ok": True}
        return {"stdout": f"episodes for {args[-1]}", "stderr": "", "returncode": 0, "ok": True}

    monkeypatch.setattr(server, "_run", fake_run)
    return seen, timeouts


def test_watch_returns_ok_after_pending_then_complete(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    seen, _ = _scripted_run(monkeypatch, ["PENDING", "PENDING", "COMPLETE"])
    # 1.5 min budget: polls at t=0, 30, 60 — COMPLETE arrives on the third.
    result = server.kaggle_watch_submission("kaggriculture", "55844550", max_minutes=1.5)

    assert result["ok"] is True
    assert result["status"] == "COMPLETE"
    assert result["timed_out"] is False
    assert result["status_line"].startswith("55844550,")
    assert result["episodes"]["stdout"] == "episodes for 55844550"
    assert clock.sleeps == [30, 30]
    assert seen[0] == ["competitions", "submissions", "-c", "kaggriculture", "--csv"]
    assert seen[-1] == ["competitions", "episodes", "55844550"]


def test_watch_resolves_quoted_description_with_commas(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    description = "v2: modal-route tape, review-fixed, 154-0"
    seen, _ = _scripted_run(monkeypatch, ["COMPLETE"], description=description)
    result = server.kaggle_watch_submission("kaggriculture", "55844550")

    assert result["ok"] is True
    assert result["status"] == "COMPLETE"
    # status_line round-trips through csv: the quoted description is one field again.
    (row,) = csv.reader(io.StringIO(result["status_line"]))
    assert row == ["55844550", "agent.tar.gz", "2026-09-02", description, "COMPLETE", "", ""]
    assert seen[-1] == ["competitions", "episodes", "55844550"]


def test_watch_returns_not_ok_on_error(monkeypatch: pytest.MonkeyPatch, clock: _FakeClock) -> None:
    seen, _ = _scripted_run(monkeypatch, ["PENDING", "ERROR"])
    result = server.kaggle_watch_submission("kaggriculture", "55844550")

    assert result["ok"] is False
    assert result["status"] == "ERROR"
    assert result["timed_out"] is False
    # Episodes are still fetched so the validation failure can be diagnosed.
    assert seen[-1] == ["competitions", "episodes", "55844550"]


def test_watch_times_out_while_pending_and_caps_budget(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    seen, timeouts = _scripted_run(monkeypatch, ["PENDING"])
    result = server.kaggle_watch_submission("kaggriculture", "55844550", max_minutes=20)

    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["status"] == "PENDING"
    assert result["episodes"] is None
    assert result["next_poll_after_s"] == 30
    # max_minutes=20 is capped to 1.5 min: polls at t=0, 30, 60; no sleep past deadline.
    assert clock.sleeps == [30, 30]
    assert all(argv[:2] == ["competitions", "submissions"] for argv in seen)
    # Poll timeouts shrink with the remaining budget: 90+10, 60+10, 30+10.
    assert timeouts == [100, 70, 40]
    assert clock.now - 1000.0 <= 1.5 * 60 + 10


def test_watch_allow_long_lifts_cap(monkeypatch: pytest.MonkeyPatch, clock: _FakeClock) -> None:
    seen, _ = _scripted_run(monkeypatch, ["PENDING"])
    result = server.kaggle_watch_submission(
        "kaggriculture", "55844550", max_minutes=2, allow_long=True
    )

    assert result["timed_out"] is True
    # 2 min budget: polls at t=0, 30, 60, 90.
    assert len(seen) == 4
    assert clock.sleeps == [30, 30, 30]


def test_watch_times_out_when_ref_never_listed(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    _scripted_run(monkeypatch, ["COMPLETE"], ref="99999999")  # a different submission
    result = server.kaggle_watch_submission("kaggriculture", "55844550", max_minutes=1)

    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["status"] == "PENDING"
    assert result["status_line"] == "not found"
    assert result["episodes"] is None


def test_watch_errors_when_status_column_missing(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    no_status_header = "ref,fileName,date,description,publicScore,privateScore"
    seen, _ = _scripted_run(monkeypatch, ["COMPLETE"], header=no_status_header)
    result = server.kaggle_watch_submission("kaggriculture", "55844550")

    assert result["ok"] is False
    assert result["timed_out"] is False
    assert "status column missing" in result["error"]
    assert result["episodes"] is None
    assert len(seen) == 1  # returned on the first poll, no sleeping, no episodes call
    assert clock.sleeps == []
