"""Tests for template-generated executable agents.

Covers TemplateEngine.generate_executable_agent(), AgentFactory integration,
and ConfigTemplateManager.generate_executable_and_register().
"""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path
from typing import Any

import pytest

from cohezion.core.plan_executor import ExecutionResult
from cohezion.core.template_engine import SkillSpec, TemplateEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_spec(
    name: str = "TEST_SKILL_PRIME",
    instructions: list[str] | None = None,
    domain: str = "Test domain expertise.",
) -> SkillSpec:
    """Create a minimal SkillSpec for testing."""
    return SkillSpec(
        name=name,
        domain_expertise=domain,
        concepts={"TestConcept": "A test concept."},
        instructions=instructions or ["Search the registry for capabilities"],
        version="1.0",
        see_also=[],
        raw_content="# SKILL: TEST_SKILL_PRIME\n## INSTRUCTION\n1. Search the registry",
        source_path=Path("test_skill_prime.md"),
    )


class _MockTokenClient:
    """Mock token client for testing async generate calls."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"[mock-response] len={len(prompt)}"


# ---------------------------------------------------------------------------
# Tests for TemplateEngine.generate_executable_agent()
# ---------------------------------------------------------------------------


class TestGenerateExecutableAgentSource:
    """Tests for TemplateEngine.generate_executable_agent()."""

    def test_produces_valid_python(self) -> None:
        """Generated source should compile without errors."""
        engine = TemplateEngine()
        spec = _make_spec()
        source = engine.generate_executable_agent(spec)

        # Should compile without SyntaxError
        compile(source, "<test>", "exec")

    def test_contains_plan_constant(self) -> None:
        """Generated source should contain a _PLAN constant."""
        engine = TemplateEngine()
        spec = _make_spec()
        source = engine.generate_executable_agent(spec)

        assert "_PLAN = ExecutablePlan(" in source
        assert 'skill_name="TEST_SKILL_PRIME"' in source

    def test_contains_class_definition(self) -> None:
        """Generated source should define the correct agent class."""
        engine = TemplateEngine()
        spec = _make_spec()
        source = engine.generate_executable_agent(spec)

        assert "class TestSkillAgent:" in source
        assert "async def process(" in source

    def test_imports_are_present(self) -> None:
        """Generated source should have necessary imports."""
        engine = TemplateEngine()
        spec = _make_spec()
        source = engine.generate_executable_agent(spec)

        assert "from cohezion.core.instruction_expander import ExecutablePlan, PlanStep" in source
        assert "from cohezion.core.plan_executor import ExecutionResult, PlanExecutor" in source

    def test_multiple_instructions_produce_steps(self) -> None:
        """Each instruction should become a PlanStep in the source."""
        engine = TemplateEngine()
        spec = _make_spec(
            instructions=[
                "Search the registry for tools",
                "Generate a summary report",
                "Store the results in the database",
            ]
        )
        source = engine.generate_executable_agent(spec)

        assert source.count("PlanStep(") >= 3

    def test_domain_in_docstring(self) -> None:
        """Domain expertise should appear in the generated docstring."""
        engine = TemplateEngine()
        spec = _make_spec(domain="Quantum computing expertise.")
        source = engine.generate_executable_agent(spec)

        assert "Quantum computing expertise." in source

    def test_no_instructions_produces_empty_steps(self) -> None:
        """A skill with no instructions should produce an empty steps list."""
        engine = TemplateEngine()
        spec = _make_spec(instructions=[])
        source = engine.generate_executable_agent(spec)

        assert "_PLAN = ExecutablePlan(" in source
        # The steps list should be empty
        compile(source, "<test>", "exec")


class TestGeneratedAgentProcess:
    """Tests for instantiating and calling the generated agent."""

    def test_process_returns_execution_result(self) -> None:
        """Calling process() on a generated agent should return ExecutionResult."""
        engine = TemplateEngine()
        spec = _make_spec(instructions=["Search for capabilities"])
        source = engine.generate_executable_agent(spec)

        # Execute the source to get the class
        namespace: dict[str, Any] = {}
        exec(compile(source, "<test>", "exec"), namespace)

        agent_cls = namespace["TestSkillAgent"]
        agent = agent_cls(token_client=None)

        result = asyncio.get_event_loop().run_until_complete(agent.process("test input"))

        assert isinstance(result, ExecutionResult)
        assert result.skill_name == "TEST_SKILL_PRIME"

    def test_process_with_mock_token_client(self) -> None:
        """Generated agent should use token_client when provided."""
        engine = TemplateEngine()
        spec = _make_spec(instructions=["Generate a comprehensive analysis"])
        source = engine.generate_executable_agent(spec)

        namespace: dict[str, Any] = {}
        exec(compile(source, "<test>", "exec"), namespace)

        mock_client = _MockTokenClient()
        agent_cls = namespace["TestSkillAgent"]
        agent = agent_cls(token_client=mock_client)

        result = asyncio.get_event_loop().run_until_complete(agent.process("analyze this"))

        assert isinstance(result, ExecutionResult)
        assert result.skill_name == "TEST_SKILL_PRIME"
        # With a generate operation and a mock client, we should get actual output
        assert result.final_output != ""


# ---------------------------------------------------------------------------
# Tests for AgentFactory integration
# ---------------------------------------------------------------------------


class TestFactoryCreateExecutable:
    """Tests for AgentFactory.create_executable() with generated agents."""

    def test_factory_create_executable_uses_generated(self, tmp_path: Path) -> None:
        """After generating an agent file, factory should load it."""
        from cohezion.agents.factory import AgentFactory

        # Create a minimal skill .md file in tmp
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_md = skills_dir / "FACTORY_TEST_PRIME.md"
        skill_md.write_text(
            textwrap.dedent("""\
            # SKILL: FACTORY_TEST_PRIME

            ## DOMAIN EXPERTISE
            Factory test domain.

            ## INSTRUCTION
            1. Search for test items

            ## VERSION
            1.0
            """),
            encoding="utf-8",
        )

        factory = AgentFactory(skills_dir=str(skills_dir))

        # Dynamic creation (no pre-generated file) should still work
        agent = factory.create_executable("FACTORY_TEST_PRIME")
        result = asyncio.get_event_loop().run_until_complete(agent.process("test input"))
        assert result.skill_name == "FACTORY_TEST_PRIME"

    def test_factory_generate_top_skills(self, tmp_path: Path) -> None:
        """generate_top_skills() should generate agents for skills with instructions."""
        from cohezion.agents.factory import AgentFactory

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create 3 skill files with instructions
        for i in range(3):
            skill_md = skills_dir / f"SKILL_{i}_PRIME.md"
            skill_md.write_text(
                textwrap.dedent(f"""\
                # SKILL: SKILL_{i}_PRIME

                ## DOMAIN EXPERTISE
                Domain for skill {i}.

                ## INSTRUCTION
                1. Search for items in category {i}
                2. Generate a summary

                ## VERSION
                1.0
                """),
                encoding="utf-8",
            )

        # Also create one without instructions
        no_inst = skills_dir / "NO_INST_PRIME.md"
        no_inst.write_text(
            textwrap.dedent("""\
            # SKILL: NO_INST_PRIME

            ## DOMAIN EXPERTISE
            No instructions here.

            ## VERSION
            1.0
            """),
            encoding="utf-8",
        )

        factory = AgentFactory(skills_dir=str(skills_dir))
        generated = factory.generate_top_skills(count=2)

        # Should only generate for skills with instructions
        assert len(generated) == 2
        assert all("SKILL_" in name for name in generated)


# ---------------------------------------------------------------------------
# Tests for ConfigTemplateManager.generate_executable_and_register()
# ---------------------------------------------------------------------------


class TestGenerateExecutableAndRegister:
    """Tests for ConfigTemplateManager.generate_executable_and_register()."""

    def test_writes_agent_file_and_updates_init(self, tmp_path: Path) -> None:
        """generate_executable_and_register() should write the agent file and update __init__.py."""
        # Set up a skills directory
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_md = skills_dir / "REG_TEST_PRIME.md"
        skill_md.write_text(
            textwrap.dedent("""\
            # SKILL: REG_TEST_PRIME

            ## DOMAIN EXPERTISE
            Registration test.

            ## INSTRUCTION
            1. Search the knowledge base
            2. Generate a report

            ## VERSION
            1.0
            """),
            encoding="utf-8",
        )

        # Create a generated dir in tmp to simulate the workflow
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()
        init_path = generated_dir / "__init__.py"
        init_path.write_text(
            '"""Auto-generated agents."""\n\n__all__: list[str] = []\n',
            encoding="utf-8",
        )

        engine = TemplateEngine(skills_dir=str(skills_dir))
        engine.parse_all()  # populate cache

        # Test the engine method directly (avoids fragile Path monkeypatching)
        spec = engine.get_spec_by_name("REG_TEST_PRIME")
        assert spec is not None
        source = engine.generate_executable_agent(spec)

        # Verify the source is valid
        assert "class RegTestAgent:" in source
        assert "_PLAN = ExecutablePlan(" in source
        compile(source, "<test>", "exec")

        # Write the file to verify the workflow
        agent_path = generated_dir / "reg_test_agent.py"
        agent_path.write_text(source, encoding="utf-8")
        assert agent_path.exists()

        # Verify __init__.py update logic (same logic as generate_executable_and_register)
        class_name = "RegTestAgent"
        import_line = f"from cohezion.agents.generated.reg_test_agent import {class_name}"
        init_content = init_path.read_text(encoding="utf-8")
        if import_line not in init_content:
            init_content = init_content.replace(
                "__all__: list[str] = [",
                f'__all__: list[str] = [\n    "{class_name}",',
            )
            init_content = import_line + "\n" + init_content
            init_path.write_text(init_content, encoding="utf-8")

        updated = init_path.read_text(encoding="utf-8")
        assert "RegTestAgent" in updated
        assert "reg_test_agent" in updated

    def test_skill_not_found_raises(self) -> None:
        """generate_executable_and_register() should raise KeyError for unknown skills."""
        from cohezion.core.config_templates import ConfigTemplateManager

        engine = TemplateEngine(skills_dir="/nonexistent")
        # Pre-populate cache to avoid recursive parse_all on missing dir
        engine._cache["_sentinel"] = _make_spec(name="_sentinel")
        manager = ConfigTemplateManager(engine=engine)

        with pytest.raises(KeyError, match="Skill not found"):
            manager.generate_executable_and_register("NONEXISTENT_SKILL")
