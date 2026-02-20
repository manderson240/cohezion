"""Tests for the cross-reference link injector module."""

import pytest
from pathlib import Path
from vault_linker.injector import LinkInjector


def test_validate_similar_papers():
    """Test validating similar_papers with tag overlap."""
    files_index = {
        "paper1": {"frontmatter": {"tags": ["quantum", "sensors"]}},
        "paper2": {"frontmatter": {"tags": ["quantum", "computing"]}},
        "paper3": {"frontmatter": {"tags": ["biology", "proteins"]}},
    }

    injector = LinkInjector(files_index)

    # Paper2 shares "quantum" tag with paper1
    valid = injector.validate_similar_paper("paper1", "paper2")
    assert valid == True

    # Paper3 shares no tags with paper1
    valid = injector.validate_similar_paper("paper1", "paper3")
    assert valid == False


def test_extract_existing_wikilinks():
    """Test extracting all existing wiki-links from content."""
    content = """
    # Paper

    Relevant to [[concept1]], [[concept2]].

    ## Related Papers
    - [[existing-paper]]
    """

    injector = LinkInjector({})
    existing_links = injector.extract_all_wikilinks(content)

    assert "concept1" in existing_links
    assert "concept2" in existing_links
    assert "existing-paper" in existing_links


def test_detect_related_sections():
    """Test detecting existing Related sections."""
    content = """
    # Paper

    Content here.

    ## Related Papers
    - [[paper1]]

    ## Related Concepts
    - [[concept1]]
    """

    injector = LinkInjector({})
    has_papers, has_concepts = injector.detect_related_sections(content)

    assert has_papers == True
    assert has_concepts == True


def test_inject_related_papers(tmp_path):
    """Test injecting Related Papers section."""
    paper_file = tmp_path / "test-paper.md"
    paper_file.write_text("""---
title: Test Paper
tags: [quantum, sensors]
similar_papers:
- paper2
- paper3
---
# Test Paper

Content here.
""")

    files_index = {
        "test-paper": {"frontmatter": {"tags": ["quantum", "sensors"]}, "similar_papers": ["paper2", "paper3"]},
        "paper2": {"frontmatter": {"tags": ["quantum", "computing"]}},
        "paper3": {"frontmatter": {"tags": ["biology"]}},
    }

    injector = LinkInjector(files_index)
    updated_content = injector.inject_links(paper_file, "test-paper")

    # Should add Related Papers section
    assert "## Related Papers" in updated_content
    # Should only include paper2 (shares quantum tag)
    assert "[[paper2]]" in updated_content
    # Should NOT include paper3 (no tag overlap)
    assert "[[paper3]]" not in updated_content


def test_skip_duplicate_links(tmp_path):
    """Test that duplicate links are not added."""
    paper_file = tmp_path / "test-paper.md"
    paper_file.write_text("""---
title: Test Paper
tags: [quantum]
similar_papers:
- paper2
---
# Test Paper

Already mentions [[paper2]] inline.
""")

    files_index = {
        "test-paper": {"frontmatter": {"tags": ["quantum"]}},
        "paper2": {"frontmatter": {"tags": ["quantum"]}},
    }

    injector = LinkInjector(files_index)
    updated_content = injector.inject_links(paper_file, "test-paper")

    # Should NOT duplicate paper2 link
    # Count occurrences
    count = updated_content.count("[[paper2]]")
    assert count == 1  # Only the inline mention


def test_limit_links_per_section(tmp_path):
    """Test that sections are limited to 5-8 items."""
    paper_file = tmp_path / "test-paper.md"
    paper_file.write_text("""---
title: Test Paper
tags: [quantum]
similar_papers:
- paper1
- paper2
- paper3
- paper4
- paper5
- paper6
- paper7
- paper8
- paper9
- paper10
---
# Test Paper
""")

    similar_papers_list = [f"paper{i}" for i in range(1, 11)]
    files_index = {
        "test-paper": {"frontmatter": {"tags": ["quantum"]}, "similar_papers": similar_papers_list},
    }
    # Add all papers with quantum tag
    for i in range(1, 11):
        files_index[f"paper{i}"] = {"frontmatter": {"tags": ["quantum"]}}

    injector = LinkInjector(files_index, max_links=5)
    updated_content = injector.inject_links(paper_file, "test-paper")

    # Count paper links in Related section
    related_section = updated_content.split("## Related Papers")[1] if "## Related Papers" in updated_content else ""
    link_count = related_section.count("[[paper")

    assert link_count <= 8
    assert link_count >= 1
