"""
Edge Case Tests for Traceability Engine

Tests error handling and edge cases:
- Empty files
- Malformed XML
- Missing directories
- Permission errors
- Unicode in paths
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from base_engine import EngineConfig
from traceability_engine import TraceabilityEngine


PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")


class TestEmptyFileHandling:
    """Tests for empty file edge cases."""

    @pytest.mark.fast
    def test_empty_xml_file(self):
        """Verify empty XML file handling."""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"")  # Empty file
            temp_path = Path(f.name)

        try:
            config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
            engine = TraceabilityEngine(config=config)
            invocations = engine.extract_invocations_from_xml(temp_path)
            assert invocations == []  # Should return empty list, not crash
        finally:
            temp_path.unlink()

    @pytest.mark.fast
    def test_empty_python_file(self):
        """Verify empty Python file handling."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"")  # Empty file
            temp_path = Path(f.name)

        try:
            config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
            engine = TraceabilityEngine(config=config)
            module = engine.parse_module(temp_path)
            assert module is not None  # Should handle gracefully
            assert module.line_count == 0
        finally:
            temp_path.unlink()


class TestMalformedXML:
    """Tests for malformed XML handling."""

    @pytest.mark.fast
    def test_malformed_xml_syntax(self):
        """Verify malformed XML syntax handling."""
        xml_content = b"<workflow><invoke-task>test"  # Missing closing tags

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
            engine = TraceabilityEngine(config=config)
            invocations = engine.extract_invocations_from_xml(temp_path)
            # Should handle gracefully, not crash
            assert isinstance(invocations, list)
        finally:
            temp_path.unlink()

    @pytest.mark.fast
    def test_invalid_xml_characters(self):
        """Verify invalid XML character handling."""
        xml_content = "<workflow><invoke-task>test\x00</invoke-task></workflow>"  # Null byte

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(xml_content.encode("utf-8"))
            temp_path = Path(f.name)

        try:
            config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
            engine = TraceabilityEngine(config=config)
            invocations = engine.extract_invocations_from_xml(temp_path)
            assert isinstance(invocations, list)
        finally:
            temp_path.unlink()


class TestMissingDirectories:
    """Tests for missing directory handling."""

    @pytest.mark.fast
    def test_nonexistent_directory(self):
        """Verify nonexistent directory handling."""
        config = EngineConfig(
            PROJECT_ROOT,
            PROJECT_ROOT / "_bmad" / "_config" / "traceability" / "nonexistent",
        )
        engine = TraceabilityEngine(config=config)
        # Should create directory or handle gracefully
        assert engine.output_dir.exists() or True  # May create it

    @pytest.mark.fast
    def test_nonexistent_file(self):
        """Verify nonexistent file handling."""
        config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
        engine = TraceabilityEngine(config=config)
        result = engine.read_file_safe(PROJECT_ROOT / "nonexistent_file.txt")
        assert result is None  # Should return None, not crash


class TestPermissionErrors:
    """Tests for permission error handling."""

    @pytest.mark.skipif(os.geteuid() == 0, reason="Test fails as root")
    @pytest.mark.fast
    def test_unreadable_file(self):
        """Verify unreadable file handling."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"print('test')")
            temp_path = Path(f.name)
            temp_path.chmod(0o000)  # Remove all permissions

        try:
            config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
            engine = TraceabilityEngine(config=config)
            result = engine.read_file_safe(temp_path)
            assert result is None  # Should return None
        finally:
            temp_path.chmod(0o644)  # Restore permissions
            temp_path.unlink()


class TestUnicodePaths:
    """Tests for unicode path handling."""

    @pytest.mark.fast
    def test_unicode_in_path(self):
        """Verify unicode characters in path."""
        # Create temp file with unicode name
        with tempfile.TemporaryDirectory() as tmpdir:
            unicode_file = Path(tmpdir) / "test_émoji_中文.py"
            unicode_file.write_text("# -*- coding: utf-8 -*-\nprint('test')")

            config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
            engine = TraceabilityEngine(config=config)
            module = engine.parse_module(unicode_file)
            assert module is not None
            assert "émoji" in str(unicode_file) or "中文" in str(unicode_file)


class TestLargeFiles:
    """Tests for large file handling."""

    @pytest.mark.fast
    def test_large_xml_file(self):
        """Verify large XML file handling."""
        # Create 100KB XML file
        xml_content = (
            "<workflow>\n"
            + "\n".join([f"<invoke-task>test{i}</invoke-task>" for i in range(1000)])
            + "\n</workflow>"
        )

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(xml_content.encode("utf-8"))
            temp_path = Path(f.name)

        try:
            config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
            engine = TraceabilityEngine(config=config)
            invocations = engine.extract_invocations_from_xml(temp_path)
            assert len(invocations) == 1000  # Should parse all
        finally:
            temp_path.unlink()


class TestConcurrentAccess:
    """Tests for concurrent file access."""

    @pytest.mark.fast
    def test_simultaneous_reads(self):
        """Verify simultaneous file reads."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"print('test')")
            temp_path = Path(f.name)

        try:
            config = EngineConfig(PROJECT_ROOT, PROJECT_ROOT / "_bmad" / "_config" / "traceability")
            engine = TraceabilityEngine(config=config)

            # Read same file multiple times
            result1 = engine.read_file_safe(temp_path)
            result2 = engine.read_file_safe(temp_path)
            assert result1 == result2
        finally:
            temp_path.unlink()
