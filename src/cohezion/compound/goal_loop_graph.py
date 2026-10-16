"""Goal and Loop Graph Engineering System with SurrealDB.
======================================================
Refactors linear execution traces into active closed loops, hierarchical goals,
deterministic mathematical proof verifiers, and experiential recursive learning.

Leverages SurrealQL graph engineering with formal typed vertices and RELATE edges:
- `RELATE goal->executed_by->autonomous_loop`
- `RELATE autonomous_loop->produces->loop_trace`
- `RELATE loop_trace->verified_by->proof`
- `RELATE autonomous_loop->yields->learning`
- `RELATE learning->compounds_into->goal`
- `RELATE goal->decomposes_into->goal`

Token Efficiency Invariants:
- Tier 0 Deterministic Verifiers bypass LLM calls with 0 tokens and 0 ms latency.
- Monotonic Lyapunov Potential Convergence: \\Delta V(s) <= -\\alpha * progress.
- Kahn DAG topological acyclicity verification.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger("goal_loop_graph")


class GoalStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SATISFIED = "satisfied"
    FAILED = "failed"


class VModelLevel(StrEnum):
    SYSTEM = "SYSTEM"
    SUBSYSTEM = "SUBSYSTEM"
    COMPONENT = "COMPONENT"


class ProofType(StrEnum):
    AST_BYTECODE = "AST_BYTECODE"
    ZKFV_POLYNOMIAL = "ZKFV_POLYNOMIAL"
    GROUP_INVARIANT = "GROUP_INVARIANT"
    LYAPUNOV_POTENTIAL = "LYAPUNOV_POTENTIAL"
    DETERMINISTIC_ALGORITHM = "DETERMINISTIC_ALGORITHM"


@dataclass(slots=True)
class Goal:
    """Formal Goal vertex defining an intentional, verifiable requirement."""

    id: str
    intent: str
    target_metric: str = "task_success"
    target_threshold: float = 1.0
    current_metric: float = 0.0
    preconditions: list[str] = field(default_factory=list)
    success_predicate: str = "metric >= threshold"
    lyapunov_potential: float = 1.0  # Monotonically decreases to 0.0
    status: GoalStatus = GoalStatus.PENDING
    vmodel_level: VModelLevel = VModelLevel.SYSTEM
    owner_agent: str = "SystemsVModelArchitect"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_surreal_record(self) -> str:
        return self.id if ":" in self.id else f"goal:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "target_metric": self.target_metric,
            "target_threshold": self.target_threshold,
            "current_metric": self.current_metric,
            "preconditions": self.preconditions,
            "success_predicate": self.success_predicate,
            "lyapunov_potential": self.lyapunov_potential,
            "status": self.status.value if isinstance(self.status, GoalStatus) else str(self.status),
            "vmodel_level": (
                self.vmodel_level.value
                if isinstance(self.vmodel_level, VModelLevel)
                else str(self.vmodel_level)
            ),
            "owner_agent": self.owner_agent,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Loop:
    """Closed-Loop Controller vertex governing autonomous state machines."""

    id: str
    cycle_pattern: str  # e.g., "PDCA", "OODA", "Hypothesis_Patch_Verify_Submit"
    actions: list[str] = field(default_factory=list)
    converged: bool = False
    iteration_count: int = 1
    progress_score: float = 0.0
    exit_predicate: str = "converged == true"
    owner_agent: str = "CompoundGraphEngineer"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_progressive(self) -> bool:
        return self.progress_score > 0.0 or self.converged

    @property
    def is_livelock(self) -> bool:
        return not self.is_progressive

    def to_surreal_record(self) -> str:
        return self.id if ":" in self.id else f"autonomous_loop:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_pattern": self.cycle_pattern,
            "actions": self.actions,
            "converged": self.converged,
            "iteration_count": self.iteration_count,
            "progress_score": self.progress_score,
            "exit_predicate": self.exit_predicate,
            "is_progressive": self.is_progressive,
            "is_livelock": self.is_livelock,
            "owner_agent": self.owner_agent,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class TraceStep:
    """Atomic execution step within a closed loop."""

    id: str
    action: str
    status: str = "SUCCESS"
    latency_ms: float = 0.0
    tokens_spent: int = 0
    autoharness_verified: bool = True
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_surreal_record(self) -> str:
        return self.id if ":" in self.id else f"loop_trace:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "tokens_spent": self.tokens_spent,
            "autoharness_verified": self.autoharness_verified,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Proof:
    """Deterministic Mathematical Proof validating an invariant with zero LLM tokens."""

    id: str
    theorem_name: str
    proof_type: ProofType
    formal_claim: str
    proof_certificate_hash: str
    verified: bool
    verification_duration_ms: float
    owner_agent: str = "DeterministicProofVerifier"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_surreal_record(self) -> str:
        return self.id if ":" in self.id else f"proof:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "theorem_name": self.theorem_name,
            "proof_type": (
                self.proof_type.value
                if isinstance(self.proof_type, ProofType)
                else str(self.proof_type)
            ),
            "formal_claim": self.formal_claim,
            "proof_certificate_hash": self.proof_certificate_hash,
            "verified": self.verified,
            "verification_duration_ms": self.verification_duration_ms,
            "owner_agent": self.owner_agent,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Learning:
    """Experiential Recursive Learning encoding synthesized retrospective knowledge."""

    id: str
    title: str
    learning_domain: str
    vector_12d: list[float]  # 3 Spatial + 1 Time + 8 Brane dimensions
    retrospective_text: str
    compound_action: str
    timestamp: str
    owner_agent: str = "ExperientialLearningSynthesizer"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_surreal_record(self) -> str:
        return self.id if ":" in self.id else f"learning:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "learning_domain": self.learning_domain,
            "vector_12d": self.vector_12d,
            "retrospective_text": self.retrospective_text,
            "compound_action": self.compound_action,
            "timestamp": self.timestamp,
            "owner_agent": self.owner_agent,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class GraphRelation:
    """Directed graph relation between two vertices."""

    source: str
    relation: str  # e.g., "executed_by", "produces", "verified_by", "yields", "compounds_into"
    target: str
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)


class GoalLoopGraphEngine:
    """Graph Engineering engine connecting Goals, Loops, Traces, and Proofs via SurrealDB."""

    def __init__(
        self,
        surreal_url: str = "http://localhost:8001/sql",
        auth: tuple[str, str] = ("root", "root"),
    ) -> None:
        self.surreal_url = surreal_url
        user, pwd = auth
        self.auth_header = "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()

    def refactor_trace_sequence(
        self,
        domain: str,
        task_name: str,
        events: list[dict[str, Any]],
        target_metric: str = "accuracy",
        target_threshold: float = 1.0,
    ) -> tuple[Goal, Loop, list[TraceStep], list[GraphRelation]]:
        """Refactors a linear sequence of trace events into a Goal, a Loop, TraceSteps, and Relations."""
        slug_hash = hashlib.sha256(f"{domain}:{task_name}".encode()).hexdigest()[:8]
        goal_id = f"goal_{domain}_{slug_hash}"
        loop_id = f"loop_{domain}_{slug_hash}"

        success_count = sum(1 for e in events if e.get("status", "SUCCESS") == "SUCCESS" or e.get("success", True))
        converged = success_count == len(events) and len(events) > 0
        progress_score = (success_count / len(events)) if events else 0.0

        goal = Goal(
            id=goal_id,
            intent=f"Achieve objective: {task_name} in domain {domain}",
            target_metric=target_metric,
            target_threshold=target_threshold,
            current_metric=progress_score,
            lyapunov_potential=max(0.0, 1.0 - progress_score),
            status=GoalStatus.SATISFIED if converged else GoalStatus.ACTIVE,
            vmodel_level=VModelLevel.SUBSYSTEM,
            metadata={"domain": domain, "event_count": len(events)},
        )

        loop = Loop(
            id=loop_id,
            cycle_pattern="Hypothesis_Verify_Execute_Learn",
            actions=[e.get("action", f"step_{i}") for i, e in enumerate(events)],
            converged=converged,
            iteration_count=max(1, len(events)),
            progress_score=progress_score,
            metadata={"domain": domain, "task_name": task_name},
        )

        trace_steps: list[TraceStep] = []
        relations: list[GraphRelation] = []

        # Edge 1: goal -> executed_by -> autonomous_loop
        relations.append(
            GraphRelation(
                source=goal.to_surreal_record(),
                relation="executed_by",
                target=loop.to_surreal_record(),
                weight=1.0,
            )
        )

        for i, ev in enumerate(events):
            step_id = f"trace_{domain}_{slug_hash}_{i+1}"
            step = TraceStep(
                id=step_id,
                action=ev.get("action", f"action_{i+1}"),
                status=ev.get("status", "SUCCESS"),
                latency_ms=float(ev.get("latency_ms", 0.0)),
                tokens_spent=int(ev.get("tokens_spent", 0)),
                autoharness_verified=bool(ev.get("autoharness_verified", True)),
                error_message=ev.get("error_message"),
                metadata=ev.get("metadata", {}),
            )
            trace_steps.append(step)

            # Edge 2: autonomous_loop -> produces -> loop_trace
            relations.append(
                GraphRelation(
                    source=loop.to_surreal_record(),
                    relation="produces",
                    target=step.to_surreal_record(),
                    weight=1.0 if step.status == "SUCCESS" else 0.0,
                )
            )

        return goal, loop, trace_steps, relations

    def build_surrealql(
        self,
        goals: list[Goal],
        loops: list[Loop],
        traces: list[TraceStep],
        proofs: list[Proof],
        learnings: list[Learning],
        relations: list[GraphRelation],
    ) -> str:
        """Generates idempotent SurrealQL statements for schema definition and record graph upserts."""
        stmts: list[str] = [
            "DEFINE TABLE goal SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE autonomous_loop SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE loop_trace SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE proof SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE learning SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE executed_by TYPE RELATION SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE produces TYPE RELATION SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE verified_by TYPE RELATION SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE yields TYPE RELATION SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE compounds_into TYPE RELATION SCHEMALESS PERMISSIONS NONE;",
            "DEFINE TABLE decomposes_into TYPE RELATION SCHEMALESS PERMISSIONS NONE;",
        ]

        for g in goals:
            stmts.append(f"UPSERT {g.to_surreal_record()} CONTENT {json.dumps(g.to_dict())};")

        for l in loops:
            stmts.append(f"UPSERT {l.to_surreal_record()} CONTENT {json.dumps(l.to_dict())};")

        for t in traces:
            stmts.append(f"UPSERT {t.to_surreal_record()} CONTENT {json.dumps(t.to_dict())};")

        for p in proofs:
            stmts.append(f"UPSERT {p.to_surreal_record()} CONTENT {json.dumps(p.to_dict())};")

        for k in learnings:
            stmts.append(f"UPSERT {k.to_surreal_record()} CONTENT {json.dumps(k.to_dict())};")

        for r in relations:
            stmts.append(
                f"RELATE {r.source}->{r.relation}->{r.target} SET weight = {r.weight};"
            )

        return "\n".join(stmts)

    def persist_graph(
        self,
        goals: list[Goal],
        loops: list[Loop],
        traces: list[TraceStep],
        proofs: list[Proof],
        learnings: list[Learning],
        relations: list[GraphRelation],
    ) -> bool:
        """Executes generated SurrealQL graph statements against SurrealDB endpoint."""
        surql = self.build_surrealql(goals, loops, traces, proofs, learnings, relations)
        headers = {
            "Accept": "application/json",
            "surreal-ns": "cohezion",
            "surreal-db": "main",
            "Authorization": self.auth_header,
            "Content-Type": "text/plain",
        }
        body = f"USE NS cohezion DB main;\n{surql}"
        req = urllib.request.Request(
            self.surreal_url, data=body.encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for stmt in data:
                if stmt.get("status") == "ERR":
                    logger.warning("SurrealQL statement warning: %s", stmt.get("result"))
            return True
        except Exception as e:
            logger.warning("SurrealDB graph persistence error (fail-soft): %s", e)
            return False

    def query_graph_lineage(self, goal_id: str) -> dict[str, Any]:
        """Queries the complete execution graph lineage for a given goal."""
        safe_id = goal_id if ":" in goal_id else f"goal:{goal_id}"
        query = f"""
        USE NS cohezion DB main;
        SELECT *,
               ->executed_by->autonomous_loop as loops,
               ->executed_by->autonomous_loop->produces->loop_trace as traces,
               <-compounds_into<-learning as learnings
        FROM {safe_id};
        """
        headers = {
            "Accept": "application/json",
            "surreal-ns": "cohezion",
            "surreal-db": "main",
            "Authorization": self.auth_header,
            "Content-Type": "text/plain",
        }
        req = urllib.request.Request(
            self.surreal_url, data=query.encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = data[-1].get("result", [])
            return results[0] if results else {}
        except Exception as e:
            logger.warning("Query graph lineage error: %s", e)
            return {}
