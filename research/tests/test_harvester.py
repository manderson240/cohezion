"""Tests for the harvest module — source adapters and configuration loading."""

import asyncio
import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def sample_config():
    """Minimal valid config for testing."""
    return {
        "focus_areas": {
            "compound_engineering": {
                "queries": ["compound AI system architecture 2026"],
                "weight": 1.0,
            },
            "token_efficiency": {
                "queries": ["LLM token optimization techniques"],
                "weight": 1.0,
            },
        },
        "sources": {
            "hackernews": {
                "tags": ["story"],
                "queries": ["AI agent"],
                "min_points": 10,
            },
            "reddit": {
                "subreddits": ["MachineLearning"],
                "sort": "hot",
                "limit": 5,
            },
            "arxiv": {
                "categories": ["cs.AI"],
                "max_results": 5,
            },
        },
    }


# --- Config loading ---


def test_load_config_from_yaml(tmp_path, sample_config):
    """Config loads from a valid YAML file."""
    from research.harvester import load_config

    config_file = tmp_path / "sources.yaml"
    config_file.write_text(yaml.dump(sample_config))

    loaded = load_config(str(config_file))
    assert "focus_areas" in loaded
    assert len(loaded["focus_areas"]) == 2


def test_load_config_validates_required_fields(tmp_path):
    """Config raises ValueError when focus_areas is missing."""
    from research.harvester import load_config

    config_file = tmp_path / "bad.yaml"
    config_file.write_text(yaml.dump({"sources": {}}))

    with pytest.raises(ValueError, match="focus_areas"):
        load_config(str(config_file))


def test_load_config_validates_query_lists(tmp_path):
    """Config raises ValueError when a focus area has no queries."""
    from research.harvester import load_config

    bad_config = {
        "focus_areas": {
            "empty_area": {"queries": [], "weight": 1.0},
        },
    }
    config_file = tmp_path / "bad.yaml"
    config_file.write_text(yaml.dump(bad_config))

    with pytest.raises(ValueError, match="queries"):
        load_config(str(config_file))


# --- Individual adapters ---


@pytest.mark.asyncio
async def test_hackernews_adapter_returns_findings(sample_config):
    """HackerNews adapter returns Finding objects from mock API response."""
    from research.harvester import hackernews_adapter
    from research.pipeline import Finding

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hits": [
            {
                "title": "New AI Agent Framework",
                "url": "https://example.com/ai-agent",
                "points": 150,
                "objectID": "12345",
                "created_at": "2026-02-19T10:00:00Z",
            },
        ],
    }

    with patch("research.harvester.requests.get", return_value=mock_response):
        findings = await hackernews_adapter(
            sample_config["sources"]["hackernews"],
            sample_config["focus_areas"],
        )

    assert len(findings) >= 1
    assert isinstance(findings[0], Finding)
    assert findings[0].source == "hackernews"


@pytest.mark.asyncio
async def test_reddit_adapter_returns_findings(sample_config):
    """Reddit adapter returns Finding objects from mock JSON API."""
    from research.harvester import reddit_adapter
    from research.pipeline import Finding

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "New ML Paper Discussion",
                        "url": "https://reddit.com/r/MachineLearning/123",
                        "permalink": "/r/MachineLearning/comments/123",
                        "selftext": "Interesting discussion about agent memory",
                        "score": 200,
                    },
                },
            ],
        },
    }

    with patch("research.harvester.requests.get", return_value=mock_response):
        findings = await reddit_adapter(
            sample_config["sources"]["reddit"],
            sample_config["focus_areas"],
        )

    assert len(findings) >= 1
    assert isinstance(findings[0], Finding)
    assert findings[0].source == "reddit"


@pytest.mark.asyncio
async def test_arxiv_adapter_returns_findings(sample_config):
    """arXiv adapter returns Finding objects from mock API response."""
    from research.harvester import arxiv_adapter
    from research.pipeline import Finding

    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <title>Scaling Agent Memory Systems</title>
            <summary>We present a novel approach to agent memory.</summary>
            <id>http://arxiv.org/abs/2602.12345v1</id>
            <link href="http://arxiv.org/abs/2602.12345v1"/>
        </entry>
    </feed>"""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_xml

    with patch("research.harvester.requests.get", return_value=mock_response):
        findings = await arxiv_adapter(
            sample_config["sources"]["arxiv"],
            sample_config["focus_areas"],
        )

    assert len(findings) >= 1
    assert isinstance(findings[0], Finding)
    assert findings[0].source == "arxiv"


@pytest.mark.asyncio
async def test_web_search_adapter_returns_findings(sample_config):
    """Web search adapter returns Finding objects from DuckDuckGo."""
    from research.harvester import web_search_adapter
    from research.pipeline import Finding

    mock_results = [
        {
            "title": "Compound AI Systems Guide",
            "href": "https://example.com/compound-ai",
            "body": "A comprehensive guide to building compound AI systems.",
        },
    ]

    with patch("research.harvester.DDGS") as MockDDGS:
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = mock_results
        MockDDGS.return_value.__enter__ = MagicMock(return_value=mock_ddgs)
        MockDDGS.return_value.__exit__ = MagicMock(return_value=False)

        findings = await web_search_adapter(
            sample_config["focus_areas"],
        )

    assert len(findings) >= 1
    assert isinstance(findings[0], Finding)
    assert findings[0].source == "web_search"


@pytest.mark.asyncio
async def test_github_adapter_returns_findings(sample_config):
    """GitHub adapter returns Finding objects from mock API response."""
    from research.harvester import github_adapter
    from research.pipeline import Finding

    mock_search_resp = MagicMock()
    mock_search_resp.status_code = 200
    mock_search_resp.json.return_value = {
        "items": [
            {
                "full_name": "org/ai-tool",
                "description": "An AI agent framework",
                "html_url": "https://github.com/org/ai-tool",
            },
        ],
    }

    mock_release_resp = MagicMock()
    mock_release_resp.status_code = 200
    mock_release_resp.json.return_value = {
        "tag_name": "v1.0.0",
        "name": "Initial Release",
        "body": "First stable release of the framework.",
        "html_url": "https://github.com/org/repo/releases/tag/v1.0.0",
    }

    with patch("research.harvester.requests.get", side_effect=[mock_search_resp, mock_release_resp]):
        findings = await github_adapter(
            {"languages": ["python"], "repos": ["org/repo"]},
            sample_config["focus_areas"],
        )

    assert len(findings) >= 1
    assert isinstance(findings[0], Finding)
    assert findings[0].source in ("github_recent", "github_releases")


@pytest.mark.asyncio
async def test_blog_feed_adapter_returns_findings(sample_config):
    """Blog feed adapter returns Finding objects from mock HTML."""
    from research.harvester import blog_feed_adapter
    from research.pipeline import Finding

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><title>Simon Willison's Blog</title><body>Latest posts</body></html>"

    with patch("research.harvester.requests.get", return_value=mock_response):
        findings = await blog_feed_adapter(
            {"urls": ["https://simonwillison.net"]},
            sample_config["focus_areas"],
        )

    assert len(findings) >= 1
    assert isinstance(findings[0], Finding)
    assert findings[0].source == "blog_feed"


# --- Harvest orchestration ---


@pytest.mark.asyncio
async def test_harvest_runs_all_adapters(sample_config):
    """Harvest function runs all configured adapters in parallel."""
    from research.harvester import harvest
    from research.pipeline import Finding

    mock_finding = Finding(
        title="Test",
        url="https://example.com",
        source="test",
        snippet="test",
        category="compound_engineering",
    )

    with patch("research.harvester.web_search_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.hackernews_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.reddit_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.arxiv_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.github_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.blog_feed_adapter", new_callable=AsyncMock, return_value=[mock_finding]):
        findings = await harvest(sample_config)

    assert len(findings) >= 1


@pytest.mark.asyncio
async def test_harvest_handles_adapter_failure(sample_config):
    """Harvest continues when one adapter raises an exception."""
    from research.harvester import harvest
    from research.pipeline import Finding

    mock_finding = Finding(
        title="Test",
        url="https://example.com",
        source="test",
        snippet="test",
        category="compound_engineering",
    )

    with patch("research.harvester.web_search_adapter", new_callable=AsyncMock, side_effect=Exception("API down")), \
         patch("research.harvester.hackernews_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.reddit_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.arxiv_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.github_adapter", new_callable=AsyncMock, return_value=[mock_finding]), \
         patch("research.harvester.blog_feed_adapter", new_callable=AsyncMock, return_value=[mock_finding]):
        findings = await harvest(sample_config)

    # Should still get findings from the adapters that didn't fail
    assert len(findings) >= 1
