"""Agentic Software Delivery Primitives.

Implements the core primitives defined in Microsoft's Command Line architecture:
Plan -> Build -> Verify -> Observe, connected by a central Purpose-Driven Knowledge Layer.
Enforces explicit stage contracts, auditable output artifacts, and materialized memory views
that directly feed into Cohezion's SLEEP continual learning and AutoHarness verification loops.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DeliveryStage(enum.StrEnum):
    """The four durable stages of the Agentic Software Delivery Lifecycle."""

    PLAN = "plan"
    BUILD = "build"
    VERIFY = "verify"
    OBSERVE = "observe"


class DeliveryArtifactType(enum.StrEnum):
    """Discrete artifact types carrying work and evidence between lifecycle stages."""

    GOAL_SPEC = "goal_spec"
    CANDIDATE_IMPLEMENTATION = "candidate_implementation"
    VERIFICATION_EVIDENCE = "verification_evidence"
    OPERATIONAL_SIGNAL = "operational_signal"


@dataclass(frozen=True, slots=True)
class DeliveryArtifact:
    """Immutable output artifact produced at an SDLC stage to carry work forward."""

    artifact_id: str
    stage: DeliveryStage
    artifact_type: DeliveryArtifactType
    title: str
    content: dict[str, Any]
    evidence: list[str] = field(default_factory=list)
    questions_remaining: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def is_valid_for_next_stage(self) -> bool:
        """Assert whether the artifact meets minimum criteria to advance."""
        return bool(self.artifact_id and self.title and self.content)


@dataclass(slots=True)
class DeliveryContract:
    """Explicit formal contract governing the handover between adjacent SDLC stages."""

    source_stage: DeliveryStage
    target_stage: DeliveryStage
    required_artifact_types: list[DeliveryArtifactType]
    custom_validators: list[Callable[[DeliveryArtifact], bool]] = field(default_factory=list)

    def validate_handover(self, artifact: DeliveryArtifact) -> tuple[bool, str]:
        """Validate whether the artifact satisfies the formal stage boundary contract."""
        if artifact.stage != self.source_stage:
            return (
                False,
                f"Artifact stage {artifact.stage} does not match expected source {self.source_stage}",
            )

        if artifact.artifact_type not in self.required_artifact_types:
            return (
                False,
                f"Artifact type {artifact.artifact_type} not in allowed types {self.required_artifact_types}",
            )

        if not artifact.is_valid_for_next_stage():
            return False, "Artifact failed internal structural validity check"

        for validator in self.custom_validators:
            try:
                if not validator(artifact):
                    return (
                        False,
                        f"Custom validator {validator.__name__} failed for artifact {artifact.artifact_id}",
                    )
            except Exception as e:
                return False, f"Validator error: {e}"

        return True, "Handover contract satisfied"


class PurposeDrivenMemory:
    """Purpose-driven materialized memory layer.

    Instead of accumulating raw context bloat, maintains specialized indices to:
    1. Avoid repeating past implementation and architectural mistakes.
    2. Retrieve hard system constraints applicable to a specific component.
    3. Measure memory utility via the Engineering Evaluation Test:
       Delta_Efficiency = (Success_with_mem - Success_without_mem) / Overhead.
    """

    def __init__(self) -> None:
        self._mistakes_index: dict[str, list[dict[str, Any]]] = {}
        self._constraints_index: dict[str, list[str]] = {}
        self._stage_history: list[DeliveryArtifact] = []
        self._eval_records: list[dict[str, Any]] = []

    def record_artifact(self, artifact: DeliveryArtifact) -> None:
        """Index a stage artifact into the purpose-driven knowledge layer."""
        self._stage_history.append(artifact)

        # Index mistakes / invariant violations from verification or observe
        if artifact.stage in (DeliveryStage.VERIFY, DeliveryStage.OBSERVE):
            failures = artifact.content.get("failures", [])
            component = artifact.content.get("component", "system")
            if component not in self._mistakes_index:
                self._mistakes_index[component] = []
            for fail in failures:
                self._mistakes_index[component].append(
                    {
                        "failure": fail,
                        "timestamp": artifact.created_at,
                        "artifact_id": artifact.artifact_id,
                    }
                )

        # Index declared constraints from plan
        if artifact.stage == DeliveryStage.PLAN:
            component = artifact.content.get("component", "system")
            constraints = artifact.content.get("constraints", [])
            if component not in self._constraints_index:
                self._constraints_index[component] = []
            self._constraints_index[component].extend(constraints)

    def query_past_mistakes(self, component: str) -> list[dict[str, Any]]:
        """Return materialized list of past failures for a component."""
        return list(self._mistakes_index.get(component, []))

    def query_constraints(self, component: str) -> list[str]:
        """Return active architectural and domain constraints for a component."""
        return list(self._constraints_index.get(component, []))

    def evaluate_memory_utility(
        self,
        task_id: str,
        success_with_mem: bool,
        success_baseline: bool,
        lookup_latency_ms: float,
    ) -> float:
        """Compute the engineering evaluation score of memory utility.

        Score = (Outcome_gain) / (1 + normalized_latency).
        Positive score indicates memory improved task outcome over baseline.
        """
        outcome_gain = (1.0 if success_with_mem else 0.0) - (1.0 if success_baseline else 0.0)
        norm_latency = min(1.0, lookup_latency_ms / 100.0)
        utility = outcome_gain / (1.0 + norm_latency)

        self._eval_records.append(
            {
                "task_id": task_id,
                "utility": utility,
                "lookup_latency_ms": lookup_latency_ms,
            }
        )
        return utility

    @property
    def total_artifacts(self) -> int:
        """Return total indexed artifacts count."""
        return len(self._stage_history)


class AgenticSoftwareDeliveryPipeline:
    """Coordinating pipeline orchestrating the four agentic software delivery primitives."""

    def __init__(self, memory: PurposeDrivenMemory | None = None) -> None:
        self.memory = memory or PurposeDrivenMemory()
        self._artifacts: dict[str, DeliveryArtifact] = {}
        self._contracts: dict[tuple[DeliveryStage, DeliveryStage], DeliveryContract] = {}
        self._setup_default_contracts()

    def _setup_default_contracts(self) -> None:
        """Configure standard transitions between adjacent SDLC stages."""
        # Plan -> Build
        self._contracts[(DeliveryStage.PLAN, DeliveryStage.BUILD)] = DeliveryContract(
            source_stage=DeliveryStage.PLAN,
            target_stage=DeliveryStage.BUILD,
            required_artifact_types=[DeliveryArtifactType.GOAL_SPEC],
            custom_validators=[
                lambda a: "intent" in a.content and "acceptance_criteria" in a.content
            ],
        )
        # Build -> Verify
        self._contracts[(DeliveryStage.BUILD, DeliveryStage.VERIFY)] = DeliveryContract(
            source_stage=DeliveryStage.BUILD,
            target_stage=DeliveryStage.VERIFY,
            required_artifact_types=[DeliveryArtifactType.CANDIDATE_IMPLEMENTATION],
            custom_validators=[lambda a: "diff_or_code" in a.content and "rationale" in a.content],
        )
        # Verify -> Observe
        self._contracts[(DeliveryStage.VERIFY, DeliveryStage.OBSERVE)] = DeliveryContract(
            source_stage=DeliveryStage.VERIFY,
            target_stage=DeliveryStage.OBSERVE,
            required_artifact_types=[DeliveryArtifactType.VERIFICATION_EVIDENCE],
            custom_validators=[lambda a: a.content.get("passed", False) is True],
        )

    def execute_plan(
        self,
        component: str,
        intent: str,
        constraints: list[str],
        acceptance_criteria: list[str],
    ) -> DeliveryArtifact:
        """Execute Stage 1: Plan. Formulate intent, constraints, and success criteria."""
        # Check memory for known past mistakes on this component
        past_mistakes = self.memory.query_past_mistakes(component)
        enhanced_constraints = list(constraints)
        for pm in past_mistakes:
            enhanced_constraints.append(f"Defense against past defect: {pm['failure']}")

        artifact = DeliveryArtifact(
            artifact_id=f"plan_{component}_{int(time.time() * 1000)}",
            stage=DeliveryStage.PLAN,
            artifact_type=DeliveryArtifactType.GOAL_SPEC,
            title=f"Plan: {component} Intent & Acceptance Criteria",
            content={
                "component": component,
                "intent": intent,
                "constraints": enhanced_constraints,
                "acceptance_criteria": acceptance_criteria,
            },
            evidence=[f"Retrieved {len(past_mistakes)} historical lessons from memory layer"],
        )
        self.memory.record_artifact(artifact)
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def execute_build(
        self,
        plan_artifact: DeliveryArtifact,
        build_handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> DeliveryArtifact:
        """Execute Stage 2: Build. Translate goals into candidate implementation with choices."""
        contract = self._contracts.get((DeliveryStage.PLAN, DeliveryStage.BUILD))
        if contract:
            valid, msg = contract.validate_handover(plan_artifact)
            if not valid:
                raise ValueError(f"Plan -> Build Contract Breach: {msg}")

        result = build_handler(plan_artifact.content)

        artifact = DeliveryArtifact(
            artifact_id=f"build_{plan_artifact.content.get('component')}_{int(time.time() * 1000)}",
            stage=DeliveryStage.BUILD,
            artifact_type=DeliveryArtifactType.CANDIDATE_IMPLEMENTATION,
            title=f"Build: Candidate Implementation for {plan_artifact.content.get('component')}",
            content={
                "component": plan_artifact.content.get("component"),
                "diff_or_code": result.get("diff_or_code", ""),
                "rationale": result.get("rationale", ""),
                "modified_files": result.get("modified_files", []),
            },
            evidence=result.get("evidence", []),
            questions_remaining=result.get("questions_remaining", []),
        )
        self.memory.record_artifact(artifact)
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def execute_verify(
        self,
        build_artifact: DeliveryArtifact,
        verifier_handler: Callable[[dict[str, Any]], tuple[bool, list[str], list[str]]],
    ) -> DeliveryArtifact:
        """Execute Stage 3: Verify. Formally validate implementation against acceptance criteria."""
        contract = self._contracts.get((DeliveryStage.BUILD, DeliveryStage.VERIFY))
        if contract:
            valid, msg = contract.validate_handover(build_artifact)
            if not valid:
                raise ValueError(f"Build -> Verify Contract Breach: {msg}")

        passed, traces, failures = verifier_handler(build_artifact.content)

        artifact = DeliveryArtifact(
            artifact_id=f"verify_{build_artifact.content.get('component')}_{int(time.time() * 1000)}",
            stage=DeliveryStage.VERIFY,
            artifact_type=DeliveryArtifactType.VERIFICATION_EVIDENCE,
            title=f"Verify: Validation Evidence for {build_artifact.content.get('component')}",
            content={
                "component": build_artifact.content.get("component"),
                "passed": passed,
                "proof_traces": traces,
                "failures": failures,
            },
            evidence=traces,
            questions_remaining=[] if passed else [f"Resolve failure: {f}" for f in failures],
        )
        self.memory.record_artifact(artifact)
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def execute_observe(
        self,
        verify_artifact: DeliveryArtifact,
        telemetry_handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> DeliveryArtifact:
        """Execute Stage 4: Observe. Ingest production telemetry, triage anomalies, synthesize lessons."""
        contract = self._contracts.get((DeliveryStage.VERIFY, DeliveryStage.OBSERVE))
        if contract:
            valid, msg = contract.validate_handover(verify_artifact)
            if not valid:
                raise ValueError(f"Verify -> Observe Contract Breach: {msg}")

        telemetry = telemetry_handler(verify_artifact.content)

        artifact = DeliveryArtifact(
            artifact_id=f"observe_{verify_artifact.content.get('component')}_{int(time.time() * 1000)}",
            stage=DeliveryStage.OBSERVE,
            artifact_type=DeliveryArtifactType.OPERATIONAL_SIGNAL,
            title=f"Observe: Operational Signals for {verify_artifact.content.get('component')}",
            content={
                "component": verify_artifact.content.get("component"),
                "metrics": telemetry.get("metrics", {}),
                "anomalies": telemetry.get("anomalies", []),
                "synthesized_learnings": telemetry.get("synthesized_learnings", []),
                "failures": telemetry.get("runtime_failures", []),
            },
            evidence=[
                f"Telemetry snapshot: {k}={v}" for k, v in telemetry.get("metrics", {}).items()
            ],
        )
        self.memory.record_artifact(artifact)
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def export_sleep_experience(self, artifact: DeliveryArtifact) -> dict[str, Any]:
        """Convert a Verify or Observe artifact into an input experience for SleepFramework."""
        if artifact.stage == DeliveryStage.VERIFY:
            passed = artifact.content.get("passed", False)
            reward = 1.0 if passed else 0.0
            loss = 0.0 if passed else 1.0
            trace_repr = f"Verify:{artifact.content.get('component')}:{passed}"
        elif artifact.stage == DeliveryStage.OBSERVE:
            anomalies = len(artifact.content.get("anomalies", []))
            reward = 1.0 if anomalies == 0 else max(0.0, 1.0 - (anomalies * 0.2))
            loss = anomalies * 0.2
            trace_repr = f"Observe:{artifact.content.get('component')}:anomalies={anomalies}"
        else:
            reward = 0.5
            loss = 0.2
            trace_repr = f"{artifact.stage}:{artifact.content.get('component')}"

        return {
            "task_id": artifact.artifact_id,
            "loss": loss,
            "reward": reward,
            "entropy": 0.05,
            "trace": trace_repr,
        }
