"""Tests for core vault operations."""

import pytest

from mcp_server.vault_ops import VaultOps


@pytest.fixture
def vault(tmp_path):
    """Create a temporary vault with test content."""
    # Create directories
    (tmp_path / "decisions").mkdir()
    (tmp_path / "patterns").mkdir()
    (tmp_path / "experiments").mkdir()
    (tmp_path / "projects").mkdir()

    # Create test notes
    (tmp_path / "decisions" / "test-decision.md").write_text(
        "---\ndate: 2025-01-15\nproject: testproj\ntags: [decision, testproj]\n---\n"
        "# Use Python for MCP\n\n## Context\nWe need a server.\n\n"
        "## Decision\nUse Python.\n"
    )
    (tmp_path / "patterns" / "retry-pattern.md").write_text(
        "---\ndate: 2025-01-10\ntags: [pattern, devops]\n---\n"
        "# Retry with Backoff\n\n## Solution\nExponential backoff with jitter.\n"
    )
    (tmp_path / "projects" / "testproj.md").write_text(
        "---\ntags: [project, testproj]\n---\n"
        "# Test Project\n\nA project for testing.\n\n"
        "## Key Decisions\n- [[test-decision]]\n"
    )

    return VaultOps(str(tmp_path))


class TestRead:
    def test_read_existing(self, vault):
        content = vault.read("decisions/test-decision.md")
        assert "Use Python for MCP" in content

    def test_read_missing(self, vault):
        with pytest.raises(FileNotFoundError):
            vault.read("nonexistent.md")


class TestWrite:
    def test_write_new(self, vault):
        vault.write("inbox/new-note.md", "# New Note\n\nContent here.")
        content = vault.read("inbox/new-note.md")
        assert "New Note" in content

    def test_write_creates_dirs(self, vault):
        vault.write("deep/nested/dir/note.md", "# Deep")
        content = vault.read("deep/nested/dir/note.md")
        assert "Deep" in content

    def test_write_overwrite(self, vault):
        vault.write("decisions/test-decision.md", "# Overwritten")
        content = vault.read("decisions/test-decision.md")
        assert content == "# Overwritten"


class TestEdit:
    def test_find_replace(self, vault):
        result = vault.edit(
            "decisions/test-decision.md",
            [
                {
                    "operation": "find_replace",
                    "find": "Use Python.",
                    "replace": "Use Python with FastMCP.",
                }
            ],
        )
        content = vault.read("decisions/test-decision.md")
        assert "FastMCP" in content
        assert "Replaced" in result

    def test_append(self, vault):
        vault.edit(
            "decisions/test-decision.md",
            [{"operation": "append", "text": "## Addendum\nMore info."}],
        )
        content = vault.read("decisions/test-decision.md")
        assert "Addendum" in content

    def test_prepend(self, vault):
        vault.edit(
            "decisions/test-decision.md",
            [{"operation": "prepend", "text": "<!-- top -->"}],
        )
        content = vault.read("decisions/test-decision.md")
        assert content.startswith("<!-- top -->")

    def test_insert_at_heading(self, vault):
        vault.edit(
            "decisions/test-decision.md",
            [
                {
                    "operation": "insert_at_heading",
                    "heading": "Context",
                    "text": "\nAdditional context here.",
                }
            ],
        )
        content = vault.read("decisions/test-decision.md")
        assert "Additional context here." in content


class TestDelete:
    def test_delete_existing(self, vault):
        vault.write("inbox/temp.md", "temp")
        vault.delete("inbox/temp.md")
        with pytest.raises(FileNotFoundError):
            vault.read("inbox/temp.md")

    def test_delete_missing(self, vault):
        with pytest.raises(FileNotFoundError):
            vault.delete("nonexistent.md")


class TestListDir:
    def test_list_root(self, vault):
        items = vault.list_dir()
        assert any("decisions/" in i for i in items)

    def test_list_recursive(self, vault):
        items = vault.list_dir("", recursive=True)
        assert any("decisions/test-decision.md" in i for i in items)

    def test_list_subdirectory(self, vault):
        items = vault.list_dir("decisions")
        assert "decisions/test-decision.md" in items


class TestSearch:
    def test_search_finds_content(self, vault):
        results = vault.search("Python")
        assert len(results) > 0
        assert any("decisions/test-decision.md" in r["path"] for r in results)

    def test_search_case_insensitive(self, vault):
        results = vault.search("python")
        assert len(results) > 0

    def test_search_in_folder(self, vault):
        results = vault.search("Python", scope="folder", folder="decisions")
        assert len(results) > 0
        assert all(r["path"].startswith("decisions/") for r in results)

    def test_search_no_results(self, vault):
        results = vault.search("xyznonexistent123")
        assert len(results) == 0


class TestPathSafety:
    def test_traversal_blocked(self, vault):
        with pytest.raises(ValueError, match="traversal|escapes"):
            vault.read("../../etc/passwd")

    def test_traversal_blocked_on_write(self, vault):
        with pytest.raises(ValueError, match="traversal|escapes"):
            vault.write("../outside.md", "malicious")
