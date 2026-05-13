"""GitHub MCP Server - Model Context Protocol wrapper for GitHub API integration.

Provides: Search repos, get repo info, create issues, manage PRs.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import aiohttp
from fastmcp import FastMCP

from cohezion.security.credentials import get_credentials


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("github-mcp")

GITHUB_API_BASE = "https://api.github.com"

# Initialize FastMCP server
app = FastMCP("cohezion-github")


# Lazy accessor — Bitwarden vault calls at module import exceed the stdio MCP
# handshake budget (CLAUDE.md L54-72). (Ω12 P1 Patch 11)
@lru_cache(maxsize=1)
def get_github_token() -> str:
    return get_credentials().get_secret("COHEZION_GITHUB_TOKEN", env_var="GITHUB_TOKEN") or ""


def __getattr__(name: str):
    """Module-level lazy GITHUB_TOKEN — preserves existing call sites without import-time cost."""
    if name == "GITHUB_TOKEN":
        return get_github_token()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Primary: Vault Warden, Fallback: Environment
# Lazy accessor — Bitwarden vault calls at module import exceed the stdio MCP
# handshake budget (CLAUDE.md L54-72). (Ω12 P1 Patch 11)
from functools import lru_cache as _lru_cache


@_lru_cache(maxsize=1)
def get_github_token() -> str:
    return get_credentials().get_secret("COHEZION_GITHUB_TOKEN", env_var="GITHUB_TOKEN") or ""


def __getattr__(name: str):
    """Module-level lazy GITHUB_TOKEN — preserves existing call sites without import-time cost."""
    if name == "GITHUB_TOKEN":
        return get_github_token()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class GitHubService:
    """GitHub API client."""

    def __init__(self, token: str):
        self.token = token
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"token {self.token}" if self.token else "",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Cohezion-MCP/1.0",
            }
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def search_repos(self, query: str, sort: str = "stars", limit: int = 10) -> list[dict]:
        """Search GitHub repositories."""
        session = await self._get_session()
        url = f"{GITHUB_API_BASE}/search/repositories"
        params = {"q": query, "sort": sort, "order": "desc", "per_page": limit}

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "name": item["name"],
                            "full_name": item["full_name"],
                            "description": item.get("description", ""),
                            "stars": item["stargazers_count"],
                            "language": item.get("language", "Unknown"),
                            "url": item["html_url"],
                            "forks": item["forks_count"],
                            "open_issues": item["open_issues_count"],
                        }
                        for item in data.get("items", [])[:limit]
                    ]
                else:
                    logger.error(f"GitHub API error: {resp.status}")
                    return []
        except Exception as e:
            logger.exception(f"Error searching repos: {e}")
            return []

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any] | None:
        """Get repository details."""
        session = await self._get_session()
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "name": data["name"],
                        "full_name": data["full_name"],
                        "description": data.get("description", ""),
                        "stars": data["stargazers_count"],
                        "forks": data["forks_count"],
                        "open_issues": data["open_issues_count"],
                        "language": data.get("language", "Unknown"),
                        "url": data["html_url"],
                        "created_at": data["created_at"],
                        "updated_at": data["updated_at"],
                        "default_branch": data["default_branch"],
                        "license": data.get("license", {}).get("name", "No license"),
                        "topics": data.get("topics", []),
                    }
                else:
                    return None
        except Exception as e:
            logger.exception(f"Error getting repo: {e}")
            return None

    async def create_issue(
        self, owner: str, repo: str, title: str, body: str = "", labels: list[str] | None = None
    ) -> dict[str, Any]:
        """Create an issue in a repository."""
        if not self.token:
            return {"error": "GitHub token required for write operations"}

        session = await self._get_session()
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return {
                        "number": data["number"],
                        "title": data["title"],
                        "url": data["html_url"],
                        "state": data["state"],
                        "created_at": data["created_at"],
                    }
                else:
                    text = await resp.text()
                    return {"error": f"Failed to create issue: {resp.status}", "details": text}
        except Exception as e:
            logger.exception(f"Error creating issue: {e}")
            return {"error": str(e)}

    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Create a comment on an issue."""
        if not self.token:
            return {"error": "GitHub token required for write operations"}

        session = await self._get_session()
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        payload = {"body": body}

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return {
                        "id": data["id"],
                        "url": data["html_url"],
                        "created_at": data["created_at"],
                    }
                else:
                    text = await resp.text()
                    return {"error": f"Failed to create comment: {resp.status}", "details": text}
        except Exception as e:
            logger.exception(f"Error creating comment: {e}")
            return {"error": str(e)}

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """List issues in a repository."""
        session = await self._get_session()
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": min(limit, 100)}
        if labels:
            params["labels"] = ",".join(labels)

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    issues = []
                    for item in data:
                        if "pull_request" in item:
                            continue
                        labels = []
                        for label in item.get("labels", []):
                            if isinstance(label, dict) and "name" in label:
                                labels.append(label["name"])
                            elif isinstance(label, str):
                                labels.append(label)
                        issues.append(
                            {
                                "number": item["number"],
                                "title": item["title"],
                                "state": item["state"],
                                "url": item["html_url"],
                                "created_at": item["created_at"],
                                "labels": labels,
                            }
                        )
                        if len(issues) >= limit:
                            break
                    return issues
                else:
                    return []
        except Exception as e:
            logger.exception(f"Error listing issues: {e}")
            return []

    async def get_user(self, username: str) -> dict[str, Any] | None:
        """Get user information."""
        session = await self._get_session()
        url = f"{GITHUB_API_BASE}/users/{username}"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "login": data["login"],
                        "name": data.get("name", ""),
                        "bio": data.get("bio", ""),
                        "public_repos": data["public_repos"],
                        "followers": data["followers"],
                        "following": data["following"],
                        "url": data["html_url"],
                        "created_at": data["created_at"],
                    }
                else:
                    return None
        except Exception as e:
            logger.exception(f"Error getting user: {e}")
            return None


# Global service instance
_service: GitHubService | None = None


def get_service() -> GitHubService:
    """Get or create GitHub service."""
    global _service
    if _service is None:
        _service = GitHubService(get_github_token())
    return _service


@app.tool()
async def github_search_repos(query: str, sort: str = "stars", limit: int = 10) -> dict[str, Any]:
    """Search GitHub repositories.

    Args:
        query: Search query
        sort: Field to sort by (stars, forks, help-wanted-issues, updated)
        limit: Max results to return
    """
    service = get_service()
    repos = await service.search_repos(query, sort, limit)
    return {"query": query, "count": len(repos), "repositories": repos}


@app.tool()
async def github_get_repo(owner: str, repo: str) -> dict[str, Any]:
    """Get repository details.

    Args:
        owner: Repository owner (user or organization)
        repo: Repository name
    """
    service = get_service()
    result = await service.get_repo(owner, repo)
    if not result:
        return {"error": f"Repository not found: {owner}/{repo}"}
    return result


@app.tool()
async def github_create_issue(
    owner: str, repo: str, title: str, body: str = "", labels: list[str] | None = None
) -> dict[str, Any]:
    """Create an issue in a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        title: Issue title
        body: Issue description
        labels: Optional list of labels
    """
    service = get_service()
    return await service.create_issue(owner, repo, title, body, labels)


@app.tool()
async def github_create_issue_comment(
    owner: str, repo: str, issue_number: int, body: str
) -> dict[str, Any]:
    """Create a comment on an issue.

    Args:
        owner: Repository owner
        repo: Repository name
        issue_number: Issue number
        body: Comment body
    """
    service = get_service()
    return await service.create_issue_comment(owner, repo, issue_number, body)


@app.tool()
async def github_list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """List issues in a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state (open, closed, all)
        labels: Optional list of labels to filter by
        limit: Max results
    """
    service = get_service()
    issues = await service.list_issues(owner, repo, state, labels, limit)
    return {"issues": issues}


@app.tool()
async def github_get_user(username: str) -> dict[str, Any]:
    """Get user information.

    Args:
        username: GitHub username
    """
    service = get_service()
    user = await service.get_user(username)
    if not user:
        return {"error": f"User not found: {username}"}
    return user


if __name__ == "__main__":
    if not get_github_token():
        logger.warning("GITHUB_TOKEN not set - write operations will fail")
    app.run(transport="stdio")