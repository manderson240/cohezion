"""Unit tests for scripts/hooks/experiential_learning_hook.py.

This is a `git post-commit` hook. Live integration (actually firing the fleet
subprocess + SurrealDB POST) is covered by post-commit behavior on real
commits. Here we cover the pure logic: SQL escaping, SQL value formatting,
session_id resolution, and the envelope-to-record shape.

Network / subprocess / git paths are patched out.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


_HOOKS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import experiential_learning_hook as hook


def test_escape_sql_string_escapes_single_quotes() -> None:
    assert hook._escape_sql_string("it's a test") == "it\\'s a test"


def test_escape_sql_string_escapes_backslashes_before_quotes() -> None:
    # Backslashes must be doubled FIRST so the subsequent quote-escape doesn't
    # produce `\\'` (which would be parsed as escaped-backslash + literal quote).
    assert hook._escape_sql_string("path\\to\\file's") == "path\\\\to\\\\file\\'s"


def test_sql_value_formats_bool_as_lowercase() -> None:
    assert hook._sql_value(True) == "true"
    assert hook._sql_value(False) == "false"


def test_sql_value_formats_numbers_unquoted() -> None:
    assert hook._sql_value(42) == "42"
    assert hook._sql_value(3.14) == "3.14"


def test_sql_value_formats_none_as_surreal_none() -> None:
    assert hook._sql_value(None) == "NONE"


def test_sql_value_quotes_and_escapes_strings() -> None:
    assert hook._sql_value("hello") == "'hello'"
    assert hook._sql_value("it's") == "'it\\'s'"


def test_session_id_uses_env_var_when_set(monkeypatch) -> None:
    monkeypatch.setenv("COHEZION_SESSION_ID", "sess-abc123")
    assert hook._session_id("deadbeefcafe000000") == "sess-abc123"


def test_session_id_falls_back_to_sha_prefix(monkeypatch) -> None:
    monkeypatch.delenv("COHEZION_SESSION_ID", raising=False)
    assert hook._session_id("deadbeefcafe000000") == "auto-deadbeefcafe"


def test_basic_auth_produces_expected_header() -> None:
    # root:root → cm9vdDpyb290 (base64)
    assert hook._basic_auth("root", "root") == "Basic cm9vdDpyb290"


def test_main_returns_0_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("EXPERIENTIAL_LEARNING_DISABLE", "1")
    assert hook.main() == 0


def test_main_returns_0_when_no_sha(monkeypatch) -> None:
    monkeypatch.delenv("EXPERIENTIAL_LEARNING_DISABLE", raising=False)
    with patch.object(hook, "_head_sha", return_value=""):
        assert hook.main() == 0


def test_main_returns_0_when_delegate_returns_none(monkeypatch) -> None:
    """If the delegate subprocess times out or fails, hook must exit 0 without
    touching the DB — commits must never be blocked."""
    monkeypatch.delenv("EXPERIENTIAL_LEARNING_DISABLE", raising=False)
    with (
        patch.object(hook, "_head_sha", return_value="abc123def456"),
        patch.object(hook, "_head_subject", return_value="fix: something"),
        patch.object(hook, "_head_diff_and_files", return_value=("diff content", ["f.py"])),
        patch.object(hook, "_git", return_value="/tmp"),
        patch.object(hook, "_delegate_narrative", return_value=None) as mock_delegate,
        patch.object(hook, "_insert_narrative") as mock_insert,
        patch("pathlib.Path.exists", return_value=True),
    ):
        rc = hook.main()
    assert rc == 0
    assert mock_delegate.called
    assert not mock_insert.called  # DB write must be skipped


def test_main_records_narrative_on_happy_path(monkeypatch) -> None:
    monkeypatch.delenv("EXPERIENTIAL_LEARNING_DISABLE", raising=False)
    captured_record: dict = {}

    def fake_insert(record: dict) -> bool:
        captured_record.update(record)
        return True

    with (
        patch.object(hook, "_head_sha", return_value="abc123def4567890"),
        patch.object(hook, "_head_subject", return_value="feat: add X"),
        patch.object(hook, "_head_diff_and_files", return_value=("+x\n", ["a.py", "b.py"])),
        patch.object(hook, "_git", return_value="/tmp"),
        patch.object(
            hook,
            "_delegate_narrative",
            return_value={
                "text": "The commit proves additive composition preserves test surface.",
                "model": "Gemma-4-E4B-it-GGUF",
                "lane": "igpu_rocwmma",
                "latency_ms": 450.0,
            },
        ),
        patch.object(hook, "_insert_narrative", side_effect=fake_insert),
        patch("pathlib.Path.exists", return_value=True),
    ):
        rc = hook.main()

    assert rc == 0
    assert captured_record["learning_id"] == "NARR-abc123def456"
    assert captured_record["commit_hash"] == "abc123def4567890"
    assert captured_record["commit_subject"] == "feat: add X"
    assert captured_record["files_changed"] == 2
    assert captured_record["model"] == "Gemma-4-E4B-it-GGUF"
    assert captured_record["lane"] == "igpu_rocwmma"
    assert "additive composition" in captured_record["narrative"]
