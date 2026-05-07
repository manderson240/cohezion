# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Team orchestrator: generate Claude Code agent specs and task plans from PRIME skills.

Bridges the internal skill system with Claude Code's team infrastructure
by converting PRIME skill definitions into agent specifications and
dependency-tracked task lists.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.graph.types import WorkflowSpec


logger = logging.getLogger(__name__)


@dataclass
class AgentSpec:
    """Specification for a Claude Code agent."""

    name: str
    description: str
    tools: list[str] = field(
        default_factory=lambda: ["Read", "Glob", "Grep", "Bash", "Edit", "Write"]
    )
    disallowed_tools: list[str] = field(default_factory=list)
    model: str = "sonnet"
    instructions: str = ""
    ollama_model: str | None = None


@dataclass
class TaskSpec:
    """Specification for a single task in a team plan."""

    id: str
    subject: str
    description: str
    assigned_to: str = ""
    blocked_by: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class TeamPlan:
    """A complete team plan with agents and dependency-tracked tasks."""

    name: str
    intent: str
    agents: list[AgentSpec] = field(default_factory=list)
    tasks: list[TaskSpec] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        """Human-readable summary of the plan."""
        lines = [f"Team: {self.name}", f"Intent: {self.intent}", ""]
        lines.append(f"Agents ({len(self.agents)}):")
        for a in self.agents:
            lines.append(f"  - {a.name} ({a.model}): {a.description[:60]}")
        lines.append(f"\nTasks ({len(self.tasks)}):")
        for t in self.tasks:
            blocked = f" [blocked by: {', '.join(t.blocked_by)}]" if t.blocked_by else ""
            lines.append(f"  - [{t.id}] {t.subject}{blocked}")
        return "\n".join(lines)


# Task type -> model mapping for local Ollama routing
_TASK_MODEL_MAP: dict[str, str] = {
    "verify": "phi3:mini",
    "test": "phi3:mini",
    "lint": "phi3:mini",
    "code": "qwen3-coder:30b",
    "implement": "qwen3-coder:30b",
    "refactor": "qwen3-coder:30b",
    "reason": "deepseek-r1:70b",
    "architect": "deepseek-r1:70b",
    "plan": "deepseek-r1:70b",
    "research": "deepseek-r1:70b",
}

# Claude Code model mapping based on task complexity
_CLAUDE_MODEL_MAP: dict[str, str] = {
    "simple": "haiku",
    "moderate": "sonnet",
    "complex": "opus",
}


class TeamOrchestrator:
    """Generate Claude Code agent specs and task plans from PRIME skills.

    Searches the capability registry for matching skills, converts them
    into agent specifications, and produces dependency-tracked task lists.
    """

    def __init__(self) -> None:
        self._registry = None
        self._engine = None

    @property
    def registry(self):
        """Lazy-load the capability registry."""
        if self._registry is None:
            from cohezion.registry.capability_registry import CapabilityRegistry

            self._registry = CapabilityRegistry()
        return self._registry

    @property
    def engine(self):
        """Lazy-load the template engine."""
        if self._engine is None:
            from cohezion.core.template_engine import TemplateEngine

            self._engine = TemplateEngine()
        return self._engine

    def plan_team(self, intent: str, max_agents: int = 4) -> TeamPlan:
        """Search capability registry for matching skills and generate a team plan.

        Parameters
        ----------
        intent : str
            Natural language description of what the team should accomplish.
        max_agents : int
            Maximum number of agents to include in the plan.

        Returns
        -------
        TeamPlan
            Complete plan with agents and dependency-tracked tasks.
        """
        # 1. Search for matching capabilities
        matches = self.registry.find(intent, top_k=max_agents * 2)

        # 2. Separate by type and deduplicate
        skill_matches = [m for m in matches if m.type == "skill"][:max_agents]

        # 3. Generate agent specs
        agents: list[AgentSpec] = []
        for cap in skill_matches[:max_agents]:
            role = self._infer_role(cap.name, cap.tags)
            spec = self.generate_agent_spec_from_capability(cap, role)
            agents.append(spec)

        # 4. Generate task list
        plan = TeamPlan(
            name=self._slugify(intent),
            intent=intent,
            agents=agents,
        )
        plan.tasks = self.generate_task_list(plan)

        # 5. Build dependency map
        plan.dependencies = {t.id: t.blocked_by for t in plan.tasks if t.blocked_by}

        return plan

    def generate_agent_spec(self, skill_name: str, role: str = "implementer") -> AgentSpec:
        """Convert a PRIME skill into a Claude Code agent specification.

        Parameters
        ----------
        skill_name : str
            Name of the PRIME skill to base the agent on.
        role : str
            Agent role: "implementer", "reviewer", "researcher", "tester".

        Returns
        -------
        AgentSpec
            Claude Code compatible agent specification.
        """
        spec = self.engine.get_spec_by_name(skill_name)
        if spec is None:
            # Try parsing all skills first
            self.engine.parse_all()
            spec = self.engine.get_spec_by_name(skill_name)

        if spec is None:
            return AgentSpec(
                name=self._slugify(skill_name),
                description=f"Agent for {skill_name}",
                instructions=f"Work on tasks related to {skill_name}.",
            )

        return self._spec_to_agent(spec, role)

    def generate_agent_spec_from_capability(self, cap, role: str = "implementer") -> AgentSpec:
        """Convert a Capability registry entry into an AgentSpec."""
        # Try to find the underlying skill spec for richer instructions
        skill_spec = self.engine.get_spec_by_name(cap.name)

        if skill_spec:
            return self._spec_to_agent(skill_spec, role)

        # Fallback: build from capability metadata
        tools, disallowed = self._tools_for_role(role)
        model = self._model_for_role(role)

        return AgentSpec(
            name=self._slugify(cap.name),
            description=cap.description[:200],
            tools=tools,
            disallowed_tools=disallowed,
            model=model,
            instructions=f"You are an expert in {cap.description[:100]}. "
            f"Focus on tasks tagged with: {', '.join(cap.tags[:5])}.",
            ollama_model=self._select_ollama_model(cap.tags),
        )

    def generate_task_list(self, plan: TeamPlan) -> list[TaskSpec]:
        """Break a team plan into ordered, dependency-tracked tasks.

        Parameters
        ----------
        plan : TeamPlan
            The team plan containing agents and intent.

        Returns
        -------
        list[TaskSpec]
            Ordered list of tasks with dependencies.
        """
        tasks: list[TaskSpec] = []

        if not plan.agents:
            return tasks

        # Phase 1: Research/planning task (always first)
        tasks.append(
            TaskSpec(
                id="t1",
                subject=f"Research: {plan.intent[:60]}",
                description=f"Explore the codebase to understand existing patterns for: {plan.intent}",
                assigned_to=plan.agents[0].name if plan.agents else "",
                tags=["research"],
            )
        )

        # Phase 2: Implementation tasks (one per agent)
        for i, agent in enumerate(plan.agents):
            task_id = f"t{i + 2}"
            tasks.append(
                TaskSpec(
                    id=task_id,
                    subject=f"Implement: {agent.description[:50]}",
                    description=f"Using {agent.name} skills, implement the component described as: {agent.description}",
                    assigned_to=agent.name,
                    blocked_by=["t1"],
                    tags=["implementation"],
                )
            )

        # Phase 3: Integration test (depends on all implementation tasks)
        impl_ids = [f"t{i + 2}" for i in range(len(plan.agents))]
        tasks.append(
            TaskSpec(
                id=f"t{len(plan.agents) + 2}",
                subject="Integration: Run tests and verify",
                description="Run the full test suite, verify imports, and check for regressions.",
                blocked_by=impl_ids,
                tags=["testing", "verification"],
            )
        )

        return tasks

    def select_model(self, task: TaskSpec) -> str:
        """Route a task to the appropriate local Ollama model.

        Parameters
        ----------
        task : TaskSpec
            Task to route.

        Returns
        -------
        str
            Ollama model name (e.g. "phi3:mini", "qwen3-coder:30b").
        """
        for tag in task.tags:
            tag_lower = tag.lower()
            for key, model in _TASK_MODEL_MAP.items():
                if key in tag_lower:
                    return model

        # Default based on description keywords
        desc_lower = task.description.lower()
        if any(kw in desc_lower for kw in ["test", "verify", "check", "lint"]):
            return "phi3:mini"
        if any(kw in desc_lower for kw in ["implement", "code", "create", "write"]):
            return "qwen3-coder:30b"
        if any(kw in desc_lower for kw in ["design", "architect", "plan", "research"]):
            return "deepseek-r1:70b"

        return "phi3:mini"  # Conservative default

    def _spec_to_agent(self, spec, role: str) -> AgentSpec:
        """Convert a SkillSpec to an AgentSpec."""
        tools, disallowed = self._tools_for_role(role)
        model = self._model_for_role(role)

        # Build instructions from skill spec
        instructions_parts = []
        if spec.domain_expertise:
            instructions_parts.append(spec.domain_expertise[:300])
        if spec.instructions:
            instructions_parts.append("Steps: " + "; ".join(spec.instructions[:5]))

        return AgentSpec(
            name=self._slugify(spec.name),
            description=spec.domain_expertise[:200]
            if spec.domain_expertise
            else f"Agent for {spec.name}",
            tools=tools,
            disallowed_tools=disallowed,
            model=model,
            instructions="\n".join(instructions_parts)
            if instructions_parts
            else f"Expert in {spec.name}.",
            ollama_model=self._select_ollama_model(
                [c.lower() for c in spec.concepts] if spec.concepts else []
            ),
        )

    def _tools_for_role(self, role: str) -> tuple[list[str], list[str]]:
        """Return (allowed_tools, disallowed_tools) for a role."""
        role_tools = {
            "implementer": (
                ["Read", "Glob", "Grep", "Bash", "Edit", "Write"],
                ["NotebookEdit"],
            ),
            "reviewer": (
                ["Read", "Glob", "Grep"],
                ["Bash", "Edit", "Write", "NotebookEdit"],
            ),
            "researcher": (
                ["Read", "Glob", "Grep", "Write"],
                ["Bash", "NotebookEdit"],
            ),
            "tester": (
                ["Bash", "Read", "Glob", "Grep"],
                ["Edit", "Write", "NotebookEdit"],
            ),
        }
        return role_tools.get(role, role_tools["implementer"])

    def _model_for_role(self, role: str) -> str:
        """Return Claude Code model for a role."""
        role_models = {
            "implementer": "sonnet",
            "reviewer": "haiku",
            "researcher": "haiku",
            "tester": "haiku",
        }
        return role_models.get(role, "sonnet")

    def _infer_role(self, name: str, tags: list[str]) -> str:
        """Infer agent role from capability name and tags."""
        name_lower = name.lower()
        tags_str = " ".join(tags).lower()

        if any(kw in name_lower or kw in tags_str for kw in ["test", "verify", "quality"]):
            return "tester"
        if any(kw in name_lower or kw in tags_str for kw in ["review", "audit", "security"]):
            return "reviewer"
        if any(kw in name_lower or kw in tags_str for kw in ["research", "scout", "explore"]):
            return "researcher"
        return "implementer"

    def _select_ollama_model(self, tags: list[str]) -> str | None:
        """Select an Ollama model based on tags."""
        tags_str = " ".join(tags).lower()
        if any(kw in tags_str for kw in ["code", "implement", "engineer"]):
            return "qwen3-coder:30b"
        if any(kw in tags_str for kw in ["reason", "architect", "quantum"]):
            return "deepseek-r1:70b"
        if any(kw in tags_str for kw in ["verify", "test", "lint"]):
            return "phi3:mini"
        return None

    async def execute_team(
        self,
        intent: str,
        max_agents: int = 4,
        auto_feedback: bool = False,
    ) -> object:
        """Plan and execute a team in one call.

        Parameters
        ----------
        intent : str
            Natural language description of the goal.
        max_agents : int
            Maximum agents in the plan.
        auto_feedback : bool
            If ``True``, run a compound feedback cycle after each skill
            execution (requires live Ollama).

        Returns
        -------
        ExecutionReport
            Aggregated execution report.
        """
        plan = self.plan_team(intent, max_agents=max_agents)

        from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator
        from cohezion.swarm.team_execution import TeamCompoundExecutor

        team_executor = TeamCompoundExecutor(auto_feedback=auto_feedback)
        orchestrator = ExecutionOrchestrator(compound_executor=team_executor)
        return await orchestrator.execute(plan)

    def plan_workflow(
        self,
        intent: str,
        max_agents: int = 4,
    ) -> WorkflowSpec:
        """Plan a team and convert to a WorkflowSpec for graph execution.

        Returns a ``WorkflowSpec`` ready for ``WorkflowEngine.execute()``.
        """
        from cohezion.graph.builder import WorkflowBuilder

        plan = self.plan_team(intent, max_agents=max_agents)
        return WorkflowBuilder().from_team_plan(plan)

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a slug suitable for agent/team names."""
        # Remove _PRIME suffix
        text = re.sub(r"_PRIME$", "", text, flags=re.IGNORECASE)
        # Convert to lowercase kebab-case
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
        # Truncate
        return slug[:40] or "agent"
