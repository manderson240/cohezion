"""Compound executor — singleton wrapping TokenEfficientClient.

Provides a high-level ``execute_skill()`` method that parses a PRIME
skill, expands its instructions, and runs the resulting plan with
per-operation model routing through the TokenEfficientClient.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.config import CompoundConfig

logger = logging.getLogger(__name__)


@dataclass
class CompoundExecutionResult:
    """Result of a compound skill execution.

    Attributes
    ----------
    skill_name : str
        Name of the executed PRIME skill.
    final_output : str
        Output of the last step.
    steps : list[dict[str, Any]]
        Per-step results with operation, output, tokens, duration, model.
    total_tokens : int
        Sum of tokens across all steps.
    total_duration_ms : float
        Wall-clock time in milliseconds.
    model_usage : dict[str, int]
        Count of calls per model.
    """

    skill_name: str
    final_output: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    model_usage: dict[str, int] = field(default_factory=dict)


class CompoundExecutor:
    """Execute PRIME skills with live Ollama models via TokenEfficientClient.

    Parameters
    ----------
    config : CompoundConfig | None
        Execution configuration. Uses defaults if ``None``.
    token_client : Any | None
        Pre-configured TokenEfficientClient. Created from config if ``None``.
    """

    def __init__(
        self,
        config: CompoundConfig | None = None,
        token_client: Any | None = None,
    ) -> None:
        self.config = config or CompoundConfig()
        self._token_client = token_client

    @property
    def token_client(self) -> Any:
        """Lazy-initialize the TokenEfficientClient."""
        if self._token_client is None:
            from cohezion.swarm.compound_client import create_compound_client

            self._token_client = create_compound_client(
                ollama_host=self.config.ollama_host,
                cache_max_size=self.config.cache_max_size,
            )
        return self._token_client

    async def execute_skill(
        self,
        skill_name: str,
        input_text: str,
        model: str | None = None,
    ) -> CompoundExecutionResult:
        """Parse a PRIME skill, expand instructions, and execute the plan.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive).
        input_text : str
            User-provided input to seed the first step.
        model : str | None
            Override model for all steps. If ``None``, uses per-operation routing.

        Returns
        -------
        CompoundExecutionResult
            Execution results with per-step details.
        """
        from cohezion.core.instruction_expander import InstructionExpander
        from cohezion.core.plan_executor import PlanExecutor
        from cohezion.core.template_engine import TemplateEngine

        t0 = time.monotonic()

        # Parse and expand
        engine = TemplateEngine()
        spec = engine.get_spec_by_name(skill_name)
        if spec is None:
            raise KeyError(f"Skill not found: {skill_name}")

        expander = InstructionExpander()
        plan = expander.expand(spec)

        # Execute with per-operation model routing
        executor = PlanExecutor(token_client=self.token_client)
        steps: list[dict[str, Any]] = []
        model_usage: dict[str, int] = {}
        context = input_text
        total_tokens = 0

        for idx, step in enumerate(plan.steps):
            step_model = model or self.config.model_for_operation(step.operation)
            step_t0 = time.monotonic()

            if step.operation in ("generate", "analyze") and step_model:
                # LLM step with specific model
                prompt = (
                    f"Domain: {plan.domain}\n"
                    f"Task: {step.description}\n"
                    f"Context: {context}"
                )
                try:
                    task_type = "coding" if step.operation == "generate" else "analysis"
                    output = await self.token_client.generate(
                        prompt, model=step_model, task_type=task_type
                    )
                    tokens = max(1, len(output) // 4)
                except Exception:
                    logger.exception("LLM call failed for step %d", idx)
                    output = f"[{step.operation}] {step.description} | input_length={len(context)}"
                    tokens = 0
            elif step.operation == "search":
                output, tokens = executor._run_search(step, context)
            elif step.operation == "transform":
                output, tokens = executor._run_transform(step, context)
            elif step.operation == "persist":
                output, tokens = executor._run_persist(step, context)
            else:
                output = context
                tokens = 0

            elapsed_ms = (time.monotonic() - step_t0) * 1000.0
            total_tokens += tokens

            if step_model:
                model_usage[step_model] = model_usage.get(step_model, 0) + 1

            steps.append(
                {
                    "step_index": idx,
                    "operation": step.operation,
                    "description": step.description,
                    "output": output[:500],  # Truncate for response size
                    "tokens_used": tokens,
                    "duration_ms": round(elapsed_ms, 2),
                    "model": step_model or "",
                }
            )
            context = output

        total_duration = (time.monotonic() - t0) * 1000.0

        logger.info(
            "Compound execution of %s: %d steps, %d tokens, %.1f ms",
            skill_name,
            len(steps),
            total_tokens,
            total_duration,
        )

        return CompoundExecutionResult(
            skill_name=skill_name,
            final_output=context[:1000],
            steps=steps,
            total_tokens=total_tokens,
            total_duration_ms=round(total_duration, 2),
            model_usage=model_usage,
        )


_executor: CompoundExecutor | None = None


def get_executor(config: CompoundConfig | None = None) -> CompoundExecutor:
    """Return the singleton CompoundExecutor.

    Parameters
    ----------
    config : CompoundConfig | None
        Configuration for first-time creation.

    Returns
    -------
    CompoundExecutor
        The shared executor instance.
    """
    global _executor
    if _executor is None:
        _executor = CompoundExecutor(config=config)
    return _executor


def reset_executor() -> None:
    """Reset the singleton (for testing)."""
    global _executor
    _executor = None
