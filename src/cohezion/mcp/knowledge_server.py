# binds 0.0.0.0 in dev/internal services
"""
Knowledge MCP Server - RAG over library and skills.

Provides tools:
- search_knowledge: Semantic search over documents
- get_skill: Retrieve a specific skill
- list_skills: List available skills
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from aiohttp import web


logger = logging.getLogger(__name__)

# Paths
LIBRARY_PATH = Path(__file__).parent.parent / "library"
SKILLS_PATH = Path(__file__).parent.parent / "skills"
KNOWLEDGE_GRAPH_PATH = Path(__file__).parent.parent / "knowledge_graph"

MCP_PORT = int(os.getenv("MCP_PORT", "8371"))


class KnowledgeMCP:
    """
    MCP server for knowledge retrieval.

    Reduces token usage by serving only relevant content.
    """

    def __init__(self):
        self._skills_cache: dict[str, str] = {}
        self._library_index: list[dict[str, Any]] = []
        # Lazily constructed on first corpus search; None until then so import stays cheap.
        self._corpus: Any | None = None
        self._load_index()

    def _load_index(self) -> None:
        """Build index of available knowledge."""
        # Index skills
        if SKILLS_PATH.exists():
            for skill_file in SKILLS_PATH.glob("*.md"):
                name = skill_file.stem
                # Skip YAML frontmatter (added by scripts/migrate_skills_to_frontmatter.py
                # per Agent Skills spec) before extracting the 200-char summary,
                # so the cache surfaces the prose body not the metadata block.
                full = skill_file.read_text()
                if full.lstrip().startswith("---\n") or full.lstrip().startswith("---\r\n"):
                    end = full.find("\n---\n", 4)
                    if end != -1:
                        full = full[end + len("\n---\n") :].lstrip()
                self._skills_cache[name] = full[:200]

        # Index library
        if LIBRARY_PATH.exists():
            for doc in LIBRARY_PATH.glob("*.md"):
                self._library_index.append(
                    {
                        "name": doc.stem,
                        "path": str(doc),
                        "type": "document",
                    }
                )

        logger.info(f"Indexed {len(self._skills_cache)} skills, {len(self._library_index)} docs")

    def search_knowledge(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search for relevant knowledge.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching items with snippets
        """
        results = []
        query_lower = query.lower()

        # Search skills
        for name, content in self._skills_cache.items():
            if query_lower in name.lower() or query_lower in content.lower():
                results.append(
                    {
                        "type": "skill",
                        "name": name,
                        "snippet": content[:100] + "...",
                        "path": str(SKILLS_PATH / f"{name}.md"),
                    }
                )

        # Search library
        for doc in self._library_index:
            if query_lower in doc["name"].lower():
                results.append(
                    {
                        "type": "document",
                        "name": doc["name"],
                        "path": doc["path"],
                    }
                )

        results.extend(self._search_corpora(query, limit))
        return results[:limit]

    def _search_corpora(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Semantic hits from the pre-embedded reference corpora in ~/.cohezion/corpora.

        The skill/library passes above are SUBSTRING matches, so they can only find text that
        literally contains the query. This pass embeds the query and ranks by cosine, which
        finds passages that are about the question without sharing its wording -- e.g.
        "distortion when projecting to lower dimensions" retrieves Johnson-Lindenstrauss
        material that contains none of those words.

        Additive: substring results are unchanged, so no existing caller regresses.
        Fail-soft: no corpora on disk, or no embedding endpoint, returns [] rather than
        raising -- a lookup helper must never take down its caller.
        """
        try:
            import httpx
            import numpy as np

            from cohezion.knowledge.corpus import KnowledgeCorpus

            resp = httpx.post(
                "http://localhost:13305/v1/embeddings",
                json={"model": "nomic-embed-text-v2-moe-GGUF", "input": query},
                timeout=30,
            )
            vector = np.array(resp.json()["data"][0]["embedding"], dtype=np.float32)
        except Exception as exc:
            logger.debug("corpus search unavailable: %s", exc)
            return []

        if self._corpus is None:
            self._corpus = KnowledgeCorpus()

        return [
            {
                "type": "corpus",
                "name": chunk.corpus,
                "snippet": chunk.text[:300],
                "score": round(chunk.score, 4),
                **chunk.meta,
            }
            for chunk in self._corpus.search(vector, limit=limit)
        ]

    def get_skill(self, skill_name: str) -> dict[str, Any]:
        """
        Get full content of a skill.

        Args:
            skill_name: Name of the skill (without .md)

        Returns:
            Skill content and metadata
        """
        from cohezion.mcp.servers.safe_input import sanitize_path

        skill_path = sanitize_path(f"{skill_name}.md", base_dir=SKILLS_PATH)
        if not skill_path.exists():
            # Try fuzzy match
            for name in self._skills_cache:
                if skill_name.lower() in name.lower():
                    skill_path = sanitize_path(f"{name}.md", base_dir=SKILLS_PATH)
                    break

        if not skill_path.exists():
            return {"error": f"Skill not found: {skill_name}"}

        content = skill_path.read_text()
        return {
            "name": skill_path.stem,
            "path": str(skill_path),
            "content": content,
        }

    def list_skills(self) -> list[dict[str, str]]:
        """List all available skills."""
        return [
            {"name": name, "summary": content[:80]} for name, content in self._skills_cache.items()
        ]

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Get entity from knowledge graph."""
        entities_path = KNOWLEDGE_GRAPH_PATH / "entities"
        if not entities_path.exists():
            return None

        entity_file = entities_path / f"{entity_id}.json"
        if entity_file.exists():
            return json.loads(entity_file.read_text())
        return None

    def store_entity(self, entity: dict[str, Any]) -> None:
        """Store entity in knowledge graph."""
        entities_path = KNOWLEDGE_GRAPH_PATH / "entities"
        entities_path.mkdir(parents=True, exist_ok=True)

        entity_file = entities_path / f"{entity['id']}.json"
        entity_file.write_text(json.dumps(entity, indent=2))

    def get_context_chunk(self, path: str, query: str | None = None) -> dict[str, Any]:
        """
        Get a specific chunk of context for a prompt.
        Inspired by the context7 pattern for high-fidelity doc retrieval.
        """
        from cohezion.mcp.servers.safe_input import sanitize_path

        project_root = Path(__file__).parent.parent.parent.parent
        try:
            file_path = sanitize_path(path, base_dir=project_root)
        except ValueError:
            return {"error": "Invalid or inaccessible path"}

        if not file_path.exists():
            return {"error": "Invalid or inaccessible path"}

        content = file_path.read_text()

        # Simple chunking: if too large, take first 2000 chars or search for query
        if len(content) > 2000:
            if query and query.lower() in content.lower():
                idx = content.lower().find(query.lower())
                start = max(0, idx - 500)
                end = min(len(content), idx + 1500)
                content = "[...]\n" + content[start:end] + "\n[...]"
            else:
                content = content[:2000] + "\n[... (truncated)]"

        return {
            "path": path,
            "content": content,
            "fidelity": "high" if "[...]" not in content else "partial",
        }


# Singleton
_server: KnowledgeMCP | None = None


def get_server() -> KnowledgeMCP:
    global _server
    if _server is None:
        _server = KnowledgeMCP()
    return _server


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "server": "knowledge"})


@routes.post("/tools/search_knowledge")
async def tool_search_knowledge(request: web.Request) -> web.Response:
    data = await request.json()
    query = data.get("query", "")
    limit = data.get("limit", 5)
    server = get_server()
    return web.json_response(server.search_knowledge(query, limit))


@routes.post("/tools/get_skill")
async def tool_get_skill(request: web.Request) -> web.Response:
    data = await request.json()
    skill_name = data.get("skill_name", "")
    server = get_server()
    return web.json_response(server.get_skill(skill_name))


@routes.post("/tools/list_skills")
async def tool_list_skills(request: web.Request) -> web.Response:
    server = get_server()
    return web.json_response(server.list_skills())


@routes.post("/tools/get_context_chunk")
async def tool_get_context_chunk(request: web.Request) -> web.Response:
    data = await request.json()
    path = data.get("path", "")
    query = data.get("query")
    server = get_server()
    return web.json_response(server.get_context_chunk(path, query))


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
    logger.info(f"Knowledge MCP Server running on port {MCP_PORT}")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
