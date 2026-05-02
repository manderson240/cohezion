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
        skill_path = SKILLS_PATH / f"{skill_name}.md"

        # Try exact match first
        if not skill_path.exists():
            # Try with _PRIME suffix
            skill_path = SKILLS_PATH / f"{skill_name}_PRIME.md"

        if not skill_path.exists():
            # Try fuzzy match
            results = self.search_skills(skill_name, limit=1)
            if results:
                skill_path = Path(results[0].get("path", ""))

        if not skill_path.exists():
            return {"error": f"Skill not found: {skill_name}"}

        content = skill_path.read_text()

        # Parse sections
        sections = {}
        current_section = "header"
        current_content = []

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
            path: Relative path to skill file

        Returns:
            Registration result
        """
        try:
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
        return [{"name": s["name"], "description": s.get("description", "")} for s in self._registry.get("skills", [])]


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
