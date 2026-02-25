"""Tests for context estimation module."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


WKDIR = Path(__file__).parent.parent


def run_cz(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "cohezion_engine.cli", *args],
        capture_output=True,
        text=True,
        cwd=WKDIR,
        env={**os.environ, "PYTHONPATH": str(WKDIR / "src")},
    )


def make_jsonl(tmp_path: Path, messages: list[dict]) -> Path:
    """Write a fake session JSONL file."""
    f = tmp_path / "session.jsonl"
    f.write_text("".join(json.dumps(m) + "\n" for m in messages))
    return f


class TestContextEstimation:
    def test_context_json_output_has_required_fields(self, tmp_path):
        from cohezion_engine.context import estimate_context

        result = estimate_context(session_jsonl=None, context_limit=200_000)
        assert "status" in result
        assert "percentage" in result
        assert result["status"] in ("OK", "WARNING", "CLEAR_NEEDED", "UNKNOWN")

    def test_context_ok_below_80_percent(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [
                {
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 10_000,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    }
                },
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "OK"
        assert result["percentage"] < 80.0

    def test_context_warning_between_80_and_90_percent(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 85% of 200k = 170k tokens
        jsonl = make_jsonl(
            tmp_path,
            [
                {
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 170_000,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    }
                },
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "WARNING"
        assert 80.0 <= result["percentage"] < 90.0

    def test_context_clear_needed_above_90_percent(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 92% of 200k = 184k tokens
        jsonl = make_jsonl(
            tmp_path,
            [
                {
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 184_000,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    }
                },
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "CLEAR_NEEDED"
        assert result["percentage"] >= 90.0

    def test_context_sums_cache_tokens(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 50k input + 100k cache = 150k total = 75%
        jsonl = make_jsonl(
            tmp_path,
            [
                {
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 50_000,
                            "cache_creation_input_tokens": 100_000,
                            "cache_read_input_tokens": 0,
                        },
                    }
                },
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "OK"
        assert abs(result["percentage"] - 75.0) < 1.0

    def test_context_ignores_non_assistant_messages(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [
                # user message - should be ignored
                {"message": {"role": "user", "content": "hello"}},
                {
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 10_000,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    }
                },
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert abs(result["percentage"] - 5.0) < 1.0

    def test_context_handles_missing_file_gracefully(self):
        from cohezion_engine.context import estimate_context

        result = estimate_context(
            session_jsonl=Path("/nonexistent/file.jsonl"), context_limit=200_000
        )
        assert result["status"] == "UNKNOWN"
        assert "error" in result

    def test_cli_context_json_flag(self):
        result = run_cz("context", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "status" in data
        assert "percentage" in data

    def test_context_handles_invalid_json_lines(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(
            '{"message": {"role": "assistant", "usage": {"input_tokens": 1000}}}\n'
            "invalid json line\n"
            '{"message": {"role": "assistant", "usage": {"input_tokens": 2000}}}\n'
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["percentage"] > 0

    def test_context_includes_cache_read_tokens(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [
                {
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 50_000,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 100_000,
                        },
                    }
                },
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert abs(result["percentage"] - 75.0) < 1.0

    def test_context_sums_multiple_assistant_messages(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [
                {"message": {"role": "assistant", "usage": {"input_tokens": 50_000}}},
                {"message": {"role": "assistant", "usage": {"input_tokens": 30_000}}},
                {"message": {"role": "assistant", "usage": {"input_tokens": 20_000}}},
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert abs(result["percentage"] - 50.0) < 1.0

    def test_context_handles_empty_file(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = tmp_path / "empty.jsonl"
        jsonl.write_text("")
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "OK"
        assert result["percentage"] == 0.0

    def test_context_handles_whitespace_only_lines(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = tmp_path / "whitespace.jsonl"
        jsonl.write_text("   \n\n   \n")
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "OK"
        assert result["percentage"] == 0.0

    def test_context_handles_file_read_error(self, tmp_path, monkeypatch):
        from cohezion_engine.context import estimate_context

        def mock_open(*args, **kwargs):
            raise OSError("Permission denied")

        jsonl = tmp_path / "session.jsonl"
        monkeypatch.setattr("builtins.open", mock_open)
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "UNKNOWN"
        assert "error" in result

    def test_find_active_session_jsonl_cwd_strategy(self, tmp_path, monkeypatch):
        from cohezion_engine.context import _find_active_session_jsonl

        project_slug = "test-project-slug"
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        projects_dir = tmp_path / ".claude" / "projects" / project_slug
        projects_dir.mkdir(parents=True)
        session_file = projects_dir / "session.jsonl"
        session_file.write_text(
            '{"message": {"role": "assistant", "usage": {"input_tokens": 100}}}\n'
        )

        result = _find_active_session_jsonl()
        assert result == session_file

    def test_find_active_session_jsonl_returns_none_when_no_projects(self, tmp_path, monkeypatch):
        from cohezion_engine.context import _find_active_session_jsonl

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        result = _find_active_session_jsonl()
        assert result is None

    def test_find_active_session_jsonl_fallback_to_global_recent(self, tmp_path, monkeypatch):
        from cohezion_engine.context import _find_active_session_jsonl

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir("/tmp")

        projects_dir = tmp_path / ".claude" / "projects" / "other-project"
        projects_dir.mkdir(parents=True)
        session_file = projects_dir / "old_session.jsonl"
        session_file.write_text(
            '{"message": {"role": "assistant", "usage": {"input_tokens": 100}}}\n'
        )

        result = _find_active_session_jsonl()
        assert result == session_file
