"""Guardrail pipeline steps for CompoundExecutor.

Input and output validation via guardrail pipeline.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from cohezion.security.guardrail_pipeline import GuardrailAction


if TYPE_CHECKING:
    from cohezion.compound.executor import CompoundExecutor

logger = logging.getLogger(__name__)


def run_async_guardrail(coro: Any) -> Any:
    """Execute async guardrail check in sync context.

    Non-blocking on failure - logs and returns None.

    Args:
        coro: Async coroutine to execute

    Returns:
        Result of coroutine or None on failure
    """
    try:
        return asyncio.run(coro)
    except Exception as e:
        logger.debug(f"Guardrail check failed (non-blocking): {e}")
        return None


def check_input_guardrails(
    executor: "CompoundExecutor",
    task_description: str,
    skill_name: str,
    operation_type: str,
) -> tuple[bool, str, dict[str, Any]]:
    """Step 3: Check input via guardrails.

    Args:
        executor: CompoundExecutor instance
        task_description: Task description
        skill_name: Skill name
        operation_type: Operation type

    Returns:
        Tuple of (should_continue, error_msg, metrics)
    """
    if not executor.guardrail_pipeline:
        return True, "", {}

    guard_context = {
        "skill_name": skill_name,
        "operation_type": operation_type,
        "task_description": task_description,
    }
    input_check = run_async_guardrail(
        executor.guardrail_pipeline.check_input(task_description, guard_context)
    )
    if input_check and input_check.action == GuardrailAction.BLOCK:
        error_msg = f"Input blocked by guardrails: {input_check.reason}"
        metrics = {"error": error_msg, "blocked_by_guardrails": True}
        logger.warning("Task input blocked: %s", input_check.reason)
        return False, error_msg, metrics

    return True, "", {}


def check_output_guardrails(
    executor: "CompoundExecutor",
    output: str,
    skill_name: str,
    operation_type: str,
    task_description: str,
) -> tuple[str, bool, dict[str, Any]]:
    """Step 5: Check output via guardrails.

    Args:
        executor: CompoundExecutor instance
        output: Execution output
        skill_name: Skill name
        operation_type: Operation type
        task_description: Task description

    Returns:
        Tuple of (modified_output, still_successful, metrics_updates)
    """
    if not executor.guardrail_pipeline:
        return output, True, {}

    guard_context = {
        "skill_name": skill_name,
        "operation_type": operation_type,
        "task_description": task_description,
    }
    output_check = run_async_guardrail(
        executor.guardrail_pipeline.check_output(output, guard_context)
    )
    if not output_check:
        return output, True, {}

    if output_check.action == GuardrailAction.BLOCK:
        modified_output = "[Output blocked by content filter]"
        metrics = {"output_blocked_by_guardrails": True}
        logger.warning("Task output blocked: %s", output_check.reason)
        return modified_output, False, metrics

    if output_check.action == GuardrailAction.SANITIZE and output_check.modified_input:
        modified_output = output_check.modified_input
        metrics = {"output_sanitized_by_guardrails": True}
        logger.debug("Task output sanitized")
        return modified_output, True, metrics

    return output, True, {}
