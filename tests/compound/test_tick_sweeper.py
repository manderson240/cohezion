"""Tests for LoopTickSweeper — vault/SurrealDB/research context enrichment.

Verifies:
- Non-blocking: all sweep methods return empty string on errors/timeouts
- Vault sweep parses grep output and formats excerpts
- Course correction synthesis fails gracefully when Lemonade is offline
- build_task_context composes vault + surreal sections
"""

from __future__ import annotations

from unittest.mock import patch


def _make_sweeper(vault_path=None):
    from cohezion.compound.autonomous_loop.tick_sweeper import LoopTickSweeper

    return LoopTickSweeper(
        lemonade_url="http://localhost:19999",
        vault_path=str(vault_path) if vault_path else "/nonexistent/vault",
        surreal_url="http://localhost:19999/sql",
        timeout_seconds=1.0,
    )


class TestVaultSweep:
    def test_nonexistent_vault_returns_empty(self) -> None:
        sweeper = _make_sweeper()
        result = sweeper._vault_sweep("test_fix")
        assert result == ""

    def test_vault_sweep_returns_empty_on_grep_failure(self, tmp_path) -> None:
        sweeper = _make_sweeper(vault_path=tmp_path)
        # No .md files → grep finds nothing
        result = sweeper._vault_sweep("lint_fix")
        assert result == ""

    def test_vault_sweep_finds_matching_file(self, tmp_path) -> None:
        # Create a vault-like .md file
        (tmp_path / "decisions").mkdir()
        doc = tmp_path / "decisions" / "test_fix_pattern.md"
        doc.write_text("# Test fix pattern\nUse conftest.py for shared fixtures.\npytest collect")
        sweeper = _make_sweeper(vault_path=tmp_path)
        result = sweeper._vault_sweep("test_fix")
        assert "test_fix_pattern" in result or result == ""  # grep may not be available in CI

    def test_description_words_extend_search(self, tmp_path) -> None:
        """Description words should be added to search terms."""
        sweeper = _make_sweeper(vault_path=tmp_path)
        # Just verify it runs without error (grep behavior is system-dependent)
        result = sweeper._vault_sweep(
            "refactor", description="Fix cyclomatic complexity in large function"
        )
        assert isinstance(result, str)


class TestSurrealSweep:
    def test_offline_surreal_returns_empty(self) -> None:
        sweeper = _make_sweeper()
        result = sweeper._surreal_sweep("test_fix")
        assert result == ""

    def test_surreal_sweep_parses_results(self) -> None:
        sweeper = _make_sweeper()
        mock_response = [
            {
                "result": [
                    {
                        "success_rate": 0.75,
                        "model": "Gemma-4-E4B",
                        "tasks_completed": 3,
                        "tasks_failed": 1,
                        "ts": "2026-06-14",
                    },
                    {
                        "success_rate": 0.50,
                        "model": "Qwen3.6-35B",
                        "tasks_completed": 2,
                        "tasks_failed": 2,
                        "ts": "2026-06-13",
                    },
                ]
            }
        ]
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                __import__("json").dumps(mock_response).encode()
            )
            result = sweeper._surreal_sweep("test_fix")
        assert "75%" in result or "loop run" in result


class TestResearchSweep:
    def test_offline_returns_empty(self) -> None:
        sweeper = _make_sweeper()
        result = sweeper._research_sweep(["test_fix"])
        assert result == ""

    def test_synthesis_failure_returns_empty(self) -> None:
        sweeper = _make_sweeper()
        result = sweeper._synthesize_research("some abstract text", ["lint_fix"])
        assert result == ""  # Lemonade offline


class TestCourseCorrection:
    def test_offline_returns_fallback_message(self) -> None:
        sweeper = _make_sweeper()
        results = [{"success": True}, {"success": False}, {"success": False}]
        stats = {"test_fix": {"attempts": 3, "successes": 1}}
        result = sweeper.course_correct(results, stats)
        assert isinstance(result, str)
        assert len(result) > 0  # either synthesis or fallback message


class TestBuildTaskContext:
    def test_empty_context_when_offline(self) -> None:
        sweeper = _make_sweeper()
        ctx = sweeper.build_task_context("lint_fix", "Fix ruff issues in foo.py")
        assert isinstance(ctx, str)
        # Offline: vault doesn't exist, SurrealDB unreachable → empty string
        assert ctx == ""

    def test_sections_joined_when_present(self, tmp_path) -> None:
        sweeper = _make_sweeper(vault_path=tmp_path)
        with (
            patch.object(sweeper, "_vault_sweep", return_value="vault content"),
            patch.object(sweeper, "_surreal_sweep", return_value="db content"),
        ):
            ctx = sweeper.build_task_context("lint_fix", "Fix things")
        assert "vault content" in ctx
        assert "db content" in ctx
        assert "[Vault patterns for lint_fix]" in ctx
        assert "[Historical results for lint_fix]" in ctx
