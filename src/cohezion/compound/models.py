"""Pydantic models for compound feedback cycle data."""

from __future__ import annotations

from pydantic import BaseModel


class CompoundCycleResult(BaseModel):
    """Result of a single compound feedback cycle."""

    skill_name: str
    input_text: str
    execution_output: str = ""
    execution_tokens: int = 0
    execution_duration_ms: float = 0.0
    compound_score_delta: float = 0.0
    patterns: list[str] = []
    refinements_applied: int = 0
    version_before: str = ""
    version_after: str = ""
    model_usage: dict[str, int] = {}


class CompoundCycleReport(BaseModel):
    """Report across multiple compound cycles."""

    skill_name: str
    cycles: list[CompoundCycleResult] = []
    total_cycles: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    total_refinements: int = 0
    final_compound_score_delta: float = 0.0
