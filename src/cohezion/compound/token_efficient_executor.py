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
from cohezion.compound.prompt_optimizer import PromptOptimizer


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
        self._prompt_optimizer = PromptOptimizer()
        self._active_task_description: str | None = None
        self._last_task_description: str | None = None
        # Card alignment: set by caller before execute_task_efficient so prefix
        # carries correct model_id + family + thinking_mode. None = unset.
        self._current_card: tuple[str, str, str] | None = None

    def _get_cacheable_prefix(self, guidance: dict[str, Any]) -> str:
        """Build a static, cacheable prefix for the LLM request.

        Architect: Implements 'Layered Anchoring'. The Base Anchor (Core Rules)
        is immutable to guarantee cache hits. The Versioned Overlay (Vault Guidance)
        can be rotated if new critical intelligence is discovered, balancing
        efficiency with adaptability.

        PR 3 (datamesh-native): the prefix now also includes a
        `# CARD-ALIGNED RECIPE` block with the model's
        (model_id, family, thinking_mode) plus a `# FLUME_VAE: <hash>`
        line. A card change produces a different hash, which
        invalidates the Anthropic prompt cache automatically.
        """
        # If the task description changed, clear the anchored base prefix to recalculate
        if self._last_task_description != self._active_task_description:
            self._anchored_base_prefix = None
            self._last_task_description = self._active_task_description

        # 1. Base Anchor (Immutable for a given task)
        if not self._anchored_base_prefix:
            prefix_parts = ["# SYSTEM INSTRUCTIONS\n"]
            prefix_parts.append(
                "You are a Cohezion compound engineering agent. "
                "Use the provided context and guidance to execute the task efficiently."
            )
            if self._context_manager.loaded_files:
                prefix_parts.append("\n## CORE CONTEXT")
                seen_word_sets: list[set[str]] = []
                for file_path in self._context_manager.loaded_files:
                    try:
                        content = self._context_manager._load_file(file_path)
                        # Dynamically prune redundant and task-irrelevant rules
                        content, seen_word_sets = self._prompt_optimizer.prune_rules(
                            content, self._active_task_description, seen_word_sets
                        )
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

        # 3. PR 3: card-aligned recipe block. The block is part of the
        # static prefix, so the Anthropic prompt cache keys on it.
        # A card change → different block → cache miss (correctly).
        card = getattr(self, "_current_card", None)
        recipe_block = self._render_card_recipe_block(card)

        return self._anchored_base_prefix + "\n" + self._anchored_overlay + recipe_block

    @staticmethod
    def _render_card_recipe_block(card: tuple[str, str, str] | None) -> str:
        """Render the `# CARD-ALIGNED RECIPE` block for the prefix.

        Includes a `# FLUME_VAE: <hash>` line so the Anthropic prompt
        cache's server-side fingerprint is reproducible from a
        SurrealDB row. A card change → different hash → cache miss.
        """
        import hashlib

        if card is None:
            return (
                "\n# CARD-ALIGNED RECIPE\n"
                "# model: <unset>\n"
                "# family: <unset>\n"
                "# thinking_mode: <unset>\n"
                "# FLUME_VAE: 0000000000000000\n"
            )
        model_id, family, thinking_mode = card
        # The FLUME_VAE hash is sha256(card) prefixed — a stable
        # 16-char digest. In production this would be a real VAE
        # embedding of the card text; sha256 is the deterministic
        # fallback.
        h = hashlib.sha256(f"{model_id}|{family}|{thinking_mode}".encode()).hexdigest()[:16]
        return (
            "\n# CARD-ALIGNED RECIPE\n"
            f"# model: {model_id}\n"
            f"# family: {family}\n"
            f"# thinking_mode: {thinking_mode}\n"
            f"# FLUME_VAE: {h}\n"
        )

    def _emit_prefix_hit_witness_mark(self, model_id: str, task: str) -> None:
        """Connection A: emit a WITNESS_MARK with coherence=0.8 on
        Anthropic prompt cache hit. Higher than the 0.6 used for
        normal executions because a prefix cache hit means the
        entire system message was cached, which is the strongest
        coherence signal we have.
        """
        try:
            from cohezion.precipitation import bus
            from cohezion.precipitation.events import (
                PrecipitationEvent,
                PrecipitationKind,
            )

            event = PrecipitationEvent(
                kind=PrecipitationKind.WITNESS_MARK,
                universe_id="cohezion_compound_executor",
                coherence=0.8,
                twelve_d={
                    "x": 0.5,
                    "y": 0.5,
                    "z": 0.5,
                    "time": 0.5,
                    "physics": 0.5,
                    "biology": 0.5,
                    "logic": 0.5,
                    "quantum": 0.5,
                    "field": 0.5,
                    "control": 0.5,
                    "novelty": 0.5,
                    "precipitation": 0.5,
                },
                payload={
                    "source": "compound.executor.prefix_hit",
                    "model_id": model_id,
                    "task": task[:200],
                },
            )
            bus.emit(event)
        except Exception as e:
            logger.debug("Prefix-hit WITNESS_MARK failed (non-blocking): %s", e)

    async def execute_task_efficient(
        self,
        task_description: str,
        skill_name: str,
        operation_type: str,
        execute_fn: Callable[[str, str], Any],
        project: str = "cohezion",
    ) -> ExecutionResult:
        """Execute task with explicit prefix/suffix separation.

        Args:
            task_description: What the task does (becomes dynamic suffix)
            skill_name: Name of the skill
            operation_type: Type of operation
            execute_fn: Async callable that takes (prefix, suffix)
            project: Vault project name

        Returns:
            ExecutionResult with token metrics
        """
        start_seconds = time.time()
        self._active_task_description = task_description

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
            # Note: execute_fn must be async and accept (prefix, suffix)
            output, metrics = await execute_fn(static_prefix, dynamic_suffix)
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
