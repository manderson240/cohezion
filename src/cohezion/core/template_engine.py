# ruff: noqa: SIM108  # if/else preferred over ternary
"""Adaptive Template Engine for parsing PRIME skill definitions.

Parses PRIME skill ``.md`` files into structured ``SkillSpec`` objects,
then generates Python agent stubs and configuration dataclasses.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)

# Section heading patterns (case-insensitive)
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_SKILL_NAME_RE = re.compile(r"^#\s+SKILL:\s*(.+?)\s*$", re.MULTILINE)
_CONCEPT_BULLET_RE = re.compile(r"^[\-\*]\s+\*\*(.+?)\*\*[:\-\s]+(.+)$", re.MULTILINE)
_NUMBERED_STEP_RE = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)


@dataclass
class SkillSpec:
    """Structured representation of a PRIME skill definition.

    Attributes
    ----------
    name : str
        Skill identifier, e.g. ``"COMPOUND_ENGINEERING_PRIME"``.
    domain_expertise : str
        Full text of the DOMAIN EXPERTISE section.
    concepts : dict[str, str]
        Mapping of concept name to description.
    instructions : list[str]
        Ordered instruction steps (top-level numbered items).
    version : str
        Version string extracted from VERSION section, or ``"unknown"``.
    see_also : list[str]
        Related skill names from SEE ALSO section.
    raw_content : str
        Complete markdown source.
    source_path : Path
        Filesystem path to the ``.md`` file.
    """

    name: str
    domain_expertise: str
    concepts: dict[str, str] = field(default_factory=dict)
    instructions: list[str] = field(default_factory=list)
    version: str = "unknown"
    see_also: list[str] = field(default_factory=list)
    raw_content: str = ""
    source_path: Path = field(default_factory=lambda: Path("."))


def _extract_sections(text: str) -> dict[str, str]:
    """Split markdown into {heading_upper: body} mapping."""
    headings = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for i, m in enumerate(headings):
        key = m.group(1).strip().upper()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        sections[key] = text[start:end].strip()
    return sections


def _parse_concepts(text: str) -> dict[str, str]:
    """Extract concept name/description pairs from bullet lists."""
    concepts: dict[str, str] = {}
    for m in _CONCEPT_BULLET_RE.finditer(text):
        name = m.group(1).strip().rstrip(":")
        desc = m.group(2).strip()
        concepts[name] = desc
    return concepts


def _parse_instructions(text: str) -> list[str]:
    """Extract top-level numbered instruction steps."""
    steps: list[str] = []
    for m in _NUMBERED_STEP_RE.finditer(text):
        step = m.group(1).strip()
        # Only capture top-level steps (not indented sub-items)
        line_start = text.rfind("\n", 0, m.start()) + 1
        prefix = text[line_start : m.start()]
        if not prefix or not prefix.strip():
            steps.append(step)
    return steps


def _parse_see_also(text: str) -> list[str]:
    """Extract see-also references."""
    refs: list[str] = []
    for line in text.splitlines():
        line = line.strip().lstrip("-*").strip()
        if line:
            # Remove .md suffix if present
            line = re.sub(r"\.md$", "", line)
            refs.append(line.strip())
    return refs


def _skill_name_to_class(skill_name: str) -> str:
    """Convert ``COMPOUND_ENGINEERING_PRIME`` to ``CompoundEngineering``."""
    # Strip description suffixes like " -- subtitle" or " - subtitle"
    base = re.split(r"\s+[-–—]+\s+", skill_name)[0]
    # Remove trailing _PRIME
    base = re.sub(r"_PRIME$", "", base, flags=re.IGNORECASE)
    # Collapse non-alphanumeric (except underscore) to single underscore
    base = re.sub(r"[^a-zA-Z0-9_]", "_", base)
    # Collapse multiple underscores
    base = re.sub(r"_+", "_", base).strip("_")
    # Title-case each word, remove underscores
    result = "".join(word.capitalize() for word in base.split("_"))
    # Ensure the class name doesn't start with a digit and is non-empty
    if not result:
        result = "UnnamedSkill"
    elif result[0].isdigit():
        result = f"Skill{result}"
    return result


def _concept_name_to_field(name: str) -> str:
    """Convert a concept name to a valid Python field name."""
    # Replace non-alphanumeric with underscore, lowercase
    field_name = re.sub(r"[^a-zA-Z0-9]", "_", name).strip("_").lower()
    # Collapse multiple underscores
    field_name = re.sub(r"_+", "_", field_name)
    # Ensure it doesn't start with a digit
    if field_name and field_name[0].isdigit():
        field_name = f"f_{field_name}"
    return field_name or "unnamed"


class TemplateEngine:
    """Parse PRIME skill definitions and generate Python code.

    Parameters
    ----------
    skills_dir : str | Path
        Directory containing PRIME skill ``.md`` files.
    """

    def __init__(self, skills_dir: str | Path = "src/cohezion/skills/") -> None:
        self.skills_dir = Path(skills_dir)
        self._cache: dict[str, SkillSpec] = {}

    def parse_skill(self, path: Path) -> SkillSpec:
        """Parse a single PRIME skill ``.md`` file into a ``SkillSpec``.

        Parameters
        ----------
        path : Path
            Path to the markdown file.

        Returns
        -------
        SkillSpec
            Parsed skill specification.
        """
        text = path.read_text(encoding="utf-8")
        sections = _extract_sections(text)

        # Extract skill name from title or filename
        name_match = _SKILL_NAME_RE.search(text)
        if name_match:
            name = name_match.group(1).strip()
        else:
            # Derive from filename
            name = path.stem.upper()

        # Domain expertise
        domain = ""
        for key in ("DOMAIN EXPERTISE", "DOMAIN_EXPERTISE"):
            if key in sections:
                domain = sections[key]
                break

        # Concepts — try multiple heading variants
        concepts: dict[str, str] = {}
        for key in ("KEY TEXTS & CONCEPTS", "KEY CONCEPTS", "CONCEPTS"):
            if key in sections:
                concepts = _parse_concepts(sections[key])
                break

        # Instructions
        instructions: list[str] = []
        if "INSTRUCTION" in sections:
            instructions = _parse_instructions(sections["INSTRUCTION"])
        elif "INSTRUCTIONS" in sections:
            instructions = _parse_instructions(sections["INSTRUCTIONS"])

        # Version
        version = "unknown"
        if "VERSION" in sections:
            version = sections["VERSION"].strip().splitlines()[0].strip()

        # See also
        see_also: list[str] = []
        if "SEE ALSO" in sections:
            see_also = _parse_see_also(sections["SEE ALSO"])

        spec = SkillSpec(
            name=name,
            domain_expertise=domain,
            concepts=concepts,
            instructions=instructions,
            version=version,
            see_also=see_also,
            raw_content=text,
            source_path=path,
        )

        self._cache[name] = spec
        return spec

    def parse_all(self) -> list[SkillSpec]:
        """Parse all ``.md`` files in the skills directory.

        Returns
        -------
        list[SkillSpec]
            All parsed skill specifications.
        """
        specs: list[SkillSpec] = []
        if not self.skills_dir.exists():
            logger.warning("Skills directory not found: %s", self.skills_dir)
            return specs

        for md_file in sorted(self.skills_dir.glob("*.md")):
            try:
                spec = self.parse_skill(md_file)
                specs.append(spec)
            except Exception:
                logger.exception("Failed to parse skill: %s", md_file)
        return specs

    def generate_agent_stub(self, spec: SkillSpec) -> str:
        """Generate a Python agent class stub from a ``SkillSpec``.

        Parameters
        ----------
        spec : SkillSpec
            Parsed skill specification.

        Returns
        -------
        str
            Python source code for the agent class.
        """
        class_name = _skill_name_to_class(spec.name) + "Agent"
        # Truncate domain for docstring (first sentence)
        domain_short = (
            spec.domain_expertise.split("\n")[0][:200]
            if spec.domain_expertise
            else "No domain specified."
        )
        # Escape any triple quotes in domain text
        domain_escaped = domain_short.replace('"""', '\\"\\"\\"')
        system_prompt = domain_escaped.replace('"', '\\"')

        return f'''"""Auto-generated agent for {spec.name}."""

from __future__ import annotations

from typing import Any

from cohezion.agents.base import BaseAgent


class {class_name}(BaseAgent):
    """Auto-generated agent for {spec.name}.

    Domain: {domain_escaped}
    Version: {spec.version}
    """

    SYSTEM_PROMPT = "{system_prompt}"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """Process input using the {spec.name} skill."""
        raise NotImplementedError
'''

    def generate_executable_agent(self, spec: SkillSpec) -> str:
        """Generate a Python agent class with a working ``process()`` method.

        The generated agent has a pre-expanded plan constant and
        delegates to :class:`PlanExecutor` for execution.

        Parameters
        ----------
        spec : SkillSpec
            Parsed skill specification.

        Returns
        -------
        str
            Python source code for the executable agent class.
        """
        class_name = _skill_name_to_class(spec.name) + "Agent"
        domain_short = (
            spec.domain_expertise.split("\n")[0][:200]
            if spec.domain_expertise
            else "No domain specified."
        )
        system_prompt = domain_short.replace('"', '\\"')

        # Pre-expand instructions into plan steps for the constant
        from cohezion.core.instruction_expander import InstructionExpander

        expander = InstructionExpander()
        plan = expander.expand(spec)

        # Serialize plan steps as multi-line format with double-quoted keys
        steps_repr = "[\n"
        for step in plan.steps:
            import json

            params_repr = json.dumps(step.params)
            desc_escaped = step.description.replace('"', '\\"')
            steps_repr += (
                f"        PlanStep(\n"
                f'            operation="{step.operation}",\n'
                f"            params={params_repr},\n"
                f'            description="{desc_escaped}",\n'
                f"        ),\n"
            )
        steps_repr += "    ]"

        domain_escaped = (plan.domain or "").replace('"', '\\"')

        return f'''"""Auto-generated executable agent for {spec.name}."""

from __future__ import annotations

from typing import Any

from cohezion.core.instruction_expander import ExecutablePlan, PlanStep
from cohezion.core.plan_executor import ExecutionResult, PlanExecutor


_PLAN = ExecutablePlan(
    skill_name="{spec.name}",
    steps={steps_repr},
    domain="{domain_escaped}",
)


class {class_name}:
    """Executable agent for {spec.name}.

    Domain: {system_prompt}
    Version: {spec.version}
    """

    SYSTEM_PROMPT = "{system_prompt}"

    def __init__(self, token_client: Any | None = None) -> None:
        self._token_client = token_client

    async def process(self, input_text: str, **kwargs: Any) -> ExecutionResult:
        """Process input by executing the pre-expanded plan."""
        executor = PlanExecutor(token_client=self._token_client)
        return await executor.execute(_PLAN, input_text)
'''

    def generate_config_class(self, spec: SkillSpec) -> str:
        """Generate a ``@dataclass`` config class from a ``SkillSpec``.

        Parameters
        ----------
        spec : SkillSpec
            Parsed skill specification.

        Returns
        -------
        str
            Python source code for the config dataclass.
        """
        class_name = _skill_name_to_class(spec.name) + "Config"

        # Build fields from concepts
        field_lines: list[str] = []
        for concept_name in spec.concepts:
            field_name = _concept_name_to_field(concept_name)
            field_lines.append(f'    {field_name}: str = ""')

        # Ensure at least one field
        if not field_lines:
            field_lines.append("    enabled: bool = True")

        fields_block = "\n".join(field_lines)

        return f'''"""Auto-generated config for {spec.name}."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class {class_name}:
    """Configuration for {spec.name}."""

{fields_block}
'''

    def get_spec_by_name(self, skill_name: str) -> SkillSpec | None:
        """Look up a cached spec by skill name.

        Parameters
        ----------
        skill_name : str
            The skill name (case-insensitive match).

        Returns
        -------
        SkillSpec | None
            The spec if found, else ``None``.
        """
        # Direct cache hit
        if skill_name in self._cache:
            return self._cache[skill_name]

        # Case-insensitive search
        upper = skill_name.upper()
        for key, spec in self._cache.items():
            if key.upper() == upper:
                return spec

        # Try parsing all if cache is empty
        if not self._cache:
            self.parse_all()
            return self.get_spec_by_name(skill_name)

        return None
