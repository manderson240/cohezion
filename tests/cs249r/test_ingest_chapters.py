"""Tests for CS249R chapter ingestion script."""

import pytest
from pathlib import Path
from scripts.cs249r.ingest_chapters import (
    parse_concept_yaml,
    create_vault_note,
    ingest_all_chapters,
)


def test_parse_concept_yaml_with_valid_file():
    """Test parsing a valid concept YAML file."""
    # This will test against actual file from cloned repo
    from scripts.cs249r.repo_access import CS249RRepo

    repo = CS249RRepo()
    concepts = repo.load_chapter_concepts("introduction", chapter_type="core")

    # Parse the concepts
    parsed = parse_concept_yaml(concepts, chapter_name="introduction")

    assert parsed is not None
    assert "primary_concepts" in parsed or "concept_map" in parsed
    assert "domain" in parsed  # Should assign a domain tag


def test_parse_concept_yaml_with_missing_file():
    """Test handling of missing concept file."""
    result = parse_concept_yaml(None, chapter_name="missing")

    # Should return None gracefully
    assert result is None


def test_create_vault_note_structure():
    """Test vault note creation with correct structure."""
    concept_data = {
        "chapter_name": "introduction",
        "chapter_type": "core",
        "domain": "foundations",
        "primary_concepts": ["ML Systems", "AI Triangle"],
        "secondary_concepts": ["Production Systems"],
        "technical_terms": ["Perceptron", "ELIZA"],
        "methodologies": ["System Version Management"],
        "applications": ["Medical Image Analysis"],
    }

    note_content = create_vault_note(concept_data)

    # Check frontmatter tags
    assert "tags: [concept, ml-systems, cs249r, foundations]" in note_content
    assert "source: cs249r/core/introduction" in note_content

    # Check sections
    assert "## Primary Concepts" in note_content
    assert "## Technical Terms" in note_content
    assert "ML Systems" in note_content
    assert "Perceptron" in note_content


def test_create_vault_note_with_minimal_data():
    """Test vault note creation with minimal concept data."""
    concept_data = {
        "chapter_name": "test",
        "chapter_type": "core",
        "domain": "foundations",
        "primary_concepts": ["Concept A"],
    }

    note_content = create_vault_note(concept_data)

    # Should not crash with minimal data
    assert "Concept A" in note_content
    assert "tags: [concept, ml-systems, cs249r, foundations]" in note_content


def test_ingest_all_chapters_dry_run(tmp_path):
    """Test dry-run mode doesn't write files."""
    # Dry run should return stats without writing
    stats = ingest_all_chapters(output_dir=tmp_path, dry_run=True)

    assert "core_chapters" in stats
    assert "advanced_chapters" in stats
    assert "total" in stats

    # No files should be written in dry-run mode
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 0


def test_ingest_all_chapters_creates_files(tmp_path):
    """Test actual file creation."""
    stats = ingest_all_chapters(output_dir=tmp_path, dry_run=False)

    # Should create files
    files = list(tmp_path.glob("*.md"))
    assert len(files) > 0
    assert stats["total"] == len(files)

    # Check one file has correct structure
    sample_file = files[0]
    content = sample_file.read_text()

    assert "---" in content  # YAML frontmatter delimiters
    assert "tags:" in content
    assert "cs249r" in content
