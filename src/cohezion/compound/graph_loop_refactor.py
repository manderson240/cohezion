"""Trace to Goal-Loop Graph Refactoring Engine.

Refactors passive linear execution traces into an active, directed bipartite
Goal-Loop Graph G = (V_G, V_L, E) grounded in Minimum Description Length (MDL)
compression and formal Systems Engineering V-Model rigor.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BipartiteEdgeType(StrEnum):
    """Bipartite edge types strictly connecting Goals <-> Loops."""

    DISPATCHED_TO = "DISPATCHED_TO"  # Goal -> Loop
    PRODUCES = "PRODUCES"  # Loop -> Goal
    SPAWNS_SUBGOAL = "SPAWNS_SUBGOAL"  # Loop -> Goal (child)
    VERIFIES = "VERIFIES"  # Loop -> Goal (verification proof)


@dataclass(slots=True)
class TraceSegment:
    """Contiguous slice of trace events serving a unified intention."""

    intent: str
    events: list[dict[str, Any]]
    terminal_success: bool
    start_time: str
    end_time: str


@dataclass(slots=True)
class GoalNode:
    """Goal vertex (V_G) defining an intentional objective."""

    id: str
    intent: str
    target_metric: str = "success_rate"
    target_threshold: float = 1.0
    preconditions: list[str] = field(default_factory=list)
    success_predicate: str = "metric >= threshold"
    lyapunov_potential: float = 1.0  # Decreases monotonically to 0.0 upon convergence
    status: str = "pending"  # "pending", "active", "satisfied", "failed"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_surreal_record(self) -> str:
        """Formatted SurrealDB record ID."""
        if ":" in self.id:
            return self.id
        return f"goal:{self.id}"


@dataclass(slots=True)
class LoopNode:
    """Loop vertex (V_L) defining an autonomous control cycle / state machine."""

    id: str
    cycle_pattern: str
    actions: list[str]
    converged: bool = False
    iteration_count: int = 1
    progress_delta: float = 0.0
    exit_predicate: str = "converged == true"
    state_transitions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_progressive(self) -> bool:
        """True if the loop achieves positive progress delta toward goal satisfaction."""
        return self.calculate_progress_score() > 0.0

    @property
    def is_livelock(self) -> bool:
        """True if the loop cycled without positive net progress."""
        return self.calculate_progress_score() <= 0.0

    def calculate_progress_score(self) -> float:
        """Calculate normalized progress score for the loop execution."""
        if self.progress_delta > 0.0:
            return self.progress_delta
        if self.converged:
            return 1.0
        return 0.0

    def to_surreal_record(self) -> str:
        """Formatted SurrealDB record ID."""
        if ":" in self.id:
            return self.id
        return f"autonomous_loop:{self.id}"


@dataclass(slots=True)
class BipartiteEdge:
    """Directed edge in the bipartite graph connecting Goal <-> Loop."""

    source_id: str
    target_id: str
    edge_type: BipartiteEdgeType
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GoalLoopGraph:
    """Directed Bipartite Goal-Loop Graph G = (V_G, V_L, E)."""

    goal_nodes: dict[str, GoalNode] = field(default_factory=dict)
    loop_nodes: dict[str, LoopNode] = field(default_factory=dict)
    edges: list[BipartiteEdge] = field(default_factory=list)

    def add_goal(self, goal: GoalNode) -> None:
        self.goal_nodes[goal.id] = goal

    def add_loop(self, loop: LoopNode) -> None:
        self.loop_nodes[loop.id] = loop

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: BipartiteEdgeType,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Add edge while strictly enforcing bipartite structure."""
        source_is_goal = source_id in self.goal_nodes
        source_is_loop = source_id in self.loop_nodes
        target_is_goal = target_id in self.goal_nodes
        target_is_loop = target_id in self.loop_nodes

        if not (
            (source_is_goal and target_is_loop)
            or (source_is_loop and target_is_goal)
        ):
            raise ValueError(
                f"Bipartite violation: Cannot connect {source_id} -> {target_id}"
            )

        self.edges.append(
            BipartiteEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                weight=weight,
                properties=properties or {},
            )
        )

    def calculate_compression_ratio(self, original_events: list[dict[str, Any]]) -> float:
        """Compute MDL compression ratio rho = |T| / (|V_L| + |V_G|)."""
        graph_complexity = max(1, len(self.goal_nodes) + len(self.loop_nodes))
        return len(original_events) / float(graph_complexity)

    def to_surrealql(self) -> str:
        """Generate idempotent SurrealQL statements to persist graph and relations."""
        statements: list[str] = []

        # 1. Upsert Goal Nodes
        for goal in self.goal_nodes.values():
            rec_id = goal.to_surreal_record()
            payload = json.dumps(
                {
                    "intent": goal.intent,
                    "target_metric": goal.target_metric,
                    "target_threshold": goal.target_threshold,
                    "preconditions": goal.preconditions,
                    "success_predicate": goal.success_predicate,
                    "lyapunov_potential": goal.lyapunov_potential,
                    "status": goal.status,
                    "metadata": goal.metadata,
                }
            )
            statements.append(f"UPSERT {rec_id} CONTENT {payload};")

        # 2. Upsert Loop Nodes
        for loop in self.loop_nodes.values():
            rec_id = loop.to_surreal_record()
            payload = json.dumps(
                {
                    "cycle_pattern": loop.cycle_pattern,
                    "actions": loop.actions,
                    "converged": loop.converged,
                    "iteration_count": loop.iteration_count,
                    "progress_delta": loop.progress_delta,
                    "exit_predicate": loop.exit_predicate,
                    "is_progressive": loop.is_progressive,
                    "is_livelock": loop.is_livelock,
                    "metadata": loop.metadata,
                }
            )
            statements.append(f"UPSERT {rec_id} CONTENT {payload};")

        # 3. Upsert RELATE Edges
        for edge in self.edges:
            src = (
                self.goal_nodes[edge.source_id].to_surreal_record()
                if edge.source_id in self.goal_nodes
                else self.loop_nodes[edge.source_id].to_surreal_record()
            )
            tgt = (
                self.goal_nodes[edge.target_id].to_surreal_record()
                if edge.target_id in self.goal_nodes
                else self.loop_nodes[edge.target_id].to_surreal_record()
            )
            statements.append(
                f"RELATE {src}->{edge.edge_type.value}->{tgt} SET weight = {edge.weight};"
            )

        return "\n".join(statements)


class TraceRefactorEngine:
    """Engine that refactors flat traces into bipartite Goal-Loop Graphs."""

    def segment_trace(self, events: list[dict[str, Any]]) -> list[TraceSegment]:
        """Partition linear trace into contiguous segments by intention shift."""
        if not events:
            return []

        segments: list[TraceSegment] = []
        current_intent = events[0].get("intent") or "default_intent"
        current_events: list[dict[str, Any]] = []
        start_time = str(events[0].get("timestamp", time.time()))

        for evt in events:
            evt_intent = evt.get("intent") or "default_intent"
            if evt_intent != current_intent and current_events:
                end_time = str(current_events[-1].get("timestamp", time.time()))
                term_succ = bool(current_events[-1].get("success", True))
                segments.append(
                    TraceSegment(
                        intent=current_intent,
                        events=current_events,
                        terminal_success=term_succ,
                        start_time=start_time,
                        end_time=end_time,
                    )
                )
                current_intent = evt_intent
                current_events = []
                start_time = str(evt.get("timestamp", time.time()))

            current_events.append(evt)

        if current_events:
            end_time = str(current_events[-1].get("timestamp", time.time()))
            term_succ = bool(current_events[-1].get("success", True))
            segments.append(
                TraceSegment(
                    intent=current_intent,
                    events=current_events,
                    terminal_success=term_succ,
                    start_time=start_time,
                    end_time=end_time,
                )
            )

        return segments

    def detect_repair_cycles(self, segment: TraceSegment) -> list[LoopNode]:
        """Detect repair/retry cycles: attempt -> failure -> diagnose -> repair -> pass."""
        actions = [str(evt.get("action", "")) for evt in segment.events]
        has_failure = any(not evt.get("success", True) for evt in segment.events)

        # Check for repair motif: execution with diagnose/patch/repair steps
        has_diagnose_or_repair = any(
            "diagnose" in a.lower()
            or "repair" in a.lower()
            or "patch" in a.lower()
            or "fix" in a.lower()
            for a in actions
        )

        pattern = (
            "attempt_diagnose_repair_verify"
            if (has_failure and has_diagnose_or_repair)
            else "direct_execution"
        )
        loop_id = "loop_" + hashlib.sha256(
            f"{segment.intent}_{pattern}_{segment.start_time}".encode()
        ).hexdigest()[:12]

        loop = LoopNode(
            id=loop_id,
            cycle_pattern=pattern,
            actions=actions,
            converged=segment.terminal_success,
            iteration_count=max(1, len(segment.events) // 2),
            progress_delta=1.0 if segment.terminal_success else 0.0,
            metadata={"segment_intent": segment.intent, "event_count": len(segment.events)},
        )
        return [loop]

    def refactor(self, events: list[dict[str, Any]]) -> GoalLoopGraph:
        """Transform raw linear events into a bipartite Goal-Loop Graph."""
        graph = GoalLoopGraph()
        segments = self.segment_trace(events)

        for seg in segments:
            goal_id = "goal_" + hashlib.sha256(seg.intent.encode()).hexdigest()[:12]
            if goal_id not in graph.goal_nodes:
                goal = GoalNode(
                    id=goal_id,
                    intent=seg.intent,
                    target_metric="task_success",
                    target_threshold=1.0,
                    status="satisfied" if seg.terminal_success else "active",
                    lyapunov_potential=0.0 if seg.terminal_success else 0.5,
                )
                graph.add_goal(goal)

            # Detect loop cycles for this segment
            loops = self.detect_repair_cycles(seg)
            for loop in loops:
                graph.add_loop(loop)
                # Bipartite edges:
                # 1. Goal dispatches Loop (g -> L)
                graph.add_edge(
                    source_id=goal_id,
                    target_id=loop.id,
                    edge_type=BipartiteEdgeType.DISPATCHED_TO,
                    weight=1.0,
                )
                # 2. Loop produces result for Goal (L -> g)
                graph.add_edge(
                    source_id=loop.id,
                    target_id=goal_id,
                    edge_type=BipartiteEdgeType.PRODUCES,
                    weight=loop.calculate_progress_score(),
                )

        return graph

    def refactor_from_surreal(self, records: list[dict[str, Any]]) -> GoalLoopGraph:
        """Refactor from SurrealDB loop_trace table records into a GoalLoopGraph."""
        events: list[dict[str, Any]] = []
        for r in records:
            intent = (
                r.get("title")
                or r.get("task_id")
                or r.get("goal_id")
                or "general_autonomous_task"
            )
            # Create synthetic event stream from the loop_trace summary record
            events.append(
                {
                    "timestamp": r.get("timestamp", time.time()),
                    "action": "execute_loop",
                    "intent": intent,
                    "success": r.get("converged", r.get("execution_success", True)),
                    "final_metric": r.get("final_metric", 1.0),
                }
            )
            if r.get("memory_as_plans", {}).get("segments"):
                for subseg in r["memory_as_plans"]["segments"]:
                    events.append(
                        {
                            "timestamp": subseg.get("created_at", time.time()),
                            "action": "verify_subgoal",
                            "intent": intent,
                            "success": subseg.get("progress", 1.0) >= 1.0,
                            "proof": subseg.get("verification_proof"),
                        }
                    )
        return self.refactor(events)
