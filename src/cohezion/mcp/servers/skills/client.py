"""Skills.sh API client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import aiohttp


logger = logging.getLogger(__name__)

SKILLS_SH_BASE_URL = "https://skills.sh"
SKILLS_SH_API_URL = "https://skills.sh/api"


@dataclass
class Skill:
    """Represents a skill from skills.sh."""

    id: str
    name: str
    owner: str
    repo: str
    description: str
    installs: int
    url: str
    category: str | None = None
    tags: list[str] | None = None

    @property
    def full_id(self) -> str:
        """Full skill ID in owner/repo format."""
        return f"{self.owner}/{self.repo}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "repo": self.repo,
            "full_id": self.full_id,
            "description": self.description,
            "installs": self.installs,
            "url": self.url,
            "category": self.category,
            "tags": self.tags,
        }


class SkillsShClient:
    """Client for skills.sh API."""

    def __init__(self, base_url: str = SKILLS_SH_BASE_URL):
        self.base_url = base_url
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Cohezion-BMAD-MCP/1.0",
                    "Accept": "application/json",
                }
            )
        return self._session

    async def search_skills(
        self, query: str = "", category: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[Skill]:
        """Search for skills on skills.sh.

        Args:
            query: Search query
            category: Filter by category
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching skills
        """
        session = await self._get_session()

        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }
        if category:
            params["category"] = category

        try:
            async with session.get(
                f"{self.base_url}/api/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    logger.warning(f"Skills.sh search failed: {response.status}")
                    return []

                data = await response.json()
                skills = []

                for item in data.get("skills", []):
                    skill = Skill(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        owner=item.get("owner", ""),
                        repo=item.get("repo", ""),
                        description=item.get("description", ""),
                        installs=item.get("installs", 0),
                        url=item.get("url", ""),
                        category=item.get("category"),
                        tags=item.get("tags", []),
                    )
                    skills.append(skill)

                return skills

        except Exception as e:
            logger.exception(f"Error searching skills: {e}")
            return []

    async def get_skill(self, owner: str, repo: str) -> Skill | None:
        """Get details of a specific skill.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Skill details or None
        """
        session = await self._get_session()

        try:
            async with session.get(
                f"{self.base_url}/api/skills/{owner}/{repo}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                return Skill(
                    id=data.get("id", ""),
                    name=data.get("name", ""),
                    owner=data.get("owner", ""),
                    repo=data.get("repo", ""),
                    description=data.get("description", ""),
                    installs=data.get("installs", 0),
                    url=data.get("url", ""),
                    category=data.get("category"),
                    tags=data.get("tags", []),
                )

        except Exception as e:
            logger.exception(f"Error getting skill: {e}")
            return None

    async def get_skill_content(self, owner: str, repo: str) -> str | None:
        """Get skill file content from GitHub.

        Skills are stored as SKILL.md files in GitHub repos.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Skill file content or None
        """
        # Try to fetch from raw.githubusercontent.com
        urls = [
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/skills/{repo}/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/master/skills/{repo}/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/master/SKILL.md",
        ]

        session = await self._get_session()

        for url in urls:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception as _e:
                logger.debug("Skipping: %s", _e)
                continue

        return None

    async def list_categories(self) -> list[str]:
        """List available skill categories."""
        session = await self._get_session()

        try:
            async with session.get(
                f"{self.base_url}/api/categories", timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("categories", [])
        except Exception as e:
            logger.exception(f"Error listing categories: {e}")

        return [
            "Development",
            "Design",
            "Testing",
            "Documentation",
            "DevOps",
            "AI/ML",
            "Product",
            "Communication",
        ]

    async def get_trending(self, limit: int = 20) -> list[Skill]:
        """Get trending skills.

        Args:
            limit: Maximum results

        Returns:
            List of trending skills
        """
        return await self.search_skills(query="", limit=limit)

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
