"""Tests for the concept stub generator module."""

import pytest
from pathlib import Path
from vault_linker.stubgen import StubGenerator


def test_identify_stub_candidates():
    """Test identifying broken links that should get stubs."""
    link_graph = {
        "paper1": {"outgoing": {"missing-concept1", "missing-concept2"}},
        "paper2": {"outgoing": {"missing-concept1", "dated-ref"}},
        "paper3": {"outgoing": {"missing-concept1", "external_ref"}},
    }

    files_index = {
        "paper1": {},
        "paper2": {},
        "paper3": {},
        # missing-concept1, missing-concept2, dated-ref, external_ref are NOT in index
    }

    stubgen = StubGenerator()
    candidates = stubgen.identify_stub_candidates(link_graph, files_index)

    # missing-concept1 has 3 references, should be candidate
    assert "missing-concept1" in candidates
    assert candidates["missing-concept1"]["ref_count"] == 3
    assert len(candidates["missing-concept1"]["references"]) == 3

    # missing-concept2 has only 1 reference, should NOT be candidate
    assert "missing-concept2" not in candidates


def test_skip_date_prefixed_links():
    """Test that date-prefixed links are skipped."""
    link_graph = {
        "paper1": {"outgoing": {"2026-02-19-decision", "2026-02-19-decision"}},
        "paper2": {"outgoing": {"2026-02-19-decision"}},
        "paper3": {"outgoing": {"2026-02-19-decision"}},
    }
    files_index = {}

    stubgen = StubGenerator()
    candidates = stubgen.identify_stub_candidates(link_graph, files_index)

    # Date-prefixed links should be filtered out
    assert "2026-02-19-decision" not in candidates


def test_skip_external_references():
    """Test that external reference patterns are skipped."""
    link_graph = {
        "paper1": {"outgoing": {"fractal_universe", "enhanced_simulator"}},
        "paper2": {"outgoing": {"fractal_universe", "lab_agent.py"}},
        "paper3": {"outgoing": {"fractal_universe"}},
        "paper4": {"outgoing": {"fractal_universe"}},
    }
    files_index = {}

    stubgen = StubGenerator()
    candidates = stubgen.identify_stub_candidates(link_graph, files_index)

    # External refs (underscores, .py) should be filtered out
    assert "fractal_universe" not in candidates
    assert "enhanced_simulator" not in candidates
    assert "lab_agent.py" not in candidates


def test_generate_stub_content():
    """Test generating stub file content."""
    stubgen = StubGenerator()

    referencing_files = ["paper1", "paper2", "paper3"]
    stub_content = stubgen.generate_stub("dark-matter-detection", referencing_files)

    # Should have frontmatter
    assert "---" in stub_content
    assert "title:" in stub_content
    assert "tags: [concept]" in stub_content

    # Should have template sections
    assert "## Definition" in stub_content
    assert "## Related Papers" in stub_content

    # Should auto-populate related papers
    assert "[[paper1]]" in stub_content
    assert "[[paper2]]" in stub_content
    assert "[[paper3]]" in stub_content

    # Should be marked as auto-generated
    assert "Auto-generated stub" in stub_content or "auto-generated" in stub_content.lower()


def test_generate_stubs_for_vault(tmp_path):
    """Test generating stub files in vault."""
    concepts_dir = tmp_path / "concepts"
    concepts_dir.mkdir()

    link_graph = {
        "paper1": {"outgoing": {"new-concept"}},
        "paper2": {"outgoing": {"new-concept"}},
        "paper3": {"outgoing": {"new-concept"}},
    }
    files_index = {}

    stubgen = StubGenerator(vault_path=tmp_path)
    stubs_created = stubgen.generate_stubs(link_graph, files_index)

    # Should create one stub
    assert len(stubs_created) == 1
    assert "new-concept" in stubs_created

    # Stub file should exist
    stub_file = concepts_dir / "new-concept.md"
    assert stub_file.exists()

    # Should contain template content
    content = stub_file.read_text()
    assert "## Definition" in content
    assert "[[paper1]]" in content


def test_skip_date_prefixed_with_directory():
    """Test that date-prefixed links with directory prefix are skipped."""
    link_graph = {
        "p1": {"outgoing": {"lessons/2026-02-10-debug-log"}},
        "p2": {"outgoing": {"lessons/2026-02-10-debug-log"}},
        "p3": {"outgoing": {"lessons/2026-02-10-debug-log"}},
    }
    files_index = {}

    stubgen = StubGenerator()
    candidates = stubgen.identify_stub_candidates(link_graph, files_index)

    assert "lessons/2026-02-10-debug-log" not in candidates


def test_normalize_filename_with_spaces(tmp_path):
    """Test that stubs with spaces in names are slug-normalized."""
    concepts_dir = tmp_path / "concepts"
    concepts_dir.mkdir()

    link_graph = {
        "p1": {"outgoing": {"agent context"}},
        "p2": {"outgoing": {"agent context"}},
        "p3": {"outgoing": {"agent context"}},
    }
    files_index = {}

    stubgen = StubGenerator(vault_path=tmp_path)
    stubs_created = stubgen.generate_stubs(link_graph, files_index)

    assert len(stubs_created) == 1
    # File should be slug-normalized
    assert (concepts_dir / "agent-context.md").exists()
    # File with spaces should NOT exist
    assert not (concepts_dir / "agent context.md").exists()
