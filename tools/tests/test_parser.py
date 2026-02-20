"""Tests for the vault parser module."""

import pytest
from pathlib import Path
from vault_linker.parser import VaultParser


def test_parse_frontmatter():
    """Test extracting YAML frontmatter from markdown file."""
    content = """---
title: Test Paper
date: 2026-02-19
tags: [concept, testing]
similar_papers:
- paper-one
- paper-two
---
# Test Paper

Some content here.
"""
    parser = VaultParser()
    frontmatter = parser.parse_frontmatter(content)

    assert frontmatter["title"] == "Test Paper"
    assert frontmatter["date"] == "2026-02-19"
    assert frontmatter["tags"] == ["concept", "testing"]
    assert frontmatter["similar_papers"] == ["paper-one", "paper-two"]


def test_parse_frontmatter_with_null_tags():
    """Test parsing frontmatter with null tags."""
    content = """---
title: Test Paper
date: 2026-02-19
tags: null
---
# Test Paper
"""
    parser = VaultParser()
    frontmatter = parser.parse_frontmatter(content)

    assert frontmatter["title"] == "Test Paper"
    assert frontmatter["tags"] is None


def test_extract_wiki_links():
    """Test extracting wiki-links from markdown content."""
    content = """
# Test

This references [[concept-one]] and [[concept-two|Display Name]].

Also see [[concept-three#section]].
"""
    parser = VaultParser()
    links = parser.extract_wiki_links(content)

    assert "concept-one" in links
    assert "concept-two" in links
    assert "concept-three" in links


def test_parse_markdown_file(tmp_path):
    """Test parsing a complete markdown file."""
    # Create test file
    test_file = tmp_path / "test-paper.md"
    test_file.write_text("""---
title: Test Paper
date: 2026-02-19
tags: [testing]
similar_papers:
- related-paper
---
# Test Paper

References [[concept-one]] and [[concept-two]].
""")

    parser = VaultParser()
    result = parser.parse_file(test_file)

    assert result["path"] == test_file
    assert result["stem"] == "test-paper"
    assert result["frontmatter"]["title"] == "Test Paper"
    assert "concept-one" in result["wiki_links"]
    assert "concept-two" in result["wiki_links"]
    assert result["similar_papers"] == ["related-paper"]


def test_walk_vault(tmp_path):
    """Test recursively walking vault and parsing all markdown files."""
    # Create test vault structure
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()
    concepts_dir = tmp_path / "concepts"
    concepts_dir.mkdir()

    (papers_dir / "paper1.md").write_text("""---
title: Paper 1
tags: [testing]
---
# Paper 1
References [[concept1]].
""")

    (concepts_dir / "concept1.md").write_text("""---
title: Concept 1
tags: [concept]
---
# Concept 1
Related to [[paper1]].
""")

    parser = VaultParser()
    files_index, link_graph = parser.walk_vault(tmp_path)

    assert "paper1" in files_index
    assert "concept1" in files_index
    assert files_index["paper1"]["frontmatter"]["title"] == "Paper 1"
    assert "concept1" in link_graph["paper1"]["outgoing"]
    assert "paper1" in link_graph["concept1"]["outgoing"]


def test_classify_broken_links(tmp_path):
    """Test classifying broken links into categories."""
    # Create test files
    (tmp_path / "file1.md").write_text("""---
title: File 1
---
References [[existing-file]], [[2026-02-19-dated-ref]], [[external_reference]].
""")

    (tmp_path / "existing-file.md").write_text("""---
title: Existing File
---
Content here.
""")

    parser = VaultParser()
    files_index, link_graph = parser.walk_vault(tmp_path)
    broken_links = parser.classify_broken_links(files_index, link_graph)

    # existing-file should NOT be in broken links
    all_broken = [link for category in broken_links.values() for link in category]
    assert "existing-file" not in all_broken

    # dated-ref and external_reference should be classified
    assert "2026-02-19-dated-ref" in broken_links["date_prefixed"] or \
           "2026-02-19-dated-ref" in broken_links["missing"]
    assert "external_reference" in broken_links["external"] or \
           "external_reference" in broken_links["missing"]
