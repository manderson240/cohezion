"""Dynamic template pipeline for batch agent generation and registry sync.

Orchestrates :class:`TemplateEngine`, :class:`ConfigTemplateManager`,
and :class:`VersionTracker` to batch-generate agents, detect staleness,
and reconcile the skill registry.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)

_SKILLS_DIR = Path("src/cohezion/skills/")


@dataclass
class GenerationResult:
    """Result of generating an agent from a skill.

    Attributes
    ----------
    skill_name : str
        PRIME skill identifier.
    agent_path : Path | None
        Path to the generated agent file.
    version : str
        Skill version used for generation.
    success : bool
        Whether generation succeeded.
    error : str
        Error message if generation failed.
    """

    skill_name: str
    agent_path: Path | None = None
    version: str = ""
    success: bool = False
    error: str = ""


@dataclass
class SyncResult:
    """Result of syncing the skill registry.

    Attributes
    ----------
    added : list[str]
        Skills newly added to the registry.
    updated : list[str]
        Skills whose registry entry was updated.
    unchanged : list[str]
        Skills already up to date.
    errors : list[str]
        Skills that failed to sync.
    """

    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class StaleAgent:
    """An agent that needs regeneration.

    Attributes
    ----------
    skill_name : str
        PRIME skill identifier.
    current_version : str
        Current version from the skill ``.md`` file.
    generated_version : str
        Version the agent was generated from.
    agent_path : str
        Path to the generated agent file.
    """

    skill_name: str
    current_version: str
    generated_version: str
    agent_path: str


class TemplatePipeline:
    """Batch agent generation, registry sync, and version tracking.

    Parameters
    ----------
    skills_dir : Path | None
        Override path to the skills directory.
    """

    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = skills_dir or _SKILLS_DIR
        self._engine = None
        self._manager = None
        self._tracker = None

    @property
    def engine(self):
        """Lazy-load TemplateEngine."""
        if self._engine is None:
            from cohezion.core.template_engine import TemplateEngine

            self._engine = TemplateEngine(self.skills_dir)
        return self._engine

    @property
    def manager(self):
        """Lazy-load ConfigTemplateManager."""
        if self._manager is None:
            from cohezion.core.config_templates import ConfigTemplateManager

            self._manager = ConfigTemplateManager(engine=self.engine)
        return self._manager

    @property
    def tracker(self):
        """Lazy-load VersionTracker."""
        if self._tracker is None:
            from cohezion.agents.version_tracker import VersionTracker

            self._tracker = VersionTracker()
        return self._tracker

    def generate_all(self, top_n: int = 20) -> list[GenerationResult]:
        """Generate executable agents for the top N skills with instructions.

        Parameters
        ----------
        top_n : int
            Maximum number of skills to generate.

        Returns
        -------
        list[GenerationResult]
            Results for each generation attempt.
        """
        specs = self.engine.parse_all()
        with_instructions = [s for s in specs if s.instructions]
        selected = with_instructions[:top_n]

        results = []
        for spec in selected:
            result = self._generate_one(spec.name, spec.version)
            results.append(result)

        logger.info(
            "Generated %d/%d agents",
            sum(1 for r in results if r.success),
            len(results),
        )
        return results

    def regenerate_for_skill(self, skill_name: str) -> GenerationResult:
        """Regenerate agent for a specific skill after refinement.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier.

        Returns
        -------
        GenerationResult
            Result of the regeneration attempt.
        """
        spec = self.engine.get_spec_by_name(skill_name)
        if spec is None:
            return GenerationResult(skill_name=skill_name, error="Skill not found")
        return self._generate_one(spec.name, spec.version)

    def sync_registry(self) -> SyncResult:
        """Parse all skill ``.md`` files and reconcile with skill_registry.json.

        Adds missing entries, updates stale ones, and leaves current ones
        unchanged.

        Returns
        -------
        SyncResult
            Summary of sync operations.
        """
        result = SyncResult()
        registry_path = Path("src/cohezion/skills/skill_registry.json")

        # Load existing registry
        registry = self._load_registry(registry_path)

        # Parse all skills
        specs = self.engine.parse_all()

        for spec in specs:
            try:
                new_entry = {
                    "version": spec.version,
                    "concepts": list(spec.concepts.keys()),
                    "see_also": spec.see_also,
                    "source": str(spec.source_path),
                }

                if spec.name not in registry:
                    registry[spec.name] = new_entry
                    result.added.append(spec.name)
                elif registry[spec.name].get("version") != spec.version:
                    registry[spec.name] = new_entry
                    result.updated.append(spec.name)
                else:
                    result.unchanged.append(spec.name)
            except Exception as exc:
                logger.exception("Failed to sync skill: %s", spec.name)
                result.errors.append(f"{spec.name}: {exc}")

        # Write updated registry
        try:
            self._write_registry(registry_path, registry)
        except OSError:
            logger.exception("Failed to write skill registry")
            result.errors.append("Failed to write registry file")

        logger.info(
            "Registry sync: %d added, %d updated, %d unchanged, %d errors",
            len(result.added),
            len(result.updated),
            len(result.unchanged),
            len(result.errors),
        )
        return result

    def detect_stale_agents(self) -> list[StaleAgent]:
        """Find agents that need regeneration based on version comparison.

        Compares the version in ``versions.json`` against the current
        version in each skill ``.md`` file.

        Returns
        -------
        list[StaleAgent]
            Agents that are out of date.
        """
        stale: list[StaleAgent] = []
        versions = self.tracker.get_all_versions()
        specs = self.engine.parse_all()

        for spec in specs:
            entry = versions.get(spec.name)
            if entry is None:
                continue
            if entry.get("version", "") != spec.version:
                stale.append(
                    StaleAgent(
                        skill_name=spec.name,
                        current_version=spec.version,
                        generated_version=entry.get("version", "unknown"),
                        agent_path=entry.get("agent_path", ""),
                    )
                )

        return stale

    @staticmethod
    def _load_registry(registry_path: Path) -> dict:
        """Load the existing skill registry from disk."""
        if not registry_path.exists():
            return {}
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            return dict(data) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read skill registry, starting fresh")
            return {}

    def _generate_one(self, skill_name: str, version: str) -> GenerationResult:
        """Generate a single agent and update version tracker.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier.
        version : str
            Current skill version.

        Returns
        -------
        GenerationResult
            Result of the generation.
        """
        try:
            paths = self.manager.generate_executable_and_register(skill_name)
            agent_path = paths.get("agent")
            self.tracker.record_generation(
                skill_name,
                version,
                str(agent_path) if agent_path else "",
            )
            return GenerationResult(
                skill_name=skill_name,
                agent_path=agent_path,
                version=version,
                success=True,
            )
        except Exception as exc:
            logger.exception("Failed to generate agent for %s", skill_name)
            return GenerationResult(skill_name=skill_name, error=str(exc))

    @staticmethod
    def _write_registry(registry_path: Path, registry: dict) -> None:
        """Write registry with optional file locking."""
        try:
            from cohezion.concurrency.file_lock import LockedFileOperation

            with LockedFileOperation(registry_path) as locked:
                locked.write_json(registry)
        except ImportError:
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(
                json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
