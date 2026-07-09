"""Ouroboros Wiki Integration — Persistent Knowledge for Self-Improvement.

Integrates Karpathy's LLM-Wiki pattern into the Ouroboros recursive loop:
- Execution exhaust → Episodic memory
- Rewrite rules → Knowledge vault
- Failure patterns → Concept graph
- System improvements → Compounded synthesis
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.integrations.obsidian_wiki import ObsidianWiki, WikiPage
from cohezion.integrations.wiki_mirix_bridge import WikiMirixBridge
from cohezion.learning.ouroboros import ExecutionExhaust, OuroborosEngine


logger = logging.getLogger(__name__)


class OuroborosWikiBridge:
    """Bridge Ouroboros self-improvement to LLM-Wiki knowledge system.

    The Ouroboros loop generates valuable knowledge about system behavior:
    - What failed and why (exhaust)
    - How it was fixed (rewrites)
    - Patterns across failures (synthesis)

    This knowledge should persist and compound in the wiki, making the
    system smarter over time.

    Attributes:
        wiki: ObsidianWiki instance
        mirix_bridge: For MIRIX memory sync
        vault_path: Root of the wiki vault
    """

    def __init__(
        self,
        vault_path: Path | None = None,
        wiki: ObsidianWiki | None = None,
        mirix_bridge: WikiMirixBridge | None = None,
    ):
        if wiki:
            self.wiki = wiki
        elif vault_path:
            self.wiki = ObsidianWiki(vault_path)
        else:
            raise ValueError("Must provide wiki or vault_path")

        self.mirix_bridge = mirix_bridge or WikiMirixBridge(self.wiki)
        self.vault_path = self.wiki.vault_path

        # Initialize Ouroboros-specific wiki structure
        self._init_structure()

    def _init_structure(self) -> None:
        """Create Ouroboros wiki directories."""
        dirs = [
            self.vault_path / "wiki" / "ouroboros" / "exhaust",
            self.vault_path / "wiki" / "ouroboros" / "rewrites",
            self.vault_path / "wiki" / "ouroboros" / "patterns",
            self.vault_path / "wiki" / "ouroboros" / "improvements",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    async def log_exhaust(self, exhaust: ExecutionExhaust) -> WikiPage:
        """Log execution failure to wiki as episodic memory.

        Creates:
        - /wiki/ouroboros/exhaust/{task_id}.md with full failure context
        - Links to related previous failures (pattern detection)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_slug = exhaust.task_id.replace("/", "_")[:50]
        filename = f"{timestamp}_{task_slug}.md"

        # Find related failures
        related = await self._find_related_exhaust(exhaust)
        related_links = "\n".join(
            [f"- [[{r.metadata.get('title', 'unknown')}]]" for r in related[:5]]
        )

        content = f"""# Execution Exhaust: {exhaust.task_id}

## Failure Details
- **Timestamp**: {timestamp}
- **Coherence Drop**: {exhaust.coherence_drop:.3f}
- **Token Usage**: {exhaust.token_usage}

## Error
{exhaust.error_message or "No explicit error"}

## Diagnostics
```json
{json.dumps(exhaust.diagnostics, indent=2, default=str)}
```

## Related Failures
{related_links or "No related failures found."}

## Root Cause Analysis
*Auto-generated from diagnostics...*

## Fix Applied
*To be filled during rewrite cycle...*
"""

        page = await self.wiki.create_wiki_page(
            path=f"ouroboros/exhaust/{filename}",
            content=content,
            category="exhaust",
            tags=["ouroboros", "failure", exhaust.diagnostics.get("component", "unknown")],
        )

        await self.wiki.append_log("ouroboros", f"Logged exhaust for {exhaust.task_id}")

        # Sync to MIRIX episodic memory
        await self.mirix_bridge.sync_wiki_to_mirix(page.path)

        return page

    async def log_rewrite(
        self,
        exhaust: ExecutionExhaust,
        new_rule: str,
        confidence: float = 0.8,
    ) -> WikiPage:
        """Log system rewrite to wiki as knowledge.

        Creates:
        - /wiki/ouroboros/rewrites/{task_id}_rewrite.md
        - Links back to original exhaust
        - Updates improvement synthesis
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_slug = exhaust.task_id.replace("/", "_")[:50]
        filename = f"{timestamp}_{task_slug}_rewrite.md"

        content = f"""# Rewrite Rule: {exhaust.task_id}

## New Rule
{new_rule}

## Triggered By
[[{exhaust.task_id}]]

## Confidence
{confidence:.2f}

## Component
{exhaust.diagnostics.get("component", "unknown")}

## Validation
*To be filled after validation...*
"""

        page = await self.wiki.create_wiki_page(
            path=f"ouroboros/rewrites/{filename}",
            content=content,
            category="rewrite",
            source_refs=[
                str(
                    self.vault_path
                    / "wiki"
                    / "ouroboros"
                    / "exhaust"
                    / f"{timestamp}_{task_slug}.md"
                )
            ],
            tags=["ouroboros", "rewrite", "improvement"],
        )

        # Update patterns
        await self._update_pattern_matrix(exhaust, new_rule)

        return page

    async def query_lessons_learned(
        self,
        component: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query accumulated wisdom from Ouroboros cycles.

        Returns relevant rewrites and patterns for a component.
        """
        query = f"Ouroboros rewrite {component}" if component else "Ouroboros rewrite rule"

        # Query wiki
        pages = await self.wiki.query_pages(query, limit=limit)

        results = []
        for page in pages:
            if "rewrite" in page.tags or "pattern" in page.tags:
                results.append(
                    {
                        "title": page.title,
                        "content": page.content[:500],
                        "tags": page.tags,
                        "path": str(page.path),
                    }
                )

        return results

    def log_session(
        self,
        skill_name: str,
        task_description: str,
        metrics: dict[str, Any] | None = None,
        execution_id: str | None = None,
    ) -> str | None:
        """Log a successful CompoundExecutor session to the wiki.

        WS1C (2026-06-04) adds this high-level helper so the executor
        can persist a session note without constructing an
        ExecutionExhaust. Writes to wiki/ouroboros/improvements/<ts>_<skill>.md
        with the task description + key metrics. Best-effort.

        Returns:
            Path to the written file, or None on failure.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_skill = skill_name.replace(" ", "-").replace("/", "_")[:50]
        filename = f"{timestamp}_{safe_skill}.md"
        path = self.vault_path / "wiki" / "ouroboros" / "improvements" / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        # Build markdown content
        lines = [
            "---",
            f"skill: {skill_name}",
            f"execution_id: {execution_id or 'unknown'}",
            f"date: {datetime.now().isoformat()}",
            "tags: [ouroboros, session, auto-promoted]",
            "---",
            "",
            f"# Session: {skill_name}",
            "",
            "## Task",
            "",
            task_description or "(no description)",
            "",
        ]
        if metrics:
            lines.extend(
                [
                    "## Metrics",
                    "",
                    "```json",
                    json.dumps(metrics, indent=2, default=str),
                    "```",
                    "",
                ]
            )
        lines.extend(
            [
                "## Notes",
                "",
                "Auto-logged by OuroborosWikiBridge.log_session() (WS1C, 2026-06-04).",
                "Linked from compound execution context; see vault for the full pattern.",
                "",
            ]
        )
        try:
            path.write_text("\n".join(lines))
            logger.info("wrote session note to wiki: %s", path)
            return str(path)
        except Exception as exc:
            logger.debug("log_session failed: %s", exc)
            return None

    async def _find_related_exhaust(
        self,
        exhaust: ExecutionExhaust,
    ) -> list[WikiPage]:
        """Find similar previous failures (simple keyword match)."""
        query = exhaust.error_message or ""
        query += " " + exhaust.diagnostics.get("component", "")
        return await self.wiki.query_pages(query, limit=5)

    async def _update_pattern_matrix(
        self,
        exhaust: ExecutionExhaust,
        new_rule: str,
    ) -> None:
        """Update pattern synthesis when similar failures cluster."""
        component = exhaust.diagnostics.get("component", "unknown")
        pattern_path = self.vault_path / "wiki" / "ouroboros" / "patterns" / f"{component}.md"

        # Check if pattern exists
        if pattern_path.exists():
            page = self.wiki._parse_page(pattern_path)
            # Update count
            content = page.content + f"\n- {datetime.now().isoformat()}: {exhaust.task_id}"
        else:
            content = f"""# Pattern: {component}

## Description
Recurring failures in {component} component.

## Incidents
- {datetime.now().isoformat()}: {exhaust.task_id}

## Mitigations
- {new_rule}
"""

        await self.wiki.create_wiki_page(
            path=f"ouroboros/patterns/{component}.md",
            content=content,
            category="pattern",
            tags=["ouroboros", "pattern", component],
        )


class OuroborosWikiEngine(OuroborosEngine):
    """Extended Ouroboros engine with wiki-backed learning.

    Integrates into the recursive self-improvement loop:
    - capture knowledge from exhaust
    - query past lessons before rewriting
    - compound improvements over time
    """

    def __init__(
        self,
        target_coherence: float = 0.5,
        vault_path: Path | None = None,
    ):
        super().__init__(target_coherence)
        self.wiki_bridge = OuroborosWikiBridge(vault_path=vault_path)

    async def consume_exhaust(self, exhaust: ExecutionExhaust) -> bool:
        """Override to add wiki logging."""
        # Log the exhaust first
        await self.wiki_bridge.log_exhaust(exhaust)

        # Check if we have lessons learned for this component
        component = exhaust.diagnostics.get("component")
        if component:
            lessons = await self.wiki_bridge.query_lessons_learned(component)
            if lessons:
                logger.info(f"Found {len(lessons)} prior lessons for {component}")
                # Could influence rewrite strategy here

        # Continue with normal Ouroboros logic
        return await super().consume_exhaust(exhaust)

    async def _trigger_rewrite_cycle(self, exhaust: ExecutionExhaust) -> bool:
        """Override to log rewrites to wiki."""
        result = await super()._trigger_rewrite_cycle(exhaust)

        if result and self.rewrite_history:
            # Log the latest rewrite
            latest = self.rewrite_history[-1]
            await self.wiki_bridge.log_rewrite(
                exhaust,
                latest["new_rule"],
                confidence=1.0 - exhaust.coherence_drop,
            )

        return result
