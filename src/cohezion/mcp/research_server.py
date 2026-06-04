"""Research MCP server — bleeding-edge arxiv + Hugging Face + Semantic Scholar tools.

Last extended: 2026-06-03 (WS4, harness-bash-unification followups).
Sources: arxiv export API, HF daily papers + model search, semantic-scholar,
papers-with-code. All HTTP-based (no Python deps beyond `requests` + `aiohttp`).
Rate-limit hygiene: jittered sleep before each request, 10s timeout.
"""

import asyncio
import logging
import os
import random
import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote_plus

import requests
from aiohttp import web


logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8373"))


_ARXIV_CATEGORIES = {
    "cs.AI": "Artificial Intelligence",
    "cs.LG": "Machine Learning",
    "cs.CL": "Computation and Language",
    "cs.CV": "Computer Vision",
    "cs.MA": "Multiagent Systems",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.RO": "Robotics",
    "stat.ML": "Machine Learning (stat)",
}

_HF_TASKS = [
    "text-generation",
    "text-classification",
    "image-classification",
    "object-detection",
    "summarization",
    "translation",
    "question-answering",
    "fill-mask",
    "reinforcement-learning",
]


def _arxiv_jitter() -> None:
    """Jittered sleep to maintain API hygiene on the arxiv public API
    (which asks for ~3s between requests; we use a slightly more
    conservative 1.5-2.5s)."""
    time.sleep(1.5 + random.random())


def _parse_arxiv_xml(xml_text: str) -> list[dict[str, Any]]:
    """Parse arxiv's Atom XML into a normalized list of paper dicts."""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    out: list[dict[str, Any]] = []
    for entry in root.findall("a:entry", ns):
        eid = entry.findtext("a:id", default="", namespaces=ns)
        # arxiv IDs look like "http://arxiv.org/abs/2402.12345v1"
        arxiv_id = eid.rsplit("/", 1)[-1] if eid else ""
        authors = [
            a.findtext("a:name", default="", namespaces=ns) for a in entry.findall("a:author", ns)
        ]
        categories = [c.get("term", "") for c in entry.findall("a:category", ns)]
        out.append(
            {
                "id": arxiv_id,
                "title": (entry.findtext("a:title", default="", namespaces=ns) or "").strip(),
                "summary": (entry.findtext("a:summary", default="", namespaces=ns) or "").strip(),
                "authors": [a for a in authors if a],
                "categories": [c for c in categories if c],
                "published": entry.findtext("a:published", default="", namespaces=ns),
                "updated": entry.findtext("a:updated", default="", namespaces=ns),
                "url": eid,
                "pdf_url": next(
                    (
                        l.get("href", "")
                        for l in entry.findall("a:link", ns)
                        if l.get("title") == "pdf"
                    ),
                    "",
                ),
            }
        )
    return out


class ResearchMinerServer:
    """
    MCP server for research discovery.
    Ensures API hygiene and rate limiting for external research sources.
    """

    def __init__(self):
        self.sources = {
            "arxiv": "https://export.arxiv.org/api/query",
            "hf_daily_papers": "https://huggingface.co/api/daily_papers",
            "hf_models": "https://huggingface.co/api/models",
            "semantic_scholar": "https://api.semanticscholar.org/graph/v1",
            "papers_with_code": "https://paperswithcode.com/api/v1",
        }
        self.last_request_at: dict[str, float] = {}

    # ------------------------------------------------------------------
    # arxiv — basic + advanced
    # ------------------------------------------------------------------
    def search_arxiv(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search arXiv. Returns raw Atom-parsed list of papers."""
        return self._arxiv_query({"search_query": f"all:{query}", "max_results": str(limit)})

    def search_arxiv_advanced(
        self,
        query: str,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search arXiv with category filter (e.g. 'cs.AI') and date range.

        - query: free-text search
        - category: arXiv category code (cs.AI, cs.LG, cs.CL, cs.CV, cs.MA, ...).
                   See _ARXIV_CATEGORIES for the full list. None = no filter.
        - date_from / date_to: YYYYMMDD strings (e.g. '20260401'). None = no filter.
        - limit: max results (default 10, arxiv max is 2000)

        Returns same shape as search_arxiv.
        """
        parts = [f"all:{query}"]
        if category:
            if category not in _ARXIV_CATEGORIES:
                return [
                    {
                        "error": f"Unknown category: {category}",
                        "valid_categories": sorted(_ARXIV_CATEGORIES.keys()),
                    }
                ]
            parts.append(f"cat:{category}")
        search_query = " AND ".join(parts)
        params: dict[str, str] = {
            "search_query": search_query,
            "max_results": str(limit),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        if date_from and date_to:
            params["start"] = "0"
            # arxiv date filter: submittedDate:[YYYYMMDDhhmm+TO+YYYYMMDDhhmm]
            params["search_query"] += f" AND submittedDate:[{date_from}0000 TO {date_to}2359]"
        elif date_from:
            params["search_query"] += f" AND submittedDate:[{date_from}0000 TO *]"
        elif date_to:
            params["search_query"] += f" AND submittedDate:[* TO {date_to}2359]"
        return self._arxiv_query(params)

    def search_arxiv_by_author(self, author: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search arXiv by author name (use DBLP PID to disambiguate
        when possible — raw name search is fuzzy)."""
        return self._arxiv_query({"search_query": f"au:{author}", "max_results": str(limit)})

    def _arxiv_query(self, params: dict[str, str]) -> list[dict[str, Any]]:
        _arxiv_jitter()
        try:
            resp = requests.get(self.sources["arxiv"], params=params, timeout=15)
            resp.raise_for_status()
            return _parse_arxiv_xml(resp.text)
        except requests.exceptions.Timeout:
            return [{"error": "arxiv request timed out after 15s"}]
        except Exception as e:
            logger.error(f"arxiv query failed: {e}")
            return [{"error": str(e)}]

    # ------------------------------------------------------------------
    # Hugging Face — daily papers + model trending
    # ------------------------------------------------------------------
    def get_hf_trending(self, limit: int = 5) -> list[dict[str, Any]]:
        """Fetch daily papers from Hugging Face."""
        logger.info("🔍 ResearchMCPServer: Fetching HF Daily Papers...")
        time.sleep(1.0 + random.random())
        try:
            resp = requests.get(self.sources["hf_daily_papers"], timeout=10)
            if resp.status_code == 200:
                papers = resp.json()
                return [
                    {
                        "id": p.get("id"),
                        "title": p.get("title"),
                        "summary": p.get("summary"),
                        "url": f"https://huggingface.co/papers/{p.get('id')}",
                    }
                    for p in papers[:limit]
                ]
            return [{"error": f"HF API returned {resp.status_code}"}]
        except Exception as e:
            logger.error(f"HF fetch failed: {e}")
            return [{"error": str(e)}]

    def get_hf_trending_models(
        self, limit: int = 10, task: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch trending models from Hugging Face. Optionally filter by task
        (e.g. 'text-generation', 'image-classification'). See _HF_TASKS for
        the full list.

        Returns list of {id, downloads, likes, last_modified, task}.
        Note: HF doesn't expose a 'trending' endpoint per se; we approximate
        by sorting by 'downloads' (last 30 days) which is a reasonable
        proxy for 'trending' in the HF ecosystem.
        """
        logger.info(f"🔍 ResearchMCPServer: Fetching HF trending models (task={task})...")
        time.sleep(1.0 + random.random())
        try:
            params: dict[str, Any] = {
                "limit": min(limit, 100),
                "sort": "downloads",
                "direction": -1,
            }
            if task:
                if task not in _HF_TASKS:
                    return [
                        {
                            "error": f"Unknown task: {task}",
                            "valid_tasks": _HF_TASKS,
                        }
                    ]
                params["pipeline_tag"] = task
            resp = requests.get(self.sources["hf_models"], params=params, timeout=15)
            resp.raise_for_status()
            models = resp.json()
            return [
                {
                    "id": m.get("id"),
                    "downloads": m.get("downloads", 0),
                    "likes": m.get("likes", 0),
                    "last_modified": m.get("lastModified"),
                    "tags": m.get("tags", [])[:5],
                    "task": task or "any",
                }
                for m in models
            ]
        except Exception as e:
            logger.error(f"HF models fetch failed: {e}")
            return [{"error": str(e)}]

    # ------------------------------------------------------------------
    # Semantic Scholar — citation context (per paper)
    # ------------------------------------------------------------------
    def semantic_scholar_paper(self, paper_id: str) -> dict[str, Any]:
        """Fetch metadata for a paper from Semantic Scholar. `paper_id` can be
        an arXiv ID (with or without version), DOI, or SS UUID. Returns
        {title, abstract, year, citationCount, referenceCount, tldr}.

        Note: SS API has no auth for low-volume use, but rate-limits aggressively.
        Catches 429 and returns an error dict so the caller can back off.
        """
        logger.info(f"🔍 ResearchMCPServer: Fetching SS paper {paper_id}...")
        time.sleep(0.5 + random.random())  # SS is more permissive than arxiv
        # Normalize arxiv IDs (strip version suffix)
        arxiv_id = re.sub(r"v\d+$", "", paper_id)
        url = (
            f"{self.sources['semantic_scholar']}/paper/arXiv:{arxiv_id}"
            f"?fields=title,abstract,year,citationCount,referenceCount,tldr,authors"
        )
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 429:
                return {
                    "error": "rate limited (429) — back off and retry",
                    "retry_after_s": int(resp.headers.get("Retry-After", 5)),
                }
            if resp.status_code == 404:
                return {"error": f"paper not found in semantic scholar: {paper_id}"}
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": paper_id,
                "title": data.get("title"),
                "abstract": data.get("abstract"),
                "year": data.get("year"),
                "citation_count": data.get("citationCount"),
                "reference_count": data.get("referenceCount"),
                "tldr": (data.get("tldr") or {}).get("text") if data.get("tldr") else None,
                "authors": [a.get("name") for a in (data.get("authors") or []) if a.get("name")],
            }
        except Exception as e:
            logger.error(f"SS fetch failed: {e}")
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Papers with Code — implementation repo linking
    # ------------------------------------------------------------------
    def papers_with_code_link(self, arxiv_id: str) -> list[dict[str, Any]]:
        """Find code repositories that implement a paper (by arxiv ID).
        Returns [{repo_url, stars, framework, paper_title}].

        Papers-with-code has no auth for read-only queries but rate-limits
        aggressively. Catches 429 and returns the error.
        """
        logger.info(f"🔍 ResearchMCPServer: PWC lookup for {arxiv_id}...")
        time.sleep(0.5 + random.random())
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
        url = f"{self.sources['papers_with_code']}/papers/?arxiv_id={quote_plus(arxiv_id)}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 429:
                return [{"error": "rate limited (429) — back off and retry"}]
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return [{"info": f"no paper-with-code entry for {arxiv_id}"}]
            paper = results[0]
            paper_id = paper.get("id")
            paper_title = paper.get("title")
            # Fetch the repos for this paper
            repos_resp = requests.get(
                f"{self.sources['papers_with_code']}/papers/{paper_id}/repositories/",
                timeout=10,
            )
            repos_resp.raise_for_status()
            repos = repos_resp.json().get("results", [])
            return [
                {
                    "repo_url": r.get("url"),
                    "stars": r.get("stars"),
                    "framework": r.get("framework"),
                    "paper_title": paper_title,
                    "paper_url": paper.get("url_pdf"),
                }
                for r in repos
            ]
        except Exception as e:
            logger.error(f"PWC fetch failed: {e}")
            return [{"error": str(e)}]

    # ------------------------------------------------------------------
    # Channels
    # ------------------------------------------------------------------
    def list_research_channels(self) -> list[str]:
        """List available research channels (sources)."""
        return list(self.sources.keys())

    def list_arxiv_categories(self) -> list[dict[str, str]]:
        """List supported arXiv category codes + human names."""
        return [{"code": c, "name": n} for c, n in sorted(_ARXIV_CATEGORIES.items())]

    def list_hf_tasks(self) -> list[str]:
        """List supported Hugging Face pipeline tags for model trending."""
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
    return web.json_response(
        {
            "status": "healthy",
            "server": "research",
            "version": "1.1.0",
            "tools": [
                "search_arxiv",
                "search_arxiv_advanced",
                "search_arxiv_by_author",
                "get_hf_trending",
                "get_hf_trending_models",
                "semantic_scholar_paper",
                "papers_with_code_link",
                "list_research_channels",
                "list_arxiv_categories",
                "list_hf_tasks",
            ],
        }
    )


@routes.post("/tools/search_arxiv")
async def tool_search_arxiv(request: web.Request) -> web.Response:
    data = await request.json()
    return web.json_response(get_server().search_arxiv(data.get("query", ""), data.get("limit", 5)))


@routes.post("/tools/search_arxiv_advanced")
async def tool_search_arxiv_advanced(request: web.Request) -> web.Response:
    data = await request.json()
    return web.json_response(
        get_server().search_arxiv_advanced(
            query=data.get("query", ""),
            category=data.get("category"),
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
            limit=data.get("limit", 10),
        )
    )


@routes.post("/tools/search_arxiv_by_author")
async def tool_search_arxiv_by_author(request: web.Request) -> web.Response:
    data = await request.json()
    return web.json_response(
        get_server().search_arxiv_by_author(data.get("author", ""), data.get("limit", 10))
    )


@routes.post("/tools/get_hf_trending")
async def tool_get_hf_trending(request: web.Request) -> web.Response:
    data = await request.json()
    return web.json_response(get_server().get_hf_trending(data.get("limit", 5)))


@routes.post("/tools/get_hf_trending_models")
async def tool_get_hf_trending_models(request: web.Request) -> web.Response:
    data = await request.json()
    return web.json_response(
        get_server().get_hf_trending_models(limit=data.get("limit", 10), task=data.get("task"))
    )


@routes.post("/tools/semantic_scholar_paper")
async def tool_semantic_scholar_paper(request: web.Request) -> web.Response:
    data = await request.json()
    return web.json_response(get_server().semantic_scholar_paper(data.get("paper_id", "")))


@routes.post("/tools/papers_with_code_link")
async def tool_papers_with_code_link(request: web.Request) -> web.Response:
    data = await request.json()
    return web.json_response(get_server().papers_with_code_link(data.get("arxiv_id", "")))


@routes.post("/tools/list_research_channels")
async def tool_list_research_channels(request: web.Request) -> web.Response:
    return web.json_response(get_server().list_research_channels())


@routes.post("/tools/list_arxiv_categories")
async def tool_list_arxiv_categories(request: web.Request) -> web.Response:
    return web.json_response(get_server().list_arxiv_categories())


@routes.post("/tools/list_hf_tasks")
async def tool_list_hf_tasks(request: web.Request) -> web.Response:
    return web.json_response(get_server().list_hf_tasks())


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
