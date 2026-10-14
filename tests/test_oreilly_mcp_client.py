"""Unit tests for OReillyMCPClient and content extraction."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.mcp.oreilly_mcp_client import (
    OReillyContentItem,
    OReillyMCPClient,
    OReillyTOCItem,
)


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    cache = tmp_path / "oreilly_cache"
    cache.mkdir()
    return cache


def test_item_from_dict() -> None:
    data = {
        "title": "The Kaggle Book - Second Edition",
        "authors": ["Luca Massaron", "Bojan Tunguz", "Konrad Banachewicz"],
        "publisher_names": ["Packt Publishing"],
        "publication_date": "2025-12-19",
        "url": "https://learning.oreilly.com/library/view/-/9781835083208/?orm_source=mcp",
        "marketing_type": "book",
        "relevance_score": 0.9109,
        "page_count": 708,
    }
    item = OReillyContentItem.from_dict("urn:orm:book:9781835083208", data)
    assert item.title == "The Kaggle Book - Second Edition"
    assert "Luca Massaron" in item.authors
    assert item.page_count == 708
    assert item.relevance_score == 0.9109


def test_client_init_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OREILLY_MCP_TOKEN", raising=False)
    with patch.object(Path, "exists", return_value=False):
        with pytest.raises(ValueError, match="token not found"):
            OReillyMCPClient(token=None)


def test_search_parses_response_and_caches(temp_cache_dir: Path) -> None:
    client = OReillyMCPClient(token="mock_token_12345", cache_dir=temp_cache_dir)

    mock_mcp_resp = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "search_results": {
                                "urn:orm:book:9781835083208": {
                                    "title": "The Kaggle Book - Second Edition",
                                    "authors": ["Luca Massaron"],
                                    "publisher_names": ["Packt Publishing"],
                                    "publication_date": "2025-12-19",
                                    "url": "https://learning.oreilly.com/library/view/-/9781835083208/",
                                    "marketing_type": "book",
                                    "relevance_score": 0.95,
                                    "page_count": 708,
                                }
                            }
                        }
                    ),
                }
            ]
        },
        "isError": False,
    }

    with patch.object(client, "call_mcp_tool", return_value=mock_mcp_resp) as mock_call:
        items = client.search("Kaggle", n_items=1, use_cache=True)
        assert len(items) == 1
        assert items[0].title == "The Kaggle Book - Second Edition"
        assert mock_call.call_count == 1

        # Second call should hit the cache without calling call_mcp_tool again
        cached_items = client.search("Kaggle", n_items=1, use_cache=True)
        assert len(cached_items) == 1
        assert cached_items[0].title == "The Kaggle Book - Second Edition"
        assert mock_call.call_count == 1


def test_get_table_of_contents_parses_and_caches(temp_cache_dir: Path) -> None:
    client = OReillyMCPClient(token="mock_token_12345", cache_dir=temp_cache_dir)

    mock_toc_data = [
        {"title": "Chapter 1: Essentials", "href": "https://example.com/ch1", "depth": 1},
        {"title": "Chapter 7: Designing Good Validation", "href": "https://example.com/ch7", "depth": 1},
    ]

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_toc_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        toc = client.get_table_of_contents("9781835083208", use_cache=True)
        assert len(toc) == 2
        assert toc[0].title == "Chapter 1: Essentials"
        assert toc[1].title == "Chapter 7: Designing Good Validation"
        assert mock_urlopen.call_count == 1

        # Second call hits cache
        cached_toc = client.get_table_of_contents("9781835083208", use_cache=True)
        assert len(cached_toc) == 2
        assert mock_urlopen.call_count == 1
