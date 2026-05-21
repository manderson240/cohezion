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

from cohezion.compound.batch_sizer import (
    BatchExecutionMetrics,
    get_batch_size_predictor,
)
from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.core.mcp_client import MCPClient, MCPToolError


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
        enable_adaptive_batch_sizing: bool = True,
        api_executor: Any | None = None,
    ):
        """Initialize batch executor.

        Args:
            executor: Base CompoundExecutor
            mcp_client: Connected MCPClient
            batch_size: Maximum batch size (can be overridden by predictor)
            enable_deduplication: Enable deduplication
            enable_adaptive_batch_sizing: Enable experience-guided batch sizing (default: True)
            api_executor: Optional HybridExecutor (or any object with ``batch_execute``).
                When set, Phase 2 routes independent tasks through
                ``api_executor.batch_execute`` instead of individual execute_task
                calls — collapsing N sequential HTTP round-trips into one batch
                submission for the Anthropic path.
        """
        self.executor = executor
        self.mcp_client = mcp_client
        self.initial_batch_size = batch_size
        self.batch_size = batch_size
        self.enable_deduplication = enable_deduplication
        self.enable_adaptive_batch_sizing = enable_adaptive_batch_sizing
        self.api_executor = api_executor  # optional Anthropic batch fast-path

        # Phase 3 Sprint 1: Experience-guided batch sizing
        if enable_adaptive_batch_sizing:
            self.batch_sizer = get_batch_size_predictor()
        else:
            self.batch_sizer = None

    async def execute_batch(self, tasks: list[CompoundTask]) -> BatchCompoundResult:
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

        # Phase 3 Sprint 1: Experience-guided batch sizing
        predicted_batch_size = self.batch_size
        prediction_confidence = 0.0
        if self.batch_sizer and len(tasks) > 1:
            task_types = self._detect_task_types(tasks)
            predicted_batch_size, prediction_confidence = self.batch_sizer.predict_optimal_size(
                task_types[0] if task_types else "unknown", len(tasks)
            )
            self.batch_size = predicted_batch_size
            logger.info(
                f"Batch sizing: predicted size={predicted_batch_size} "
                f"(confidence={prediction_confidence:.2f})"
            )

        try:
            # Phase 1: Get experience guidance for all tasks
            logger.debug("Phase 1: Querying vault for experience guidance")
            guidance_map = await self._get_batch_guidance(tasks)

            # Phase 2: Execute tasks with batch optimization
            logger.debug("Phase 2: Executing batch LLM operations")
            batch_results = await self._execute_batch_phase2(tasks, guidance_map)

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
        cache_hits = sum(r.metrics.get("cache_hits", 0) for r in results)
        cache_misses = sum(r.metrics.get("cache_misses", 0) for r in results)
        total_requests = cache_hits + cache_misses
        cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0.0

        # Phase 3 Sprint 1: Record metrics for batch sizing learning
        if self.batch_sizer and results:
            try:
                throughput = (
                    sum(r.metrics.get("tokens_used", 0) for r in results) / duration
                    if duration > 0
                    else 0.0
                )
                task_types = self._detect_task_types(tasks)
                metrics = BatchExecutionMetrics(
                    batch_size=predicted_batch_size,
                    task_count=len(tasks),
                    task_types=task_types,
                    execution_time=duration,
                    tokens_used=sum(r.metrics.get("tokens_used", 0) for r in results),
                    throughput=throughput,
                    cache_hit_rate=cache_hit_rate / 100.0,
                    errors=tasks_failed,
                )
                self.batch_sizer.record_execution(metrics)
                logger.debug(f"Recorded batch metrics: throughput={throughput:.1f} tok/sec")
            except Exception as e:
                logger.debug(f"Failed to record batch metrics: {e}")

        # Phase 3 Sprint 2: Record thermal metrics for 30-min prediction
        try:
            from cohezion.compound.hardware_monitor import get_hardware_monitor
            from cohezion.compound.thermal_history_persistence import (
                get_thermal_time_series_collector,
            )

            monitor = get_hardware_monitor()
            metrics = monitor.get_current_metrics()
            thermal_collector = get_thermal_time_series_collector()

            thermal_collector.record_batch_thermal(
                batch_size=predicted_batch_size,
                peak_gpu_temp=metrics.gpu_temp_current,
                throttle_detected=monitor.is_thermal_throttling(),
            )
            logger.debug(
                f"Recorded thermal metrics: temp={metrics.gpu_temp_current:.1f}°C, "
                f"batch_size={predicted_batch_size}"
            )
        except Exception as e:
            logger.debug(f"Failed to record thermal metrics (non-blocking): {e}")

        # Phase 3 Sprint 1: Log batch performance to vault for learning feedback
        # Calculate throughput if we have results
        if results:
            total_tokens = sum(r.metrics.get("tokens_used", 0) for r in results)
            throughput = total_tokens / duration if duration > 0 else 0.0
            self._log_batch_performance(
                batch_size=predicted_batch_size,
                task_count=len(tasks),
                throughput=throughput,
                cache_hit_rate=cache_hit_rate,
                execution_time=duration,
                tasks_failed=tasks_failed,
                tasks_executed=tasks_executed,
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

    async def _get_batch_guidance(self, tasks: list[CompoundTask]) -> dict[str, dict[str, Any]]:
        """Phase 1: Get experience guidance for all tasks in parallel.

        Queries vault for each task to find similar prior executions.
        Non-blocking on failures - continues with empty guidance.

        Args:
            tasks: List of tasks

        Returns:
            Dict mapping task_id → guidance dict
        """
        guidance_tasks = [self._get_single_guidance(task) for task in tasks]

        # Run all guidance queries in parallel
        guidance_results = await asyncio.gather(*guidance_tasks, return_exceptions=True)

        guidance_map = {}
        for task, result in zip(tasks, guidance_results, strict=True):
            if isinstance(result, Exception):
                logger.debug(f"Guidance lookup failed for {task.task_id}: {result}")
                guidance_map[task.task_id] = {}
            else:
                guidance_map[task.task_id] = result or {}

        return guidance_map

    async def _get_single_guidance(self, task: CompoundTask) -> dict[str, Any]:
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
                guidance = await selector.select_skill(task.prompt, task.task_id)
                return guidance if guidance else {}

            return {}
        except Exception as e:
            logger.debug(f"Error getting guidance for {task.task_id}: {e}")
            return {}

    def _detect_task_types(self, tasks: list[CompoundTask]) -> list[str]:
        """Detect task types from task metadata or prompt keywords.

        Phase 3 Sprint 1: Task type detection for batch sizing.

        Classifies tasks as:
        - generate: Creative content generation
        - analyze: Analysis and understanding
        - search: Information retrieval
        - transform: Content transformation
        - persist: Data persistence
        - unknown: Unable to classify

        Args:
            tasks: List of tasks to classify

        Returns:
            List of task type strings (one per task)
        """
        task_types = []

        for task in tasks:
            # Check metadata first
            if hasattr(task, "metadata") and "task_type" in task.metadata:
                task_types.append(task.metadata["task_type"])
                continue

            # Fall back to keyword detection in prompt
            prompt_lower = task.prompt.lower()

            if any(
                word in prompt_lower
                for word in ["generate", "create", "write", "compose", "write a"]
            ):
                task_types.append("generate")
            elif any(
                word in prompt_lower
                for word in ["analyze", "analyze", "examine", "review", "evaluate"]
            ):
                task_types.append("analyze")
            elif any(
                word in prompt_lower for word in ["search", "find", "look for", "retrieve", "list"]
            ):
                task_types.append("search")
            elif any(
                word in prompt_lower
                for word in ["transform", "convert", "change", "format", "rewrite"]
            ):
                task_types.append("transform")
            elif any(
                word in prompt_lower for word in ["save", "store", "persist", "record", "store"]
            ):
                task_types.append("persist")
            else:
                task_types.append("unknown")

        return task_types

    async def _execute_batch_phase2(
        self,
        tasks: list[CompoundTask],
        guidance_map: dict[str, dict[str, Any]],
    ) -> list[ExecutionResult]:
        """Phase 2: Execute batch LLM operations.

        Fast path (api_executor set): all unique tasks are submitted as a single
        batch request via HybridExecutor.batch_execute. For the Anthropic provider
        this collapses N sequential HTTP round-trips into one batch submission.

        Fallback path (api_executor is None): retains original sequential
        executor.execute_task loop — no behaviour change for existing callers.

        Args:
            tasks: List of tasks to execute
            guidance_map: Guidance dict from Phase 1

        Returns:
            List of ExecutionResults (one per task, order preserved)
        """
        # Optional: Deduplicate identical prompts within batch
        task_groups = (
            self._deduplicate_tasks(tasks)
            if self.enable_deduplication
            else {id(task): [task] for task in tasks}
        )

        unique_tasks = [group[0] for group in task_groups.values()]

        # ── Anthropic batch fast-path ───────────────────────────────────────
        if self.api_executor is not None and hasattr(self.api_executor, "batch_execute"):
            requests = [
                {
                    "custom_id": str(task_id),
                    "prompt": task.prompt,
                    "system": task.system_prompt,
                    "max_tokens": 1024,
                }
                for task_id, task in zip(task_groups.keys(), unique_tasks, strict=True)
            ]
            try:
                import time as _time

                t0 = _time.monotonic()
                api_results = await self.api_executor.batch_execute(requests)
                elapsed = _time.monotonic() - t0

                id_to_api = {
                    r["custom_id"] if isinstance(r, dict) else str(i): r
                    for i, r in enumerate(api_results)
                }

                unique_results: dict[int, ExecutionResult] = {}
                for task_id, task in zip(task_groups.keys(), unique_tasks, strict=True):
                    api_res = id_to_api.get(str(task_id))
                    if api_res is None:
                        unique_results[task_id] = ExecutionResult(
                            success=False,
                            output="missing from batch response",
                            metrics={"error": "missing"},
                            duration_seconds=elapsed,
                        )
                        continue
                    # Unify dict/APIResult access
                    success = (
                        api_res.success
                        if hasattr(api_res, "success")
                        else api_res.get("success", False)
                    )
                    output = (
                        api_res.output if hasattr(api_res, "output") else api_res.get("output", "")
                    )
                    tokens = (
                        api_res.tokens_used
                        if hasattr(api_res, "tokens_used")
                        else api_res.get("tokens_used", 0)
                    )
                    cost = (
                        api_res.cost_usd
                        if hasattr(api_res, "cost_usd")
                        else api_res.get("cost_usd", 0.0)
                    )
                    cache_read = (
                        getattr(api_res, "cache_read_tokens", None)
                        if not isinstance(api_res, dict)
                        else api_res.get("cache_read_tokens", 0)
                    ) or 0
                    unique_results[task_id] = ExecutionResult(
                        success=success,
                        output=output,
                        metrics={
                            "tokens_used": tokens,
                            "cost_usd": cost,
                            "cache_read_tokens": cache_read,
                            "via": "anthropic_batch",
                        },
                        duration_seconds=elapsed / max(len(unique_tasks), 1),
                    )
                logger.info(
                    "Phase 2 batch fast-path: %d tasks in %.2fs (via api_executor)",
                    len(unique_tasks),
                    elapsed,
                )
            except Exception as exc:
                logger.warning("api_executor.batch_execute failed, falling back: %s", exc)
                unique_results = await self._phase2_sequential(
                    unique_tasks, task_groups, guidance_map
                )
        else:
            # ── Sequential fallback ─────────────────────────────────────────
            unique_results = await self._phase2_sequential(unique_tasks, task_groups, guidance_map)

        # Replicate results to all deduplicated tasks (order preserved)
        results: list[ExecutionResult] = []
        for task_id, task_group in task_groups.items():
            result = unique_results[task_id]
            for _ in task_group:
                results.append(result)

        return results

    async def _phase2_sequential(
        self,
        unique_tasks: list[CompoundTask],
        task_groups: dict[int, list[CompoundTask]],
        guidance_map: dict[str, dict[str, Any]],
    ) -> dict[int, ExecutionResult]:
        """Original sequential execute_task loop (fallback / non-Anthropic path)."""
        unique_results: dict[int, ExecutionResult] = {}
        for task_id, task in zip(task_groups.keys(), unique_tasks, strict=True):
            guidance = guidance_map.get(task.task_id, {})
            try:
                result = await self.executor.execute_task(
                    task.prompt,
                    system_prompt=task.system_prompt,
                    model=task.model,
                    timeout_seconds=task.timeout_seconds,
                    guidance=guidance,
                )
                unique_results[task_id] = result
            except Exception as e:
                logger.error(f"Task execution failed: {e}", exc_info=True)
                unique_results[task_id] = ExecutionResult(
                    success=False,
                    output=f"Execution failed: {e!s}",
                    metrics={"error": str(e)},
                    duration_seconds=0.0,
                )
        return unique_results

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
            for task, result in zip(tasks, results, strict=True)
        ]

        # Run all post-execution in parallel
        await asyncio.gather(*phase3_tasks, return_exceptions=True)

    async def _process_single_result(self, task: CompoundTask, result: ExecutionResult) -> None:
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

    def _deduplicate_tasks(self, tasks: list[CompoundTask]) -> dict[int, list[CompoundTask]]:
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

        logger.info(f"Batch deduplication: {len(tasks)} tasks → {len(result)} unique")

        return result

    def _log_batch_performance(
        self,
        batch_size: int,
        task_count: int,
        throughput: float,
        cache_hit_rate: float,
        execution_time: float,
        tasks_failed: int,
        tasks_executed: int,
    ) -> int:
        """Log batch performance metrics to vault for learning feedback.

        Logs batch execution metrics to vault as an experiment for
        historical analysis and pattern learning. Non-blocking operation
        that doesn't impact execution on failure.

        Parameters
        ----------
        batch_size : int
            Batch size used for execution
        task_count : int
            Total number of tasks in batch
        throughput : float
            Tokens per second achieved
        cache_hit_rate : float
            Cache hit percentage (0-100)
        execution_time : float
            Total execution time in seconds
        tasks_failed : int
            Number of failed tasks
        tasks_executed : int
            Number of successfully executed tasks

        Returns
        -------
        int
            1 if logged successfully, 0 otherwise
        """
        if not self.mcp_client:
            logger.debug("No MCPClient configured, skipping batch performance logging")
            return 0

        try:
            # Format metrics for vault experiment
            hypothesis = f"Batch execution with batch_size={batch_size}, task_count={task_count}"

            method = (
                f"Executed {task_count} tasks in batch with "
                f"deduplication={self.enable_deduplication}, "
                f"adaptive_sizing={self.enable_adaptive_batch_sizing}"
            )

            result = (
                f"Success: {tasks_executed}/{task_count} tasks executed\n"
                f"Failures: {tasks_failed}\n"
                f"Throughput: {throughput:.1f} tokens/sec\n"
                f"Cache Hit Rate: {cache_hit_rate:.1f}%\n"
                f"Execution Time: {execution_time:.2f}s\n"
                f"Average Time per Task: {execution_time / task_count:.3f}s"
            )

            learnings = (
                f"Achieved {throughput:.1f} tok/sec with {cache_hit_rate:.1f}% cache hits. "
                f"Batch size {batch_size} processed {task_count} tasks in {execution_time:.2f}s. "
                f"Success rate: {(tasks_executed / task_count * 100):.1f}%"
            )

            # Log to vault as experiment
            path = self.mcp_client.vault_log_experiment(
                project="cohezion",
                hypothesis=hypothesis,
                method=method,
                result=result,
                learnings=learnings,
                title=f"batch_performance_size{batch_size}_{task_count}tasks",
            )

            logger.debug(
                f"Logged batch performance to vault: "
                f"throughput={throughput:.1f} tok/sec, "
                f"cache_hit={cache_hit_rate:.1f}%, "
                f"path={path}"
            )
            return 1

        except MCPToolError as e:
            # Vault unavailable - non-blocking failure
            logger.debug(f"Vault logging failed (non-blocking): {e}")
            return 0

        except Exception as e:
            # Unexpected error - non-blocking failure
            logger.debug(f"Batch performance logging failed (non-blocking): {e}")
            return 0


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
