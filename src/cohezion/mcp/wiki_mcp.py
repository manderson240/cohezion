"""MCP server implementing Karpathy LLM-Wiki operations.

Three core operations: ingest, query, lint
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cohezion.integrations.obsidian_wiki import ObsidianWiki


logger = logging.getLogger(__name__)


class WikiMCP:
    """
    MCP server for Karpathy LLM-Wiki operations.

    Implements the three core operations:
    - ingest: Add sources to wiki
    - query: Progressive disclosure search
    - lint: Health check

    Plus: sync, extract, suggest
    """

    def __init__(self, wiki: ObsidianWiki | None = None, vault_path: Path | None = None):
        if wiki:
            self.wiki = wiki
        elif vault_path:
            self.wiki = ObsidianWiki(vault_path)
        else:
            raise ValueError("Must provide wiki or vault_path")

        self._llm_client = None  # Placeholder for actual LLM integration

    # ============== CORE OPERATIONS ==============

    async def wiki_ingest(
        self,
        source: str,
        source_type: str = "article",
        source_id: str | None = None,
        auto_extract: bool = True,
    ) -> dict[str, Any]:
        """
        Ingest a source into the wiki (Karpathy: Ingest operation).

        Flow:
        1. Store in /raw/ (immutable)
        2. Create /wiki/sources/ summary (LLM-generated)
        3. Create/update /wiki/entities/ (extracted concepts)
        4. Update /wiki/concepts/ (link related ideas)
        5. Update index.md
        6. Append to log.md
        """
        result = {
            "raw_path": None,
            "wiki_pages_created": [],
            "entities_extracted": [],
            "linked_to": [],
        }

        # 1. Store in raw/
        raw_path = await self.wiki.create_raw_entry(source, source_type, source_id)
        result["raw_path"] = str(raw_path)

        if auto_extract:
            # 2. Create source summary (simulated LLM extraction)
            title = self._extract_title(source)
            summary = self._generate_summary(source)
            entities = self._extract_entities(source)

            # 3. Create wiki/source/ page
            source_page = await self.wiki.create_wiki_page(
                path=f"sources/{source_type}/{title.replace(' ', '_')}.md",
                content=f"# {title}\n\n## Summary\n{summary}\n\n## Source\nSee: [[raw/{source_type}/{raw_path.name}]]",
                category="source",
                source_refs=[str(raw_path)],
            )
            result["wiki_pages_created"].append(str(source_page.path))

            # 4. Create entity pages - parallel
            import asyncio

            entity_tasks = [self._get_or_create_entity(entity) for entity in entities]
            entity_pages = await asyncio.gather(*entity_tasks)
            for entity_page in entity_pages:
                result["entities_extracted"].append(entity_page.title)
                result["wiki_pages_created"].append(str(entity_page.path))

            # 5. Update index
            await self.wiki.update_index(source_page)

            # Link to existing concepts
            for entity in entities:
                concepts = self._find_related_concepts(entity)
                result["linked_to"].extend(concepts)

        # 6. Log
        await self.wiki.append_log(
            "ingest", f"Ingested {source_type}: {title if auto_extract else 'unnamed'}"
        )

        return result

    async def wiki_query(
        self,
        query: str,
        depth: str = "standard",
        file_back: bool = False,
    ) -> dict[str, Any]:
        """
        Query the wiki with progressive disclosure (Karpathy: Query operation).

        Args:
            depth: quick (index only), standard (index+pages), deep (+related)
            file_back: Save synthesis to /wiki/synthesis/

        Progressive disclosure token budget:
        - quick: ~200 tokens (index only)
        - standard: ~1-2K tokens (index + relevant pages)
        - deep: ~5-20K tokens (index + pages + related + synthesis)
        """
        result = {
            "query": query,
            "depth": depth,
            "sources_consulted": [],
            "answer": "",
            "synthesis_path": None,
        }

        # Step 1: Read index
        await self.wiki.get_index()
        result["sources_consulted"].append("index.md")

        # Step 2: Find relevant pages
        pages = await self.wiki.query_pages(query, limit=10)
        result["sources_consulted"].extend([str(p.path) for p in pages])

        # Step 3: Read relevant pages
        context = "\n\n".join([f"## {p.title}\n{p.content[:500]}" for p in pages])

        # Step 4: Synthesize answer (simulated LLM)
        answer = self._synthesize_answer(query, context)
        result["answer"] = answer

        # Step 5: If deep, include related pages
        if depth == "deep":
            related = []
            for page in pages:
                for link in page.backlinks[:3]:  # Limit related
                    related_page = await self.wiki.get_page(link)
                    if related_page:
                        related.append(related_page)
            result["sources_consulted"].extend([str(r.path) for r in related])

        # Step 6: File back if requested
        if file_back:
            synthesis = await self.wiki.create_wiki_page(
                path=f"synthesis/questions/{query.replace(' ', '_')[:50]}.md",
                content=f"# Q: {query}\n\n{answer}\n\n## Sources\n"
                + "\n".join(f"- [[{p}]]" for p in result["sources_consulted"]),
                category="synthesis",
            )
            result["synthesis_path"] = str(synthesis.path)

        return result

    async def wiki_lint(
        self,
        fix: bool = False,
        full_scan: bool = True,
    ) -> dict[str, Any]:
        """
        Health check the wiki (Karpathy: Lint operation).

        Checks:
        - orphans: Pages with no inbound links
        - dead_links: Broken [[wiki_links]]
        - contradictions: Flagged by LLM (simulated)
        - stale_claims: Superseded by newer sources
        - missing_concepts: Mentioned but no page
        - gaps: Suggested sources from web search (simulated)
        """
        issues = {
            "orphans": [],
            "dead_links": [],
            "contradictions": [],
            "stale_claims": [],
            "missing_concepts": [],
            "suggested_sources": [],
        }

        # Check orphans
        orphans = await self.wiki.list_orphans()
        issues["orphans"] = [o.title for o in orphans]

        # Check dead links
        dead = await self.wiki.find_dead_links()
        issues["dead_links"] = dead

        # Find missing concepts (entities mentioned but no page)
        mentioned = set()
        existing = set()
        for category_dir in self.wiki.wiki_dir.iterdir():
            if category_dir.is_dir():
                for md_file in category_dir.rglob("*.md"):
                    page = self.wiki._parse_page(md_file)
                    existing.add(page.title)
                    mentioned.update(page.backlinks)

        missing = mentioned - existing
        issues["missing_concepts"] = list(missing)

        # Auto-fix if requested
        fixed = []
        if fix:
            # Fix orphans by adding to index
            for orphan in orphans:
                await self.wiki.update_index(orphan)
                fixed.append(f"Linked orphan: {orphan.title}")

            # Note: Dead links and missing concepts need manual fix
            issues["fix_applied"] = fixed

        # Generate suggestions
        if missing:
            issues["suggested_sources"] = [f"Search for: {m}" for m in list(missing)[:5]]

        issues["total_issues"] = (
            len(issues["orphans"]) + len(issues["dead_links"]) + len(issues["missing_concepts"])
        )

        # Log the lint
        await self.wiki.append_log(
            "lint", f"Found {issues['total_issues']} issues, fixed {len(fixed)}"
        )

        return issues

    # ============== ADDITIONAL OPERATIONS ==============

    async def wiki_extract(
        self,
        source_path: str,
        extract_type: str = "entities",
    ) -> dict[str, Any]:
        """Extract structured info from a source."""
        content = Path(source_path).read_text()

        if extract_type == "entities":
            entities = self._extract_entities(content)
            return {"entities": entities}
        elif extract_type == "concepts":
            concepts = self._extract_concepts(content)
            return {"concepts": concepts}
        elif extract_type == "summary":
            summary = self._generate_summary(content)
            return {"summary": summary}

        return {}

    async def wiki_sync(
        self,
        target: str = "surrealdb",
    ) -> dict[str, Any]:
        """Sync wiki to external store."""
        from cohezion.integrations.wiki_mirix_bridge import WikiMirixBridge

        bridge = WikiMirixBridge(self.wiki)

        if target == "surrealdb":
            count = await bridge.sync_all_to_surreal()
            return {"synced_pages": count, "target": target}
        elif target == "mirix":
            mappings = await bridge.sync_wiki_to_mirix()
            return {"synced_pages": len(mappings), "target": target}

        return {"error": f"Unknown target: {target}"}

    # ============== HELPER METHODS ==============

    def _extract_title(self, content: str) -> str:
        """Extract or generate title from content."""
        lines = content.strip().split("\n")
        if lines[0].startswith("# "):
            return lines[0][2:].strip()
        return "Untitled"

    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate summary (placeholder for LLM)."""
        # Simple extraction - real implementation would use LLM
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        summary = " ".join(lines[:3])
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return summary

    def _extract_entities(self, content: str) -> list[str]:
        """Extract entities (placeholder for NER)."""
        # Simple pattern matching - real implementation would use LLM/NER
        import re

        # Match capitalized phrases (naive)
        entities = re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", content)
        # Also match [[wiki_links]]
        entities += re.findall(r"\[\[([^\]]+)\]\]", content)
        return list(set(entities))[:10]

    def _extract_concepts(self, content: str) -> list[str]:
        """Extract abstract concepts."""
        # Placeholder - real implementation would use LLM
        return ["concept_a", "concept_b", "concept_c"]

    def _find_related_concepts(self, entity: str) -> list[str]:
        """Find related concepts (placeholder for graph query)."""
        # Placeholder - real implementation would use SurrealDB graph
        return []

    async def _get_or_create_entity(self, entity: str) -> Any:
        """Get or create entity page."""
        # Check if exists
        existing = await self.wiki.get_page(entity)
        if existing:
            return existing

        # Create new entity page
        return await self.wiki.create_wiki_page(
            path=f"entities/people/{entity.replace(' ', '_')}.md",
            content=f"# {entity}\n\nEntity extracted from sources.\n\n## Related\n- See also: [[index]]",
            category="entity",
        )

    def _synthesize_answer(self, query: str, context: str) -> str:
        """Synthesize answer from context (placeholder for LLM)."""
        # Placeholder - real implementation would use actual LLM
        lines = context.split("\n")
        if len(lines) > 3:
            return f"Based on {len(lines)} sources:\n\n" + context[:500] + "..."
        return "No relevant information found."

    # ============== MCP TOOL INTERFACE ==============

    def get_tools(self) -> list[dict]:
        """Return MCP tool definitions."""
        return [
            {
                "name": "wiki_ingest",
                "description": "Ingest a source into the wiki",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Content to ingest"},
                        "source_type": {
                            "type": "string",
                            "enum": ["article", "book", "paper", "daily"],
                        },
                        "auto_extract": {"type": "boolean"},
                    },
                    "required": ["source"],
                },
            },
            {
                "name": "wiki_query",
                "description": "Query the wiki with progressive disclosure",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "depth": {"type": "string", "enum": ["quick", "standard", "deep"]},
                        "file_back": {"type": "boolean"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "wiki_lint",
                "description": "Health check the wiki",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fix": {"type": "boolean"},
                        "full_scan": {"type": "boolean"},
                    },
                },
            },
        ]
