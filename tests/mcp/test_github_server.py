"""Tests for GitHub MCP Server."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.mcp.servers.github.server import GitHubService


@pytest.fixture
def service():
    return GitHubService(token="fake-token")


@pytest.mark.asyncio
async def test_list_issues_filters_prs(service):
    """Verify that list_issues excludes pull requests."""
    # Mock data: 1 issue, 1 PR
    mock_data = [
        {
            "number": 1,
            "title": "Real Issue",
            "state": "open",
            "html_url": "https://github.com/owner/repo/issues/1",
            "created_at": "2026-04-07T12:00:00Z",
            "labels": [{"name": "bug"}],
        },
        {
            "number": 2,
            "title": "Pull Request",
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/2",
            "created_at": "2026-04-07T12:01:00Z",
            "labels": [],
            "pull_request": {},  # This indicates it's a PR
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_data)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch.object(service, "_get_session", AsyncMock(return_value=mock_session)):
        issues = await service.list_issues("owner", "repo")

        assert len(issues) == 1
        assert issues[0]["number"] == 1
        assert issues[0]["title"] == "Real Issue"


@pytest.mark.asyncio
async def test_list_issues_handles_string_labels(service):
    """Verify that list_issues handles labels as strings or dicts."""
    mock_data = [
        {
            "number": 1,
            "title": "Issue with mixed labels",
            "state": "open",
            "html_url": "url",
            "created_at": "date",
            "labels": [{"name": "dict-label"}, "string-label"],
        }
    ]

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_data)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch.object(service, "_get_session", AsyncMock(return_value=mock_session)):
        issues = await service.list_issues("owner", "repo")

        assert len(issues) == 1
        assert "dict-label" in issues[0]["labels"]
        assert "string-label" in issues[0]["labels"]


@pytest.mark.asyncio
async def test_list_issues_pagination_limit(service):
    """Verify that list_issues respects the limit and caps per_page."""
    # Mock 150 items, but we only want 5
    mock_data = [
        {
            "number": i,
            "title": f"Issue {i}",
            "state": "open",
            "html_url": "u",
            "created_at": "d",
            "labels": [],
        }
        for i in range(150)
    ]

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_data)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch.object(service, "_get_session", AsyncMock(return_value=mock_session)):
        # Case 1: Limit 5
        issues = await service.list_issues("owner", "repo", limit=5)
        assert len(issues) == 5

        # Verify params were capped at 100
        _args, kwargs = mock_session.get.call_args
        assert kwargs["params"]["per_page"] == 100 or kwargs["params"]["per_page"] == 5
