"""
The Agentic Scientist module for Cohezion.
Synthesized from arXiv:2610.18933 (Sakana AI & University of Oxford, Oct 2026).
"""

from cohezion.agentic_scientist.contracts import (
    AblationPlan,
    AblationResult,
    AttemptOutcome,
    ClaimToSourceLink,
    EvaluationStatus,
    IdeationContract,
    RubricCriterion,
    RubricEvaluation,
    TaskSpecification,
)
from cohezion.agentic_scientist.orchestrator import (
    AblationStudyEngine,
    ClaimAuditor,
    ExecutionAgent,
    IdeationAgent,
    SharedKnowledgeMemory,
)


__all__ = [
    "AblationPlan",
    "AblationResult",
    "AblationStudyEngine",
    "AttemptOutcome",
    "ClaimAuditor",
    "ClaimToSourceLink",
    "EvaluationStatus",
    "ExecutionAgent",
    "IdeationAgent",
    "IdeationContract",
    "RubricCriterion",
    "RubricEvaluation",
    "SharedKnowledgeMemory",
    "TaskSpecification",
]
