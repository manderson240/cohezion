"""Tests for the paper tag populator module."""

import pytest
from pathlib import Path
from vault_linker.tagger import TagPopulator


def test_extract_keywords_from_title():
    """Test extracting keywords from paper title."""
    tagger = TagPopulator()

    title = "Quantum Sensors for Dark Matter Detection"
    keywords = tagger.extract_keywords(title)

    assert "quantum" in keywords
    assert "sensors" in keywords
    assert "dark" in keywords or "matter" in keywords


def test_extract_keywords_from_content():
    """Test extracting keywords from paper content."""
    tagger = TagPopulator()

    content = """
    # JWST Dark Matter Detection

    The James Webb Space Telescope uses gravitational lensing
    to detect dark matter concentrations in distant galaxies.

    ## Key Findings
    - Gravitational lensing techniques
    - Dark matter distribution patterns
    """

    keywords = tagger.extract_keywords(content)

    assert "dark-matter" in keywords or "dark" in keywords or "matter" in keywords
    assert "jwst" in keywords or "telescope" in keywords


def test_generate_tags_from_keywords():
    """Test generating tags from extracted keywords."""
    existing_concepts = ["quantum-sensors", "dark-matter-detection", "gravitational-lensing"]
    existing_tags = [["quantum", "sensors"], ["dark-matter", "detection"], ["astronomy", "cosmology"]]

    tagger = TagPopulator(existing_concepts=existing_concepts, existing_tags=existing_tags)

    keywords = ["quantum", "sensors", "dark", "matter", "detection"]
    tags = tagger.generate_tags_from_keywords(keywords)

    # Should match existing concepts/tags where possible
    assert len(tags) >= 2
    assert len(tags) <= 5


def test_populate_paper_tags(tmp_path):
    """Test populating tags for a paper with tags: null."""
    paper_file = tmp_path / "test-paper.md"
    paper_file.write_text("""---
title: Quantum Sensors for Dark Matter
date: 2026-02-19
tags: null
similar_papers:
- axion-dark-matter
---
# Quantum Sensors for Dark Matter

Detecting dark matter using quantum sensor technology.
""")

    existing_concepts = ["quantum-sensors", "dark-matter-detection"]
    existing_tags = [["quantum", "sensors"], ["dark-matter", "detection"]]

    tagger = TagPopulator(existing_concepts=existing_concepts, existing_tags=existing_tags)
    updated_content = tagger.populate_tags(paper_file)

    # Should have replaced tags: null with an array
    assert "tags: null" not in updated_content
    assert "tags: [" in updated_content
    assert "quantum" in updated_content or "dark-matter" in updated_content


def test_surgical_replacement_preserves_formatting(tmp_path):
    """Test that tag replacement preserves frontmatter formatting."""
    paper_file = tmp_path / "test-paper.md"
    original_content = """---
title: Test Paper
date: 2026-02-19
tags: null
connectivity: 0.5
cross_domain: 0.3
---
# Test Paper

Content here.
"""
    paper_file.write_text(original_content)

    tagger = TagPopulator()
    updated_content = tagger.populate_tags(paper_file)

    # Should preserve other frontmatter fields
    assert "connectivity: 0.5" in updated_content
    assert "cross_domain: 0.3" in updated_content
    # Tags should be updated but everything else unchanged
    assert updated_content.count("---") == 2


def test_skip_papers_with_existing_tags(tmp_path):
    """Test that papers with existing tags are not modified."""
    paper_file = tmp_path / "test-paper.md"
    original_content = """---
title: Test Paper
tags: [existing, tags]
---
# Test Paper
"""
    paper_file.write_text(original_content)

    tagger = TagPopulator()
    updated_content = tagger.populate_tags(paper_file)

    # Should return unchanged
    assert updated_content == original_content
