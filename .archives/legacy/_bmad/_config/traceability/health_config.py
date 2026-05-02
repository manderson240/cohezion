#!/usr/bin/env python3
"""
Health Configuration System

Extracts health score weights and thresholds to configuration.
Allows per-project tuning without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HealthWeights:
    """Health score category weights (must sum to 1.0)."""

    code_quality: float = 0.30  # 30%
    test_health: float = 0.25  # 25%
    tech_debt: float = 0.20  # 20%
    git_health: float = 0.15  # 15%
    doc_health: float = 0.10  # 10%

    def __post_init__(self):
        total = (
            self.code_quality
            + self.test_health
            + self.tech_debt
            + self.git_health
            + self.doc_health
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Health weights must sum to 1.0, got {total}")


@dataclass
class HealthThresholds:
    """Health score thresholds and bounds."""

    # Code quality thresholds
    lint_errors_max: int = 100
    type_errors_max: int = 50
    loc_min: int = 10000
    loc_max: int = 1000000

    # Test health thresholds
    coverage_min_percent: float = 60.0
    coverage_target_percent: float = 80.0
    failing_tests_max: int = 10

    # Tech debt thresholds
    todo_max: int = 50
    fixme_max: int = 20
    long_file_lines: int = 500

    # Git health thresholds
    untracked_files_max: int = 20
    branches_max: int = 50
    large_file_size_mb: int = 1

    # Documentation thresholds
    doc_coverage_min_percent: float = 50.0


@dataclass
class HealthConfig:
    """Complete health configuration."""

    weights: HealthWeights = field(default_factory=HealthWeights)
    thresholds: HealthThresholds = field(default_factory=HealthThresholds)
    verbose: bool = True
    dry_run: bool = False

    @classmethod
    def from_dict(cls, config_dict: dict) -> HealthConfig:
        """Create config from dictionary (e.g., YAML/JSON)."""
        weights_dict = config_dict.get("weights", {})
        thresholds_dict = config_dict.get("thresholds", {})

        weights = HealthWeights(
            code_quality=weights_dict.get("code_quality", 0.30),
            test_health=weights_dict.get("test_health", 0.25),
            tech_debt=weights_dict.get("tech_debt", 0.20),
            git_health=weights_dict.get("git_health", 0.15),
            doc_health=weights_dict.get("doc_health", 0.10),
        )

        thresholds = HealthThresholds(
            lint_errors_max=thresholds_dict.get("lint_errors_max", 100),
            type_errors_max=thresholds_dict.get("type_errors_max", 50),
            coverage_min_percent=thresholds_dict.get("coverage_min_percent", 60.0),
            coverage_target_percent=thresholds_dict.get("coverage_target_percent", 80.0),
            failing_tests_max=thresholds_dict.get("failing_tests_max", 10),
            todo_max=thresholds_dict.get("todo_max", 50),
            fixme_max=thresholds_dict.get("fixme_max", 20),
        )

        return cls(
            weights=weights,
            thresholds=thresholds,
            verbose=config_dict.get("verbose", True),
            dry_run=config_dict.get("dry_run", False),
        )

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "weights": {
                "code_quality": self.weights.code_quality,
                "test_health": self.weights.test_health,
                "tech_debt": self.weights.tech_debt,
                "git_health": self.weights.git_health,
                "doc_health": self.weights.doc_health,
            },
            "thresholds": {
                "lint_errors_max": self.thresholds.lint_errors_max,
                "type_errors_max": self.thresholds.type_errors_max,
                "coverage_min_percent": self.thresholds.coverage_min_percent,
                "coverage_target_percent": self.thresholds.coverage_target_percent,
                "failing_tests_max": self.thresholds.failing_tests_max,
                "todo_max": self.thresholds.todo_max,
                "fixme_max": self.thresholds.fixme_max,
            },
            "verbose": self.verbose,
            "dry_run": self.dry_run,
        }


# Default configuration
DEFAULT_CONFIG = HealthConfig()
