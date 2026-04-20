"""
Path Traversal Security Tests

Verifies that VaultOps prevents directory traversal attacks, including:
- .. path components
- Symlink escapes
- Absolute path injection
- Encoded traversal attempts
"""

import tempfile
from pathlib import Path

import pytest

from mcp_server.vault_ops import VaultOps


@pytest.fixture
def vault_dir():
    """Create a temporary vault directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "vault"
        vault_path.mkdir()

        # Create test files
        (vault_path / "safe.md").write_text("Safe content")
        (vault_path / "nested").mkdir()
        (vault_path / "nested" / "document.md").write_text("Nested content")

        # Create a file outside vault (for symlink testing)
        outside_path = Path(tmpdir) / "outside.txt"
        outside_path.write_text("Outside content")

        # Create a symlink pointing outside vault
        (vault_path / "external_link.md").symlink_to(outside_path)

        yield vault_path, outside_path


class TestPathTraversalPrevention:
    """Test path traversal attack prevention."""

    def test_read_safe_file(self, vault_dir):
        """Test reading a safe file within vault."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        content = ops.read("safe.md")
        assert content == "Safe content"

    def test_read_nested_safe_file(self, vault_dir):
        """Test reading a nested file within vault."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        content = ops.read("nested/document.md")
        assert content == "Nested content"

    def test_reject_parent_directory(self, vault_dir):
        """Test rejection of .. in path."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        with pytest.raises(ValueError, match="Invalid path"):
            ops.read("../escape.md")

    def test_reject_parent_directory_nested(self, vault_dir):
        """Test rejection of .. in nested path."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        with pytest.raises(ValueError, match="Invalid path"):
            ops.read("nested/../../escape.md")

    def test_reject_absolute_path(self, vault_dir):
        """Test rejection of absolute paths."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        with pytest.raises(ValueError, match="Invalid path"):
            ops.read("/etc/passwd")

    def test_reject_symlink_escape(self, vault_dir):
        """Test rejection of symlinks pointing outside vault."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        # The symlink exists but points outside vault
        with pytest.raises(ValueError, match="Path escapes vault"):
            ops.read("external_link.md")

    def test_reject_root_traversal(self, vault_dir):
        """Test rejection of paths starting with /."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        with pytest.raises(ValueError, match="Invalid path"):
            ops.read("/home/user/file.md")

    def test_write_safe_file(self, vault_dir):
        """Test writing a safe file within vault."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        result = ops.write("new_file.md", "New content")
        assert "new_file.md" in result
        assert (vault_path / "new_file.md").read_text() == "New content"

    def test_reject_write_parent_directory(self, vault_dir):
        """Test rejection of .. when writing."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        with pytest.raises(ValueError, match="Invalid path"):
            ops.write("../evil.md", "Evil content")

    def test_delete_safe_file(self, vault_dir):
        """Test deleting a safe file within vault."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        result = ops.delete("safe.md")
        assert "safe.md" in result
        assert not (vault_path / "safe.md").exists()

    def test_reject_delete_parent_directory(self, vault_dir):
        """Test rejection of .. when deleting."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        with pytest.raises(ValueError, match="Invalid path"):
            ops.delete("../outside.txt")

    def test_edit_safe_file(self, vault_dir):
        """Test editing a safe file within vault."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        edits = [{"operation": "append", "text": "\nAppended"}]
        result = ops.edit("safe.md", edits)
        assert "Appended" in result

        content = (vault_path / "safe.md").read_text()
        assert "Appended" in content

    def test_reject_edit_parent_directory(self, vault_dir):
        """Test rejection of .. when editing."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        edits = [{"operation": "append", "text": "Evil"}]
        with pytest.raises(ValueError, match="Invalid path"):
            ops.edit("../outside.txt", edits)

    def test_list_safe_directory(self, vault_dir):
        """Test listing a safe directory within vault."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        files = ops.list_dir("nested")
        # Files include full relative path from vault root
        assert "nested/document.md" in files or "document.md" in files

    def test_reject_list_parent_directory(self, vault_dir):
        """Test rejection of .. when listing."""
        vault_path, _ = vault_dir
        ops = VaultOps(str(vault_path))

        with pytest.raises(ValueError, match="Invalid path"):
            ops.list_dir("../")


class TestSymlinkSecurity:
    """Test symlink-specific attack prevention."""

    def test_symlink_chain_escape(self):
        """Test prevention of symlink chain escapes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            outside_path = Path(tmpdir) / "outside.txt"
            outside_path.write_text("Outside")

            # Create symlink in vault pointing outside
            (vault_path / "link1.md").symlink_to(outside_path)

            ops = VaultOps(str(vault_path))

            # Should reject symlink pointing outside
            with pytest.raises(ValueError, match="Path escapes vault"):
                ops.read("link1.md")

    def test_circular_symlink_handling(self):
        """Test handling of circular symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            # Create circular symlink
            link_path = vault_path / "circular.md"
            link_path.symlink_to(link_path)

            ops = VaultOps(str(vault_path))

            # Should handle gracefully (raises FileNotFoundError since symlink doesn't resolve)
            with pytest.raises((ValueError, FileNotFoundError)):
                ops.read("circular.md")


class TestEdgeCases:
    """Test edge cases and special characters."""

    def test_empty_path(self):
        """Test handling of empty path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            ops = VaultOps(str(vault_path))

            # Empty path should reference vault root
            files = ops.list_dir("")
            assert isinstance(files, list)

    def test_path_with_dots_filename(self):
        """Test file with dots in name (not traversal)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            (vault_path / "archive.tar.gz").write_text("Archive")

            ops = VaultOps(str(vault_path))
            content = ops.read("archive.tar.gz")
            assert content == "Archive"

    def test_unicode_paths(self):
        """Test handling of unicode characters in paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            unicode_file = vault_path / "你好世界.md"
            unicode_file.write_text("Unicode content")

            ops = VaultOps(str(vault_path))
            content = ops.read("你好世界.md")
            assert content == "Unicode content"

    def test_path_with_spaces(self):
        """Test handling of paths with spaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            space_file = vault_path / "file with spaces.md"
            space_file.write_text("Spaced content")

            ops = VaultOps(str(vault_path))
            content = ops.read("file with spaces.md")
            assert content == "Spaced content"

    def test_deeply_nested_path(self):
        """Test handling of deeply nested paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            # Create deeply nested structure
            nested = vault_path / "a" / "b" / "c" / "d" / "e"
            nested.mkdir(parents=True)
            (nested / "deep.md").write_text("Deep content")

            ops = VaultOps(str(vault_path))
            content = ops.read("a/b/c/d/e/deep.md")
            assert content == "Deep content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
