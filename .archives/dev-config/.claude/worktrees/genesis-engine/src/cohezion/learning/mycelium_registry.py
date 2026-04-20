"""Mycelium Registry — Autonomous Skill Synthesis (Story 4.6, FR11).

Performs daily audits of the MISSION_JOURNAL and KEY_LEARNINGS,
autonomously synthesizing and registering new reusable skills.
Extracted patterns are broadcast as KnowledgeSpores across EVOs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class JournalEntry:
    """An entry from the MISSION_JOURNAL or KEY_LEARNINGS."""

    entry_id: str
    content: str
    domain: str  # "decision" | "experiment" | "pattern"
    timestamp: float = field(default_factory=time.time)


@dataclass
class SynthesizedSkill:
    """A skill synthesized from journal entries."""

    skill_name: str
    skill_content: str
    source_entries: list[str]  # Entry IDs that contributed
    content_hash: str = ""
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.skill_content.encode()).hexdigest()


@dataclass
class AuditReport:
    """Result of a Mycelium Audit cycle."""

    entries_scanned: int
    skills_synthesized: int
    skills_updated: int
    timestamp: float = field(default_factory=time.time)


class MyceliumRegistry:
    """Synthesizes skills from journal entries autonomously."""

    def __init__(self, min_entries_for_pattern: int = 2) -> None:
        self._min_entries = min_entries_for_pattern
        self._entries: list[JournalEntry] = []
        self._skills: dict[str, SynthesizedSkill] = {}
        self._audit_history: list[AuditReport] = []

    @property
    def skills(self) -> dict[str, SynthesizedSkill]:
        return dict(self._skills)

    def ingest_entry(self, entry: JournalEntry) -> None:
        """Add a journal entry for analysis."""
        self._entries.append(entry)

    def run_audit(self) -> AuditReport:
        """Run a Mycelium Audit — synthesize skills from journal entries."""
        synthesized = 0
        updated = 0

        # Group entries by domain
        by_domain: dict[str, list[JournalEntry]] = {}
        for entry in self._entries:
            by_domain.setdefault(entry.domain, []).append(entry)

        # Synthesize skills from domains with enough entries
        for domain, entries in by_domain.items():
            if len(entries) >= self._min_entries:
                skill_name = f"{domain.upper()}_SYNTHESIZED"
                content = self._synthesize_content(domain, entries)
                source_ids = [e.entry_id for e in entries]

                if skill_name in self._skills:
                    # Update existing
                    old = self._skills[skill_name]
                    if old.content_hash != hashlib.sha256(content.encode()).hexdigest():
                        self._skills[skill_name] = SynthesizedSkill(
                            skill_name=skill_name,
                            skill_content=content,
                            source_entries=source_ids,
                        )
                        updated += 1
                else:
                    self._skills[skill_name] = SynthesizedSkill(
                        skill_name=skill_name,
                        skill_content=content,
                        source_entries=source_ids,
                    )
                    synthesized += 1

        report = AuditReport(
            entries_scanned=len(self._entries),
            skills_synthesized=synthesized,
            skills_updated=updated,
        )
        self._audit_history.append(report)

        logger.info(
            "Mycelium Audit: scanned %d entries, synthesized %d, updated %d",
            len(self._entries),
            synthesized,
            updated,
        )
        return report

    def _synthesize_content(self, domain: str, entries: list[JournalEntry]) -> str:
        """Synthesize skill content from journal entries."""
        lines = [f"# {domain.title()} Skill (Auto-Synthesized)", ""]
        for entry in entries:
            lines.append(f"- {entry.content}")
        return "\n".join(lines)

    def get_audit_history(self) -> list[AuditReport]:
        """Get all audit reports."""
        return list(self._audit_history)
