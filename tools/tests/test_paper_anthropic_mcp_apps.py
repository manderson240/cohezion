"""Tests for the anthropic-mcp-apps-claude-integrations.md vault note."""

import pytest
from pathlib import Path
from vault_linker.parser import VaultParser

VAULT_ROOT = Path(__file__).parent.parent.parent
NOTE_PATH = VAULT_ROOT / "papers" / "anthropic-mcp-apps-claude-integrations.md"
NOTE_STEM = "anthropic-mcp-apps-claude-integrations"


@pytest.fixture(scope="module")
def parsed():
    parser = VaultParser()
    return parser.parse_file(NOTE_PATH)


@pytest.fixture(scope="module")
def frontmatter(parsed):
    return parsed["frontmatter"]


@pytest.fixture(scope="module")
def content():
    return NOTE_PATH.read_text(encoding="utf-8")


# --- File existence ---

def test_note_file_exists():
    assert NOTE_PATH.exists(), f"Note not found at {NOTE_PATH}"


# --- Frontmatter: required fields ---

def test_has_title(frontmatter):
    assert "title" in frontmatter
    assert frontmatter["title"]


def test_has_date(frontmatter):
    assert "date" in frontmatter
    assert frontmatter["date"]


def test_has_tags(frontmatter):
    assert "tags" in frontmatter


def test_tags_is_list(frontmatter):
    assert isinstance(frontmatter["tags"], list), (
        f"tags must be an array, got {type(frontmatter['tags'])}"
    )


def test_tags_not_empty(frontmatter):
    assert len(frontmatter["tags"]) > 0


def test_has_source_url(frontmatter):
    assert "source" in frontmatter
    assert frontmatter["source"].startswith("http"), (
        f"source should be a URL, got: {frontmatter['source']}"
    )


# --- Frontmatter: dimension scores in valid range ---

DIMENSION_FIELDS = [
    "connectivity", "cross_domain", "completion", "conceptual_depth",
]


@pytest.mark.parametrize("field", DIMENSION_FIELDS)
def test_top_level_dimension_in_range(frontmatter, field):
    if field not in frontmatter:
        pytest.skip(f"{field} not present in frontmatter")
    val = frontmatter[field]
    assert isinstance(val, (int, float)), f"{field} should be numeric"
    assert 0.0 <= float(val) <= 1.0, f"{field}={val} out of range [0, 1]"


def test_nested_dimensions_are_numeric(frontmatter):
    """Nested dimensions use a mixed scale (some 0-1, completion is 0-100), so only assert numeric."""
    dims = frontmatter.get("dimensions", {})
    if not dims:
        pytest.skip("no nested dimensions block")
    for key, val in dims.items():
        assert isinstance(val, (int, float)), f"dimensions.{key} should be numeric, got {type(val)}"


# --- Content: required sections ---

REQUIRED_SECTIONS = ["## Summary", "## Key Findings", "## Relevance to Cohezion"]


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_section_present(content, section):
    assert section in content, f"Missing section: {section!r}"


# --- Content: key claims ---

def test_mentions_mcp(content):
    assert "MCP" in content or "Model Context Protocol" in content


def test_mentions_at_least_one_tool(content):
    tools = ["Slack", "Figma", "Asana", "Canva"]
    assert any(tool in content for tool in tools), (
        "Expected at least one tool name (Slack, Figma, Asana, Canva) in content"
    )


def test_mentions_cohezion_relevance(content):
    assert "Cohezion" in content


# --- Wiki-links ---

def test_has_wiki_links(parsed):
    assert len(parsed["wiki_links"]) > 0, "Note should contain at least one wiki-link"


def test_expected_wiki_links_present(parsed):
    links = [lnk.lower() for lnk in parsed["wiki_links"]]
    # These links are explicitly in the note body
    expected = ["mcp-model-context-protocol", "tool-use"]
    for expected_link in expected:
        assert expected_link in links, f"Expected wiki-link [[{expected_link}]] not found"
