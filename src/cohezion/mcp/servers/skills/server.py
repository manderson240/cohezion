"""Skills.sh MCP Server.

Port: 8362
Provides: Search, install, and execute skills from skills.sh (85K+ skills).
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys

from aiohttp import web

from .cache import SkillsCache
from .client import SkillsShClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Configuration
MCP_PORT = int(os.getenv("MCP_PORT", "8362"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Global instances
_client: SkillsShClient | None = None
_cache: SkillsCache | None = None


def get_client() -> SkillsShClient:
    """Get or create skills.sh client."""
    global _client
    if _client is None:
        _client = SkillsShClient()
    return _client


def get_cache() -> SkillsCache:
    """Get or create skills cache."""
    global _cache
    if _cache is None:
        _cache = SkillsCache()
    return _cache


# HTTP API routes
routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "skills",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    cache = get_cache()
    stats = await cache.get_stats()

    return web.json_response(
        {
            "name": "Skills.sh MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "source": "https://skills.sh",
            "cache": stats,
        }
    )


# =============================================================================
# TOOLS API
# =============================================================================


@routes.post("/tools/skills_search")
async def tool_skills_search(request: web.Request) -> web.Response:
    """Search skills.sh for skills."""
    try:
        data = await request.json()
        query = data.get("query", "")
        category = data.get("category")
        limit = data.get("limit", 20)

        client = get_client()
        skills = await client.search_skills(
            query=query,
            category=category,
            limit=limit,
        )

        return web.json_response(
            {
                "tool": "skills_search",
                "query": query,
                "category": category,
                "count": len(skills),
                "skills": [skill.to_dict() for skill in skills],
            }
        )
    except Exception as e:
        logger.exception("Error searching skills")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/skills_get")
async def tool_skills_get(request: web.Request) -> web.Response:
    """Get details of a specific skill."""
    try:
        data = await request.json()
        skill_id = data.get("skill_id", "")

        if "/" not in skill_id:
            return web.json_response(
                {"error": "Invalid skill_id format. Use owner/repo format."}, status=400
            )

        owner, repo = skill_id.split("/", 1)

        # Try cache first
        cache = get_cache()
        cached = await cache.get(skill_id)

        if cached:
            return web.json_response(
                {
                    "tool": "skills_get",
                    "skill_id": skill_id,
                    "source": "cache",
                    "skill": cached,
                }
            )

        # Fetch from API
        client = get_client()
        skill = await client.get_skill(owner, repo)

        if skill:
            # Cache it
            await cache.set(skill_id, skill.to_dict())

            return web.json_response(
                {
                    "tool": "skills_get",
                    "skill_id": skill_id,
                    "source": "api",
                    "skill": skill.to_dict(),
                }
            )

        return web.json_response({"error": f"Skill not found: {skill_id}"}, status=404)

    except Exception as e:
        logger.exception("Error getting skill")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/skills_install")
async def tool_skills_install(request: web.Request) -> web.Response:
    """Install a skill locally using npx skills add."""
    try:
        data = await request.json()
        skill_id = data.get("skill_id", "")

        import re as _re

        # Validate skill_id is a safe owner/repo format (alphanumeric, hyphens, underscores)
        if not _re.match(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$", skill_id):
            return web.json_response(
                {"error": "Invalid skill_id format. Use owner/repo format (alphanumeric only)."},
                status=400,
            )

        # Run npx skills add — skill_id is validated above
        import shutil

        npx_exec = shutil.which("npx") or "/usr/bin/npx"
        cmd = [npx_exec, "skills", "add", skill_id]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return web.json_response(
                {
                    "tool": "skills_install",
                    "skill_id": skill_id,
                    "status": "success",
                    "output": result.stdout,
                }
            )
        else:
            return web.json_response(
                {
                    "tool": "skills_install",
                    "skill_id": skill_id,
                    "status": "error",
                    "error": result.stderr,
                },
                status=500,
            )

    except subprocess.TimeoutExpired:
        return web.json_response({"error": "Installation timed out after 60 seconds"}, status=500)
    except Exception as e:
        logger.exception("Error installing skill")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/skills_execute")
async def tool_skills_execute(request: web.Request) -> web.Response:
    """Execute a skill (fetch and return content)."""
    try:
        data = await request.json()
        skill_id = data.get("skill_id", "")

        if "/" not in skill_id:
            return web.json_response(
                {"error": "Invalid skill_id format. Use owner/repo format."}, status=400
            )

        owner, repo = skill_id.split("/", 1)

        # Try cache first
        cache = get_cache()
        content = await cache.get_content(skill_id)
        source = "cache"

        if not content:
            # Fetch from API
            client = get_client()
            content = await client.get_skill_content(owner, repo)
            source = "api"

            if content:
                # Cache it
                await cache.set_content(skill_id, content)

        if content:
            return web.json_response(
                {
                    "tool": "skills_execute",
                    "skill_id": skill_id,
                    "source": source,
                    "content": content[:5000] if len(content) > 5000 else content,
                    "truncated": len(content) > 5000,
                    "full_length": len(content),
                }
            )

        return web.json_response(
            {"error": f"Could not fetch skill content: {skill_id}"}, status=404
        )

    except Exception as e:
        logger.exception("Error executing skill")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/skills_list")
async def tool_skills_list(request: web.Request) -> web.Response:
    """List skills by category or trending."""
    try:
        data = await request.json()
        category = data.get("category")
        trending = data.get("trending", False)
        limit = data.get("limit", 20)
        installed_only = data.get("installed_only", False)

        if installed_only:
            # List locally cached skills
            cache = get_cache()
            cached = await cache.list_cached()
            return web.json_response(
                {
                    "tool": "skills_list",
                    "source": "cache",
                    "count": len(cached),
                    "skills": cached,
                }
            )

        if trending:
            client = get_client()
            skills = await client.get_trending(limit=limit)
            return web.json_response(
                {
                    "tool": "skills_list",
                    "source": "api",
                    "filter": "trending",
                    "count": len(skills),
                    "skills": [skill.to_dict() for skill in skills],
                }
            )

        # Search by category
        client = get_client()
        skills = await client.search_skills(
            query="",
            category=category,
            limit=limit,
        )

        return web.json_response(
            {
                "tool": "skills_list",
                "source": "api",
                "category": category,
                "count": len(skills),
                "skills": [skill.to_dict() for skill in skills],
            }
        )

    except Exception as e:
        logger.exception("Error listing skills")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/skills_categories")
async def tool_skills_categories(request: web.Request) -> web.Response:
    """List available skill categories."""
    try:
        client = get_client()
        categories = await client.list_categories()

        return web.json_response(
            {
                "tool": "skills_categories",
                "count": len(categories),
                "categories": categories,
            }
        )
    except Exception as e:
        logger.exception("Error getting categories")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/skills_sync")
async def tool_skills_sync(request: web.Request) -> web.Response:
    """Sync skills cache with remote."""
    try:
        data = await request.json()
        force = data.get("force", False)

        cache = get_cache()

        if force:
            await cache.clear()

        # Fetch trending skills to populate cache
        client = get_client()
        skills = await client.get_trending(limit=100)

        cached_count = 0
        for skill in skills:
            await cache.set(skill.full_id, skill.to_dict())
            cached_count += 1

        stats = await cache.get_stats()

        return web.json_response(
            {
                "tool": "skills_sync",
                "force": force,
                "cached": cached_count,
                "stats": stats,
            }
        )
    except Exception as e:
        logger.exception("Error syncing skills")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/skills_cache_info")
async def tool_skills_cache_info(request: web.Request) -> web.Response:
    """Get cache statistics."""
    try:
        cache = get_cache()
        stats = await cache.get_stats()

        return web.json_response(
            {
                "tool": "skills_cache_info",
                "stats": stats,
            }
        )
    except Exception as e:
        logger.exception("Error getting cache info")
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


# Global app instance for import
app = create_app()


async def main():
    """Run the Skills.sh MCP Server."""
    # Initialize cache
    get_cache()

    # Run the server
    logger.info(f"Starting Skills.sh MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"Skills.sh MCP Server running on http://localhost:{MCP_PORT}")

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Skills.sh MCP Server stopped")
