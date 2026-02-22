"""Tests for vault_linker suggest subcommand and find_bidirectional_gaps."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


# ============================================================
# Helpers to create fixture vaults
# ============================================================

def make_md(tmp_path: Path, name: str, tags: list[str], links: list[str] = None, content: str = "") -> Path:
    """Create a markdown file in a temp vault."""
    tags_yaml = json.dumps(tags)
    links_str = "\n".join(f"[[{lnk}]]" for lnk in (links or []))
    body = f"---\ntitle: {name}\ntags: {tags_yaml}\n---\n\n{content}\n\n{links_str}\n"
    p = tmp_path / f"{name}.md"
    p.write_text(body, encoding="utf-8")
    return p


# ============================================================
# Tests for VaultParser.find_bidirectional_gaps
# ============================================================

class TestFindBidirectionalGaps:
    def test_returns_files_that_link_to_target_but_target_doesnt_link_back(self, tmp_path):
        from vault_linker.parser import VaultParser

        # paper-a links to paper-b but paper-b does NOT link back
        make_md(tmp_path, "paper-a", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-b", ["ml"])

        vp = VaultParser()
        _, link_graph = vp.walk_vault(tmp_path)

        gaps = vp.find_bidirectional_gaps(link_graph, "paper-b")
        assert "paper-a" in gaps

    def test_no_gaps_when_target_links_back(self, tmp_path):
        from vault_linker.parser import VaultParser

        # paper-a links to paper-b AND paper-b links back to paper-a
        make_md(tmp_path, "paper-a", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-b", ["ml"], links=["paper-a"])

        vp = VaultParser()
        _, link_graph = vp.walk_vault(tmp_path)

        gaps = vp.find_bidirectional_gaps(link_graph, "paper-b")
        assert "paper-a" not in gaps

    def test_empty_for_file_with_no_incoming_links(self, tmp_path):
        from vault_linker.parser import VaultParser

        make_md(tmp_path, "isolated", ["ml"])

        vp = VaultParser()
        _, link_graph = vp.walk_vault(tmp_path)

        gaps = vp.find_bidirectional_gaps(link_graph, "isolated")
        assert gaps == []

    def test_multiple_gaps_returned(self, tmp_path):
        from vault_linker.parser import VaultParser

        # paper-a and paper-c both link to paper-b, but paper-b links to neither
        make_md(tmp_path, "paper-a", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-c", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-b", ["ml"])

        vp = VaultParser()
        _, link_graph = vp.walk_vault(tmp_path)

        gaps = vp.find_bidirectional_gaps(link_graph, "paper-b")
        assert "paper-a" in gaps
        assert "paper-c" in gaps

    def test_handles_unknown_target(self, tmp_path):
        from vault_linker.parser import VaultParser

        make_md(tmp_path, "paper-a", ["ml"])

        vp = VaultParser()
        _, link_graph = vp.walk_vault(tmp_path)

        # Target doesn't exist in vault — should return empty without error
        gaps = vp.find_bidirectional_gaps(link_graph, "nonexistent")
        assert gaps == []

    def test_partial_bidirectional_with_multiple_incomers(self, tmp_path):
        from vault_linker.parser import VaultParser

        # paper-a → paper-b (gap) ; paper-b → paper-c (so paper-c IS linked back)
        make_md(tmp_path, "paper-a", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-c", ["ml"], links=["paper-b"])
        make_md(tmp_path, "paper-b", ["ml"], links=["paper-c"])

        vp = VaultParser()
        _, link_graph = vp.walk_vault(tmp_path)

        gaps = vp.find_bidirectional_gaps(link_graph, "paper-b")
        assert "paper-a" in gaps
        assert "paper-c" not in gaps


# ============================================================
# Tests for suggest_file function
# ============================================================

class TestSuggestFile:
    def test_suggests_tag_overlap_files(self, tmp_path):
        from vault_linker.__main__ import suggest_file

        make_md(tmp_path, "concept-a", ["ml", "agents"])
        make_md(tmp_path, "concept-b", ["ml"])  # shares tag, not linked

        target = tmp_path / "concept-a.md"
        output = suggest_file(tmp_path, target)

        assert "concept-b" in output.lower()

    def test_does_not_suggest_already_linked_files(self, tmp_path):
        from vault_linker.__main__ import suggest_file

        make_md(tmp_path, "concept-a", ["ml"], links=["concept-b"])
        make_md(tmp_path, "concept-b", ["ml"])

        target = tmp_path / "concept-a.md"
        output = suggest_file(tmp_path, target)

        assert "concept-b" not in output.lower()

    def test_suggests_bidirectional_gaps(self, tmp_path):
        from vault_linker.__main__ import suggest_file

        # concept-c links TO concept-a but concept-a doesn't link back
        make_md(tmp_path, "concept-a", ["ml"])
        make_md(tmp_path, "concept-c", ["other"], links=["concept-a"])

        target = tmp_path / "concept-a.md"
        output = suggest_file(tmp_path, target)

        assert "concept-c" in output.lower()

    def test_no_suggestions_for_file_with_no_tags_and_no_incoming(self, tmp_path):
        from vault_linker.__main__ import suggest_file

        make_md(tmp_path, "brand-new", [])

        target = tmp_path / "brand-new.md"
        output = suggest_file(tmp_path, target)

        # Should output a helpful message, not crash
        assert output.strip() != ""
        # And it should NOT suggest the file itself
        assert "brand-new" not in output.lower()

    def test_excludes_self_from_suggestions(self, tmp_path):
        from vault_linker.__main__ import suggest_file

        make_md(tmp_path, "self-test", ["ml"])

        target = tmp_path / "self-test.md"
        output = suggest_file(tmp_path, target)

        assert "self-test" not in output.lower()

    def test_returns_string(self, tmp_path):
        from vault_linker.__main__ import suggest_file

        make_md(tmp_path, "paper-x", ["ml"])
        target = tmp_path / "paper-x.md"

        result = suggest_file(tmp_path, target)
        assert isinstance(result, str)

    def test_limits_suggestions_to_five(self, tmp_path):
        from vault_linker.__main__ import suggest_file

        # Create target with tag shared by 10 other files
        make_md(tmp_path, "target", ["shared-tag"])
        for i in range(10):
            make_md(tmp_path, f"peer-{i:02d}", ["shared-tag"])

        target = tmp_path / "target.md"
        output = suggest_file(tmp_path, target)

        # Count lines that start with " - [["
        suggestion_lines = [l for l in output.splitlines() if "[[" in l]
        assert len(suggestion_lines) <= 5


# ============================================================
# CLI integration test for suggest subcommand
# ============================================================

class TestSuggestCLI:
    def _run(self, *args, cwd=None):
        result = subprocess.run(
            [sys.executable, "-m", "vault_linker", *args],
            capture_output=True,
            text=True,
            cwd=cwd or Path(__file__).parent.parent,
            env={"PYTHONPATH": str(Path(__file__).parent.parent), "PATH": "/usr/bin:/bin"},
        )
        return result

    def test_suggest_prints_output(self, tmp_path):
        make_md(tmp_path, "paper-x", ["ml"])
        make_md(tmp_path, "paper-y", ["ml"])

        result = self._run("suggest", str(tmp_path / "paper-x.md"), "--vault-path", str(tmp_path))
        assert result.returncode == 0

    def test_suggest_exits_nonzero_for_missing_file(self, tmp_path):
        result = self._run("suggest", str(tmp_path / "no-such-file.md"), "--vault-path", str(tmp_path))
        assert result.returncode != 0

    def test_suggest_help(self):
        result = self._run("suggest", "--help")
        assert result.returncode == 0
        assert "suggest" in result.stdout.lower() or "suggest" in result.stderr.lower()
