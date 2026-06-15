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

# Module-level singleton shared by the executor (writer) and mycelium API (reader).
_singleton: MyceliumRegistry | None = None


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
class HyperedgePattern:
    """N-ary relationship captured from an executor trace.

    Unlike pairwise graph edges, a hyperedge models many-to-many participation:
    e.g. [Act, Checker, Refiner] all co-produced one ExecutionResult.

    Inspired by Hyper-Extract (yifanfeng97/Hyper-Extract) applied to execution
    traces instead of text corpora.
    """

    nodes: list[str]  # executor step names that participated
    relation: str  # "co_produced" | "co_verified" | "co_refined"
    source_domains: list[str]  # task domains this pattern appeared in
    weight: float = 1.0  # occurrence count (incremented on dedup)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AuditReport:
    """Result of a Mycelium Audit cycle."""

    entries_scanned: int
    skills_synthesized: int
    skills_updated: int
    hyperedges_captured: int = 0
    timestamp: float = field(default_factory=time.time)


class MyceliumRegistry:
    """Synthesizes skills from journal entries autonomously."""

    def __init__(self, min_entries_for_pattern: int = 2) -> None:
        self._min_entries = min_entries_for_pattern
        self._entries: list[JournalEntry] = []
        self._skills: dict[str, SynthesizedSkill] = {}
        self._audit_history: list[AuditReport] = []
        self._hyperedges: list[HyperedgePattern] = []
        # dedup index: sorted(nodes)+relation → list index
        self._hyperedge_index: dict[str, int] = {}

    @classmethod
    def get_instance(cls) -> MyceliumRegistry:
        """Return the module-level singleton, creating it on first call.

        Closes the recursion loop: the CompoundExecutor (writer, Step 10.6) and
        the mycelium API (reader, ``/skills``) must share ONE registry, or skills
        synthesized on the write side are invisible on the read side. Mirrors
        ``SemanticCache.get_instance()`` (harness CA2).
        """
        global _singleton
        if _singleton is None:
            _singleton = cls()
        return _singleton

    @classmethod
    def reset_instance(cls) -> None:
        """Clear the module-level singleton (test isolation). Mirrors CA2."""
        global _singleton
        _singleton = None

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
                if domain == "evo_deliberation":
                    content = self._synthesize_evo_deliberation_skill(entries)
                else:
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
            hyperedges_captured=len(self._hyperedges),
        )
        self._audit_history.append(report)

        logger.info(
            "Mycelium Audit: scanned %d entries, synthesized %d, updated %d",
            len(self._entries),
            synthesized,
            updated,
        )
        return report

    @property
    def hyperedges(self) -> list[HyperedgePattern]:
        """Read-only snapshot of captured hyperedge patterns."""
        return list(self._hyperedges)

    def ingest_execution_trace(
        self,
        step_names: list[str],
        domains: list[str] | None = None,
        relation: str = "co_produced",
    ) -> HyperedgePattern:
        """Capture an n-ary relationship from one executor trace.

        Deduplicates by (sorted step_names, relation): repeated traces increment
        weight rather than adding duplicate hyperedges.

        Args:
            step_names: Executor step names that participated (e.g. ["Act", "Checker"]).
            domains: Task domains this trace came from.
            relation: Relationship type ("co_produced", "co_verified", "co_refined").

        Returns:
            The HyperedgePattern (new or updated existing).
        """
        key = f"{','.join(sorted(step_names))}::{relation}"
        if key in self._hyperedge_index:
            existing = self._hyperedges[self._hyperedge_index[key]]
            existing.weight += 1.0
            if domains:
                for d in domains:
                    if d not in existing.source_domains:
                        existing.source_domains.append(d)
            return existing

        pattern = HyperedgePattern(
            nodes=list(step_names),
            relation=relation,
            source_domains=list(domains or []),
        )
        self._hyperedge_index[key] = len(self._hyperedges)
        self._hyperedges.append(pattern)
        logger.debug("MyceliumRegistry: new hyperedge %s (relation=%s)", step_names, relation)
        return pattern

    def _synthesize_content(self, domain: str, entries: list[JournalEntry]) -> str:
        """Synthesize skill content from journal entries."""
        lines = [f"# {domain.title()} Skill (Auto-Synthesized)", ""]
        for entry in entries:
            lines.append(f"- {entry.content}")
        return "\n".join(lines)

    def get_audit_history(self) -> list[AuditReport]:
        """Get all audit reports."""
        return list(self._audit_history)

    def ingest_evo_journeys(self, event_metadata_list: list[dict]) -> int:
        """Ingest EVO journey data from FlumeJourneyEvent.metadata records (E3/E6).

        Each entry is the full metadata dict from a FlumeJourneyEvent, containing
        `evo_biography`, `voice_scores`, `consensus_score`, and `approved`.
        Per-voice scores are encoded for the E6 score-adjustment feedback loop.

        Returns the number of entries ingested.
        """
        ingested = 0
        for meta in event_metadata_list:
            bio = meta.get("evo_biography") or {}
            voice_scores = meta.get("voice_scores") or {}
            consensus = meta.get("consensus_score", 0.0)
            approved = meta.get("approved", False)

            agent_id = bio.get("agent_id", "unknown")
            evo_coherence = bio.get("evo_coherence_metric", 0.0)
            lifetime = bio.get("lifetime_ticks", 0)
            marks = bio.get("witness_marks", [])
            mark_types = [m.get("mark_type", "?") for m in marks]

            # Encode per-voice scores for E6 learning
            voice_str = " ".join(f"{k}={v:.3f}" for k, v in sorted(voice_scores.items()))
            content = (
                f"EVO {agent_id}: evo_coherence={evo_coherence:.3f} "
                f"consensus={consensus:.3f} approved={int(approved)} "
                f"voice_scores=[{voice_str}] "
                f"lifetime={lifetime} marks=[{','.join(mark_types)}]"
            )
            entry = JournalEntry(
                entry_id=f"evo_{agent_id}_{int(time.time() * 1000)}",
                content=content,
                domain="evo_deliberation",
            )
            self.ingest_entry(entry)
            ingested += 1

        logger.debug("MyceliumRegistry: ingested %d EVO journey entries", ingested)
        return ingested

    def _synthesize_evo_deliberation_skill(self, entries: list[JournalEntry]) -> str:
        """Synthesize a skill from EVO deliberation journal entries (E3/E6).

        Extracts: mean evo_coherence, approval rate, per-voice mean scores
        (for E6 score-adjustment feedback), common mark types.
        """
        import re

        coherences: list[float] = []
        mark_type_counts: dict[str, int] = {}
        voice_score_sums: dict[str, float] = {}
        voice_score_counts: dict[str, int] = {}

        for entry in entries:
            m = re.search(r"evo_coherence=(\d+\.\d+)", entry.content)
            if m:
                coherences.append(float(m.group(1)))
            marks_m = re.search(r"marks=\[([^\]]*)\]", entry.content)
            if marks_m:
                for mt in marks_m.group(1).split(","):
                    mt = mt.strip()
                    if mt:
                        mark_type_counts[mt] = mark_type_counts.get(mt, 0) + 1
            # Parse per-voice scores: voice_scores=[architect=0.800 engineer=0.750 ...]
            vs_m = re.search(r"voice_scores=\[([^\]]*)\]", entry.content)
            if vs_m:
                for pair in vs_m.group(1).split():
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        try:
                            voice_score_sums[k] = voice_score_sums.get(k, 0.0) + float(v)
                            voice_score_counts[k] = voice_score_counts.get(k, 0) + 1
                        except ValueError:
                            pass

        mean_coh = sum(coherences) / len(coherences) if coherences else 0.0
        approval_rate = mark_type_counts.get("directive", 0) / max(len(entries), 1)
        voice_means = {k: voice_score_sums[k] / voice_score_counts[k] for k in voice_score_sums}

        top_marks = sorted(mark_type_counts.items(), key=lambda x: -x[1])
        voice_lines = [f"- {k}: mean_score={v:.3f}" for k, v in sorted(voice_means.items())]
        lines = [
            "# EVO_DELIBERATION Skill (Auto-Synthesized from Nexus Journeys)",
            "",
            f"## Pattern Statistics ({len(entries)} deliberations)",
            f"- Mean EVO coherence: {mean_coh:.3f}",
            f"- Approval rate: {approval_rate:.1%}",
            f"- Common outcomes: {', '.join(f'{k}({v})' for k, v in top_marks[:3])}",
            "",
            "## Per-Voice Mean Scores (E6 feedback)",
            *voice_lines,
            "",
            "## Extracted Patterns",
        ]
        for entry in entries[:5]:
            lines.append(f"- {entry.content}")
        return "\n".join(lines)
