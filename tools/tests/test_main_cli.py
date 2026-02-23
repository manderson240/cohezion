"""Tests for vault_linker.__main__ CLI functions and dispatch."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _vault_with_notes(tmp_path, notes: dict) -> Path:
    """Write markdown files into tmp_path and return it as vault_path."""
    for name, (tags, links) in notes.items():
        tags_yaml = str(tags).replace("'", '"')
        links_str = "\n".join(f"[[{lnk}]]" for lnk in links)
        body = f"---\ntitle: {name}\ntags: {tags_yaml}\n---\n\n{links_str}\n"
        (tmp_path / f"{name}.md").write_text(body, encoding="utf-8")
    return tmp_path


# ── analyze ───────────────────────────────────────────────────────────────────

class TestAnalyze:
    def test_returns_zero_and_writes_report(self, tmp_path):
        from vault_linker.__main__ import analyze

        _vault_with_notes(tmp_path, {
            "note-a": (["ml"], []),
            "note-b": (["ml"], ["note-a"]),
        })
        result = analyze(tmp_path)
        assert result == 0
        report = tmp_path / "tools" / "vault_health_report.md"
        assert report.exists()
        assert len(report.read_text()) > 0

    def test_empty_vault_returns_zero(self, tmp_path):
        from vault_linker.__main__ import analyze

        result = analyze(tmp_path)
        assert result == 0


# ── _is_read_only ─────────────────────────────────────────────────────────────

class TestIsReadOnly:
    def test_daily_dir_is_read_only(self, tmp_path):
        from vault_linker.__main__ import _is_read_only

        daily_file = tmp_path / "daily" / "2026-01-01.md"
        assert _is_read_only(daily_file, tmp_path) is True

    def test_decisions_dir_is_not_read_only(self, tmp_path):
        from vault_linker.__main__ import _is_read_only

        decisions_file = tmp_path / "decisions" / "2026-01-01-foo.md"
        assert _is_read_only(decisions_file, tmp_path) is False

    def test_file_outside_vault_returns_false(self, tmp_path):
        from vault_linker.__main__ import _is_read_only

        outside = Path("/tmp/some-other-file.md")
        assert _is_read_only(outside, tmp_path) is False


# ── fix ───────────────────────────────────────────────────────────────────────

class TestFix:
    def test_dry_run_returns_zero_no_writes(self, tmp_path):
        from vault_linker.__main__ import fix

        _vault_with_notes(tmp_path, {
            "alpha": (["security"], []),
            "beta":  (["security"], []),
        })
        result = fix(tmp_path, dry_run=True)
        assert result == 0

    def test_live_run_returns_zero(self, tmp_path):
        from vault_linker.__main__ import fix

        _vault_with_notes(tmp_path, {
            "alpha": (["security"], []),
            "beta":  (["security"], []),
        })
        result = fix(tmp_path, dry_run=False)
        assert result == 0


# ── suggest ───────────────────────────────────────────────────────────────────

class TestSuggest:
    def test_missing_file_returns_one(self, tmp_path):
        from vault_linker.__main__ import suggest

        result = suggest(tmp_path, tmp_path / "nonexistent.md")
        assert result == 1

    def test_existing_file_returns_zero(self, tmp_path, make_md):
        from vault_linker.__main__ import suggest

        make_md("target", ["ml"])
        make_md("other", ["ml"])
        target = tmp_path / "target.md"
        result = suggest(tmp_path, target)
        assert result == 0

    def test_suggest_propagates_exception_as_one(self, tmp_path, make_md):
        from vault_linker.__main__ import suggest

        target = make_md("target", ["ml"])
        with patch("vault_linker.__main__.suggest_file", side_effect=RuntimeError("boom")):
            result = suggest(tmp_path, target)
        assert result == 1


# ── inject_single (additional cases) ─────────────────────────────────────────

class TestInjectSingleExtra:
    def test_missing_file_returns_one(self, tmp_path):
        from vault_linker.__main__ import inject_single

        result = inject_single(tmp_path, tmp_path / "ghost.md")
        assert result == 1

    def test_daily_file_returns_one(self, tmp_path):
        from vault_linker.__main__ import inject_single

        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        f = daily_dir / "2026-01-01.md"
        f.write_text("---\ntitle: log\ntags: []\n---\n", encoding="utf-8")
        result = inject_single(tmp_path, f)
        assert result == 1

    def test_no_changes_returns_zero(self, tmp_path, make_md):
        from vault_linker.__main__ import inject_single

        # Solo note with no peers — nothing to inject
        target = make_md("solo", ["unique-tag-xyz"])
        result = inject_single(tmp_path, target)
        assert result == 0

    def test_dry_run_shows_diff_and_returns_zero(self, tmp_path, make_md):
        from vault_linker.__main__ import inject_single

        make_md("peer-a", ["shared"])
        make_md("peer-b", ["shared"])
        target = tmp_path / "peer-a.md"
        result = inject_single(tmp_path, target, dry_run=True)
        assert result == 0


# ── main() dispatch ───────────────────────────────────────────────────────────

class TestMainDispatch:
    def test_no_command_prints_help_returns_zero(self, tmp_path):
        from vault_linker.__main__ import main

        with patch("sys.argv", ["vault_linker"]):
            result = main()
        assert result == 0

    def test_analyze_command_dispatches(self, tmp_path):
        from vault_linker.__main__ import main

        with patch("sys.argv", ["vault_linker", "analyze", "--vault-path", str(tmp_path)]):
            with patch("vault_linker.__main__.analyze", return_value=0) as mock_analyze:
                result = main()
        mock_analyze.assert_called_once_with(tmp_path.resolve())
        assert result == 0

    def test_fix_command_dispatches(self, tmp_path):
        from vault_linker.__main__ import main

        with patch("sys.argv", ["vault_linker", "fix", "--vault-path", str(tmp_path), "--dry-run"]):
            with patch("vault_linker.__main__.fix", return_value=0) as mock_fix:
                result = main()
        mock_fix.assert_called_once_with(tmp_path.resolve(), dry_run=True)

    def test_suggest_command_dispatches(self, tmp_path, make_md):
        from vault_linker.__main__ import main

        target = make_md("note", ["ml"])
        with patch("sys.argv", ["vault_linker", "suggest", str(target), "--vault-path", str(tmp_path)]):
            with patch("vault_linker.__main__.suggest", return_value=0) as mock_suggest:
                result = main()
        mock_suggest.assert_called_once()

    def test_inject_single_command_dispatches(self, tmp_path, make_md):
        from vault_linker.__main__ import main

        target = make_md("note", ["ml"])
        with patch("sys.argv", ["vault_linker", "inject-single", str(target), "--vault-path", str(tmp_path)]):
            with patch("vault_linker.__main__.inject_single", return_value=0) as mock_inject:
                result = main()
        mock_inject.assert_called_once()
