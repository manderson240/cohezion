"""Token-efficient compound executor with context separation.

Optimizes for API-level prompt caching by separating static system context
and vault guidance from dynamic task-specific instructions.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.compound.exp_persistence.vault import ExecutionContext


if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


class TokenEfficientCompoundExecutor(CompoundExecutor):
    """Executor that maximizes token efficiency via context separation.

    Separates context into:
    1. Static Prefix: System instructions + Core Context + Vault Guidance
       (Targeted for prompt caching)
    2. Dynamic Suffix: Specific task description + transient state
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._anchored_base_prefix: str | None = None
        self._anchored_overlay: str | None = None
        self._overlay_version: int = 0

    def _get_cacheable_prefix(self, guidance: dict[str, Any]) -> str:
        """Build a static, cacheable prefix for the LLM request.

        Architect: Implements 'Layered Anchoring'. The Base Anchor (Core Rules)
        is immutable to guarantee cache hits. The Versioned Overlay (Vault Guidance)
        can be rotated if new critical intelligence is discovered, balancing
        efficiency with adaptability.
        """
        # 1. Base Anchor (Immutable)
        if not self._anchored_base_prefix:
            prefix_parts = ["# SYSTEM INSTRUCTIONS\n"]
            prefix_parts.append(
                "You are a Cohezion compound engineering agent. "
                "Use the provided context and guidance to execute the task efficiently."
            )
            if self._context_manager.loaded_files:
                prefix_parts.append("\n## CORE CONTEXT")
                for file_path in self._context_manager.loaded_files:
                    try:
                        content = self._context_manager._load_file(file_path)
                        prefix_parts.append(f"\n### {file_path}\n{content}")
                    except Exception as e:
                        logger.debug(f"Failed to load context file {file_path} for prefix: {e}")
            self._anchored_base_prefix = "\n".join(prefix_parts)

        # 2. Versioned Overlay (Semi-Static)
        # In a full implementation, we'd check if `guidance` has radically changed.
        # For now, we establish the pattern.
        if not self._anchored_overlay:
            overlay_parts = []
            relevant_context = guidance.get("relevant_context", [])
            if relevant_context:
                overlay_parts.append(f"\n## EXPERIENCE OVERLAY (v{self._overlay_version})")
                for i, item in enumerate(relevant_context[:3]):
                    overlay_parts.append(f"\n[Pattern {i + 1}]: {item}")
            self._anchored_overlay = "\n".join(overlay_parts)

        return self._anchored_base_prefix + "\n" + self._anchored_overlay

    async def execute_task_efficient(
        self,
        task_description: str,
        skill_name: str,
        operation_type: str,
        execute_fn: Callable[..., Any],
        project: str = "cohezion",
    ) -> ExecutionResult:
        """Execute task with explicit prefix/suffix separation.

        Args:
            task_description: What the task does (becomes dynamic suffix)
            skill_name: Name of the skill
            operation_type: Type of operation
            execute_fn: Async callable(system_stable, system) → (output, metrics).
                The first arg is the stable cacheable prefix (passed as ``system_stable``
                kwarg); the second is the dynamic task-specific portion (passed as
                ``system`` kwarg). When wrapping APILLMExecutor.execute(), pass them
                as ``system_stable=`` and ``system=`` for optimal cache utilisation.
            project: Vault project name

        Returns:
            ExecutionResult with token metrics
        """
        start_seconds = time.time()

        # 1. Standard setup (Context, Logging)
        if not self._context_loaded:
            self.load_execution_context()
            self._context_loaded = True

        ctx = ExecutionContext(
            project=project,
            skill_name=skill_name,
            task_description=task_description,
            operation_type=operation_type,
            start_time=datetime.now(),
            mcp_client=self.mcp_client,
        )
        experiment_path = self.logger.log_execution_start(ctx)

        # 2. Get Guidance
        guidance = self.get_experience_guidance(task_description, project, operation_type)

        # 3. Build cacheable prefix (Anchor it if first run)
        static_prefix = self._get_cacheable_prefix(guidance)

        dynamic_suffix = task_description

        # 4. Execute with separation
        success = False
        output = ""
        metrics = {}
        token_metrics_before = self.token_client.get_metrics() if self.token_client else None

        try:
            # execute_fn receives system_stable (cacheable prefix) and system (dynamic)
            output, metrics = await execute_fn(system_stable=static_prefix, system=dynamic_suffix)
            success = True
        except Exception as e:
            logger.error(f"Efficient task execution failed: {e}", exc_info=True)
            output = f"Error: {e}"
            metrics = {"error": str(e)}

        # 5. Finalize
        token_metrics = None
        if self.token_client:
            token_metrics_after = self.token_client.get_metrics()
            token_metrics = self._compute_token_delta(token_metrics_before, token_metrics_after)

        self.logger.log_execution_result(
            experiment_path=experiment_path,
            success=success,
            output=output,
            metrics=metrics,
        )

        return ExecutionResult(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=time.time() - start_seconds,
            vault_experiment_path=experiment_path,
            token_metrics=token_metrics,
        )
