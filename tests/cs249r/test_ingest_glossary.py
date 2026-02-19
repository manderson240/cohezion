"""Tests for CS249R glossary ingestion."""

import json
import pytest
from pathlib import Path
from scripts.cs249r.ingest_glossary import (
    parse_glossary_terms,
    create_glossary_vault_note,
    create_surreal_json,
    ingest_glossary,
)


def test_parse_glossary_terms_from_repo():
    """Test parsing glossary terms from actual repository."""
    from scripts.cs249r.repo_access import CS249RRepo

    repo = CS249RRepo()
    glossary_data = repo.load_global_glossary()

    terms = parse_glossary_terms(glossary_data)

    assert isinstance(terms, list)
    assert len(terms) >= 656  # Should have at least 656 terms
    assert all("term" in t for t in terms)  # All should have term field


def test_create_glossary_vault_note():
    """Test vault note generation from glossary terms."""
    sample_terms = [
        {"term": "Machine Learning", "definition": "A method of data analysis"},
        {"term": "Neural Network", "definition": "A computational model"},
    ]

    note_content = create_glossary_vault_note(sample_terms)

    # Check structure
    assert "---" in note_content  # YAML frontmatter
    assert "tags: [glossary, ml-systems, cs249r]" in note_content
    assert "Machine Learning" in note_content
    assert "Neural Network" in note_content
    assert "## M" in note_content or "###" in note_content  # Alphabetical grouping


def test_create_surreal_json():
    """Test SurrealDB JSON format creation."""
    sample_terms = [
        {"term": "API", "definition": "Application Programming Interface"},
        {"term": "ML", "definition": "Machine Learning"},
    ]

    surreal_data = create_surreal_json(sample_terms)

    assert isinstance(surreal_data, list)
    assert len(surreal_data) == 2
    assert all("id" in t for t in surreal_data)
    assert all("term" in t for t in surreal_data)
    assert all("definition" in t for t in surreal_data)
    # Check ID format: glossary:term-slug
    assert surreal_data[0]["id"].startswith("glossary:")


def test_ingest_glossary_dry_run(tmp_path):
    """Test dry-run mode doesn't write files."""
    stats = ingest_glossary(output_dir=tmp_path, dry_run=True)

    assert "term_count" in stats
    assert stats["term_count"] >= 656

    # No files should be written
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 0


def test_ingest_glossary_creates_files(tmp_path):
    """Test actual file creation."""
    stats = ingest_glossary(output_dir=tmp_path, dry_run=False)

    # Should create glossary markdown
    glossary_file = tmp_path / "ml-systems-glossary.md"
    assert glossary_file.exists()

    content = glossary_file.read_text()
    assert "tags: [glossary, ml-systems, cs249r]" in content
    assert len(content) > 1000  # Should have substantial content
