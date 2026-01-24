"""
Research MCP Server - Specialized for arXiv, Hugging Face, and GitHub mining.

Provides tools:
- search_arxiv: Fetch research papers from arXiv
- get_hf_trending: Fetch trending papers/models from Hugging Face
- list_research_channels: List available research sources
"""

import logging
import time
import random
from typing import Any, Dict, List
import requests

logger = logging.getLogger(__name__)

class ResearchMinerServer:
    """
    MCP server for research discovery.
    Ensures API hygiene and rate limiting for external research sources.
    """

    def __init__(self):
        self.sources = {
            "arxiv": "https://export.arxiv.org/api/query",
            "hf": "https://huggingface.co/api/daily_papers",
            "github": "https://api.github.com/search/repositories"
        }

    def search_arxiv(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search arXiv for papers.
        """
        logger.info(f"🔍 ResearchMCPServer: Searching arXiv for '{query}'...")
        # Jittered delay to maintain hygiene
        time.sleep(1.0 + random.random())

        try:
            import arxiv
            search = arxiv.Search(
                query=query,
                max_results=limit,
                sort_by=arxiv.SortCriterion.Relevance
            )

            results = []
            for result in search.results():
                results.append({
                    "id": result.entry_id,
                    "title": result.title,
                    "summary": result.summary,
                    "url": result.pdf_url,
                    "published": result.published.isoformat()
                })
            return results
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return [{"error": str(e)}]

    def get_hf_trending(self, limit: int = 5) -> List[Dict[str, Any]]:
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
                    results.append({
                        "id": p.get("id"),
                        "title": p.get("title"),
                        "summary": p.get("summary"),
                        "url": f"https://huggingface.co/papers/{p.get('id')}"
                    })
                return results
            return [{"error": f"HF API returned {resp.status_code}"}]
        except Exception as e:
            logger.error(f"HF fetch failed: {e}")
            return [{"error": str(e)}]

    def list_research_channels(self) -> List[str]:
        """List available research channels."""
        return list(self.sources.keys())

# MCP tool definitions
TOOLS = [
    {
        "name": "search_arxiv",
        "description": "Search arXiv for technical research papers",
        "parameters": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 5},
        },
    },
    {
        "name": "get_hf_trending",
        "description": "Fetch daily trending papers from Hugging Face",
        "parameters": {
            "limit": {"type": "integer", "default": 5},
        },
    },
    {
        "name": "list_research_channels",
        "description": "List available research sources and channels",
        "parameters": {},
    },
]

# Singleton
_server: ResearchMinerServer | None = None

def get_server() -> ResearchMinerServer:
    global _server
    if _server is None:
        _server = ResearchMinerServer()
    return _server
