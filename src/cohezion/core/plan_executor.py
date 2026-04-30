"""Plan executor: runs an :class:`ExecutablePlan` step-by-step.

Each step's output is piped as context into the next step. Operations
map to real backends (token_client, capability registry) when available,
falling back to structured placeholders otherwise.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable


if TYPE_CHECKING:
    from cohezion.core.instruction_expander import ExecutablePlan, PlanStep


logger = logging.getLogger(__name__)


@runtime_checkable
class TokenClient(Protocol):
    """Minimal protocol for an LLM token client."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt."""
        ...


@dataclass
class StepResult:
    """Result of executing a single plan step.

    Attributes
    ----------
    step_index : int
        Zero-based index of the step in the plan.
    operation : str
        The operation type that was executed.
    output : str
        Textual output produced by the step.
    tokens_used : int
        Approximate token count consumed (0 for non-LLM steps).
    duration_ms : float
        Wall-clock time in milliseconds.
    """

    step_index: int
    operation: str
    output: str
    tokens_used: int = 0
    duration_ms: float = 0.0


@dataclass
class ExecutionResult:
    """Aggregated result of executing an entire plan.

    Attributes
    ----------
    skill_name : str
        Name of the source PRIME skill.
    steps : list[StepResult]
        Results for each step, in execution order.
    final_output : str
        Output of the last step (or empty if no steps).
    total_tokens : int
        Sum of tokens across all steps.
    total_duration_ms : float
        Sum of durations across all steps.
    """

    skill_name: str
    steps: list[StepResult] = field(default_factory=list)
    final_output: str = ""
    total_tokens: int = 0
    total_duration_ms: float = 0.0


class PlanExecutor:
    """Execute an :class:`ExecutablePlan` step-by-step.

    Parameters
    ----------
    token_client : TokenClient | None
        Optional LLM client for generate/analyze operations.
        If ``None``, those operations return structured placeholders.
    """

    def __init__(self, token_client: TokenClient | None = None) -> None:
        self._token_client = token_client

    async def execute(self, plan: ExecutablePlan, input_text: str) -> ExecutionResult:
        """Execute all steps in *plan* sequentially.

        The output of each step is passed as context to the next.

        Parameters
        ----------
        plan : ExecutablePlan
            The plan to execute.
        input_text : str
            User-provided input to seed the first step.

        Returns
        -------
        ExecutionResult
            Aggregated execution results.
        """
        results: list[StepResult] = []
        context = input_text

        for idx, step in enumerate(plan.steps):
            t0 = time.monotonic()
            output, tokens = await self._run_step(step, context, plan.domain)
            elapsed_ms = (time.monotonic() - t0) * 1000.0

            result = StepResult(
                step_index=idx,
                operation=step.operation,
                output=output,
                tokens_used=tokens,
                duration_ms=round(elapsed_ms, 2),
            )
            results.append(result)
            context = output

        total_tokens = sum(r.tokens_used for r in results)
        total_duration = sum(r.duration_ms for r in results)
        final_output = results[-1].output if results else ""

        logger.info(
            "Executed plan %s: %d steps, %d tokens, %.1f ms",
            plan.skill_name,
            len(results),
            total_tokens,
            total_duration,
        )

        return ExecutionResult(
            skill_name=plan.skill_name,
            steps=results,
            final_output=final_output,
            total_tokens=total_tokens,
            total_duration_ms=round(total_duration, 2),
        )

    async def _run_step(self, step: PlanStep, context: str, domain: str) -> tuple[str, int]:
        """Dispatch a single step to the appropriate handler.

        Returns
        -------
        tuple[str, int]
            (output_text, tokens_used)
        """
        op = step.operation
        if op in ("generate", "analyze"):
            return await self._run_llm(step, context, domain)
        elif op == "search":
            return self._run_search(step, context)
        elif op == "transform":
            return self._run_transform(step, context)
        elif op == "persist":
            return self._run_persist(step, context)
        else:
            logger.warning("Unknown operation %r, passing through", op)
            return context, 0

    async def _run_llm(
        self,
        step: PlanStep,
        context: str,
        domain: str,
        model: str | None = None,
    ) -> tuple[str, int]:
        """Run a generate or analyze step via token_client.

        Parameters
        ----------
        model : str | None
            Override model name for this step. Forwarded to
            ``token_client.generate(model=...)``.
        """
        if self._token_client is not None:
            prompt = f"Domain: {domain}\nTask: {step.description}\nContext: {context}"
            kwargs: dict[str, Any] = {}
            if model:
                kwargs["model"] = model
            try:
                output = await self._token_client.generate(prompt, **kwargs)
                # Rough token estimate: ~4 chars per token
                tokens = max(1, len(output) // 4)
                return output, tokens
            except Exception:
                logger.exception(
                    "Token client failed for step %r; using placeholder",
                    step.description,
                )

        # Placeholder when no client is available
        return (f"[{step.operation}] {step.description} | input_length={len(context)}"), 0

    def _run_search(self, step: PlanStep, context: str) -> tuple[str, int]:
        """Run a search step via CapabilityRegistry if available."""
        try:
            from cohezion.registry.capability_registry import CapabilityRegistry

            registry = CapabilityRegistry()
            results = registry.find(context[:200], top_k=3)
            if results:
                lines = [f"- {cap.name} ({cap.type}): {cap.description[:80]}" for cap in results]
                return "\n".join(lines), 0
        except Exception:
            logger.debug("CapabilityRegistry unavailable; returning input")

        return context, 0

    def _run_transform(self, step: PlanStep, context: str) -> tuple[str, int]:
        """Run a basic text transformation step."""
        # Extract keywords: words 4+ chars, deduplicated
        words = re.findall(r"\b[a-zA-Z]{4,}\b", context)
        unique = list(dict.fromkeys(words))[:20]  # preserve order
        output = (
            f"Transformed ({step.description[:60]}): keywords=[{', '.join(unique)}] | "
            f"length={len(context)}"
        )
        return output, 0

    def _run_persist(self, step: PlanStep, context: str) -> tuple[str, int]:
        """Run a persist step: log the result and return confirmation."""
        logger.info(
            "Persisting result for step %r: %d chars",
            step.description,
            len(context),
        )
        return (f"[persisted] {step.description} | chars={len(context)}"), 0
