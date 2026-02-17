"""Analysis and learning steps for CompoundExecutor.

Anomaly detection, pattern extraction, and skill refinement.
"""

import json
import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.compound.executor import CompoundExecutor
    from cohezion.compound.executor_types import ExecutionResult

logger = logging.getLogger(__name__)


def detect_anomalies(
    executor: "CompoundExecutor",
    result: "ExecutionResult",
    skill_name: str,
    task_description: str,
    project: str,
) -> tuple[dict[str, Any], list[str]]:
    """Step 5: Detect execution anomalies.

    Args:
        executor: CompoundExecutor instance
        result: Temporary execution result
        skill_name: Skill name
        task_description: Task description
        project: Project name

    Returns:
        Tuple of (metrics_updates, decision_paths)
    """
    metrics_updates = {}
    decision_paths = []

    try:
        from cohezion.compound.inflection_detector import Severity

        anomaly = executor.inflection_detector.detect_anomaly(result)
        metrics_updates["anomaly_severity"] = anomaly.severity.value
        metrics_updates["anomaly_score"] = anomaly.score
        logger.debug(
            "Anomaly detection: severity=%s, score=%.2f, issues=%s",
            anomaly.severity.value,
            anomaly.score,
            anomaly.issues,
        )

        if anomaly.severity == Severity.CRITICAL:
            logger.warning(
                "Critical inflection point detected: %s issues",
                len(anomaly.issues),
            )
            try:
                recommendation = (
                    anomaly.recommendations[0]
                    if anomaly.recommendations
                    else "Investigate issues"
                )
                decision_path = executor.log_inflection_point(
                    title=f"Critical anomaly in {skill_name}",
                    context=(
                        f"Task: {task_description}\nIssues: {'; '.join(anomaly.issues)}"
                    ),
                    decision="Re-execution recommended",
                    rationale=f"Quality score {anomaly.score:.2f}, {recommendation}",
                    project=project,
                )
                if decision_path:
                    decision_paths.append(decision_path)
            except Exception as e:
                logger.debug("Failed to log inflection point (non-blocking): %s", e)
    except Exception as e:
        logger.debug("Anomaly detection failed (non-blocking): %s", e, exc_info=True)

    return metrics_updates, decision_paths


def extract_patterns(
    executor: "CompoundExecutor",
    success: bool,
    experiment_path: str,
    skill_name: str,
    operation_type: str,
    task_description: str,
    metrics: dict[str, Any],
) -> list[str]:
    """Step 6: Extract execution patterns to vault.

    Args:
        executor: CompoundExecutor instance
        success: Whether execution succeeded
        experiment_path: Vault experiment path
        skill_name: Skill name
        operation_type: Operation type
        task_description: Task description
        metrics: Execution metrics

    Returns:
        List of decision paths created
    """
    decision_paths = []

    if not success or not experiment_path or executor._degradation_mode:
        return decision_paths

    try:
        pattern_path = executor.logger.extract_execution_pattern(
            source_path=experiment_path,
            pattern_name=f"{skill_name}_{operation_type}_success",
            description=f"Successful execution pattern for {skill_name} "
            f"operation: {operation_type}. "
            f"Task: {task_description[:100]}",
            code_example=f"Result metrics: {json.dumps(metrics, indent=2)}",
            domain="compound-engineering",
        )
        if pattern_path:
            decision_paths.append(pattern_path)
    except Exception as e:
        logger.warning("Failed to extract pattern: %s", e, exc_info=True)

    return decision_paths


def refine_skills(
    executor: "CompoundExecutor",
    success: bool,
    skill_name: str,
    operation_type: str,
    output: str,
    metrics: dict[str, Any],
    duration_seconds: float,
    token_metrics: dict[str, Any] | None,
    decision_paths: list[str],
    should_refine: bool,
) -> list[str]:
    """Step 7: Refine skills based on execution results.

    Args:
        executor: CompoundExecutor instance
        success: Whether execution succeeded
        skill_name: Skill name
        operation_type: Operation type
        output: Execution output
        metrics: Execution metrics
        duration_seconds: Execution duration
        token_metrics: Token usage metrics
        decision_paths: Paths created so far
        should_refine: Whether retrospection allows refinement

    Returns:
        Updated list of decision paths
    """
    if not (success and executor.skill_refiner and should_refine):
        return decision_paths

    try:
        exec_result = {
            "success": success,
            "output": output,
            "metrics": metrics,
            "duration_seconds": duration_seconds,
            "token_metrics": token_metrics,
        }

        refined_path = executor.skill_refiner.refine(
            skill_name=skill_name,
            operation_type=operation_type,
            execution_result=exec_result,
            patterns_extracted=decision_paths,
        )

        if refined_path:
            logger.info(f"Skill refined: {refined_path}")
            decision_paths.append(refined_path)

    except Exception as e:
        logger.debug("Skill refinement failed (non-blocking): %s", e, exc_info=True)

    return decision_paths
