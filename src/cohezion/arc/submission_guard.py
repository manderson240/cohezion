"""AutoHarness Zero-Cost Submission Guard for ARC Prize 2026 (ARC-AGI-2).

Prevents silent 0.00 submission scores (Kaggle Topic 704408) by enforcing:
1. Dynamic Dataset & Asset Path Resolution with fail-loud diagnostics.
2. Complete Task & Prediction Coverage invariants before submission generation.
3. Strict Grid Rectangularity, Dimension Bounds (1..30), and Color Range (0..9).
4. Zero-Cost Deterministic Fallback Generation on worker failure or timeout.
5. Atomic disk writes to prevent truncated submission files.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ARC Invariant Constants
MIN_GRID_DIM = 1
MAX_GRID_DIM = 30
VALID_COLORS = set(range(10))


class DatasetPathResolutionError(FileNotFoundError):
    """Raised when critical competition input datasets or weights cannot be resolved."""
    pass


class SubmissionInvariantViolationError(ValueError):
    """Raised when submission dictionary violates structural or completeness invariants."""
    pass


class DynamicPathResolver:
    """Dynamically locates competition datasets, LoRA weights, and tokenizers."""

    DEFAULT_KAGGLE_INPUT = Path("/kaggle/input")
    DEFAULT_LOCAL_INPUT = Path("data/arc-agi-2")
    FALLBACK_SEARCH_ROOTS = [
        Path("/kaggle/input"),
        Path("data/arc-agi-2"),
        Path("data/arc"),
        Path("data"),
        Path("."),
    ]

    @classmethod
    def resolve_challenges_file(cls, explicit_path: str | Path | None = None) -> Path:
        """Finds arc-agi_test_challenges.json across dynamic Kaggle directories."""
        if explicit_path:
            p = Path(explicit_path)
            if p.is_file():
                return p.resolve()
            if p.is_dir():
                found = cls._search_dir(p, ["*test_challenges*.json", "*challenges*.json", "test*.json"])
                if found:
                    return found

        # Search standard search roots
        for root in cls.FALLBACK_SEARCH_ROOTS:
            if root.exists():
                found = cls._search_dir(root, ["*test_challenges*.json", "*challenges*.json", "test*.json"])
                if found:
                    logger.info("DynamicPathResolver: Resolved challenges file to '%s'", found)
                    return found

        # Fail loud with full environment inventory
        available_dirs = []
        if cls.DEFAULT_KAGGLE_INPUT.exists():
            try:
                available_dirs = [str(p) for p in cls.DEFAULT_KAGGLE_INPUT.iterdir()]
            except Exception:
                pass

        raise DatasetPathResolutionError(
            f"FATAL: Unable to resolve ARC test challenges JSON file!\n"
            f"Explicit path checked: {explicit_path}\n"
            f"Roots searched: {[str(r) for r in cls.FALLBACK_SEARCH_ROOTS if r.exists()]}\n"
            f"Available /kaggle/input contents: {available_dirs}\n"
            f"Action: Verify Kaggle dataset attachment name and version."
        )

    @classmethod
    def resolve_weights_dir(cls, model_name_or_pattern: str, explicit_path: str | Path | None = None) -> Path:
        """Resolves directory containing LoRA weights or model checkpoints."""
        if explicit_path:
            p = Path(explicit_path)
            if p.exists():
                return p.resolve()

        patterns = [f"*{model_name_or_pattern}*", "*lora*", "*checkpoint*", "*sft139*"]
        for root in cls.FALLBACK_SEARCH_ROOTS:
            if root.exists():
                found = cls._search_dir(root, patterns, match_dir=True)
                if found:
                    logger.info("DynamicPathResolver: Resolved model directory to '%s'", found)
                    return found

        raise DatasetPathResolutionError(
            f"FATAL: Unable to resolve weights directory for '{model_name_or_pattern}'!\n"
            f"Searched roots: {[str(r) for r in cls.FALLBACK_SEARCH_ROOTS if r.exists()]}"
        )

    @staticmethod
    def _search_dir(root: Path, patterns: list[str], match_dir: bool = False) -> Path | None:
        """Performs depth-bounded search for file or directory matching pattern."""
        for pattern in patterns:
            try:
                for candidate in root.glob(f"**/{pattern}"):
                    if match_dir and candidate.is_dir():
                        return candidate.resolve()
                    if not match_dir and candidate.is_file():
                        if candidate.stat().st_size > 0:
                            return candidate.resolve()
            except Exception as e:
                logger.debug("Error globbing in %s with %s: %s", root, pattern, e)
        return None


class DeterministicTaskFallback:
    """Generates strictly valid fallback predictions when models fail or time out."""

    @classmethod
    def generate_task_fallback(cls, task_data: dict[str, Any]) -> list[dict[str, list[list[int]]]]:
        """Generates valid 2-attempt predictions for all test instances in a task."""
        train_examples = task_data.get("train", [])
        test_examples = task_data.get("test", [])

        # Extract training priors for Attempt 2
        mode_train_color = cls._extract_mode_output_color(train_examples)
        fixed_output_shape = cls._extract_fixed_output_shape(train_examples)

        predictions = []
        for test_case in test_examples:
            test_in = test_case.get("input", [[0]])

            # Attempt 1: Safe Identity Mapping (Preserves canvas, bounds, and palette)
            attempt_1 = cls._ensure_valid_grid(test_in)

            # Attempt 2: Calibrated Shape / Color Remap
            attempt_2 = cls._generate_calibrated_attempt_2(
                test_in, mode_train_color, fixed_output_shape
            )

            predictions.append({
                "attempt_1": attempt_1,
                "attempt_2": attempt_2,
            })

        return predictions

    @classmethod
    def _ensure_valid_grid(cls, grid: Any) -> list[list[int]]:
        """Ensures grid is rectangular, non-empty, within [1..30] dims, and colors in [0..9]."""
        if not isinstance(grid, list) or len(grid) == 0:
            return [[0]]

        clean_grid: list[list[int]] = []
        target_cols = None

        for row in grid[:MAX_GRID_DIM]:
            if not isinstance(row, list) or len(row) == 0:
                continue
            if target_cols is None:
                target_cols = min(len(row), MAX_GRID_DIM)

            clean_row = [int(v) if isinstance(v, (int, float)) and 0 <= int(v) <= 9 else 0 
                         for v in row[:target_cols]]
            # Pad row if ragged
            if len(clean_row) < target_cols:
                clean_row.extend([0] * (target_cols - len(clean_row)))
            clean_grid.append(clean_row)

        if not clean_grid:
            return [[0]]

        return clean_grid

    @classmethod
    def _generate_calibrated_attempt_2(
        cls, 
        test_in: list[list[int]], 
        mode_color: int, 
        fixed_shape: tuple[int, int] | None
    ) -> list[list[int]]:
        """Generates secondary hypothesis exploiting shape or color invariants."""
        if fixed_shape is not None:
            r, c = fixed_shape
            r = min(max(r, MIN_GRID_DIM), MAX_GRID_DIM)
            c = min(max(c, MIN_GRID_DIM), MAX_GRID_DIM)
            return [[mode_color for _ in range(c)] for _ in range(r)]

        # Otherwise: Horizontal flip
        clean_in = cls._ensure_valid_grid(test_in)
        h = len(clean_in)
        w = len(clean_in[0])
        flipped = [[clean_in[r][w - 1 - c] for c in range(w)] for r in range(h)]
        return flipped

    @staticmethod
    def _extract_mode_output_color(train_examples: list[dict[str, Any]]) -> int:
        colors: list[int] = []
        for ex in train_examples:
            out = ex.get("output", [])
            for row in out:
                if isinstance(row, list):
                    for val in row:
                        if isinstance(val, int) and 1 <= val <= 9:
                            colors.append(val)
        if colors:
            return Counter(colors).most_common(1)[0][0]
        return 0

    @staticmethod
    def _extract_fixed_output_shape(train_examples: list[dict[str, Any]]) -> tuple[int, int] | None:
        shapes = []
        for ex in train_examples:
            out = ex.get("output", [])
            if isinstance(out, list) and len(out) > 0 and isinstance(out[0], list):
                shapes.append((len(out), len(out[0])))
        if shapes and all(s == shapes[0] for s in shapes):
            return shapes[0]
        return None


@dataclass
class ValidationReport:
    is_valid: bool
    total_tasks: int
    total_predictions: int
    defects: list[str] = field(default_factory=list)


class AutoHarnessSubmissionGuard:
    """Master guard validating and securing ARC-AGI-2 submissions."""

    def __init__(self, challenges_file: Path | str | None = None) -> None:
        self.challenges_path = (
            Path(challenges_file) if challenges_file 
            else DynamicPathResolver.resolve_challenges_file()
        )
        self.challenges: dict[str, Any] = self._load_challenges()

    def _load_challenges(self) -> dict[str, Any]:
        try:
            with open(self.challenges_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or len(data) == 0:
                raise ValueError("Challenges JSON must be a non-empty dictionary.")
            return data
        except Exception as e:
            raise DatasetPathResolutionError(f"Failed to load challenges from {self.challenges_path}: {e}") from e

    def safe_execute_task(
        self,
        task_id: str,
        inference_fn: Callable[[dict[str, Any]], list[dict[str, list[list[int]]]]],
    ) -> list[dict[str, list[list[int]]]]:
        """Wraps task inference in a zero-cost guard with automatic fallback recovery."""
        task_data = self.challenges.get(task_id)
        if task_data is None:
            raise KeyError(f"Task ID '{task_id}' not found in challenges manifest!")

        try:
            predictions = inference_fn(task_data)
            expected_tests = len(task_data.get("test", []))
            if not isinstance(predictions, list) or len(predictions) != expected_tests:
                logger.warning(
                    "Task %s: Predicted count (%s) != expected (%s). Triggering fallback.",
                    task_id, len(predictions) if isinstance(predictions, list) else 0, expected_tests
                )
                return DeterministicTaskFallback.generate_task_fallback(task_data)

            validated_preds = []
            for pred in predictions:
                att1 = DeterministicTaskFallback._ensure_valid_grid(pred.get("attempt_1"))
                att2 = DeterministicTaskFallback._ensure_valid_grid(pred.get("attempt_2"))
                validated_preds.append({"attempt_1": att1, "attempt_2": att2})

            return validated_preds

        except Exception as exc:
            logger.error("Task %s worker failed with exception: %s. Applying fallback.", task_id, exc, exc_info=True)
            return DeterministicTaskFallback.generate_task_fallback(task_data)

    def validate_submission_dict(self, submission: dict[str, Any]) -> ValidationReport:
        """Validates all ARC-AGI-2 submission invariants."""
        defects = []
        expected_task_ids = set(self.challenges.keys())
        submitted_task_ids = set(submission.keys())

        # Invariant 1: Task Completeness
        missing_tasks = expected_task_ids - submitted_task_ids
        if missing_tasks:
            defects.append(f"Invariant Violation: Missing {len(missing_tasks)} tasks (e.g., {list(missing_tasks)[:3]})")

        extra_tasks = submitted_task_ids - expected_task_ids
        if extra_tasks:
            defects.append(f"Invariant Violation: Contains {len(extra_tasks)} unrecognized tasks (e.g., {list(extra_tasks)[:3]})")

        total_preds = 0
        for tid in expected_task_ids:
            if tid not in submission:
                continue

            preds = submission[tid]
            expected_tests = len(self.challenges[tid].get("test", []))
            if not isinstance(preds, list):
                defects.append(f"Task {tid}: predictions must be a list, got {type(preds)}")
                continue

            if len(preds) != expected_tests:
                defects.append(f"Task {tid}: prediction count {len(preds)} != expected {expected_tests}")

            for idx, p in enumerate(preds):
                total_preds += 1
                if not isinstance(p, dict):
                    defects.append(f"Task {tid} [{idx}]: prediction is not a dictionary")
                    continue

                for att in ("attempt_1", "attempt_2"):
                    if att not in p:
                        defects.append(f"Task {tid} [{idx}]: missing '{att}'")
                        continue

                    grid = p[att]
                    if not isinstance(grid, list) or len(grid) == 0:
                        defects.append(f"Task {tid} [{idx}] {att}: empty or non-list grid")
                        continue

                    h = len(grid)
                    if h < MIN_GRID_DIM or h > MAX_GRID_DIM:
                        defects.append(f"Task {tid} [{idx}] {att}: height {h} outside [1..30]")

                    if not isinstance(grid[0], list) or len(grid[0]) == 0:
                        defects.append(f"Task {tid} [{idx}] {att}: first row empty or non-list")
                        continue

                    w = len(grid[0])
                    if w < MIN_GRID_DIM or w > MAX_GRID_DIM:
                        defects.append(f"Task {tid} [{idx}] {att}: width {w} outside [1..30]")

                    for r_idx, row in enumerate(grid):
                        if not isinstance(row, list) or len(row) != w:
                            defects.append(f"Task {tid} [{idx}] {att}: row {r_idx} ragged (len {len(row) if isinstance(row, list) else 'nan'} != {w})")
                            break
                        for c_idx, val in enumerate(row):
                            if not isinstance(val, int) or val not in VALID_COLORS:
                                defects.append(f"Task {tid} [{idx}] {att}: cell ({r_idx},{c_idx})={val} invalid color")
                                break

        return ValidationReport(
            is_valid=len(defects) == 0,
            total_tasks=len(submitted_task_ids),
            total_predictions=total_preds,
            defects=defects,
        )

    def write_atomic_submission(
        self, 
        submission: dict[str, Any], 
        output_path: Path | str = "submission.json",
        auto_repair: bool = True
    ) -> Path:
        """Repairs defects if requested, verifies invariants, and writes atomically."""
        out_p = Path(output_path).resolve()
        sub_copy = dict(submission)

        # Auto-repair missing tasks with deterministic fallback
        if auto_repair:
            for tid, t_data in self.challenges.items():
                if tid not in sub_copy:
                    logger.warning("Auto-repairing missing task '%s' with deterministic fallback", tid)
                    sub_copy[tid] = DeterministicTaskFallback.generate_task_fallback(t_data)

        report = self.validate_submission_dict(sub_copy)
        if not report.is_valid:
            defect_summary = "\n".join(report.defects[:10])
            raise SubmissionInvariantViolationError(
                f"AutoHarness Refused to write invalid submission.json!\n"
                f"Found {len(report.defects)} invariant defects:\n{defect_summary}"
            )

        # Atomic Write
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=str(out_p.parent), delete=False, encoding="utf-8") as tmp:
            json.dump(sub_copy, tmp, separators=(",", ":"))
            tmp_path = Path(tmp.name)

        tmp_path.replace(out_p)
        logger.info(
            "AutoHarness: Successfully verified and atomically wrote %d tasks to %s",
            len(sub_copy), out_p
        )
        return out_p
