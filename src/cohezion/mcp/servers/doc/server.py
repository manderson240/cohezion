"""BMAD Doc Retriever MCP Server - Standalone document retrieval.

Port: 8364
Elegant simplicity: Single-purpose, token-efficient.

Features:
- Context7-compatible interface
- Token-efficient chunking
- Local embeddings (Ollama)
- SurrealDB vector search
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from aiohttp import web

from cohezion.mcp.servers.doc.indexer import (
    DocumentIndexer,
    OllamaEmbedder,
    SimpleSurrealStore,
    SmartChunker,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8364"))

# Global indexer instance
_indexer: DocumentIndexer | None = None


async def get_indexer() -> DocumentIndexer:
    """Get or create indexer."""
    global _indexer
    if _indexer is None:
        store = SimpleSurrealStore()
        embedder = OllamaEmbedder()
        chunker = SmartChunker()

        _indexer = DocumentIndexer(store, embedder, chunker)
        await store.connect()
        logger.info("Doc indexer initialized")
    return _indexer


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "bmad-doc-retriever",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "BMAD Doc Retriever",
            "version": "1.0.0",
            "port": MCP_PORT,
            "tools": [
                "resolve-library-id",
                "query-docs",
                "doc-index-library",
                "doc-get-stats",
            ],
            "features": [
                "Token-efficient chunks",
                "Local embeddings (Ollama)",
                "SurrealDB vector search",
                "Context7-compatible",
            ],
        }
    )


@routes.post("/tools/resolve-library-id")
async def tool_resolve_library(request: web.Request) -> web.Response:
    """Resolve library name to ID (Context7-compatible)."""
    try:
        data = await request.json()
        library_name = data.get("libraryName", "")

        # Simple resolution for BMAD modules
        if library_name.startswith("bmad/"):
            library_id = library_name
        elif library_name in ["bmm", "gds", "cis", "tea", "bmb", "core"]:
            library_id = f"bmad/{library_name}"
        else:
            # Try to find in _bmad
            library_id = f"bmad/{library_name}"

        return web.json_response(
            {
                "tool": "resolve-library-id",
                "libraryName": library_name,
                "libraryId": library_id,
            }
        )
    except Exception as e:
        logger.exception("Resolve failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/query-docs")
async def tool_query_docs(request: web.Request) -> web.Response:
    """Query documentation (Context7-compatible)."""
    try:
        data = await request.json()
        library_id = data.get("libraryId", "")
        query = data.get("query", "")

        if not query:
            return web.json_response({"error": "Query is required"}, status=400)

        indexer = await get_indexer()

        # Use library_id if provided, otherwise search all
        library = library_id if library_id else None

        result = await indexer.retrieve(query, library, max_tokens=2000)

        return web.json_response(
            {
                "tool": "query-docs",
                "libraryId": library_id,
                "query": query,
                "chunks": result["chunks"],
                "chunkCount": result["chunk_count"],
                "totalTokens": result["total_tokens"],
                "source": result["source"],
            }
        )
    except Exception as e:
        logger.exception("Query failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/doc-index-library")
async def tool_index_library(request: web.Request) -> web.Response:
    """Index a library directory."""
    try:
        data = await request.json()
        library_id = data.get("library_id", "")
        source_path = data.get("source_path", "")

        if not library_id or not source_path:
            return web.json_response({"error": "library_id and source_path are required"}, status=400)

        indexer = await get_indexer()
        result = await indexer.index_library(library_id, Path(source_path))

        return web.json_response(
            {
                "tool": "doc-index-library",
                "library_id": library_id,
                "files_indexed": result["files_indexed"],
                "chunks_created": result["chunks_created"],
                "total_tokens": result["total_tokens"],
            }
        )
    except Exception as e:
        logger.exception("Index failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/doc-get-stats")
async def tool_get_stats(request: web.Request) -> web.Response:
    """Get library statistics."""
    try:
        data = await request.json()
        library_id = data.get("library_id", "")

        if not library_id:
            return web.json_response({"error": "library_id is required"}, status=400)

        indexer = await get_indexer()
        stats = await indexer.store.get_library_stats(library_id)

        return web.json_response(
            {
                "tool": "doc-get-stats",
                "library_id": library_id,
                "stats": stats,
            }
        )
    except Exception as e:
        logger.exception("Stats failed")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


# Global app instance for import
app = create_app()


async def main():
    """Run the Doc Retriever MCP Server."""
    # Initialize indexer
    await get_indexer()

    logger.info(f"Starting BMAD Doc Retriever on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ Doc Retriever running on http://localhost:{MCP_PORT}")
    logger.info(f"   Health: http://localhost:{MCP_PORT}/health")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Doc Retriever stopped")
