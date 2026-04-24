# ruff: noqa: S104  # binds 0.0.0.0 in dev/internal services
"""GitHub MCP Server - GitHub API integration.

Port: Auto-allocated by MCP Manager
Provides: Search repos, get repo info, create issues, manage PRs
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

import aiohttp
from aiohttp import web

from cohezion.security.credentials import get_credentials


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Configuration
MCP_PORT = int(os.getenv("MCP_PORT", "8363"))
# Primary: Vault Warden, Fallback: Environment
GITHUB_TOKEN = get_credentials().get_secret("COHEZION_GITHUB_TOKEN", env_var="GITHUB_TOKEN") or ""
GITHUB_API_BASE = "https://api.github.com"


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
    ) -> dict[str, Any] | None:
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
            return None

    async def list_issues(
        self, owner: str, repo: str, state: str = "open", limit: int = 10
    ) -> list[dict]:
        """List issues in a repository."""
        session = await self._get_session()
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": limit}

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "number": item["number"],
                            "title": item["title"],
                            "state": item["state"],
                            "url": item["html_url"],
                            "created_at": item["created_at"],
                            "labels": [label["name"] for label in item.get("labels", [])],
                        }
                        for item in data[:limit]
                    ]
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

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global service instance
_service: GitHubService | None = None


def get_service() -> GitHubService:
    """Get or create GitHub service."""
    global _service
    if _service is None:
        _service = GitHubService(GITHUB_TOKEN)
    return _service


# HTTP API routes
routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "github",
            "port": MCP_PORT,
            "authenticated": bool(GITHUB_TOKEN),
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "GitHub MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "authenticated": bool(GITHUB_TOKEN),
            "tools": [
                "github_search_repos",
                "github_get_repo",
                "github_create_issue",
                "github_list_issues",
                "github_get_user",
            ],
            "note": "Set GITHUB_TOKEN env var for write operations",
        }
    )


# =============================================================================
# TOOLS
# =============================================================================


@routes.post("/tools/github_search_repos")
async def tool_github_search_repos(request: web.Request) -> web.Response:
    """Search GitHub repositories."""
    try:
        data = await request.json()
        query = data.get("query", "")
        sort = data.get("sort", "stars")
        limit = data.get("limit", 10)

        if not query:
            return web.json_response({"error": "Query is required"}, status=400)

        service = get_service()
        repos = await service.search_repos(query, sort, limit)

        return web.json_response(
            {
                "tool": "github_search_repos",
                "query": query,
                "sort": sort,
                "count": len(repos),
                "repositories": repos,
            }
        )
    except Exception as e:
        logger.exception("Error searching repos")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/github_get_repo")
async def tool_github_get_repo(request: web.Request) -> web.Response:
    """Get repository details."""
    try:
        data = await request.json()
        owner = data.get("owner", "")
        repo = data.get("repo", "")

        if not owner or not repo:
            return web.json_response({"error": "Owner and repo are required"}, status=400)

        service = get_service()
        result = await service.get_repo(owner, repo)

        if result:
            return web.json_response(
                {
                    "tool": "github_get_repo",
                    "owner": owner,
                    "repo": repo,
                    "repository": result,
                }
            )
        else:
            return web.json_response({"error": f"Repository not found: {owner}/{repo}"}, status=404)
    except Exception as e:
        logger.exception("Error getting repo")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/github_create_issue")
async def tool_github_create_issue(request: web.Request) -> web.Response:
    """Create an issue in a repository."""
    try:
        data = await request.json()
        owner = data.get("owner", "")
        repo = data.get("repo", "")
        title = data.get("title", "")
        body = data.get("body", "")
        labels = data.get("labels", [])

        if not owner or not repo or not title:
            return web.json_response({"error": "Owner, repo, and title are required"}, status=400)

        if not GITHUB_TOKEN:
            return web.json_response(
                {"error": "GITHUB_TOKEN environment variable required for write operations"},
                status=401,
            )

        service = get_service()
        result = await service.create_issue(owner, repo, title, body, labels)

        if result and "error" not in result:
            return web.json_response(
                {
                    "tool": "github_create_issue",
                    "owner": owner,
                    "repo": repo,
                    "issue": result,
                    "status": "created",
                }
            )
        else:
            return web.json_response(
                {
                    "error": result.get("error", "Failed to create issue")
                    if result
                    else "Unknown error"
                },
                status=500,
            )
    except Exception as e:
        logger.exception("Error creating issue")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/github_list_issues")
async def tool_github_list_issues(request: web.Request) -> web.Response:
    """List issues in a repository."""
    try:
        data = await request.json()
        owner = data.get("owner", "")
        repo = data.get("repo", "")
        state = data.get("state", "open")
        limit = data.get("limit", 10)

        if not owner or not repo:
            return web.json_response({"error": "Owner and repo are required"}, status=400)

        service = get_service()
        issues = await service.list_issues(owner, repo, state, limit)

        return web.json_response(
            {
                "tool": "github_list_issues",
                "owner": owner,
                "repo": repo,
                "state": state,
                "count": len(issues),
                "issues": issues,
            }
        )
    except Exception as e:
        logger.exception("Error listing issues")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/github_get_user")
async def tool_github_get_user(request: web.Request) -> web.Response:
    """Get user information."""
    try:
        data = await request.json()
        username = data.get("username", "")

        if not username:
            return web.json_response({"error": "Username is required"}, status=400)

        service = get_service()
        user = await service.get_user(username)

        if user:
            return web.json_response(
                {
                    "tool": "github_get_user",
                    "username": username,
                    "user": user,
                }
            )
        else:
            return web.json_response({"error": f"User not found: {username}"}, status=404)
    except Exception as e:
        logger.exception("Error getting user")
        return web.json_response({"error": str(e)}, status=500)


# =============================================================================
# MAIN
# =============================================================================


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


# Global app instance
app = create_app()


async def main():
    """Run the GitHub MCP Server."""
    # Initialize service
    get_service()

    # Run the server
    logger.info(f"Starting GitHub MCP Server on port {MCP_PORT}")
    if not GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set - write operations will fail")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ GitHub MCP Server running on http://localhost:{MCP_PORT}")
    logger.info(f"   Health check: http://localhost:{MCP_PORT}/health")
    logger.info("   API: https://api.github.com")

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("GitHub MCP Server stopped")
