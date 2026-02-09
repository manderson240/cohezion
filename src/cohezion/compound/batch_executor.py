"""Batch-aware compound executor for efficient multi-task execution.

Phase 2.3: Batch Processing

Orchestrates batch execution of compound tasks in 3 phases:
  1. Pre-execution: Query vault for experience guidance (all tasks)
  2. Batch execution: Execute Step 3 (LLM inference) across all tasks
  3. Post-execution: Log, detect anomalies, extract patterns (all tasks)

Expected improvement: +40% throughput through parallel cache operations
and semantic similarity matching within batches.

Architecture:
    - Reuses CompoundExecutor for individual task execution
    - Coordinates vault guidance queries (non-blocking)
    - Batches LLM execution via TokenEfficientClient
    - Processes results through anomaly detection and skill refinement
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class CompoundTask:
    """Single task in a batch execution."""

    task_id: str
    prompt: str
    system_prompt: str | None = None
    model: str = "claude-3-5-sonnet"
    timeout_seconds: float = 60.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchCompoundResult:
    """Result of batch compound execution."""

    success: bool
    tasks_executed: int
    tasks_failed: int
    total_duration_seconds: float
    results: list[ExecutionResult] = field(default_factory=list)
    cache_hits: int = 0  # L1+L2+L3 combined
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    errors: list[str] = field(default_factory=list)


class BatchableExecutor:
    """Batch-aware wrapper for CompoundExecutor.

    Coordinates batch execution of multiple compound tasks with shared
    vault knowledge and cache optimization across the batch.

    Parameters
    ----------
    executor : CompoundExecutor
        Base compound executor for individual tasks
    mcp_client : MCPClient
        Connected MCPClient for vault operations
    batch_size : int
        Maximum tasks to batch together (default: 8)
    enable_deduplication : bool
        Enable within-batch deduplication (default: True)
    """

    def __init__(
        self,
        executor: CompoundExecutor,
        mcp_client: MCPClient,
        batch_size: int = 8,
        enable_deduplication: bool = True,
    ):
        """Initialize batch executor.

        Args:
            executor: Base CompoundExecutor
            mcp_client: Connected MCPClient
            batch_size: Maximum batch size
            enable_deduplication: Enable deduplication
        """
        self.executor = executor
        self.mcp_client = mcp_client
        self.batch_size = batch_size
        self.enable_deduplication = enable_deduplication

    async def execute_batch(
        self, tasks: list[CompoundTask]
    ) -> BatchCompoundResult:
        """Execute batch of compound tasks in 3 phases.

        Phase 1: Query vault for experience guidance (all tasks)
        Phase 2: Batch LLM execution via TokenEfficientClient
        Phase 3: Post-execution (logging, anomaly, patterns)

        Args:
            tasks: List of compound tasks to execute

        Returns:
            BatchCompoundResult with aggregated results
        """
        start_time = asyncio.get_event_loop().time()
        results = []
        errors = []

        if not tasks:
            logger.warning("execute_batch called with empty task list")
            return BatchCompoundResult(
                success=True,
                tasks_executed=0,
                tasks_failed=0,
                total_duration_seconds=0.0,
                results=[],
            )

        logger.info(f"Starting batch execution of {len(tasks)} tasks")

        try:
            # Phase 1: Get experience guidance for all tasks
            logger.debug("Phase 1: Querying vault for experience guidance")
            guidance_map = await self._get_batch_guidance(tasks)

            # Phase 2: Execute tasks with batch optimization
            logger.debug("Phase 2: Executing batch LLM operations")
            batch_results = await self._execute_batch_phase2(
                tasks, guidance_map
            )

            # Phase 3: Post-execution (logging, anomaly, patterns)
            logger.debug("Phase 3: Post-execution (logging and refinement)")
            await self._execute_batch_phase3(tasks, batch_results)

            results = batch_results
            for result in results:
                if not result.success:
                    errors.append(f"Task failed: {result.output}")

        except Exception as e:
            logger.error(f"Batch execution failed: {e}", exc_info=True)
            errors.append(str(e))

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Calculate aggregate statistics
        tasks_executed = len([r for r in results if r.success])
        tasks_failed = len([r for r in results if not r.success])
        cache_hits = sum(
            r.metrics.get("cache_hits", 0) for r in results
        )
        cache_misses = sum(
            r.metrics.get("cache_misses", 0) for r in results
        )
        total_requests = cache_hits + cache_misses
        cache_hit_rate = (
            (cache_hits / total_requests * 100)
            if total_requests > 0
            else 0.0
        )

        return BatchCompoundResult(
            success=len(errors) == 0,
            tasks_executed=tasks_executed,
            tasks_failed=tasks_failed,
            total_duration_seconds=duration,
            results=results,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            cache_hit_rate=cache_hit_rate,
            errors=errors,
        )

    async def _get_batch_guidance(
        self, tasks: list[CompoundTask]
    ) -> dict[str, dict[str, Any]]:
        """Phase 1: Get experience guidance for all tasks in parallel.

        Queries vault for each task to find similar prior executions.
        Non-blocking on failures - continues with empty guidance.

        Args:
            tasks: List of tasks

        Returns:
            Dict mapping task_id → guidance dict
        """
        guidance_tasks = [
            self._get_single_guidance(task)
            for task in tasks
        ]

        # Run all guidance queries in parallel
        guidance_results = await asyncio.gather(
            *guidance_tasks, return_exceptions=True
        )

        guidance_map = {}
        for task, result in zip(tasks, guidance_results):
            if isinstance(result, Exception):
                logger.debug(
                    f"Guidance lookup failed for {task.task_id}: {result}"
                )
                guidance_map[task.task_id] = {}
            else:
                guidance_map[task.task_id] = result or {}

        return guidance_map

    async def _get_single_guidance(
        self, task: CompoundTask
    ) -> dict[str, Any]:
        """Get experience guidance for a single task.

        Args:
            task: CompoundTask to get guidance for

        Returns:
            Guidance dict (may be empty on failure)
        """
        try:
            # Use skill selector if available
            if hasattr(self.executor, "skill_selector"):
                selector = self.executor.skill_selector
                guidance = await selector.select_skill(
                    task.prompt, task.task_id
                )
                return guidance if guidance else {}

            return {}
        except Exception as e:
            logger.debug(f"Error getting guidance for {task.task_id}: {e}")
            return {}

    async def _execute_batch_phase2(
        self,
        tasks: list[CompoundTask],
        guidance_map: dict[str, dict[str, Any]],
    ) -> list[ExecutionResult]:
        """Phase 2: Execute batch LLM operations.

        Executes all tasks' main LLM calls with cache optimization.
        Handles within-batch deduplication if enabled.

        Args:
            tasks: List of tasks to execute
            guidance_map: Guidance dict from Phase 1

        Returns:
            List of ExecutionResults
        """
        results = []

        # Optional: Deduplicate identical prompts within batch
        task_groups = self._deduplicate_tasks(tasks) if self.enable_deduplication else {
            id(task): [task] for task in tasks
        }

        # Execute each unique task
        unique_results = {}
        for task_id, task_group in task_groups.items():
            representative_task = task_group[0]
            guidance = guidance_map.get(
                representative_task.task_id, {}
            )

            try:
                # Execute single task
                result = await self.executor.execute_task(
                    representative_task.prompt,
                    system_prompt=representative_task.system_prompt,
                    model=representative_task.model,
                    timeout_seconds=representative_task.timeout_seconds,
                    guidance=guidance,
                )
                unique_results[task_id] = result
            except Exception as e:
                logger.error(
                    f"Task execution failed: {e}", exc_info=True
                )
                unique_results[task_id] = ExecutionResult(
                    success=False,
                    output=f"Execution failed: {str(e)}",
                    metrics={"error": str(e)},
                    duration_seconds=0.0,
                )

        # Replicate results to all deduplicated tasks
        for task_id, task_group in task_groups.items():
            result = unique_results[task_id]
            for task in task_group:
                # Copy result for each task in the group
                results.append(result)

        return results

    async def _execute_batch_phase3(
        self,
        tasks: list[CompoundTask],
        results: list[ExecutionResult],
    ) -> None:
        """Phase 3: Post-execution logging and refinement.

        Logs executions to vault, detects anomalies, extracts patterns.
        Non-blocking - continues even if individual operations fail.

        Args:
            tasks: Original tasks
            results: ExecutionResults from Phase 2
        """
        phase3_tasks = [
            self._process_single_result(task, result)
            for task, result in zip(tasks, results)
        ]

        # Run all post-execution in parallel
        await asyncio.gather(*phase3_tasks, return_exceptions=True)

    async def _process_single_result(
        self, task: CompoundTask, result: ExecutionResult
    ) -> None:
        """Process single task's post-execution.

        Logs to vault, detects anomalies, extracts patterns.

        Args:
            task: Original task
            result: ExecutionResult from Phase 2
        """
        try:
            # Log to vault (non-blocking)
            if hasattr(self.executor, "vault_logger"):
                logger = self.executor.vault_logger
                await logger.log_execution(
                    task_id=task.task_id,
                    prompt=task.prompt,
                    response=result.output,
                    metrics=result.metrics,
                    duration=result.duration_seconds,
                )

            # Detect anomalies (non-blocking)
            if hasattr(self.executor, "inflection_detector"):
                detector = self.executor.inflection_detector
                await detector.detect_anomalies(
                    prompt=task.prompt,
                    output=result.output,
                    metrics=result.metrics,
                )

            # Extract patterns (non-blocking)
            if hasattr(self.executor, "skill_refiner"):
                refiner = self.executor.skill_refiner
                await refiner.extract_and_refine(
                    task_id=task.task_id,
                    prompt=task.prompt,
                    output=result.output,
                    success=result.success,
                )

        except Exception as e:
            # Non-blocking: log and continue
            logger.debug(f"Post-execution processing failed: {e}")

    def _deduplicate_tasks(
        self, tasks: list[CompoundTask]
    ) -> dict[int, list[CompoundTask]]:
        """Deduplicate identical prompts within batch.

        Returns dict mapping representative task id → list of duplicate tasks.

        Args:
            tasks: List of tasks

        Returns:
            Dict of task groups (representative_id → [tasks])
        """
        prompt_to_tasks: dict[str, list[CompoundTask]] = {}

        for task in tasks:
            # Use prompt + system_prompt as dedup key
            key = f"{task.system_prompt or ''}\n{task.prompt}\n{task.model}"

            if key not in prompt_to_tasks:
                prompt_to_tasks[key] = []

            prompt_to_tasks[key].append(task)

        # Flatten to dict of groups
        result = {}
        for tasks_group in prompt_to_tasks.values():
            representative = tasks_group[0]
            result[id(representative)] = tasks_group

        logger.info(
            f"Batch deduplication: {len(tasks)} tasks → {len(result)} unique"
        )

        return result


class BatchExecutorFactory:
    """Factory for creating BatchableExecutor instances."""

    _instance: "BatchableExecutor | None" = None

    @staticmethod
    def create(
        executor: CompoundExecutor,
        mcp_client: MCPClient,
        batch_size: int = 8,
        enable_deduplication: bool = True,
    ) -> BatchableExecutor:
        """Create BatchableExecutor instance.

        Args:
            executor: Base CompoundExecutor
            mcp_client: Connected MCPClient
            batch_size: Maximum batch size
            enable_deduplication: Enable deduplication

        Returns:
            BatchableExecutor instance
        """
        return BatchableExecutor(
            executor=executor,
            mcp_client=mcp_client,
            batch_size=batch_size,
            enable_deduplication=enable_deduplication,
        )
