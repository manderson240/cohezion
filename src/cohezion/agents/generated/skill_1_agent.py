# Generated from SKILL_1_PRIME v1.0 at 2026-03-27T07:47:38
"""Auto-generated executable agent for SKILL_1_PRIME."""

from __future__ import annotations

from typing import Any

from cohezion.core.instruction_expander import ExecutablePlan, PlanStep
from cohezion.core.plan_executor import ExecutionResult, PlanExecutor


_PLAN = ExecutablePlan(
    skill_name="SKILL_1_PRIME",
    steps=[
        PlanStep(operation="search", params={'search_type': 'capability'}, description="Search for items in category 1"),
        PlanStep(operation="generate", params={}, description="Generate a summary"),
    ],
    domain="Domain for skill 1.",
)


class Skill1Agent:
    """Executable agent for SKILL_1_PRIME.

    Domain: Domain for skill 1.
    Version: 1.0
    """

    SYSTEM_PROMPT = "Domain for skill 1."

    def __init__(self, token_client: Any | None = None) -> None:
        self._token_client = token_client

    async def process(self, input_text: str, **kwargs: Any) -> ExecutionResult:
        """Process input by executing the pre-expanded plan."""
        executor = PlanExecutor(token_client=self._token_client)
        return await executor.execute(_PLAN, input_text)
