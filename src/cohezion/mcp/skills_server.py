"""
Skills MCP Server - Direct skill invocation.

Provides tools:
- invoke_skill: Load and parse a skill
- register_skill: Add a new skill
- search_skills: Fuzzy search skills
"""

import logging
from pathlib import Path
from typing import Any

from cohezion.registry.skill_registry import (
    load_registry,
)
from cohezion.registry.skill_registry import (
    register_skill as _register_skill,
)
from cohezion.registry.skill_registry import (
    search_skills as _search_skills,
)


logger = logging.getLogger(__name__)

SKILLS_PATH = Path(__file__).parent.parent / "skills"


class SkillsMCP:
    """
    MCP server for skill management.

    Wraps the existing skill_registry with MCP interface.
    """

    def __init__(self):
        self._registry = load_registry()

    def invoke_skill(self, skill_name: str) -> dict[str, Any]:
        """
        Load and return a skill's content.

        Args:
            skill_name: Name of the skill

        Returns:
            Skill content and metadata
        """
        from cohezion.mcp.servers.safe_input import sanitize_path

        # Sanitize name to prevent directory traversal via filename
        # We allow .md extension or not
        filename = f"{skill_name}.md" if not skill_name.endswith(".md") else skill_name

        try:
            skill_path = sanitize_path(filename, base_dir=SKILLS_PATH)
        except ValueError:
            # Try with _PRIME suffix
            try:
                skill_path = sanitize_path(f"{skill_name}_PRIME.md", base_dir=SKILLS_PATH)
            except ValueError:
                # Try fuzzy match
                results = self.search_skills(skill_name, limit=1)
                if results and results[0].get("path"):
                    try:
                        skill_path = sanitize_path(results[0]["path"], base_dir=SKILLS_PATH)
                    except ValueError:
                        return {"error": f"Invalid skill path in registry: {results[0]['path']}"}
                else:
                    return {"error": f"Skill not found: {skill_name}"}

        if not skill_path.exists():
            # If sanitize_path succeeded but file doesn't exist (e.g. no _PRIME)
            return {"error": f"Skill not found: {skill_name}"}

        content = skill_path.read_text()

        # Parse sections
        sections: dict[str, str] = {}
        current_section = "header"
        current_content: list[str] = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                current_section = line[3:].strip().lower()
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content)

        return {
            "name": skill_path.stem,
            "path": str(skill_path),
            "sections": sections,
            "full_content": content,
        }

    def register_skill(
        self,
        name: str,
        description: str,
        keywords: list[str],
        path: str,
    ) -> dict[str, Any]:
        """
        Register a new skill.

        Args:
            name: Skill name
            description: Short description
            keywords: Search keywords
            path: Relative path to skill file (relative to project root)

        Returns:
            Registration result
        """
        from cohezion.mcp.servers.safe_input import sanitize_path

        try:
            # Path Traversal Protection: Validate registration path
            # Skills must be within the skills directory
            try:
                sanitize_path(path, base_dir=SKILLS_PATH)
            except ValueError as e:
                logger.warning(f"RAH Security: {e}")
                return {"success": False, "error": str(e)}

            _register_skill(name, description, keywords, path)
            self._registry = load_registry()  # Reload

            # Trigger hooks
            from cohezion.registry.hooks import get_hook_manager

            get_hook_manager().dispatch_skill_registered(
                name, {"description": description, "keywords": keywords, "path": path}
            )

            return {"success": True, "name": name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_skills(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search skills by query.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching skills
        """
        results = _search_skills(query)
        return [
            {
                "name": r.get("name"),
                "description": r.get("description"),
                "path": r.get("path"),
                "score": r.get("score"),
            }
            for r in results[:limit]
        ]

    def list_all(self) -> list[dict[str, str]]:
        """List all registered skills."""
        return [
            {"name": s["name"], "description": s.get("description", "")}
            for s in self._registry.get("skills", [])
        ]


TOOLS = [
    {
        "name": "invoke_skill",
        "description": "Load and return a skill's content",
        "parameters": {"skill_name": {"type": "string", "required": True}},
    },
    {
        "name": "register_skill",
        "description": "Register a new skill",
        "parameters": {
            "name": {"type": "string", "required": True},
            "description": {"type": "string", "required": True},
            "keywords": {"type": "array", "required": True},
            "path": {"type": "string", "required": True},
        },
    },
    {
        "name": "search_skills",
        "description": "Fuzzy search skills",
        "parameters": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 5},
        },
    },
]

_server: SkillsMCP | None = None


def get_server() -> SkillsMCP:
    global _server
    if _server is None:
        _server = SkillsMCP()
    return _server
