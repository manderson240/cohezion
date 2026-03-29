"""Tests for GraphRAG helper functions"""

from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

from src.mcp_server.graphrag_helpers import (
    check_document_exists,
    detect_circular_reference,
    detect_document_type,
    escape_sql,
    parse_frontmatter,
    parse_wiki_links,
    safe_create_edge,
    slugify,
)


def test_slugify():
    """Test slug generation"""
    assert slugify("Test Document") == "test_document"
    assert slugify("Decision: Use GraphRAG") == "decision_use_graphrag"
    assert slugify("  spaces  ") == "spaces"
    assert slugify("Test-Already-Slug") == "test_already_slug"


def test_escape_sql():
    """Test SQL escaping"""
    assert escape_sql("Simple text") == "Simple text"
    assert escape_sql("Text with 'quotes'") == "Text with \\'quotes\\'"
    assert escape_sql("Path\\with\\backslashes") == "Path\\\\with\\\\backslashes"

    # Test truncation
    long_text = "x" * 3000
    result = escape_sql(long_text)
    assert len(result) == 2000


def test_parse_wiki_links():
    """Test wiki-link extraction"""
    content = """
    Some text with [[link-one]] and [[link-two]].
    Also [[link-three|Display Text]].
    Not a link: [regular](link).
    """
    links = parse_wiki_links(content)
    assert len(links) == 3
    assert "link-one" in links
    assert "link-two" in links
    assert "link-three" in links


def test_detect_document_type():
    """Test document type detection"""
    vault_path = Path("/vaults/cohezion-vault")

    assert (
        detect_document_type(
            Path("/vaults/cohezion-vault/decisions/test.md"), vault_path
        )
        == "decision"
    )

    assert (
        detect_document_type(
            Path("/vaults/cohezion-vault/patterns/test.md"), vault_path
        )
        == "pattern"
    )

    assert (
        detect_document_type(
            Path("/vaults/cohezion-vault/experiments/test.md"), vault_path
        )
        == "experiment"
    )

    assert (
        detect_document_type(Path("/vaults/cohezion-vault/other/test.md"), vault_path)
        == "document"
    )


def test_parse_frontmatter():
    """Test YAML frontmatter parsing"""
    content = """---
title: Test Document
tags: [tag1, tag2]
---
Body content here.
"""
    frontmatter, body = parse_frontmatter(content)
    assert frontmatter["title"] == "Test Document"
    assert frontmatter["tags"] == ["tag1", "tag2"]
    assert body == "Body content here."

    # No frontmatter
    content_no_fm = "Just body text"
    fm, body = parse_frontmatter(content_no_fm)
    assert fm == {}
    assert body == content_no_fm


@pytest.mark.asyncio
async def test_check_document_exists():
    """Test document existence check"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Document exists
    mock_client.post.return_value = AsyncMock(
        status_code=200,
        json=lambda: [
            {"status": "OK"},
            {"status": "OK", "result": [{"id": "vault_memory:test"}]},
        ],
    )

    exists = await check_document_exists("vault_memory:test", mock_client)
    assert exists is True

    # Document doesn't exist
    mock_client.post.return_value = AsyncMock(
        status_code=200, json=lambda: [{"status": "OK"}, {"status": "OK", "result": []}]
    )

    exists = await check_document_exists("vault_memory:missing", mock_client)
    assert exists is False


@pytest.mark.asyncio
async def test_safe_create_edge_with_missing_target():
    """Test edge creation when target missing"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Target doesn't exist
    mock_client.post.return_value = AsyncMock(
        status_code=200, json=lambda: [{"status": "OK"}, {"status": "OK", "result": []}]
    )

    # skip_missing=True should return None
    result = await safe_create_edge(
        "vault_memory:source",
        "informed_by",
        "vault_memory:missing",
        None,
        mock_client,
        skip_missing=True,
    )
    assert result is None


@pytest.mark.asyncio
async def test_detect_circular_reference():
    """Test circular reference detection"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Circular reference exists
    mock_client.post.return_value = AsyncMock(
        status_code=200,
        json=lambda: [
            {"status": "OK"},
            {"status": "OK", "result": [{"id": "vault_memory:source"}]},
        ],
    )

    is_circular = await detect_circular_reference(
        "vault_memory:source", "vault_memory:target", "informed_by", mock_client
    )
    assert is_circular is True

    # No circular reference
    mock_client.post.return_value = AsyncMock(
        status_code=200, json=lambda: [{"status": "OK"}, {"status": "OK", "result": []}]
    )

    is_circular = await detect_circular_reference(
        "vault_memory:source", "vault_memory:target", "informed_by", mock_client
    )
    assert is_circular is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
