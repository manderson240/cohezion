"""O'Reilly Learning MCP Client and Content Extraction Engine.

Integrates with O'Reilly Learning's Model Context Protocol (MCP) server
(https://api.oreilly.com/api/search/v1/mcp) and O'Reilly Learning Content APIs
(https://learning.oreilly.com/api/v2/) to enable autonomous search, table-of-contents
inspection, and targeted chapter extraction for agent workflows.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class OReillyContentItem:
    """Represents a content item returned by O'Reilly Search."""

    urn: str
    title: str
    authors: list[str]
    publisher_names: list[str]
    publication_date: str
    url: str
    display_format: str
    relevance_score: float
    page_count: Optional[int] = None

    @classmethod
    def from_dict(cls, urn: str, data: dict[str, Any]) -> OReillyContentItem:
        """Construct an item from O'Reilly API search dictionary."""
        return cls(
            urn=urn,
            title=data.get("title", "Untitled"),
            authors=data.get("authors", []),
            publisher_names=data.get("publisher_names", []),
            publication_date=data.get("publication_date", ""),
            url=data.get("url", ""),
            display_format=data.get("display_format", data.get("marketing_type", "book")),
            relevance_score=float(data.get("relevance_score", 0.0)),
            page_count=data.get("page_count"),
        )


@dataclass
class OReillyTOCItem:
    """Represents a chapter or section in a book's Table of Contents."""

    title: str
    url: str
    depth: int = 1


class OReillyMCPClient:
    """Client for O'Reilly MCP search and content extraction APIs.

    Parameters
    ----------
    token : str, optional
        O'Reilly API token. If omitted, loaded from OREILLY_MCP_TOKEN env var
        or from `/home/mike-anderson/dev/cohezion/.env`.
    cache_dir : Path or str, optional
        Directory for caching queries and responses. Defaults to `cache/oreilly`.
    """

    MCP_ENDPOINT = "https://api.oreilly.com/api/search/v1/mcp"
    API_V2_BASE = "https://learning.oreilly.com/api/v2"

    def __init__(
        self,
        token: Optional[str] = None,
        cache_dir: Path | str = "cache/oreilly",
    ) -> None:
        self.token = token or self._resolve_token()
        if not self.token:
            raise ValueError(
                "O'Reilly MCP token not found. Set OREILLY_MCP_TOKEN in environment "
                "or /home/mike-anderson/dev/cohezion/.env"
            )
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _resolve_token() -> str:
        """Resolve token from environment or developer .env file."""
        env_token = os.environ.get("OREILLY_MCP_TOKEN")
        if env_token:
            return env_token.strip("\"' ")

        env_file = Path("/home/mike-anderson/dev/cohezion/.env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("OREILLY_MCP_TOKEN="):
                    return line.split("=", 1)[1].strip("\"' ")

        return ""

    def _get_cache(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached JSON payload if present."""
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _set_cache(self, key: str, data: dict[str, Any]) -> None:
        """Store JSON payload in cache."""
        cache_file = self.cache_dir / f"{key}.json"
        try:
            cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def call_mcp_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool on the O'Reilly MCP Server via JSON-RPC 2.0.

        Parameters
        ----------
        tool_name : str
            Name of the MCP tool (e.g. 'search_oreilly_content').
        arguments : dict[str, Any]
            Arguments matching tool's inputSchema.

        Returns
        -------
        dict[str, Any]
            JSON-RPC response.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.MCP_ENDPOINT, method="POST", data=data)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")

        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def search(
        self,
        query: str,
        content_types: Optional[list[str]] = None,
        n_items: int = 5,
        order_by: Optional[str] = None,
        sort_order: str = "desc",
        use_cache: bool = True,
    ) -> list[OReillyContentItem]:
        """Search O'Reilly platform using the MCP search tool.

        Parameters
        ----------
        query : str
            Keyword search string.
        content_types : list[str], optional
            Filter by content types (e.g., ['books', 'articles', 'videos']).
        n_items : int, default 5
            Number of items to retrieve.
        order_by : str, optional
            Sorting criteria ('relevance', 'popularity', 'rating', 'date_published').
        sort_order : str, default 'desc'
            'desc' or 'asc'.
        use_cache : bool, default True
            Whether to use local disk cache.

        Returns
        -------
        list[OReillyContentItem]
            Parsed list of matching content items.
        """
        cache_key = hashlib.sha256(
            f"search:{query}:{content_types}:{n_items}:{order_by}:{sort_order}".encode()
        ).hexdigest()

        if use_cache:
            cached = self._get_cache(cache_key)
            if cached and "items" in cached:
                return [OReillyContentItem(**item) for item in cached["items"]]

        args: dict[str, Any] = {"query": query, "n_items": n_items}
        if content_types:
            args["content_types"] = content_types
        if order_by:
            args["order_by"] = order_by
            args["sort_order"] = sort_order

        resp = self.call_mcp_tool("search_oreilly_content", args)
        items: list[OReillyContentItem] = []

        if not resp.get("isError") and "result" in resp:
            for content in resp["result"].get("content", []):
                if content.get("type") == "text":
                    try:
                        raw = json.loads(content.get("text", "{}"))
                        for urn, metadata in raw.get("search_results", {}).items():
                            items.append(OReillyContentItem.from_dict(urn, metadata))
                    except Exception:
                        pass

        if use_cache and items:
            self._set_cache(cache_key, {"items": [asdict(i) for i in items]})

        return items

    def get_table_of_contents(
        self, book_urn_or_isbn: str, use_cache: bool = True
    ) -> list[OReillyTOCItem]:
        """Fetch the Table of Contents for an EPUB on O'Reilly.

        Parameters
        ----------
        book_urn_or_isbn : str
            Full URN (e.g., 'urn:orm:book:9781835083208') or ISBN ('9781835083208').
        use_cache : bool, default True
            Whether to read from cache.

        Returns
        -------
        list[OReillyTOCItem]
            List of TOC entries with title and URL.
        """
        urn = (
            book_urn_or_isbn
            if book_urn_or_isbn.startswith("urn:orm:book:")
            else f"urn:orm:book:{book_urn_or_isbn}"
        )
        cache_key = hashlib.sha256(f"toc:{urn}".encode()).hexdigest()

        if use_cache:
            cached = self._get_cache(cache_key)
            if cached and "toc" in cached:
                return [OReillyTOCItem(**item) for item in cached["toc"]]

        url = f"{self.API_V2_BASE}/epubs/{urn}/table-of-contents/"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Token {self.token}")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_toc = json.loads(resp.read().decode("utf-8"))

        toc_items: list[OReillyTOCItem] = []
        for entry in raw_toc:
            title = entry.get("title", entry.get("label", "Untitled Section"))
            href = entry.get("href", entry.get("url", ""))
            depth = entry.get("depth", 1)
            toc_items.append(OReillyTOCItem(title=title, url=href, depth=depth))

        if use_cache and toc_items:
            self._set_cache(cache_key, {"toc": [asdict(i) for i in toc_items]})

        return toc_items

    def get_chapter_metadata(
        self, chapter_url: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """Fetch chapter metadata and content URI from O'Reilly API.

        Parameters
        ----------
        chapter_url : str
            Full chapter endpoint URL.
        use_cache : bool, default True
            Whether to read from cache.

        Returns
        -------
        dict[str, Any]
            Chapter metadata.
        """
        cache_key = hashlib.sha256(f"chapter:{chapter_url}".encode()).hexdigest()

        if use_cache:
            cached = self._get_cache(cache_key)
            if cached:
                return cached

        req = urllib.request.Request(chapter_url)
        req.add_header("Authorization", f"Token {self.token}")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if use_cache and data:
            self._set_cache(cache_key, data)

        return data


if __name__ == "__main__":
    import sys

    client = OReillyMCPClient()
    if len(sys.argv) > 1 and sys.argv[1] == "--search":
        q = sys.argv[2] if len(sys.argv) > 2 else "Kaggle"
        res = client.search(q, n_items=3)
        for item in res:
            print(f"[{item.display_format}] {item.title} ({item.publication_date}) - {item.urn}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--toc":
        urn = sys.argv[2] if len(sys.argv) > 2 else "urn:orm:book:9781835083208"
        toc = client.get_table_of_contents(urn)
        for t in toc:
            print(f"[{t.depth}] {t.title} -> {t.url}")
    else:
        print("Usage: python -m cohezion.mcp.oreilly_mcp_client --search <query> | --toc <urn>")
