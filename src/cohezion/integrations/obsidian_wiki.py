"""Obsidian vault as Karpathy LLM-Wiki frontend."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class WikiPage:
    """Represents a wiki page."""

    path: Path
    title: str
    content: str
    category: str  # entity, concept, source, synthesis
    tags: list[str]
    backlinks: list[str]
    created_at: datetime
    updated_at: datetime
    source_refs: list[str]


class ObsidianWiki:
    """Obsidian vault implementing Karpathy's 3-layer LLM-Wiki pattern."""

    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self.raw_dir = self.vault_path / "raw"
        self.wiki_dir = self.vault_path / "wiki"
        self._init_structure()

    def _init_structure(self) -> None:
        """Initialize Karpathy wiki structure."""
        dirs = [
            self.raw_dir / "articles",
            self.raw_dir / "books",
            self.raw_dir / "papers",
            self.raw_dir / "daily",
            self.wiki_dir / "entities" / "people",
            self.wiki_dir / "entities" / "organizations",
            self.wiki_dir / "concepts",
            self.wiki_dir / "sources",
            self.wiki_dir / "synthesis",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    async def create_raw_entry(
        self,
        content: str,
        source_type: str,
        source_id: str | None = None,
    ) -> Path:
        """Create immutable raw source entry."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source_id = source_id or f"{timestamp}"
        filename = f"{source_id}.md"
        target_dir = self.raw_dir / source_type
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename

        # Add YAML frontmatter
        content_with_frontmatter = f"""---
source_type: {source_type}
added_at: {datetime.now().isoformat()}
content_hash: {hash(content) & 0xFFFFFFFF}
---

{content}
"""
        target_path.write_text(content_with_frontmatter)
        logger.info(f"Created raw entry: {target_path}")
        return target_path

    async def create_wiki_page(
        self,
        path: str | Path,
        content: str,
        category: str,
        source_refs: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> WikiPage:
        """Create or update a wiki page."""
        full_path = self.wiki_dir / path if isinstance(path, str) else path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        title = content.split("\n")[0].lstrip("# ").strip()
        now = datetime.now()

        # Extract wiki links [[...]]
        backlinks = re.findall(r"\[\[([^\]]+)\]\]", content)

        # YAML frontmatter
        frontmatter = f"""---
category: {category}
title: {title}
created_at: {now.isoformat()}
updated_at: {now.isoformat()}
tags: {tags or []}
source_refs: {source_refs or []}
backlinks: {backlinks}
---

"""
        full_content = frontmatter + content
        full_path.write_text(full_content)

        page = WikiPage(
            path=full_path,
            title=title,
            content=full_content,
            category=category,
            tags=tags or [],
            backlinks=backlinks,
            created_at=now,
            updated_at=now,
            source_refs=source_refs or [],
        )
        logger.info(f"Created wiki page: {full_path}")
        return page

    async def update_index(self, page: WikiPage) -> None:
        """Update index.md with new page entry."""
        index_path = self.vault_path / "index.md"

        entry = f"- [[{page.title}]] - {page.category} - {page.created_at.strftime('%Y-%m-%d')}"

        if index_path.exists():
            content = index_path.read_text()
            # Simple append for now; could be more sophisticated
            if entry not in content:
                content += f"\n{entry}"
        else:
            content = f"""# Wiki Index

{entry}
"""

        index_path.write_text(content)

    async def append_log(
        self,
        operation: str,
        details: str,
    ) -> None:
        """Append entry to log.md."""
        log_path = self.vault_path / "log.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"## [{timestamp}] {operation} | {details}\n\n"

        if log_path.exists():
            with open(log_path, "a") as f:
                f.write(entry)
        else:
            log_path.write_text(f"# Wiki Log\n\n{entry}")

    async def get_page(self, title: str) -> WikiPage | None:
        """Retrieve wiki page by title."""
        # Search all wiki directories
        for category_dir in self.wiki_dir.iterdir():
            if category_dir.is_dir():
                for md_file in category_dir.rglob("*.md"):
                    content = md_file.read_text()
                    if content.split("\n")[0].lstrip("# ").strip() == title:
                        return self._parse_page(md_file)
        return None

    async def query_pages(
        self,
        query: str,
        category: str | None = None,
        limit: int = 10,
    ) -> list[WikiPage]:
        """Simple keyword-based query (placeholder for vector search)."""
        results = []
        query_lower = query.lower()

        search_dirs = [self.wiki_dir / category] if category else [self.wiki_dir]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for md_file in search_dir.rglob("*.md"):
                content = md_file.read_text().lower()
                score = content.count(query_lower)
                if score > 0:
                    page = self._parse_page(md_file)
                    results.append((score, page))

        # Sort by relevance score
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def _parse_page(self, path: Path) -> WikiPage:
        """Parse markdown file into WikiPage."""
        content = path.read_text()

        # Extract frontmatter
        frontmatter = {}
        if content.startswith("---"):
            _, fm, body = content.split("---", 2)
            # Simple YAML parsing
            for line in fm.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip()] = v.strip()
        else:
            body = content

        title = body.lstrip("\n").split("\n")[0].lstrip("# ").strip()
        backlinks = re.findall(r"\[\[([^\]]+)\]\]", body)

        return WikiPage(
            path=path,
            title=title,
            content=content,
            category=frontmatter.get("category", "unknown"),
            tags=eval(frontmatter.get("tags", "[]")),
            backlinks=backlinks,
            created_at=datetime.fromisoformat(
                frontmatter.get("created_at", datetime.now().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                frontmatter.get("updated_at", datetime.now().isoformat())
            ),
            source_refs=eval(frontmatter.get("source_refs", "[]")),
        )

    async def get_index(self) -> str:
        """Read index.md for progressive disclosure."""
        index_path = self.vault_path / "index.md"
        if index_path.exists():
            return index_path.read_text()
        return ""

    async def list_orphans(self) -> list[WikiPage]:
        """Find pages with no inbound links."""
        all_pages = []
        all_links = set()

        for category_dir in self.wiki_dir.iterdir():
            if category_dir.is_dir():
                for md_file in category_dir.rglob("*.md"):
                    page = self._parse_page(md_file)
                    all_pages.append(page)
                    all_links.update(page.backlinks)

        orphans = [p for p in all_pages if p.title not in all_links]
        return orphans

    async def find_dead_links(self) -> list[str]:
        """Find broken [[wiki_links]]."""
        valid_titles = set()
        all_links = set()

        for category_dir in self.wiki_dir.iterdir():
            if category_dir.is_dir():
                for md_file in category_dir.rglob("*.md"):
                    page = self._parse_page(md_file)
                    valid_titles.add(page.title)
                    all_links.update(page.backlinks)

        dead = all_links - valid_titles
        return list(dead)
