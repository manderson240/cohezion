# ruff: noqa: S104, S311  # random used for simulation/jitter, not cryptography
import asyncio
import logging
import os
import random
import time
from typing import Any

import requests
from aiohttp import web


logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8373"))


class ResearchMinerServer:
    """
    MCP server for research discovery.
    Ensures API hygiene and rate limiting for external research sources.
    """

    def __init__(self):
        self.sources = {
            "arxiv": "https://export.arxiv.org/api/query",
            "hf": "https://huggingface.co/api/daily_papers",
            "github": "https://api.github.com/search/repositories",
        }

    def search_arxiv(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search arXiv for papers.
        """
        logger.info(f"🔍 ResearchMCPServer: Searching arXiv for '{query}'...")
        # Jittered delay to maintain hygiene
        time.sleep(1.0 + random.random())

        try:
            import arxiv

            search = arxiv.Search(
                query=query, max_results=limit, sort_by=arxiv.SortCriterion.Relevance
            )

            results = []
            for result in search.results():
                results.append(
                    {
                        "id": result.entry_id,
                        "title": result.title,
                        "summary": result.summary,
                        "url": result.pdf_url,
                        "published": result.published.isoformat(),
                    }
                )
            return results
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return [{"error": str(e)}]

    def get_hf_trending(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Fetch daily papers from Hugging Face.
        """
        logger.info("🔍 ResearchMCPServer: Fetching HF Daily Papers...")
        time.sleep(1.0 + random.random())

        try:
            resp = requests.get(self.sources["hf"], timeout=10)
            if resp.status_code == 200:
                papers = resp.json()
                results = []
                for p in papers[:limit]:
                    results.append(
                        {
                            "id": p.get("id"),
                            "title": p.get("title"),
                            "summary": p.get("summary"),
                            "url": f"https://huggingface.co/papers/{p.get('id')}",
                        }
                    )
                return results
            return [{"error": f"HF API returned {resp.status_code}"}]
        except Exception as e:
            logger.error(f"HF fetch failed: {e}")
            return [{"error": str(e)}]

    def list_research_channels(self) -> list[str]:
        """List available research channels."""
        return list(self.sources.keys())


# Singleton
_server: ResearchMinerServer | None = None


def get_server() -> ResearchMinerServer:
    global _server
    if _server is None:
        _server = ResearchMinerServer()
    return _server


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "server": "research"})


@routes.post("/tools/search_arxiv")
async def tool_search_arxiv(request: web.Request) -> web.Response:
    data = await request.json()
    query = data.get("query", "")
    limit = data.get("limit", 5)
    server = get_server()
    return web.json_response(server.search_arxiv(query, limit))


@routes.post("/tools/get_hf_trending")
async def tool_get_hf_trending(request: web.Request) -> web.Response:
    data = await request.json()
    limit = data.get("limit", 5)
    server = get_server()
    return web.json_response(server.get_hf_trending(limit))


@routes.post("/tools/list_research_channels")
async def tool_list_research_channels(request: web.Request) -> web.Response:
    server = get_server()
    return web.json_response(server.list_research_channels())


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes(routes)
    return app


app = create_app()


async def main():
    get_server()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()
    logger.info(f"Research MCP Server running on port {MCP_PORT}")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
