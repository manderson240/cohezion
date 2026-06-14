import asyncio
import logging
import os
import random
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests
from aiohttp import web

_ARXIV_CATEGORIES: dict[str, str] = {
    "cs.AI": "Artificial Intelligence",
    "cs.LG": "Machine Learning",
    "cs.CL": "Computation and Language",
    "cs.CV": "Computer Vision and Pattern Recognition",
    "cs.MA": "Multiagent Systems",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.RO": "Robotics",
    "cs.SE": "Software Engineering",
    "cs.CR": "Cryptography and Security",
    "stat.ML": "Machine Learning (Statistics)",
}

_HF_TASKS: list[str] = [
    "text-generation",
    "text-classification",
    "image-classification",
    "object-detection",
    "reinforcement-learning",
    "question-answering",
    "summarization",
    "translation",
    "token-classification",
    "fill-mask",
    "feature-extraction",
    "image-segmentation",
    "automatic-speech-recognition",
]


def _parse_arxiv_xml(xml_text: str) -> list[dict[str, Any]]:
    """Parse arXiv Atom XML into a list of paper dicts."""
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    papers: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        entry_id = (entry.findtext("atom:id", "", ns) or "").split("/abs/")[-1]
        title = (entry.findtext("atom:title", "", ns) or "").strip()
        summary = (entry.findtext("atom:summary", "", ns) or "").strip()
        authors = [a.findtext("atom:name", "", ns) or "" for a in entry.findall("atom:author", ns)]
        categories = [c.get("term", "") for c in entry.findall("atom:category", ns)]
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
                break
        papers.append(
            {
                "id": entry_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "pdf_url": pdf_url,
            }
        )
    return papers


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

    def search_arxiv_advanced(
        self,
        query: str,
        category: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search arXiv with optional category and date filters."""
        if category and category not in _ARXIV_CATEGORIES:
            return [
                {
                    "error": f"Unknown category '{category}'",
                    "valid_categories": list(_ARXIV_CATEGORIES),
                }
            ]
        search_query = f"all:{query}"
        if category:
            search_query += f" AND cat:{category}"
        if date_from and date_to:
            search_query += f" AND submittedDate:[{date_from}0000 TO {date_to}2359]"
        try:
            resp = requests.get(
                self.sources["arxiv"],
                params={"search_query": search_query, "max_results": str(limit)},
                timeout=15,
            )
            resp.raise_for_status()
            return _parse_arxiv_xml(resp.text)
        except requests.exceptions.Timeout:
            return [{"error": "arxiv request timed out after 15s"}]
        except Exception as e:
            logger.error(f"search_arxiv_advanced failed: {e}")
            return [{"error": str(e)}]

    def get_hf_trending_models(self, limit: int = 10, task: str = "") -> list[dict[str, Any]]:
        """Fetch trending HuggingFace models, optionally filtered by task."""
        if task and task not in _HF_TASKS:
            return [
                {
                    "error": f"Unknown task '{task}'",
                    "valid_tasks": list(_HF_TASKS),
                }
            ]
        try:
            params: dict[str, Any] = {"limit": limit, "sort": "trending"}
            if task:
                params["pipeline_tag"] = task
            resp = requests.get("https://huggingface.co/api/models", params=params, timeout=10)
            resp.raise_for_status()
            models = resp.json()
            return [
                {
                    "id": m.get("id", ""),
                    "task": m.get("pipeline_tag", ""),
                    "likes": m.get("likes", 0),
                    "downloads": m.get("downloads", 0),
                }
                for m in models[:limit]
            ]
        except Exception as e:
            logger.error(f"get_hf_trending_models failed: {e}")
            return [{"error": str(e)}]

    def list_arxiv_categories(self) -> list[dict[str, str]]:
        """Return all supported arXiv category codes and descriptions."""
        return [{"code": k, "description": v} for k, v in _ARXIV_CATEGORIES.items()]

    def list_hf_tasks(self) -> list[str]:
        """Return all supported HuggingFace task names."""
        return list(_HF_TASKS)


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
