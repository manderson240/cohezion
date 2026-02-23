"""Parametrized structural tests for all vault paper notes.

Runs the same set of validations against every .md file in papers/,
excluding _template.md. Failures show the paper stem so issues are easy
to locate.
"""

import re
from pathlib import Path

import pytest
from vault_linker.parser import VaultParser

VAULT_ROOT = Path(__file__).parent.parent.parent
PAPERS_DIR = VAULT_ROOT / "papers"

# Top-level frontmatter dimension fields that should be in [0.0, 1.0]
TOP_LEVEL_DIMS = [
    "connectivity",
    "cross_domain",
    "completion",
    "temporal",
    "recency",
    "conceptual_depth",
]

# Some nested dimension fields use raw counts/percentages rather than 0-1 scores:
#   completion  — 0-100 percentage (e.g. 100 = 100% complete)
#   cross_domain — raw integer count of domain intersections (can be 2, 3, ...)
NESTED_DIMS_UNCONSTRAINED = {"completion", "cross_domain"}


# Papers with known structural issues — marked xfail rather than excluded so the
# failures are still visible in the test report and prompt remediation.
KNOWN_BROKEN: dict[str, str] = {
    # Duplicate file with spaces in filename — no frontmatter at all
    "The Awareness of Nothing at All and Quadrature Physics": (
        "spaces-in-filename duplicate; no frontmatter"
    ),
    # Hyphenated version also missing frontmatter (no --- block)
    "the-awareness-of-nothing-at-all-and-quadrature-physics": (
        "missing frontmatter block"
    ),
    # Auto-processed draft — missing 'title' field and no # heading
    "2026-02-09-unique-investment-opportunities-research": (
        "auto-processed draft; missing title field and # heading"
    ),
}


def _paper_param(path: Path) -> pytest.param:
    stem = path.stem
    reason = KNOWN_BROKEN.get(stem)
    marks = [pytest.mark.xfail(reason=reason, strict=False)] if reason else []
    return pytest.param(stem, marks=marks, id=stem)


def _all_papers() -> list[Path]:
    return sorted(
        p for p in PAPERS_DIR.glob("*.md") if p.stem != "_template"
    )


def _paper_params() -> list[pytest.param]:
    return [_paper_param(p) for p in _all_papers()]


@pytest.fixture(scope="module")
def parser() -> VaultParser:
    return VaultParser()


@pytest.fixture(scope="module")
def all_parsed(parser) -> dict[str, dict]:
    """Parse all papers once and cache by stem."""
    return {p.stem: parser.parse_file(p) for p in _all_papers()}


PAPER_PARAMS = _paper_params()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_file_is_parseable(stem, all_parsed):
    """parse_file should return a non-empty frontmatter dict."""
    result = all_parsed[stem]
    assert isinstance(result, dict), f"{stem}: parse_file returned non-dict"
    # A parseable file always has these keys from VaultParser
    assert "frontmatter" in result
    assert "wiki_links" in result


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_has_title(stem, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    assert "title" in fm, f"{stem}: missing 'title' in frontmatter"
    assert fm["title"], f"{stem}: 'title' is empty"


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_has_date(stem, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    assert "date" in fm, f"{stem}: missing 'date' in frontmatter"
    assert fm["date"], f"{stem}: 'date' is empty"


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_has_tags(stem, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    assert "tags" in fm, f"{stem}: missing 'tags' in frontmatter"


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_tags_is_list(stem, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    tags = fm.get("tags")
    assert isinstance(tags, list), (
        f"{stem}: tags should be a YAML array, got {type(tags).__name__!r}"
    )


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_tags_not_empty(stem, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        assert len(tags) > 0, f"{stem}: tags array is empty"


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_has_source(stem, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    assert "source" in fm, f"{stem}: missing 'source' in frontmatter"
    assert fm["source"], f"{stem}: 'source' is empty"


@pytest.mark.parametrize("stem", PAPER_PARAMS)
@pytest.mark.parametrize("field", TOP_LEVEL_DIMS)
def test_top_level_dim_in_range(stem, field, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    if field not in fm:
        pytest.skip(f"{stem}: '{field}' not present")
    val = fm[field]
    assert isinstance(val, (int, float)), (
        f"{stem}: '{field}' should be numeric, got {type(val).__name__!r}"
    )
    assert 0.0 <= float(val) <= 1.0, (
        f"{stem}: '{field}'={val} is out of range [0.0, 1.0]"
    )


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_nested_dims_are_numeric(stem, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    dims = fm.get("dimensions", {})
    if not dims:
        pytest.skip(f"{stem}: no nested 'dimensions' block")
    for key, val in dims.items():
        assert isinstance(val, (int, float)), (
            f"{stem}: dimensions.{key} should be numeric, got {type(val).__name__!r}"
        )


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_nested_dims_non_percentage_in_range(stem, all_parsed):
    """All nested dimension fields except known percentage fields must be in [0, 1]."""
    fm = all_parsed[stem]["frontmatter"]
    dims = fm.get("dimensions", {})
    if not dims:
        pytest.skip(f"{stem}: no nested 'dimensions' block")
    for key, val in dims.items():
        if key in NESTED_DIMS_UNCONSTRAINED:
            continue
        if not isinstance(val, (int, float)):
            continue  # caught by test_nested_dims_are_numeric
        assert 0.0 <= float(val) <= 1.0, (
            f"{stem}: dimensions.{key}={val} is out of range [0.0, 1.0]"
        )


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_has_at_least_one_section(stem):
    """Note body should have at least one ## heading."""
    path = PAPERS_DIR / f"{stem}.md"
    content = path.read_text(encoding="utf-8")
    assert re.search(r'^##\s+\S', content, re.MULTILINE), (
        f"{stem}: no '## ...' section headings found"
    )


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_has_title_heading(stem):
    """Note body should have a top-level # heading."""
    path = PAPERS_DIR / f"{stem}.md"
    content = path.read_text(encoding="utf-8")
    assert re.search(r'^#\s+\S', content, re.MULTILINE), (
        f"{stem}: no '# ...' title heading found"
    )


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_no_self_links(stem, all_parsed):
    """A note should not contain a wiki-link to itself."""
    links = [lnk.lower() for lnk in all_parsed[stem]["wiki_links"]]
    assert stem.lower() not in links, (
        f"{stem}: note contains a self-referencing wiki-link [[{stem}]]"
    )


@pytest.mark.parametrize("stem", PAPER_PARAMS)
def test_similar_papers_is_list_or_absent(stem, all_parsed):
    fm = all_parsed[stem]["frontmatter"]
    val = fm.get("similar_papers")
    if val is None:
        return  # field absent — ok
    assert isinstance(val, list), (
        f"{stem}: 'similar_papers' should be a list, got {type(val).__name__!r}"
    )
