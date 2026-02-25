"""Tests for context estimation module."""

import json
import os
import subprocess
import sys
from pathlib import Path

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


class TestOutputTokenTracking:
    def test_output_tokens_included_in_result(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [
                {
                    "message": {
                        "role": "assistant",
                        "usage": {"input_tokens": 10_000, "output_tokens": 2_000},
                    }
                }
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert "output_tokens" in result
        assert result["output_tokens"] == 2_000

    def test_output_tokens_zero_when_absent(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [{"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}}],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["output_tokens"] == 0

    def test_output_tokens_summed_across_turns(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [
                {
                    "message": {
                        "role": "assistant",
                        "usage": {"input_tokens": 5_000, "output_tokens": 1_000},
                    }
                },
                {
                    "message": {
                        "role": "assistant",
                        "usage": {"input_tokens": 5_000, "output_tokens": 3_000},
                    }
                },
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["output_tokens"] == 4_000


class TestContextVelocity:
    def test_velocity_zero_when_single_turn(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [{"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}}],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert "velocity_tokens_per_turn" in result
        assert result["velocity_tokens_per_turn"] == 10_000

    def test_velocity_averages_last_n_turns(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 3 turns of 10k, 20k, 30k — velocity over last 2 = avg(20k, 30k) = 25k
        jsonl = make_jsonl(
            tmp_path,
            [
                {"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}},
                {"message": {"role": "assistant", "usage": {"input_tokens": 20_000}}},
                {"message": {"role": "assistant", "usage": {"input_tokens": 30_000}}},
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000, velocity_window=2)
        assert result["velocity_tokens_per_turn"] == 25_000

    def test_turns_remaining_computed_from_velocity(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 2 turns of 10k each → velocity = 10k, total = 20k, remaining = 180k → 18 turns
        jsonl = make_jsonl(
            tmp_path,
            [
                {"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}},
                {"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}},
            ],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert "turns_remaining" in result
        assert result["turns_remaining"] == 18

    def test_turns_remaining_none_when_velocity_zero(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = tmp_path / "empty.jsonl"
        jsonl.write_text("")
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["turns_remaining"] is None

    def test_turns_remaining_zero_when_already_at_limit(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [{"message": {"role": "assistant", "usage": {"input_tokens": 200_000}}}],
        )
        result = estimate_context(session_jsonl=jsonl, context_limit=200_000)
        assert result["turns_remaining"] == 0


class TestContextTopTurns:
    def test_top_turns_omitted_by_default(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [{"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}}],
        )
        result = estimate_context(session_jsonl=jsonl)
        assert "top_turns" not in result

    def test_top_turns_returns_sorted_descending(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [
                {"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}},
                {"message": {"role": "assistant", "usage": {"input_tokens": 30_000}}},
                {"message": {"role": "assistant", "usage": {"input_tokens": 20_000}}},
            ],
        )
        result = estimate_context(session_jsonl=jsonl, top_turns=2)
        assert "top_turns" in result
        assert len(result["top_turns"]) == 2
        assert result["top_turns"][0]["tokens"] == 30_000
        assert result["top_turns"][1]["tokens"] == 20_000

    def test_top_turns_has_turn_index(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [
                {"message": {"role": "assistant", "usage": {"input_tokens": 5_000}}},
                {"message": {"role": "assistant", "usage": {"input_tokens": 15_000}}},
            ],
        )
        result = estimate_context(session_jsonl=jsonl, top_turns=2)
        turns = {t["turn"]: t["tokens"] for t in result["top_turns"]}
        assert turns[2] == 15_000  # turn index is 1-based
        assert turns[1] == 5_000

    def test_top_turns_capped_at_available(self, tmp_path):
        from cohezion_engine.context import estimate_context

        jsonl = make_jsonl(
            tmp_path,
            [{"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}}],
        )
        result = estimate_context(session_jsonl=jsonl, top_turns=5)
        assert len(result["top_turns"]) == 1


class TestContextHypothetical:
    def test_hypothetical_fits_when_under_limit(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 10k used + 30k hypothetical = 40k / 200k = 20% → fits
        jsonl = make_jsonl(
            tmp_path,
            [{"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}}],
        )
        result = estimate_context(
            session_jsonl=jsonl, context_limit=200_000, hypothetical_tokens=30_000
        )
        assert result["fits"] is True
        assert result["status_after"] == "OK"
        assert abs(result["percentage_after"] - 20.0) < 0.1

    def test_hypothetical_not_fits_over_clear_threshold(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 10k used + 190k hypothetical = 200k / 200k = 100% → CLEAR_NEEDED
        jsonl = make_jsonl(
            tmp_path,
            [{"message": {"role": "assistant", "usage": {"input_tokens": 10_000}}}],
        )
        result = estimate_context(
            session_jsonl=jsonl, context_limit=200_000, hypothetical_tokens=190_000
        )
        assert result["fits"] is False
        assert result["status_after"] == "CLEAR_NEEDED"

    def test_hypothetical_warning_boundary(self, tmp_path):
        from cohezion_engine.context import estimate_context

        # 50k used + 120k hypothetical = 170k / 200k = 85% → WARNING, fits=True (< 90%)
        jsonl = make_jsonl(
            tmp_path,
            [{"message": {"role": "assistant", "usage": {"input_tokens": 50_000}}}],
        )
        result = estimate_context(
            session_jsonl=jsonl, context_limit=200_000, hypothetical_tokens=120_000
        )
        assert result["fits"] is True
        assert result["status_after"] == "WARNING"


class TestContextSnapshot:
    def test_write_snapshot_creates_file(self, tmp_path):
        from cohezion_engine.context import write_context_snapshot

        session_dir = tmp_path / "session"
        session_dir.mkdir()
        result = {"status": "WARNING", "percentage": 82.5}
        path = write_context_snapshot(session_dir, result)
        assert path.exists()
        import json as _json

        data = _json.loads(path.read_text())
        assert data["status"] == "WARNING"
        assert "timestamp" in data

    def test_write_snapshot_creates_snapshots_dir(self, tmp_path):
        from cohezion_engine.context import write_context_snapshot

        session_dir = tmp_path / "session"
        session_dir.mkdir()
        write_context_snapshot(session_dir, {"status": "WARNING"})
        assert (session_dir / "context-snapshots").is_dir()

    def test_read_previous_status_returns_none_when_absent(self, tmp_path):
        from cohezion_engine.context import read_previous_status

        assert read_previous_status(tmp_path) is None

    def test_read_write_current_status_roundtrip(self, tmp_path):
        from cohezion_engine.context import read_previous_status, write_current_status

        write_current_status(tmp_path, "WARNING")
        assert read_previous_status(tmp_path) == "WARNING"

    def test_context_monitor_writes_snapshot_on_warning_transition(self, tmp_path):
        """Hook writes snapshot when status transitions OK → WARNING."""
        import json as _json
        import os
        import subprocess
        import sys

        hooks_dir = Path(__file__).parent.parent / "src" / "cohezion_engine" / "hooks"
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Seed previous status as OK
        (session_dir / "context-status.txt").write_text("OK")

        # Create a JSONL that puts context at WARNING (85%)
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(
            _json.dumps({"message": {"role": "assistant", "usage": {"input_tokens": 170_000}}})
            + "\n"
        )

        env = {
            **os.environ,
            "CZ_TEST_SESSION_JSONL": str(jsonl),
            "CZ_TEST_SESSION_DIR": str(session_dir),
        }
        result = subprocess.run(
            [sys.executable, str(hooks_dir / "context_monitor.py")],
            input=_json.dumps({}),
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        snapshots = list((session_dir / "context-snapshots").glob("*.json"))
        assert len(snapshots) == 1

    def test_context_monitor_no_snapshot_on_repeat_warning(self, tmp_path):
        """Hook does NOT write snapshot when status stays WARNING → WARNING."""
        import json as _json
        import os
        import subprocess
        import sys

        hooks_dir = Path(__file__).parent.parent / "src" / "cohezion_engine" / "hooks"
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        (session_dir / "context-status.txt").write_text("WARNING")

        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(
            _json.dumps({"message": {"role": "assistant", "usage": {"input_tokens": 170_000}}})
            + "\n"
        )

        env = {
            **os.environ,
            "CZ_TEST_SESSION_JSONL": str(jsonl),
            "CZ_TEST_SESSION_DIR": str(session_dir),
        }
        subprocess.run(
            [sys.executable, str(hooks_dir / "context_monitor.py")],
            input=_json.dumps({}),
            capture_output=True,
            text=True,
            env=env,
        )
        snapshots_dir = session_dir / "context-snapshots"
        assert not snapshots_dir.exists() or len(list(snapshots_dir.glob("*.json"))) == 0
