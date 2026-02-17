"""Monitoring and metrics collection steps for CompoundExecutor.

Degradation detection, quality classification, metrics recording, and journey tracking.
"""

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.compound.executor import CompoundExecutor
    from cohezion.compound.executor_types import ExecutionResult

logger = logging.getLogger(__name__)


def check_degradation(
    executor: "CompoundExecutor",
    coherence_val: float,
    duration_seconds: float,
    success: bool,
    token_metrics: dict[str, Any] | None,
    task_description: str,
    project: str,
) -> tuple[dict[str, Any], list[str], bool]:
    """Step 7.5: Check for degradation and manage HIHO band.

    Args:
        executor: CompoundExecutor instance
        coherence_val: Computed coherence value
        duration_seconds: Execution duration
        success: Whether execution succeeded
        token_metrics: Token usage metrics
        task_description: Task description
        project: Project name

    Returns:
        Tuple of (metrics_updates, decision_paths, degradation_mode_flag)
    """
    metrics_updates = {}
    decision_paths = []
    degradation_mode = executor._degradation_mode

    if 0.4 <= coherence_val <= 0.6 and degradation_mode:
        logger.info(
            "Cohesion returned to HIHO band (%.2f), exiting degradation mode",
            coherence_val,
        )
        degradation_mode = False

    if not executor._degradation_detector:
        return metrics_updates, decision_paths, degradation_mode

    try:
        degradation_metrics = {
            "combined_hit_rate": 0.0,
            "tokens_per_second": 0.0,
            "mean_coherence": coherence_val,
            "elapsed_seconds": duration_seconds,
            "success_rate": 1.0 if success else 0.0,
        }
        if token_metrics:
            degradation_metrics["combined_hit_rate"] = token_metrics.get(
                "cache_hit_rate", token_metrics.get("combined_hit_rate", 0.0)
            )
            degradation_metrics["tokens_per_second"] = token_metrics.get(
                "tokens_per_second", 0.0
            )

        alerts = executor._degradation_detector.check_degradation(degradation_metrics)
        if alerts:
            metrics_updates["degradation_alerts"] = len(alerts)
            for alert in alerts:
                logger.warning(
                    "Degradation alert [%s]: %s",
                    alert.severity.value,
                    alert.message,
                )

            critical_alerts = [a for a in alerts if a.severity.value == "CRITICAL"]
            if critical_alerts:
                degradation_mode = True
                metrics_updates["execution_degraded"] = True
                logger.warning(
                    "Entering degradation mode: %d CRITICAL alerts, "
                    "cohesion=%.2f outside HIHO band",
                    len(critical_alerts),
                    coherence_val,
                )

            for alert in critical_alerts:
                try:
                    dp = executor.log_inflection_point(
                        title=f"Degradation: {alert.metric}",
                        context=f"Task: {task_description}\n{alert.message}",
                        decision="Investigate degradation",
                        rationale=f"Current: {alert.current_value:.3f}, "
                        f"Baseline: {alert.baseline_value:.3f}, "
                        f"Threshold: {alert.threshold:.3f}",
                        project=project,
                    )
                    if dp:
                        decision_paths.append(dp)
                except Exception as e:
                    logger.debug(
                        "Failed to log degradation alert (non-blocking): %s",
                        e,
                    )
    except Exception as e:
        logger.debug("Degradation detection failed (non-blocking): %s", e)

    return metrics_updates, decision_paths, degradation_mode


def record_model_quality(
    executor: "CompoundExecutor",
    token_metrics: dict[str, Any] | None,
    coherence: float,
    success: bool,
    duration_seconds: float,
) -> None:
    """Step 7.7: Record model quality metrics.

    Args:
        executor: CompoundExecutor instance
        token_metrics: Token usage metrics
        coherence: Computed coherence value
        success: Whether execution succeeded
        duration_seconds: Execution duration
    """
    if not executor._model_quality_classifier:
        return

    try:
        model_name = "unknown"
        tokens_used = 0
        if token_metrics:
            model_name = token_metrics.get("model", "unknown")
            tokens_used = token_metrics.get("tokens_used", 0)

        executor._model_quality_classifier.add_execution(
            model=model_name,
            coherence=coherence,
            success=success,
            tokens_used=tokens_used,
            duration=duration_seconds,
        )
    except Exception as e:
        logger.debug("Model quality recording failed (non-blocking): %s", e)


def record_metrics(
    executor: "CompoundExecutor",
    skill_name: str,
    success: bool,
    token_metrics: dict[str, Any] | None,
    duration_seconds: float,
) -> None:
    """Step 8: Record execution metrics.

    Args:
        executor: CompoundExecutor instance
        skill_name: Skill name
        success: Whether execution succeeded
        token_metrics: Token usage metrics
        duration_seconds: Execution duration
    """
    if not executor._metrics_collector:
        return

    try:
        tokens_used = 0
        model_used = ""
        if token_metrics:
            tokens_used = token_metrics.get("tokens_used", 0)
            model_used = token_metrics.get("model", "")

        executor._metrics_collector.record_execution(
            skill_name=skill_name,
            success=success,
            tokens_used=tokens_used,
            duration_ms=duration_seconds * 1000,
            model_used=model_used,
        )
    except Exception as e:
        logger.debug("Metrics recording failed (non-blocking): %s", e)


def track_journey(
    executor: "CompoundExecutor",
    result: "ExecutionResult",
    task_description: str,
    operation_type: str,
) -> tuple[bool, dict[str, Any]]:
    """Step 9: Track journey through 12D FLUME space.

    Args:
        executor: CompoundExecutor instance
        result: Execution result
        task_description: Task description
        operation_type: Operation type

    Returns:
        Tuple of (point_tracked, metrics_updates)
    """
    metrics_updates = {}
    point_tracked = False

    if not executor._journey_tracker:
        return point_tracked, metrics_updates

    try:
        point = executor._journey_tracker.track_execution(
            result, task_description, operation_type
        )
        point_tracked = True

        if point and point.metadata:
            metrics_updates["phi_score"] = point.metadata.get("phi_score", 0.0)

        if executor._journey_persistence and point:
            try:
                point_data = {
                    "coherence": point.coherence,
                    "efficiency": point.efficiency,
                    "operation_type": point.operation_type,
                    "task_description": point.task_description[:200],
                    "timestamp": point.timestamp,
                }
                if point.metadata:
                    point_data["metadata"] = point.metadata

                exec_id = f"exec_{int(time.time())}"
                try:
                    asyncio.get_running_loop()
                    _task = asyncio.ensure_future(  # noqa: RUF006
                        executor._journey_persistence.save_trajectory_point(
                            exec_id,
                            point_data,
                        )
                    )
                except RuntimeError:
                    asyncio.run(
                        executor._journey_persistence.save_trajectory_point(
                            exec_id,
                            point_data,
                        )
                    )
            except Exception as e:
                logger.debug("Journey persistence failed (non-blocking): %s", e)
    except Exception as e:
        logger.debug("Journey tracking failed (non-blocking): %s", e)

    return point_tracked, metrics_updates
