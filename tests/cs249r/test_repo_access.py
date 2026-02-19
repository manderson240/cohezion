"""Tests for CS249R repository access module."""

import pytest
from pathlib import Path
from scripts.cs249r.repo_access import CS249RRepo


def test_repo_initialization():
    """Test CS249RRepo initializes with correct path."""
    repo = CS249RRepo()
    assert repo.repo_path.exists()
    assert repo.repo_path.name == "cs249r_book"


def test_list_core_chapters():
    """Test listing core chapters."""
    repo = CS249RRepo()
    core_chapters = repo.get_core_chapters()

    assert len(core_chapters) == 21
    assert all(isinstance(ch, dict) for ch in core_chapters)
    assert all("name" in ch and "path" in ch for ch in core_chapters)


def test_list_advanced_chapters():
    """Test listing advanced chapters."""
    repo = CS249RRepo()
    advanced_chapters = repo.get_advanced_chapters()

    assert len(advanced_chapters) == 9
    assert all(isinstance(ch, dict) for ch in advanced_chapters)


def test_all_chapters_property():
    """Test chapters property returns all chapters."""
    repo = CS249RRepo()
    all_chapters = repo.chapters

    assert len(all_chapters) == 30  # 21 core + 9 advanced
    assert all("type" in ch for ch in all_chapters)  # Should have type: core or advanced


def test_load_chapter_concepts():
    """Test loading concept YAML for a chapter."""
    repo = CS249RRepo()

    # Load introduction chapter concepts
    concepts = repo.load_chapter_concepts("introduction", chapter_type="core")

    assert concepts is not None
    assert "concept_map" in concepts or "primary_concepts" in concepts.get("concept_map", {})


def test_load_chapter_glossary():
    """Test loading glossary JSON for a chapter."""
    repo = CS249RRepo()

    # Load introduction chapter glossary
    glossary = repo.load_chapter_glossary("introduction", chapter_type="core")

    # Glossary might be None or empty for some chapters - that's okay
    assert glossary is None or isinstance(glossary, (list, dict))


def test_global_glossary_count():
    """Test global glossary has expected term count."""
    repo = CS249RRepo()
    glossary = repo.load_global_glossary()

    assert glossary is not None
    # Glossary structure has metadata and terms
    terms = glossary.get("terms", glossary) if isinstance(glossary, dict) else glossary
    assert len(terms) >= 656  # At least 656 terms


def test_tinytorch_modules_count():
    """Test TinyTorch modules enumeration."""
    repo = CS249RRepo()
    modules = repo.get_tinytorch_modules()

    assert len(modules) == 20
    assert all("number" in m and "path" in m for m in modules)
    # Modules should be numbered 01-20
    numbers = sorted([m["number"] for m in modules])
    assert numbers[0] == 1
    assert numbers[-1] == 20


def test_glossary_term_count_property():
    """Test glossary_term_count property."""
    repo = CS249RRepo()
    count = repo.glossary_term_count

    assert isinstance(count, int)
    assert count == 656


def test_tinytorch_modules_property():
    """Test tinytorch_modules property."""
    repo = CS249RRepo()
    modules = repo.tinytorch_modules

    assert len(modules) == 20
