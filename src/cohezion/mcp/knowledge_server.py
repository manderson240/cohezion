"""
Knowledge MCP Server - RAG over library and skills.

Provides tools:
- search_knowledge: Semantic search over documents
- get_skill: Retrieve a specific skill
- list_skills: List available skills
"""

import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Paths
LIBRARY_PATH = Path(__file__).parent.parent / "library"
SKILLS_PATH = Path(__file__).parent.parent / "skills"
KNOWLEDGE_GRAPH_PATH = Path(__file__).parent.parent / "knowledge_graph"


class KnowledgeMCP:
    """
    MCP server for knowledge retrieval.

    Reduces token usage by serving only relevant content.
    """

    def __init__(self):
        self._skills_cache: dict[str, str] = {}
        self._library_index: list[dict[str, Any]] = []
        self._load_index()

    def _load_index(self) -> None:
        """Build index of available knowledge."""
        # Index skills
        if SKILLS_PATH.exists():
            for skill_file in SKILLS_PATH.glob("*.md"):
                name = skill_file.stem
                # Read first 200 chars for summary
                content = skill_file.read_text()[:200]
                self._skills_cache[name] = content

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

        return results[:limit]

    def get_skill(self, skill_name: str) -> dict[str, Any]:
        """
        Get full content of a skill.

        Args:
            skill_name: Name of the skill (without .md)

        Returns:
            Skill content and metadata
        """
        skill_path = SKILLS_PATH / f"{skill_name}.md"
        if not skill_path.exists():
            # Try fuzzy match
            for name in self._skills_cache:
                if skill_name.lower() in name.lower():
                    skill_path = SKILLS_PATH / f"{name}.md"
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
        return [{"name": name, "summary": content[:80]} for name, content in self._skills_cache.items()]

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

        # Trigger hooks

    def get_context_chunk(self, path: str, query: str | None = None) -> dict[str, Any]:
        """
        Get a specific chunk of context for a prompt.
        Inspired by the context7 pattern for high-fidelity doc retrieval.
        """
        file_path = Path(path)
        if not file_path.exists() or not str(file_path).startswith(str(Path(__file__).parent.parent)):
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


# MCP tool definitions
TOOLS = [
    {
        "name": "search_knowledge",
        "description": "Search for relevant knowledge in skills and library",
        "parameters": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 5},
        },
    },
    {
        "name": "get_skill",
        "description": "Get full content of a specific skill",
        "parameters": {
            "skill_name": {"type": "string", "required": True},
        },
    },
    {
        "name": "get_context_chunk",
        "description": "Retrieve a specific, high-fidelity context chunk for a code file or doc",
        "parameters": {
            "path": {"type": "string", "required": True},
            "query": {"type": "string", "required": False},
        },
    },
]


# Singleton
_server: KnowledgeMCP | None = None


def get_server() -> KnowledgeMCP:
    global _server
    if _server is None:
        _server = KnowledgeMCP()
    return _server
