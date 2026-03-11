"""Tests for Claude Code hook scripts."""

import json
import os
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).parent.parent / "src" / "cohezion_engine" / "hooks"
PYTHON = sys.executable


def run_hook(
    hook_file: str, stdin_data: dict, env_overrides: dict | None = None
) -> subprocess.CompletedProcess:
    """Run a hook script with JSON stdin."""
    env = {**os.environ}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [PYTHON, str(HOOKS_DIR / hook_file)],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        env=env,
    )


class TestFileChecker:
    def test_passes_small_file(self, tmp_path):
        small_file = tmp_path / "small.py"
        small_file.write_text("x = 1\n" * 10)
        result = run_hook(
            "file_checker.py",
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(small_file)},
            },
        )
        assert result.returncode == 0

    def test_warns_file_over_300_lines(self, tmp_path):
        big_file = tmp_path / "big.py"
        big_file.write_text("x = 1\n" * 310)
        result = run_hook(
            "file_checker.py",
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(big_file)},
            },
        )
        # exit 0 with warning (non-blocking)
        assert result.returncode == 0
        assert (
            "300" in result.stdout
            or "WARNING" in result.stdout
            or "warning" in result.stdout.lower()
        )

    def test_blocks_file_over_500_lines(self, tmp_path):
        huge_file = tmp_path / "huge.py"
        huge_file.write_text("x = 1\n" * 510)
        result = run_hook(
            "file_checker.py",
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(huge_file)},
            },
        )
        # exit 2 blocks with message
        assert result.returncode == 2
        assert "500" in result.stdout or "lines" in result.stdout.lower()

    def test_skips_non_file_tool(self, tmp_path):
        result = run_hook(
            "file_checker.py",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
            },
        )
        assert result.returncode == 0

    def test_skips_test_files(self, tmp_path):
        test_file = tmp_path / "test_big.py"
        test_file.write_text("x = 1\n" * 600)
        result = run_hook(
            "file_checker.py",
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(test_file)},
            },
        )
        assert result.returncode == 0  # test files exempt


class TestTDDEnforcer:
    def test_passes_when_test_file_modified(self, tmp_path):
        test_file = tmp_path / "test_mymodule.py"
        result = run_hook(
            "tdd_enforcer.py",
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(test_file)},
            },
        )
        assert result.returncode == 0

    def test_warns_when_production_code_without_tests(self, tmp_path):
        prod_file = tmp_path / "mymodule.py"
        result = run_hook(
            "tdd_enforcer.py",
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(prod_file)},
            },
        )
        # Non-blocking warning - exit 0 with message
        assert result.returncode == 0

    def test_skips_non_python_files(self, tmp_path):
        md_file = tmp_path / "README.md"
        result = run_hook(
            "tdd_enforcer.py",
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(md_file)},
            },
        )
        assert result.returncode == 0


class TestContextMonitor:
    def test_outputs_ok_status(self, tmp_path):
        # Minimal JSONL with very few tokens
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 1000,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    }
                }
            )
            + "\n"
        )
        result = run_hook(
            "context_monitor.py",
            {
                "tool_name": "Bash",
                "tool_input": {},
            },
            env_overrides={"CZ_TEST_SESSION_JSONL": str(jsonl)},
        )
        assert result.returncode == 0

    def test_outputs_clear_needed_at_high_usage(self, tmp_path):
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 185_000,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    }
                }
            )
            + "\n"
        )
        result = run_hook(
            "context_monitor.py",
            {
                "tool_name": "Bash",
                "tool_input": {},
            },
            env_overrides={"CZ_TEST_SESSION_JSONL": str(jsonl)},
        )
        assert result.returncode == 0
        assert "CLEAR_NEEDED" in result.stdout or "90" in result.stdout
