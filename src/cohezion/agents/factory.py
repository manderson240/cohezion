"""Dynamic Agent Factory for PRIME skill-driven agent creation.

Accepts a skill name, uses :class:`TemplateEngine` to parse the skill
definition, and dynamically generates a Python agent class. Classes are
cached so repeated calls for the same skill return the same type.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from cohezion.core.template_engine import SkillSpec, TemplateEngine


logger = logging.getLogger(__name__)


class _StubAgent:
    """Minimal fallback agent when BaseAgent cannot be imported."""

    SYSTEM_PROMPT: str = ""

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    async def process(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class AgentFactory:
    """Create agent instances from PRIME skill definitions.

    Parameters
    ----------
    skills_dir : str | Path
        Directory containing PRIME skill ``.md`` files.
    """

    def __init__(self, skills_dir: str | Path = "src/cohezion/skills/") -> None:
        self._engine = TemplateEngine(skills_dir)
        self._class_cache: dict[str, type] = {}

    def create(self, skill_name: str, **agent_kwargs: Any) -> Any:
        """Create an agent instance from a PRIME skill name.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive, e.g.
            ``"COMPOUND_ENGINEERING_PRIME"``).
        **agent_kwargs
            Keyword arguments forwarded to the agent constructor.

        Returns
        -------
        Any
            An instance of the dynamically generated agent class.

        Raises
        ------
        KeyError
            If *skill_name* cannot be found.
        """
        cls = self.get_class(skill_name)
        # BaseAgent requires model_name — provide a sensible default
        if "model_name" not in agent_kwargs:
            agent_kwargs["model_name"] = "phi3:mini"
        try:
            return cls(**agent_kwargs)
        except TypeError:
            # _StubAgent or other fallback that doesn't accept model_name
            return cls()
        except RuntimeError:
            # BaseAgent.__init__ calls asyncio.create_task — fails outside an
            # event loop. Re-compile with _StubAgent as the base so the
            # returned object is still named after the skill.
            spec = self._resolve_spec(skill_name)
            source = self._engine.generate_agent_stub(spec)
            cls_fallback = self._compile_class_with_stub(spec, source)
            return cls_fallback()

    def get_class(self, skill_name: str) -> type:
        """Return the agent class (cached) for *skill_name*.

        Raises
        ------
        KeyError
            If the skill cannot be found.
        """
        # Normalise for cache lookup
        key = skill_name.strip().upper()
        if key in self._class_cache:
            return self._class_cache[key]

        spec = self._resolve_spec(skill_name)
        source = self._engine.generate_agent_stub(spec)
        cls = self._compile_class(spec, source)
        self._class_cache[key] = cls
        return cls

    def create_executable(
        self,
        skill_name: str,
        token_client: Any = None,
        auto_regenerate: bool = False,
    ) -> Any:
        """Create an agent whose ``process()`` runs via PlanExecutor.

        Checks ``agents/generated/`` first for a pre-generated executable
        agent. Falls back to dynamic generation if not found.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive).
        token_client : Any, optional
            An LLM token client supporting ``async generate(prompt)``.
            If ``None``, LLM-dependent steps return placeholders.
        auto_regenerate : bool
            If ``True``, check version tracker and regenerate stale agents.

        Returns
        -------
        Any
            An agent instance with a working ``process()`` method.

        Raises
        ------
        KeyError
            If *skill_name* cannot be found.
        """
        # Check for staleness if auto_regenerate is enabled
        if auto_regenerate:
            try:
                from cohezion.agents.version_tracker import VersionTracker

                tracker = VersionTracker()
                spec = self._resolve_spec(skill_name)
                if tracker.needs_regeneration(skill_name, spec.version):
                    from cohezion.agents.template_pipeline import TemplatePipeline

                    pipeline = TemplatePipeline()
                    pipeline.regenerate_for_skill(skill_name)
            except Exception:
                logger.debug("Auto-regeneration check failed for %s", skill_name)

        # Check for pre-generated executable agent
        generated = self._try_load_generated(skill_name)
        if generated is not None:
            return generated(token_client=token_client)

        # Fall back to dynamic generation
        from cohezion.core.instruction_expander import InstructionExpander
        from cohezion.core.plan_executor import PlanExecutor

        spec = self._resolve_spec(skill_name)
        expander = InstructionExpander()
        plan = expander.expand(spec)
        executor = PlanExecutor(token_client=token_client)

        class _ExecutableAgent(_StubAgent):
            """Agent with plan-based process() method."""

            SYSTEM_PROMPT = spec.domain_expertise[:200] if spec.domain_expertise else ""

            async def process(self, *args: Any, **kwargs: Any) -> Any:
                input_text = args[0] if args else kwargs.get("input_text", "")
                return await executor.execute(plan, str(input_text))

        agent = _ExecutableAgent()
        agent.skill_name = skill_name  # type: ignore[attr-defined]
        agent.plan = plan  # type: ignore[attr-defined]
        return agent

    def generate_top_skills(self, count: int = 5) -> list[str]:
        """Generate executable agents for the top N skills with instructions.

        Parameters
        ----------
        count : int
            Maximum number of skills to generate agents for.

        Returns
        -------
        list[str]
            List of generated skill names.
        """
        from cohezion.core.config_templates import ConfigTemplateManager

        specs = self._engine.parse_all()
        with_instructions = [s for s in specs if s.instructions]
        selected = with_instructions[:count]

        manager = ConfigTemplateManager(engine=self._engine)
        generated: list[str] = []
        for spec in selected:
            try:
                manager.generate_executable_and_register(spec.name)
                generated.append(spec.name)
            except Exception:
                logger.exception("Failed to generate agent for %s", spec.name)

        return generated

    def list_available_skills(self) -> list[str]:
        """Return names of all parseable PRIME skills."""
        specs = self._engine.parse_all()
        return [s.name for s in specs]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_load_generated(self, skill_name: str) -> type | None:
        """Try to load a pre-generated executable agent class.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier.

        Returns
        -------
        type | None
            The agent class if found, else ``None``.
        """
        base = re.sub(r"_PRIME$", "", skill_name.strip(), flags=re.IGNORECASE)
        snake_name = base.lower()
        module_path = Path("src/cohezion/agents/generated") / f"{snake_name}_agent.py"

        if not module_path.exists():
            return None

        try:
            import importlib

            module = importlib.import_module(f"cohezion.agents.generated.{snake_name}_agent")
            class_name = "".join(w.capitalize() for w in base.split("_")) + "Agent"
            return getattr(module, class_name, None)  # type: ignore[return-value]
        except Exception:
            logger.debug("Failed to load generated agent for %s", skill_name)
            return None

    def _resolve_spec(self, skill_name: str) -> SkillSpec:
        """Look up a spec by name, trying filename match as fallback."""
        spec = self._engine.get_spec_by_name(skill_name)
        if spec is not None:
            return spec

        # Try matching against filenames (without extension)
        for md_file in sorted(self._engine.skills_dir.glob("*.md")):
            if md_file.stem.upper() == skill_name.strip().upper():
                return self._engine.parse_skill(md_file)

        raise KeyError(f"Skill not found: {skill_name}")

    @staticmethod
    def _validate_spec_name(name: str) -> None:
        """Validate spec name to prevent injection via exec() source filename."""
        if not re.match(r"^[a-zA-Z0-9_\- ]+$", name):
            raise ValueError(f"Invalid spec name: {name!r}")

    @staticmethod
    def _compile_class_with_stub(spec: SkillSpec, source: str) -> type:
        """Compile agent source using _StubAgent as the base class."""
        AgentFactory._validate_spec_name(spec.name)
        match = re.search(r"class (\w+)\(", source)
        if not match:
            raise RuntimeError(f"Could not find class definition in generated stub for {spec.name}")
        class_name = match.group(1)
        source = source.replace("from cohezion.agents.base import BaseAgent", "").replace(
            "(BaseAgent)", f"({_StubAgent.__name__})"
        )
        # Restrict builtins to only what's needed for class definition
        namespace: dict[str, Any] = {
            "__builtins__": __builtins__,
            _StubAgent.__name__: _StubAgent,
        }
        exec(compile(source, f"<agent:{spec.name}>", "exec"), namespace)
        cls = namespace.get(class_name)
        if cls is None:
            raise RuntimeError(f"Class {class_name} not found after compiling stub for {spec.name}")
        return cls

    @staticmethod
    def _compile_class(spec: SkillSpec, source: str) -> type:
        """Compile agent source and extract the class object."""
        AgentFactory._validate_spec_name(spec.name)
        # Extract class name from the source
        match = re.search(r"class (\w+)\(", source)
        if not match:
            raise RuntimeError(f"Could not find class definition in generated stub for {spec.name}")
        class_name = match.group(1)

        # Build a namespace with a BaseAgent fallback
        namespace: dict[str, Any] = {"__builtins__": __builtins__}

        # Patch the import so BaseAgent resolves even if deps are missing
        try:
            # Provide the module that the generated code tries to import
            import types

            from cohezion.agents.base import BaseAgent

            fake_mod = types.ModuleType("cohezion.agents.base")
            fake_mod.BaseAgent = BaseAgent  # type: ignore[attr-defined]
            namespace["cohezion"] = types.ModuleType("cohezion")
        except Exception:
            logger.debug("BaseAgent import failed; using _StubAgent fallback")
            # Rewrite the source to use _StubAgent instead
            source = source.replace(
                "from cohezion.agents.base import BaseAgent",
                "",
            ).replace("(BaseAgent)", f"({_StubAgent.__name__})")
            namespace[_StubAgent.__name__] = _StubAgent

        exec(compile(source, f"<agent:{spec.name}>", "exec"), namespace)

        cls = namespace.get(class_name)
        if cls is None:
            raise RuntimeError(f"Class {class_name} not found after compiling stub for {spec.name}")
        return cls
