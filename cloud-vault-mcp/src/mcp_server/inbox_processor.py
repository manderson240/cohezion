"""AI-powered inbox processor for vault notes."""

import asyncio
import contextlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from .vault_ops import VaultOps


logger = logging.getLogger(__name__)

CLASSIFICATION_SYSTEM_PROMPT = """You are a note classifier for an Obsidian knowledge vault. Given a raw note dropped into the inbox, classify it and return a JSON object with these fields:

{
  "note_type": "research" | "decision" | "experiment" | "pattern" | "concept" | "project" | "daily",
  "title": "A clear, descriptive title for this note",
  "target_dir": "papers/" | "decisions/" | "experiments/" | "patterns/" | "concepts/" | "projects/" | "daily/",
  "task": "expand_research" | "structure_decision" | "structure_experiment" | "extract_pattern" | "define_concept" | "structure_project" | "structure_daily",
  "summary": "Brief 1-sentence summary of the note's content"
}

Classification rules:
- Research requests, topic exploration, paper notes → research, papers/, expand_research
- Decision language, ADR, "we decided", tradeoffs → decision, decisions/, structure_decision
- Hypothesis, experiment, "what if", testing → experiment, experiments/, structure_experiment
- Reusable solution, code pattern, "pattern:", best practice → pattern, patterns/, extract_pattern
- Project overview, goals, roadmap, milestones → project, projects/, structure_project
- Daily log, standup, journal entry, today → daily, daily/, structure_daily
- Definition, concept, "what is", terminology → concept, concepts/, define_concept

Return ONLY the JSON object, no other text."""

TASK_PROMPTS = {
    "expand_research": "Expand this research note into a well-structured document with sections: Overview, Key Concepts, Analysis, Open Questions, and References. Preserve all original content and add structure.",
    "structure_decision": "Structure this as an Architecture Decision Record with sections: Context, Decision, Rationale, Alternatives Considered, Consequences, and Related. Extract the key decision and reasoning.",
    "structure_experiment": "Structure this as an experiment log with sections: Hypothesis, Method, Expected Results, Actual Results, Learnings, and Follow-up. Identify the core hypothesis being tested.",
    "extract_pattern": "Extract the reusable pattern from this note. Structure with: Problem (what recurring problem does this solve), Solution (the pattern), Example (code or process), When to Use, When NOT to Use, and Related Decisions.",
    "define_concept": "Define this concept clearly with sections: Definition, Context, Examples, Related Concepts, and References. Make it a useful reference document.",
    "structure_project": "Structure this as a project document with sections: Overview, Goals, Current Status, Key Decisions, Architecture, and Next Steps.",
    "structure_daily": "Structure this as a daily log with sections: Summary, Accomplished, In Progress, Blockers, and Tomorrow's Plan. Keep the original content.",
}


@dataclass
class Classification:
    """Result of classifying an inbox note."""

    note_type: str
    title: str
    target_dir: str
    task: str
    summary: str


@dataclass
class ProcessingResult:
    """Result of processing an inbox note."""

    source: str
    target: str
    classification: Classification
    success: bool = True
    error: str | None = None


class InboxProcessor:
    """Process inbox notes: classify -> expand -> file."""

    def __init__(
        self,
        vault: VaultOps,
        compound,
        anthropic_client,
        model: str = "claude-sonnet-4-5-20250929",
    ):
        self._vault = vault
        self._compound = compound
        self._client = anthropic_client
        self._model = model

    async def process_note(self, path: str) -> ProcessingResult:
        """Full pipeline: read -> classify -> execute -> file -> cleanup."""
        empty_classification = Classification("", "", "", "", "")

        try:
            content = self._vault.read(path)
        except FileNotFoundError:
            return ProcessingResult(
                source=path,
                target="",
                classification=empty_classification,
                success=False,
                error=f"File not found: {path}",
            )

        if not content.strip():
            return ProcessingResult(
                source=path,
                target="",
                classification=empty_classification,
                success=False,
                error="Empty note",
            )

        try:
            classification = await self._classify(content)
        except Exception as e:
            logger.error("Classification failed for %s: %s", path, e)
            return ProcessingResult(
                source=path,
                target="",
                classification=empty_classification,
                success=False,
                error=f"Classification failed: {e}",
            )

        try:
            processed = await self._execute_task(content, classification)
        except Exception as e:
            logger.error("Task execution failed for %s: %s", path, e)
            return ProcessingResult(
                source=path,
                target="",
                classification=classification,
                success=False,
                error=f"Task execution failed: {e}",
            )

        try:
            target_path = self._write_processed(processed, classification)
        except Exception as e:
            logger.error("Write failed for %s: %s", path, e)
            return ProcessingResult(
                source=path,
                target="",
                classification=classification,
                success=False,
                error=f"Write failed: {e}",
            )

        # Remove from inbox only on success
        with contextlib.suppress(FileNotFoundError):
            self._vault.delete(path)

        logger.info(
            "Processed %s -> %s (%s)", path, target_path, classification.note_type
        )
        return ProcessingResult(
            source=path, target=target_path, classification=classification
        )

    async def _classify(self, content: str) -> Classification:
        """Classify note content via Claude API."""
        response = await asyncio.to_thread(
            self._client.messages.create,
            model=self._model,
            max_tokens=500,
            system=CLASSIFICATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Classify this note:\n\n{content}"}],
        )

        text = response.content[0].text.strip()

        # Parse JSON (handle potential markdown code blocks)
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        data = json.loads(text)
        return Classification(
            note_type=data["note_type"],
            title=data["title"],
            target_dir=data["target_dir"],
            task=data["task"],
            summary=data["summary"],
        )

    async def _execute_task(self, content: str, classification: Classification) -> str:
        """Execute the identified task to expand/structure the note."""
        return await self._structure_via_claude(content, classification.task)

    async def _structure_via_claude(self, content: str, task: str) -> str:
        """Use Claude to structure/expand content."""
        prompt = TASK_PROMPTS.get(
            task, "Structure this note clearly with appropriate headings and sections."
        )

        response = await asyncio.to_thread(
            self._client.messages.create,
            model=self._model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": f"{prompt}\n\nOriginal note:\n\n{content}"},
            ],
        )
        return response.content[0].text

    def _write_processed(
        self, processed_content: str, classification: Classification
    ) -> str:
        """Write processed note to target directory."""
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        slug = self._slugify(classification.title)

        target_dir = classification.target_dir.rstrip("/")
        path = f"{target_dir}/{date}-{slug}.md"

        content = self._add_frontmatter(processed_content, classification, date)
        self._vault.write(path, content)
        return path

    def _add_frontmatter(
        self, content: str, classification: Classification, date: str
    ) -> str:
        """Add YAML frontmatter to processed content."""
        # Don't double-add frontmatter
        if content.startswith("---"):
            return content

        frontmatter = (
            f"---\n"
            f"date: {date}\n"
            f"type: {classification.note_type}\n"
            f"source: inbox\n"
            f"tags: [{classification.note_type}, auto-processed]\n"
            f"summary: {classification.summary}\n"
            f"---\n"
        )
        return frontmatter + content

    def _slugify(self, text: str) -> str:
        """Convert text to filename-safe slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text[:80].strip("-")

    def should_process(self, path: str) -> bool:
        """Check if a vault-relative path should be processed."""
        if not path.startswith("inbox/"):
            return False
        if path.endswith("/_template.md"):
            return False
        if not path.endswith(".md"):
            return False
        # Skip dotfiles
        parts = path.split("/")
        return not any(p.startswith(".") for p in parts)
