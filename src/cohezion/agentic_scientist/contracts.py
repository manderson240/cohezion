"""
Data contracts and typed interfaces for The Agentic Scientist orchestration layer.
Synthesized from arXiv:2610.18933 (Sakana AI & University of Oxford, Oct 2026).

Enforces:
1. Strict separation between Read-Only Ideation and Sandboxed Execution.
2. Decoupled dual gating: RubricGate (contract validity) vs ScoreGate (scalar optimization).
3. Retrospective single-change ablation definitions with causal lift tracking.
4. Grounded manuscript and artifact claim-to-source mapping.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvaluationStatus(StrEnum):
    """Execution status for candidate programs or ablations."""

    SUCCESS = "success"
    EVALUATION_ERROR = "evaluation_error"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    RUBRIC_VIOLATION = "rubric_violation"
    PROTOCOL_TAMPER_DETECTED = "protocol_tamper_detected"


class RubricCriterion(BaseModel):
    """
    A single falsifiable, programmatic rubric criterion.
    Used by the IdeationAgent to define runtime constraints that prevent
    shortcuts, reward-hacking, or unstated protocol drift.
    """

    id: str = Field(description="Unique rubric identifier, e.g. 'R1_DALE_COMPLIANT'")
    name: str = Field(description="Human-readable title of the constraint")
    description: str = Field(description="Detailed expectation for the implementation")
    verification_type: str = Field(
        default="ast_inspection",
        description="Type of verification: 'ast_inspection', 'runtime_check', 'metric_boundary', or 'adversarial_critic'",
    )
    is_mandatory: bool = Field(
        default=True, description="Whether passing this rubric is strictly required"
    )


class RubricEvaluation(BaseModel):
    """Result of evaluating a specific rubric criterion against candidate code."""

    rubric_id: str
    passed: bool
    evidence: str
    diagnostics: dict[str, Any] | None = None


class IdeationContract(BaseModel):
    """
    Structured research contract produced by the read-only IdeationAgent.
    Decouples hypothesis generation from implementation.
    """

    id: str = Field(
        default_factory=lambda: f"contract_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')[:20]}"
    )
    title: str = Field(description="Concise descriptive title of the proposed idea")
    falsifiable_hypothesis: str = Field(description="The scientific hypothesis under test")
    implementation_plan: list[str] = Field(description="Ordered steps for the execution agent")
    target_rubrics: list[RubricCriterion] = Field(
        description="Explicit rubrics that must be satisfied"
    )
    target_metrics: list[str] = Field(description="List of metrics targeted for causal improvement")
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    worker_id: str = Field(default="worker_0", description="Originating worker beam")


class TaskSpecification(BaseModel):
    """
    Task definition comprising deterministic initial baseline, evaluators, and contract boundaries.
    Prevents the agent from modifying the test harness or evaluator protocols.
    """

    task_id: str
    description: str
    initial_program_code: str
    search_evaluator_code: str
    final_evaluator_code: str | None = None
    search_evaluator_hash: str = Field(default="")
    final_evaluator_hash: str = Field(default="")
    immutable_files: list[str] = Field(default_factory=lambda: ["evaluator.py", "test_set.json"])
    primary_metric: str = Field(default="score")
    higher_is_better: bool = Field(default=True)
    baseline_score: float = Field(default=0.0)

    def model_post_init(self, __context: Any) -> None:
        """Compute SHA-256 hashes of evaluators to detect any protocol tampering."""
        if not self.search_evaluator_hash and self.search_evaluator_code:
            self.search_evaluator_hash = hashlib.sha256(
                self.search_evaluator_code.encode("utf-8")
            ).hexdigest()
        if not self.final_evaluator_hash and self.final_evaluator_code:
            self.final_evaluator_hash = hashlib.sha256(
                self.final_evaluator_code.encode("utf-8")
            ).hexdigest()

    def verify_evaluator_integrity(self, current_evaluator_code: str) -> bool:
        """Verify that the evaluator code has not been tampered with or modified by the agent."""
        current_hash = hashlib.sha256(current_evaluator_code.encode("utf-8")).hexdigest()
        return current_hash == self.search_evaluator_hash


class AttemptOutcome(BaseModel):
    """
    Complete outcome of a single execution attempt against a contract.
    Encapsulates the dual decoupled gates:
    - all_rubrics_passed (contract satisfaction)
    - is_new_best (scalar optimization advancement)
    """

    attempt_id: str
    contract_id: str
    worker_id: str
    status: EvaluationStatus
    code_diff: str
    metrics: dict[str, float]
    scalar_score: float
    rubric_results: list[RubricEvaluation]
    all_rubrics_passed: bool
    is_new_best: bool
    execution_time_seconds: float
    artifacts: dict[str, str] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AblationPlan(BaseModel):
    """
    Plan for isolating an individual innovation component between baseline and final code.
    Synthesized during Retrospective Evidence Generation.
    """

    ablation_id: str
    target_program_id: str
    isolated_innovation: str
    component_type: str = Field(
        description="'architecture', 'loss_objective', 'hyperparameter', 'routing'"
    )
    rationale: str
    code_patch_to_revert: str
    expected_causal_lift: float = 0.0


class AblationResult(BaseModel):
    """Result of running an isolated single-change ablation study across multiple seeds."""

    ablation_id: str
    isolated_innovation: str
    full_program_mean: float
    ablated_program_mean: float
    causal_lift: float
    seed_scores: list[float]
    ablated_seed_scores: list[float]
    is_statistically_significant: bool
    provenance_hash: str


class ClaimToSourceLink(BaseModel):
    """
    Grounded mapping linking a quantitative statement in a report or manuscript
    to an unassailable empirical run artifact.
    """

    claim_id: str
    statement_text: str
    run_id: str
    metric_key: str
    reported_value: float
    canonical_value: float
    artifact_uri: str
    is_verified: bool
    audit_notes: str | None = None
