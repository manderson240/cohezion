"""Experience-guided batch sizing for optimal throughput.

Learns optimal batch sizes from vault history and predicts sizes for new tasks.
Implements Phase 3 Sprint 1: Experience-Guided Batch Sizing (+8% throughput).

Key features:
- In-memory history of recent batch executions
- Task type classification for pattern matching
- Linear regression model for batch_size → throughput correlation
- Vault integration for persistent learning
- Fallback heuristics when no history available
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class BatchExecutionMetrics:
    """Metrics from a batch execution for learning."""

    batch_size: int
    task_count: int
    task_types: list[str]
    execution_time: float  # seconds
    tokens_used: int
    throughput: float  # tokens/sec
    cache_hit_rate: float  # 0-1
    errors: int = 0
    timestamp: str = field(default_factory=lambda: "")

    @property
    def tokens_per_task(self) -> float:
        """Average tokens per task."""
        return self.tokens_used / self.task_count if self.task_count > 0 else 0

    @property
    def primary_task_type(self) -> str:
        """Most common task type in batch."""
        if not self.task_types:
            return "unknown"
        return max(set(self.task_types), key=self.task_types.count)


class BatchSizePredictor:
    """Learns optimal batch sizes from execution history.

    Maintains in-memory history of batch executions and predicts optimal
    batch sizes for new tasks based on:
    - Task type (generate, analyze, search, transform, persist)
    - Batch task count
    - Historical throughput patterns

    Parameters
    ----------
    history_size : int
        Maximum number of execution records to keep in memory (default: 100)
    min_confidence_threshold : float
        Minimum confidence (0-1) required to make prediction (default: 0.5)
    vault_client : optional
        VaultClient for persistent learning (Phase 2)
    """

    # Heuristic batch sizes per task type (fallback when no history)
    DEFAULT_BATCH_SIZES = {
        "generate": 16,  # Slow, token-heavy
        "analyze": 32,  # Medium speed
        "search": 64,  # Fast, low token cost
        "transform": 32,  # Medium speed
        "persist": 48,  # Medium speed
        "unknown": 32,  # Default fallback
    }

    # Expected throughput (tokens/sec) per task type (baseline)
    BASELINE_THROUGHPUT = {
        "generate": 85.0,  # tok/sec
        "analyze": 120.0,
        "search": 150.0,
        "transform": 100.0,
        "persist": 110.0,
        "unknown": 100.0,
    }

    def __init__(
        self,
        history_size: int = 100,
        min_confidence_threshold: float = 0.5,
        vault_client: Any | None = None,
    ) -> None:
        """Initialize batch size predictor."""
        self.history_size = history_size
        self.min_confidence_threshold = min_confidence_threshold
        self.vault_client = vault_client

        # In-memory history: {task_type: [metrics]}
        self.history: dict[str, list[BatchExecutionMetrics]] = {}
        self._last_prediction: tuple[int, float] | None = None  # (size, confidence)

    def record_execution(self, metrics: BatchExecutionMetrics) -> None:
        """Record a batch execution for learning.

        Parameters
        ----------
        metrics : BatchExecutionMetrics
            Metrics from batch execution
        """
        task_type = metrics.primary_task_type

        if task_type not in self.history:
            self.history[task_type] = []

        self.history[task_type].append(metrics)

        # Limit history size (keep most recent)
        if len(self.history[task_type]) > self.history_size:
            self.history[task_type] = self.history[task_type][-self.history_size :]

        logger.debug(
            f"Recorded execution: batch_size={metrics.batch_size} "
            f"throughput={metrics.throughput:.1f} tok/sec "
            f"task_type={task_type}"
        )

    def predict_optimal_size(self, task_type: str, task_count: int) -> tuple[int, float]:
        """Predict optimal batch size for a task.

        Uses historical patterns to recommend batch size. Falls back to
        heuristics if insufficient history.

        Parameters
        ----------
        task_type : str
            Type of task (generate, analyze, search, transform, persist)
        task_count : int
            Total number of tasks to process

        Returns
        -------
        tuple[int, float]
            (recommended_batch_size, confidence_0_to_1)
        """
        if not task_type or task_type not in self.DEFAULT_BATCH_SIZES:
            task_type = "unknown"

        # Get history for this task type
        type_history = self.history.get(task_type, [])

        if not type_history:
            # No history: use heuristic
            size = self.DEFAULT_BATCH_SIZES[task_type]
            confidence = 0.3  # Low confidence for heuristic
            logger.debug(f"No history for {task_type}, using heuristic batch_size={size}")
            self._last_prediction = (size, confidence)
            return size, confidence

        # Analyze historical throughput by batch size
        optimal_size, confidence = self._find_optimal_from_history(type_history, task_count, task_type)

        self._last_prediction = (optimal_size, confidence)
        return optimal_size, confidence

    def _find_optimal_from_history(
        self,
        history: list[BatchExecutionMetrics],
        task_count: int,
        task_type: str,
    ) -> tuple[int, float]:
        """Find optimal batch size from historical data.

        Simple strategy:
        1. Group by batch size
        2. Calculate average throughput per size
        3. Find size with highest throughput
        4. Adjust for task_count if needed

        Parameters
        ----------
        history : list[BatchExecutionMetrics]
            Historical execution data
        task_count : int
            Number of tasks to process
        task_type : str
            Task type for fallback

        Returns
        -------
        tuple[int, float]
            (optimal_batch_size, confidence)
        """
        if not history:
            size = self.DEFAULT_BATCH_SIZES[task_type]
            return size, 0.3

        # Group by batch size
        size_groups: dict[int, list[float]] = {}
        for metrics in history:
            if metrics.batch_size not in size_groups:
                size_groups[metrics.batch_size] = []
            size_groups[metrics.batch_size].append(metrics.throughput)

        # Calculate average throughput per batch size
        size_throughput = {size: sum(values) / len(values) for size, values in size_groups.items()}

        # Find optimal size (highest throughput)
        if not size_throughput:
            size = self.DEFAULT_BATCH_SIZES[task_type]
            return size, 0.3

        optimal_size = max(size_throughput, key=size_throughput.get)
        max_throughput = size_throughput[optimal_size]

        # Calculate confidence based on:
        # 1. Number of samples for this batch size
        # 2. Consistency (variance) of throughput
        num_samples = len(size_groups[optimal_size])
        confidence = min(
            0.95,  # Cap at 95%
            0.5 + (num_samples / 20.0) * 0.3,  # More samples = higher confidence
        )

        # Variance penalty: if very inconsistent, lower confidence
        if num_samples > 1:
            throughputs = size_groups[optimal_size]
            variance = sum((t - max_throughput) ** 2 for t in throughputs) / len(throughputs)
            variance_penalty = min(0.2, variance / max_throughput)
            confidence -= variance_penalty

        logger.debug(
            f"Found optimal batch_size={optimal_size} for {task_type} "
            f"(throughput={max_throughput:.1f} tok/sec, confidence={confidence:.2f})"
        )

        return optimal_size, max(0.3, confidence)

    def get_confidence(self) -> float:
        """Get confidence of last prediction.

        Returns
        -------
        float
            Confidence from 0-1
        """
        if self._last_prediction is None:
            return 0.0
        return self._last_prediction[1]

    def get_stats(self) -> dict[str, Any]:
        """Get batch sizer statistics.

        Returns
        -------
        dict[str, Any]
            Statistics about learning history
        """
        total_records = sum(len(v) for v in self.history.values())

        return {
            "task_types_learned": list(self.history.keys()),
            "total_records": total_records,
            "history_per_type": {k: len(v) for k, v in self.history.items()},
            "last_prediction": self._last_prediction,
        }

    def learn_from_vault(self, project: str = "cohezion") -> int:
        """Query vault for historical batch execution metrics and learn patterns.

        Searches the vault for batch performance experiment records and loads
        historical performance data for throughput optimization. Non-blocking
        operation that gracefully handles vault connection failures.

        Parameters
        ----------
        project : str
            Project name to search for (default: "cohezion")

        Returns
        -------
        int
            Number of metrics loaded from vault (0 if vault unavailable)
        """
        if not self.vault_client:
            logger.debug("No vault client configured, skipping vault learning")
            return 0

        try:
            # Query vault for batch execution patterns
            results = self.vault_client.vault_search("batch_size throughput execution metrics", scope="all")

            if not results:
                logger.debug("No batch performance metrics found in vault")
                return 0

            loaded_count = 0
            for result in results:
                try:
                    path = result.get("path", "")
                    if not path.endswith(".md"):
                        continue

                    # Read full content from vault
                    content = self.vault_client.vault_read(path)

                    # Parse metrics from content
                    metrics = self._parse_batch_metrics(content)
                    if metrics:
                        self.record_execution(metrics)
                        loaded_count += 1

                except Exception as e:
                    # Non-blocking: skip problematic entries
                    logger.debug(f"Failed to load batch metrics from {path}: {e}")
                    continue

            logger.info(f"Loaded {loaded_count} batch execution metrics from vault")
            return loaded_count

        except Exception as e:
            # Non-blocking: vault unavailable, continue with in-memory history
            logger.debug(f"Vault learning failed (non-blocking): {e}")
            return 0

    def _parse_batch_metrics(self, content: str) -> BatchExecutionMetrics | None:
        """Parse batch execution metrics from vault experiment markdown.

        Extracts metrics from YAML front matter or structured markdown format.
        Handles multiple content formats for robustness.

        Parameters
        ----------
        content : str
            Vault experiment content in markdown

        Returns
        -------
        Optional[BatchExecutionMetrics]
            Parsed metrics if valid, None otherwise
        """
        try:
            # Try to extract YAML front matter
            if content.startswith("---"):
                # Split by --- to get front matter
                parts = content.split("---", 3)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    # Simple YAML parsing for our fields
                    metrics = self._parse_yaml_metrics(yaml_content)
                    if metrics:
                        return metrics

            # Try to extract JSON block (some experiments use JSON)
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return self._dict_to_metrics(data)
                except json.JSONDecodeError:
                    pass

            # Try to extract structured fields from markdown
            metrics = self._parse_markdown_fields(content)
            if metrics:
                return metrics

            return None

        except Exception as e:
            logger.debug(f"Error parsing batch metrics: {e}")
            return None

    def _parse_yaml_metrics(self, yaml_content: str) -> BatchExecutionMetrics | None:
        """Parse metrics from YAML front matter.

        Parameters
        ----------
        yaml_content : str
            YAML content from front matter

        Returns
        -------
        Optional[BatchExecutionMetrics]
            Parsed metrics if valid, None otherwise
        """
        try:
            data = {}

            # Simple YAML parsing (key: value format)
            for line in yaml_content.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()

                    # Convert types as needed
                    if key in ["batch_size", "task_count", "tokens_used", "errors"]:
                        data[key] = int(value)
                    elif key in ["throughput", "cache_hit_rate", "execution_time"]:
                        data[key] = float(value)
                    elif key == "task_types":
                        # Parse comma-separated task types
                        data[key] = [t.strip() for t in value.split(",")]
                    elif key == "timestamp":
                        data[key] = value
                    else:
                        data[key] = value

            return self._dict_to_metrics(data)

        except Exception as e:
            logger.debug(f"Error parsing YAML metrics: {e}")
            return None

    def _parse_markdown_fields(self, content: str) -> BatchExecutionMetrics | None:
        """Parse metrics from structured markdown fields.

        Looks for patterns like:
        - **batch_size**: 8
        - throughput: 45.3 tokens/sec
        - task_types: [analyze, transform]

        Parameters
        ----------
        content : str
            Markdown content

        Returns
        -------
        Optional[BatchExecutionMetrics]
            Parsed metrics if valid, None otherwise
        """
        try:
            data = {}

            # Extract field patterns (handles ** markers and various formats)
            patterns = {
                "batch_size": r"\*?\*?batch[_\s]*size\*?\*?[:\s]*(\d+)",
                "task_count": r"\*?\*?task[_\s]*count\*?\*?[:\s]*(\d+)",
                "execution_time": r"\*?\*?execution[_\s]*time\*?\*?[:\s]*([\d.]+)",
                "tokens_used": r"\*?\*?tokens[_\s]*used\*?\*?[:\s]*(\d+)",
                "throughput": r"\*?\*?throughput\*?\*?[:\s]*([\d.]+)",
                "cache_hit_rate": r"\*?\*?cache[_\s]*hit[_\s]*rate\*?\*?[:\s]*([\d.]+)",
                "errors": r"\*?\*?errors\*?\*?[:\s]*(\d+)",
            }

            for field, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    if field in ["batch_size", "task_count", "tokens_used", "errors"]:
                        data[field] = int(value)
                    else:
                        data[field] = float(value)

            # Extract task_types - handle various formats
            # Patterns: [analyze, search], "analyze, search", or just text
            task_types_match = re.search(r"task[_\s]*types?[:\s]*\[([^\]]+)\]", content, re.IGNORECASE)
            if task_types_match:
                types_str = task_types_match.group(1)
                data["task_types"] = [t.strip().strip("\"'") for t in types_str.split(",")]
            else:
                # Try alternative format without brackets
                task_types_alt = re.search(r"task[_\s]*types?[:\s]*([^\n]+?)(?:\n|$)", content, re.IGNORECASE)
                if task_types_alt:
                    types_str = task_types_alt.group(1).strip()
                    # Handle comma-separated or space-separated
                    if "," in types_str:
                        data["task_types"] = [t.strip().strip("\"'") for t in types_str.split(",")]
                    else:
                        data["task_types"] = [types_str.strip("\"'")]
                else:
                    # Default to unknown if not specified
                    data["task_types"] = ["unknown"]

            # Extract timestamp
            timestamp_match = re.search(r"timestamp[:\s]*([^\n]+)", content, re.IGNORECASE)
            if timestamp_match:
                data["timestamp"] = timestamp_match.group(1).strip()

            return self._dict_to_metrics(data)

        except Exception as e:
            logger.debug(f"Error parsing markdown fields: {e}")
            return None

    def _dict_to_metrics(self, data: dict[str, Any]) -> BatchExecutionMetrics | None:
        """Convert dictionary to BatchExecutionMetrics.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary with metrics fields

        Returns
        -------
        Optional[BatchExecutionMetrics]
            Parsed metrics if all required fields present, None otherwise
        """
        try:
            # Check required fields
            required = {"batch_size", "task_count", "throughput", "execution_time"}
            if not required.issubset(data.keys()):
                missing = required - set(data.keys())
                logger.debug(f"Missing required fields for metrics: {missing}")
                return None

            return BatchExecutionMetrics(
                batch_size=int(data["batch_size"]),
                task_count=int(data["task_count"]),
                task_types=data.get("task_types", ["unknown"]),
                execution_time=float(data["execution_time"]),
                tokens_used=int(data.get("tokens_used", 0)),
                throughput=float(data["throughput"]),
                cache_hit_rate=float(data.get("cache_hit_rate", 0.0)),
                errors=int(data.get("errors", 0)),
                timestamp=data.get("timestamp", ""),
            )

        except (KeyError, ValueError, TypeError) as e:
            logger.debug(f"Error converting dict to metrics: {e}")
            return None


def get_batch_size_predictor(reset: bool = False) -> BatchSizePredictor:
    """Get or create singleton batch size predictor.

    Parameters
    ----------
    reset : bool
        If True, create new instance (default: False)

    Returns
    -------
    BatchSizePredictor
        Singleton instance
    """
    global _predictor_instance

    if reset or _predictor_instance is None:
        _predictor_instance = BatchSizePredictor()

    return _predictor_instance


# Module-level singleton
_predictor_instance: BatchSizePredictor | None = None


__all__ = [
    "BatchExecutionMetrics",
    "BatchSizePredictor",
    "get_batch_size_predictor",
]
