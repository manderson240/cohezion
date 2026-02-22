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

        jsonl = make_jsonl(tmp_path, [
            {"message": {"role": "assistant", "usage": {
                "input_tokens": 10_000,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            }}},
        ])
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "OK"
        assert result["percentage"] < 80.0

    def test_context_warning_between_80_and_90_percent(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 85% of 200k = 170k tokens
        jsonl = make_jsonl(tmp_path, [
            {"message": {"role": "assistant", "usage": {
                "input_tokens": 170_000,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            }}},
        ])
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "WARNING"
        assert 80.0 <= result["percentage"] < 90.0

    def test_context_clear_needed_above_90_percent(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 92% of 200k = 184k tokens
        jsonl = make_jsonl(tmp_path, [
            {"message": {"role": "assistant", "usage": {
                "input_tokens": 184_000,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            }}},
        ])
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "CLEAR_NEEDED"
        assert result["percentage"] >= 90.0

    def test_context_sums_cache_tokens(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 50k input + 100k cache = 150k total = 75%
        jsonl = make_jsonl(tmp_path, [
            {"message": {"role": "assistant", "usage": {
                "input_tokens": 50_000,
                "cache_creation_input_tokens": 100_000,
                "cache_read_input_tokens": 0,
            }}},
        ])
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["status"] == "OK"
        assert abs(result["percentage"] - 75.0) < 1.0

    def test_context_ignores_non_assistant_messages(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(tmp_path, [
            # user message - should be ignored
            {"message": {"role": "user", "content": "hello"}},
            {"message": {"role": "assistant", "usage": {
                "input_tokens": 10_000,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            }}},
        ])
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert abs(result["percentage"] - 5.0) < 1.0

    def test_context_handles_missing_file_gracefully(self):
        from cohezion_engine.context import estimate_context

        result = estimate_context(session_jsonl=Path("/nonexistent/file.jsonl"), context_limit=200_000)
        assert result["status"] == "UNKNOWN"
        assert "error" in result

    def test_cli_context_json_flag(self):
        result = run_cz("context", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "status" in data
        assert "percentage" in data
