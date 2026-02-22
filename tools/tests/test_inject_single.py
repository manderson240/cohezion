"""Tests for vault_linker inject-single subcommand."""

import subprocess
import sys
from pathlib import Path

import pytest


# ============================================================
# Helpers
# ============================================================

def make_md(tmp_path: Path, name: str, tags: list[str], links: list[str] = None, content: str = "") -> Path:
    """Create a markdown file in a temp vault."""
    import json
    tags_yaml = json.dumps(tags)
    links_str = "\n".join(f"[[{lnk}]]" for lnk in (links or []))
    body = f"---\ntitle: {name}\ntags: {tags_yaml}\n---\n\n{content}\n\n{links_str}\n"
    p = tmp_path / f"{name}.md"
    p.write_text(body, encoding="utf-8")
    return p


# ============================================================
# Tests for inject_single function
# ============================================================

class TestInjectSingleFunction:
    def test_injects_related_concepts_section(self, tmp_path):
        from vault_linker.__main__ import inject_single

        # concept-a and concept-b share a tag; a has no links yet
        make_md(tmp_path, "concept-a", ["ml"])
        make_md(tmp_path, "concept-b", ["ml"])

        target = tmp_path / "concept-a.md"
        result = inject_single(tmp_path, target)

        assert result == 0
        content = target.read_text(encoding="utf-8")
        assert "concept-b" in content.lower()

    def test_dry_run_does_not_modify_file(self, tmp_path):
        from vault_linker.__main__ import inject_single

        make_md(tmp_path, "concept-a", ["ml"])
        make_md(tmp_path, "concept-b", ["ml"])

        target = tmp_path / "concept-a.md"
        original = target.read_text(encoding="utf-8")

        result = inject_single(tmp_path, target, dry_run=True)

        assert result == 0
        assert target.read_text(encoding="utf-8") == original

    def test_returns_zero_when_nothing_to_inject(self, tmp_path):
        from vault_linker.__main__ import inject_single

        # Isolated file with no shared tags → nothing to inject
        make_md(tmp_path, "isolated", ["unique-tag-xyz"])

        target = tmp_path / "isolated.md"
        result = inject_single(tmp_path, target)
        assert result == 0

    def test_returns_nonzero_for_missing_file(self, tmp_path):
        from vault_linker.__main__ import inject_single

        result = inject_single(tmp_path, tmp_path / "no-such-file.md")
        assert result != 0

    def test_returns_nonzero_for_daily_file(self, tmp_path):
        from vault_linker.__main__ import inject_single

        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        daily_file = daily_dir / "2026-02-22-note.md"
        daily_file.write_text("---\ntitle: daily\ntags: [ml]\n---\n\ncontent\n", encoding="utf-8")

        result = inject_single(tmp_path, daily_file)
        assert result != 0

    def test_does_not_inject_into_other_files(self, tmp_path):
        from vault_linker.__main__ import inject_single

        make_md(tmp_path, "concept-a", ["ml"])
        make_md(tmp_path, "concept-b", ["ml"])

        target = tmp_path / "concept-a.md"
        b_original = (tmp_path / "concept-b.md").read_text(encoding="utf-8")

        inject_single(tmp_path, target)

        # concept-b should be unchanged
        assert (tmp_path / "concept-b.md").read_text(encoding="utf-8") == b_original

    def test_only_modifies_target_file_not_entire_vault(self, tmp_path):
        from vault_linker.__main__ import inject_single

        make_md(tmp_path, "concept-a", ["ml"])
        make_md(tmp_path, "concept-b", ["ml"])
        make_md(tmp_path, "concept-c", ["ml"])

        target = tmp_path / "concept-a.md"
        b_before = (tmp_path / "concept-b.md").read_text(encoding="utf-8")
        c_before = (tmp_path / "concept-c.md").read_text(encoding="utf-8")

        inject_single(tmp_path, target)

        # Other files unchanged
        assert (tmp_path / "concept-b.md").read_text(encoding="utf-8") == b_before
        assert (tmp_path / "concept-c.md").read_text(encoding="utf-8") == c_before


# ============================================================
# CLI integration tests for inject-single
# ============================================================

class TestInjectSingleCLI:
    def _run(self, *args, cwd=None):
        result = subprocess.run(
            [sys.executable, "-m", "vault_linker", *args],
            capture_output=True,
            text=True,
            cwd=cwd or Path(__file__).parent.parent,
            env={"PYTHONPATH": str(Path(__file__).parent.parent), "PATH": "/usr/bin:/bin"},
        )
        return result

    def test_inject_single_exits_zero(self, tmp_path):
        import json
        (tmp_path / "paper-x.md").write_text(
            "---\ntitle: x\ntags: [ml]\n---\n\ncontent\n", encoding="utf-8"
        )
        (tmp_path / "paper-y.md").write_text(
            "---\ntitle: y\ntags: [ml]\n---\n\ncontent\n", encoding="utf-8"
        )

        result = self._run(
            "inject-single", str(tmp_path / "paper-x.md"),
            "--vault-path", str(tmp_path)
        )
        assert result.returncode == 0

    def test_dry_run_flag_works(self, tmp_path):
        (tmp_path / "paper-x.md").write_text(
            "---\ntitle: x\ntags: [ml]\n---\n\ncontent\n", encoding="utf-8"
        )
        (tmp_path / "paper-y.md").write_text(
            "---\ntitle: y\ntags: [ml]\n---\n\ncontent\n", encoding="utf-8"
        )
        original = (tmp_path / "paper-x.md").read_text(encoding="utf-8")

        self._run(
            "inject-single", str(tmp_path / "paper-x.md"),
            "--vault-path", str(tmp_path),
            "--dry-run"
        )

        # File unchanged after dry run
        assert (tmp_path / "paper-x.md").read_text(encoding="utf-8") == original

    def test_inject_single_help(self):
        result = self._run("inject-single", "--help")
        assert result.returncode == 0
