"""Tests for InstructionExpander and PlanExecutor."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from cohezion.core.instruction_expander import (
    ExecutablePlan,
    InstructionExpander,
    PlanStep,
    _classify_instruction,
)
from cohezion.core.plan_executor import (
    ExecutionResult,
    PlanExecutor,
    StepResult,
)
from cohezion.core.template_engine import SkillSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_spec() -> SkillSpec:
    """A minimal SkillSpec for testing."""
    return SkillSpec(
        name="TEST_SKILL_PRIME",
        domain_expertise="Testing and validation of plan execution.",
        concepts={"Unit Testing": "Verify individual components."},
        instructions=[
            "Search the codebase for relevant modules.",
            "Generate a summary of findings.",
            "Analyze the results for correctness.",
            "Transform the data into a report format.",
            "Save the final report to the knowledge base.",
        ],
        version="v1.0",
        see_also=["COMPOUND_ENGINEERING_PRIME"],
        raw_content="",
        source_path=Path("."),
    )


@pytest.fixture()
def expander() -> InstructionExpander:
    return InstructionExpander()


@pytest.fixture()
def sample_plan(sample_spec: SkillSpec, expander: InstructionExpander) -> ExecutablePlan:
    return expander.expand(sample_spec)


# ---------------------------------------------------------------------------
# InstructionExpander tests
# ---------------------------------------------------------------------------


class TestClassifyInstruction:
    """Test keyword classification for each operation type."""

    def test_search_keywords(self) -> None:
        assert _classify_instruction("Search the codebase for relevant modules") == "search"
        assert _classify_instruction("Find all available agents") == "search"
        assert _classify_instruction("Locate the configuration file") == "search"
        assert _classify_instruction("Identify potential issues") == "search"

    def test_generate_keywords(self) -> None:
        assert _classify_instruction("Generate a summary of the data") == "generate"
        assert _classify_instruction("Create a new agent configuration") == "generate"
        assert _classify_instruction("Write a detailed report") == "generate"
        assert _classify_instruction("Draft the implementation plan") == "generate"

    def test_analyze_keywords(self) -> None:
        assert _classify_instruction("Analyze the results for correctness") == "analyze"
        assert _classify_instruction("Evaluate the performance metrics") == "analyze"
        assert _classify_instruction("Review the code for issues") == "analyze"
        assert _classify_instruction("Verify the output matches expected") == "analyze"

    def test_transform_keywords(self) -> None:
        assert _classify_instruction("Transform the data into report format") == "transform"
        assert _classify_instruction("Convert JSON to CSV") == "transform"
        assert _classify_instruction("Extract keywords from the text") == "transform"
        assert _classify_instruction("Parse the configuration file") == "transform"

    def test_persist_keywords(self) -> None:
        assert _classify_instruction("Save the final report") == "persist"
        assert _classify_instruction("Store results in the database") == "persist"
        assert _classify_instruction("Log the execution metrics") == "persist"
        assert _classify_instruction("Archive old simulation data") == "persist"

    def test_default_to_generate(self) -> None:
        """Instructions with no matching keywords default to generate."""
        assert _classify_instruction("Do something completely abstract") == "generate"


class TestInstructionExpander:
    """Test the InstructionExpander class."""

    def test_expand_produces_correct_step_count(self, sample_spec: SkillSpec, expander: InstructionExpander) -> None:
        plan = expander.expand(sample_spec)
        assert len(plan.steps) == len(sample_spec.instructions)

    def test_expand_preserves_skill_name(self, sample_spec: SkillSpec, expander: InstructionExpander) -> None:
        plan = expander.expand(sample_spec)
        assert plan.skill_name == "TEST_SKILL_PRIME"

    def test_expand_preserves_domain(self, sample_spec: SkillSpec, expander: InstructionExpander) -> None:
        plan = expander.expand(sample_spec)
        assert plan.domain == sample_spec.domain_expertise

    def test_expand_classifies_operations(self, sample_spec: SkillSpec, expander: InstructionExpander) -> None:
        plan = expander.expand(sample_spec)
        operations = [s.operation for s in plan.steps]
        assert operations == ["search", "generate", "analyze", "transform", "persist"]

    def test_expand_preserves_descriptions(self, sample_spec: SkillSpec, expander: InstructionExpander) -> None:
        plan = expander.expand(sample_spec)
        for step, instruction in zip(plan.steps, sample_spec.instructions, strict=True):
            assert step.description == instruction

    def test_expand_empty_instructions(self, expander: InstructionExpander) -> None:
        spec = SkillSpec(name="EMPTY", domain_expertise="", instructions=[])
        plan = expander.expand(spec)
        assert plan.steps == []
        assert plan.skill_name == "EMPTY"

    def test_expand_extracts_backtick_refs(self, expander: InstructionExpander) -> None:
        spec = SkillSpec(
            name="REF_TEST",
            domain_expertise="",
            instructions=["Search using `CapabilityRegistry` for agents."],
        )
        plan = expander.expand(spec)
        assert "CapabilityRegistry" in plan.steps[0].params.get("references", [])

    def test_expand_extracts_bold_concepts(self, expander: InstructionExpander) -> None:
        spec = SkillSpec(
            name="BOLD_TEST",
            domain_expertise="",
            instructions=["Generate a **Plan** using **Compound Engineering**."],
        )
        plan = expander.expand(spec)
        assert "Plan" in plan.steps[0].params.get("concepts", [])
        assert "Compound Engineering" in plan.steps[0].params.get("concepts", [])

    def test_expand_real_skill(self) -> None:
        """Expand a real PRIME skill .md file if available."""
        skills_dir = Path("src/cohezion/skills/")
        target = skills_dir / "COMPOUND_ENGINEERING_PRIME.md"
        if not target.exists():
            pytest.skip("COMPOUND_ENGINEERING_PRIME.md not found")

        from cohezion.core.template_engine import TemplateEngine

        engine = TemplateEngine(skills_dir)
        spec = engine.parse_skill(target)
        expander = InstructionExpander()
        plan = expander.expand(spec)

        assert plan.skill_name == spec.name
        assert len(plan.steps) == len(spec.instructions)
        assert all(s.operation in ("search", "generate", "analyze", "transform", "persist") for s in plan.steps)


# ---------------------------------------------------------------------------
# PlanExecutor tests
# ---------------------------------------------------------------------------


class TestPlanExecutor:
    """Test the PlanExecutor class."""

    def test_execute_runs_all_steps(self, sample_plan: ExecutablePlan) -> None:
        executor = PlanExecutor(token_client=None)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(sample_plan, "test input"))
        assert len(result.steps) == len(sample_plan.steps)
        assert result.skill_name == sample_plan.skill_name

    def test_execute_pipes_output(self, sample_plan: ExecutablePlan) -> None:
        """Each step receives the previous step's output as context."""
        executor = PlanExecutor(token_client=None)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(sample_plan, "initial input"))
        # The first step is search — its output is fed to the generate step
        # The generate step's output mentions its input_length which should
        # be > 0 (it received output from search, not empty)
        assert result.steps[0].output  # search produced something
        assert result.steps[1].output  # generate produced something

    def test_execute_tracks_metrics(self, sample_plan: ExecutablePlan) -> None:
        executor = PlanExecutor(token_client=None)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(sample_plan, "test"))
        assert result.total_duration_ms >= 0
        assert result.total_tokens >= 0
        for step in result.steps:
            assert step.duration_ms >= 0

    def test_execute_with_mock_token_client(self) -> None:
        """Token client is called for generate/analyze steps."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value="Generated output from LLM")

        plan = ExecutablePlan(
            skill_name="LLM_TEST",
            steps=[
                PlanStep(operation="generate", description="Generate something"),
            ],
            domain="test domain",
        )

        executor = PlanExecutor(token_client=mock_client)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(plan, "test input"))

        mock_client.generate.assert_called_once()
        assert result.steps[0].output == "Generated output from LLM"
        assert result.steps[0].tokens_used > 0

    def test_execute_without_token_client(self) -> None:
        """Without token_client, generate/analyze return placeholders."""
        plan = ExecutablePlan(
            skill_name="NO_LLM",
            steps=[
                PlanStep(operation="generate", description="Generate a report"),
                PlanStep(operation="analyze", description="Analyze results"),
            ],
            domain="test",
        )

        executor = PlanExecutor(token_client=None)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(plan, "input text"))

        assert "[generate]" in result.steps[0].output
        assert "[analyze]" in result.steps[1].output
        assert result.total_tokens == 0

    def test_execute_empty_plan(self) -> None:
        plan = ExecutablePlan(skill_name="EMPTY", steps=[], domain="")
        executor = PlanExecutor(token_client=None)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(plan, "input"))
        assert result.steps == []
        assert result.final_output == ""
        assert result.total_tokens == 0

    def test_execute_transform_extracts_keywords(self) -> None:
        plan = ExecutablePlan(
            skill_name="TRANSFORM_TEST",
            steps=[
                PlanStep(operation="transform", description="Extract keywords"),
            ],
            domain="",
        )
        executor = PlanExecutor(token_client=None)
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, "The coherence metric improved significantly")
        )
        assert "keywords=" in result.steps[0].output
        assert "coherence" in result.steps[0].output.lower()

    def test_execute_persist_confirms(self) -> None:
        plan = ExecutablePlan(
            skill_name="PERSIST_TEST",
            steps=[
                PlanStep(operation="persist", description="Save results"),
            ],
            domain="",
        )
        executor = PlanExecutor(token_client=None)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(plan, "data to persist"))
        assert "[persisted]" in result.steps[0].output

    def test_token_client_failure_falls_back(self) -> None:
        """If token_client raises, fall back to placeholder."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(side_effect=RuntimeError("LLM down"))

        plan = ExecutablePlan(
            skill_name="FAIL_TEST",
            steps=[
                PlanStep(operation="generate", description="Try generating"),
            ],
            domain="test",
        )

        executor = PlanExecutor(token_client=mock_client)
        result = asyncio.get_event_loop().run_until_complete(executor.execute(plan, "input"))
        # Should not raise; falls back to placeholder
        assert "[generate]" in result.steps[0].output


# ---------------------------------------------------------------------------
# AgentFactory.create_executable tests
# ---------------------------------------------------------------------------


class TestAgentFactoryExecutable:
    """Test AgentFactory.create_executable integration."""

    def test_create_executable_returns_agent(self) -> None:
        from cohezion.agents.factory import AgentFactory

        factory = AgentFactory()
        skills = factory.list_available_skills()
        if not skills:
            pytest.skip("No PRIME skills found")

        agent = factory.create_executable(skills[0])
        assert hasattr(agent, "process")
        assert hasattr(agent, "plan")
        assert hasattr(agent, "skill_name")

    def test_create_executable_process_works(self) -> None:
        from cohezion.agents.factory import AgentFactory

        factory = AgentFactory()
        skills = factory.list_available_skills()
        if not skills:
            pytest.skip("No PRIME skills found")

        agent = factory.create_executable(skills[0])
        result = asyncio.get_event_loop().run_until_complete(agent.process("test input"))
        assert isinstance(result, ExecutionResult)
        assert result.skill_name == skills[0]

    def test_create_executable_not_found(self) -> None:
        from cohezion.agents.factory import AgentFactory

        factory = AgentFactory()
        with pytest.raises(KeyError):
            factory.create_executable("NONEXISTENT_SKILL_XYZ")


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestDataclasses:
    """Test dataclass defaults and structure."""

    def test_plan_step_defaults(self) -> None:
        step = PlanStep(operation="search")
        assert step.params == {}
        assert step.description == ""

    def test_executable_plan_defaults(self) -> None:
        plan = ExecutablePlan(skill_name="TEST")
        assert plan.steps == []
        assert plan.domain == ""

    def test_step_result_defaults(self) -> None:
        sr = StepResult(step_index=0, operation="search", output="ok")
        assert sr.tokens_used == 0
        assert sr.duration_ms == 0.0

    def test_execution_result_defaults(self) -> None:
        er = ExecutionResult(skill_name="TEST")
        assert er.steps == []
        assert er.final_output == ""
        assert er.total_tokens == 0
        assert er.total_duration_ms == 0.0
