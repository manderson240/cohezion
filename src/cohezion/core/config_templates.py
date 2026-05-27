# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Config Template Manager for PRIME skill-driven code generation.

Provides a high-level interface over :class:`TemplateEngine` to look up
skills by name and generate config classes or agent stubs.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.core.template_engine import SkillSpec, TemplateEngine

logger = logging.getLogger(__name__)


class ConfigTemplateManager:
    """High-level manager for skill-based code generation.

    Parameters
    ----------
    engine : TemplateEngine | None
        Pre-configured engine instance.  If ``None``, a default one is
        created on first access.
    """

    def __init__(self, engine: TemplateEngine | None = None) -> None:
        self._engine = engine

    @property
    def engine(self) -> TemplateEngine:
        """Lazily initialise the template engine."""
        if self._engine is None:
            from cohezion.core.template_engine import TemplateEngine

            self._engine = TemplateEngine()
        return self._engine

    def get_config_for_skill(self, skill_name: str) -> str:
        """Return generated config-class source for *skill_name*.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive).

        Returns
        -------
        str
            Python source code for the config dataclass.

        Raises
        ------
        KeyError
            If the skill cannot be found.
        """
        spec = self.engine.get_spec_by_name(skill_name)
        if spec is None:
            raise KeyError(f"Skill not found: {skill_name}")
        return self.engine.generate_config_class(spec)

    def get_agent_for_skill(self, skill_name: str) -> str:
        """Return generated agent-stub source for *skill_name*.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive).

        Returns
        -------
        str
            Python source code for the agent class.

        Raises
        ------
        KeyError
            If the skill cannot be found.
        """
        spec = self.engine.get_spec_by_name(skill_name)
        if spec is None:
            raise KeyError(f"Skill not found: {skill_name}")
        return self.engine.generate_agent_stub(spec)

    def update_registry(self, spec: SkillSpec) -> None:
        """Update ``skill_registry.json`` with parsed skill metadata.

        Parameters
        ----------
        spec : SkillSpec
            The skill spec to register.
        """
        registry_path = Path("src/cohezion/skills/skill_registry.json")
        registry: dict = {}

        if registry_path.exists():
            try:
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not read skill registry, creating new one")

        registry[spec.name] = {
            "version": spec.version,
            "concepts": list(spec.concepts.keys()),
            "see_also": spec.see_also,
            "source": str(spec.source_path),
        }

        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Updated skill registry for %s", spec.name)

    def generate_executable_and_register(self, skill_name: str) -> dict[str, Path]:
        """Generate an executable agent (with working ``process()``) and register it.

        Unlike :meth:`generate_and_register` which produces ``NotImplementedError``
        stubs, this generates agents with pre-expanded plans that call
        :class:`PlanExecutor`.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive).

        Returns
        -------
        dict[str, Path]
            Mapping of ``"agent"`` to the generated file path.

        Raises
        ------
        KeyError
            If the skill cannot be found.
        """
        spec = self.engine.get_spec_by_name(skill_name)
        if spec is None:
            raise KeyError(f"Skill not found: {skill_name}")

        base = re.sub(r"_PRIME$", "", spec.name, flags=re.IGNORECASE)
        snake_name = base.lower()

        generated_dir = Path("src/cohezion/agents/generated")
        generated_dir.mkdir(parents=True, exist_ok=True)

        # Ensure __init__.py exists
        init_path = generated_dir / "__init__.py"
        if not init_path.exists():
            init_path.write_text(
                '"""Auto-generated agents from PRIME skill definitions."""\n\n__all__: list[str] = []\n',
                encoding="utf-8",
            )

        # Generate executable agent
        agent_source = self.engine.generate_executable_agent(spec)
        version_header = f"# Generated from {spec.name} v{spec.version} at {time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
        agent_source = version_header + agent_source
        agent_path = generated_dir / f"{snake_name}_agent.py"
        agent_path.write_text(agent_source, encoding="utf-8")

        # Update __init__.py with the new class
        class_name = re.sub(r"_PRIME$", "", spec.name, flags=re.IGNORECASE)
        class_name = "".join(word.capitalize() for word in class_name.split("_")) + "Agent"

        init_content = init_path.read_text(encoding="utf-8")
        import_line = f"from cohezion.agents.generated.{snake_name}_agent import {class_name}"
        if import_line not in init_content:
            # Add import and update __all__
            if "__all__" in init_content:
                init_content = init_content.replace(
                    "__all__: list[str] = [",
                    f'__all__: list[str] = [\n    "{class_name}",',
                )
            init_content = import_line + "\n" + init_content
            init_path.write_text(init_content, encoding="utf-8")

        # Update the skill registry
        self.update_registry(spec)

        logger.info("Generated executable agent: %s -> %s", skill_name, agent_path)
        return {"agent": agent_path}

    def generate_and_register(self, skill_name: str) -> dict[str, Path]:
        """Generate agent + config files on disk and register in the skill registry.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive).

        Returns
        -------
        dict[str, Path]
            Mapping of ``"agent"`` and ``"config"`` to the generated file paths.

        Raises
        ------
        KeyError
            If the skill cannot be found.
        """
        spec = self.engine.get_spec_by_name(skill_name)
        if spec is None:
            raise KeyError(f"Skill not found: {skill_name}")

        # Derive a snake_case filename from the skill name
        base = re.sub(r"_PRIME$", "", spec.name, flags=re.IGNORECASE)
        snake_name = base.lower()

        generated_dir = Path("src/cohezion/agents/generated")
        generated_dir.mkdir(parents=True, exist_ok=True)

        # Ensure __init__.py exists
        init_path = generated_dir / "__init__.py"
        if not init_path.exists():
            init_path.write_text(
                '"""Auto-generated agents from PRIME skill definitions."""\n\n__all__: list[str] = []\n',
                encoding="utf-8",
            )

        # Generate and write agent stub
        agent_source = self.engine.generate_agent_stub(spec)
        agent_path = generated_dir / f"{snake_name}_agent.py"
        agent_path.write_text(agent_source, encoding="utf-8")
        logger.info("Generated agent stub: %s", agent_path)

        # Generate and write config class
        config_source = self.engine.generate_config_class(spec)
        config_path = generated_dir / f"{snake_name}_config.py"
        config_path.write_text(config_source, encoding="utf-8")
        logger.info("Generated config class: %s", config_path)

        # Update the skill registry
        self.update_registry(spec)

        return {"agent": agent_path, "config": config_path}
