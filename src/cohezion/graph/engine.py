"""Workflow execution engine with topological DAG dispatch.

Replaces linear pipeline execution with graph-native parallel dispatch.
Nodes whose predecessors are all completed run in parallel via asyncio.gather.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import TYPE_CHECKING, Any

from cohezion.graph.types import (
    EdgeSpec,
    NodeResult,
    NodeStatus,
    WorkflowResult,
    WorkflowSpec,
)


if TYPE_CHECKING:
    from cohezion.flux.aggregator import FluxAggregator
    from cohezion.graph.nodes import WorkflowNode


logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Graph-native execution engine with parallel dispatch.

    Algorithm:
      1. Validate the workflow DAG (detect cycles, verify nodes).
      2. Build adjacency structures for fast traversal.
      3. Topological dispatch loop:
         a. Find all READY nodes (all predecessors COMPLETED).
         b. Dispatch ready nodes in parallel via asyncio.gather.
         c. Propagate outputs through edges (message passing).
         d. Update node states. Repeat until done or failure.
    """

    def __init__(self, flux_aggregator: FluxAggregator | None = None) -> None:
        self._node_impls: dict[str, WorkflowNode] = {}
        self._flux = flux_aggregator

    def register_node(self, node: WorkflowNode) -> None:
        """Register a node implementation by its spec ID."""
        self._node_impls[node.spec.id] = node

    def validate_dag(self, workflow: WorkflowSpec) -> list[str]:
        """Validate workflow is a valid DAG. Returns list of error strings."""
        errors: list[str] = []
        node_ids = {n.id for n in workflow.nodes}

        if workflow.entry_node_id not in node_ids:
            errors.append(f"Entry node '{workflow.entry_node_id}' not found in nodes")

        for exit_id in workflow.exit_node_ids:
            if exit_id not in node_ids:
                errors.append(f"Exit node '{exit_id}' not found in nodes")

        for edge in workflow.edges:
            if edge.sender_id not in node_ids:
                errors.append(f"Edge '{edge.id}' references missing sender '{edge.sender_id}'")
            if edge.receiver_id not in node_ids:
                errors.append(f"Edge '{edge.id}' references missing receiver '{edge.receiver_id}'")

        if self._has_cycle(workflow):
            errors.append("Workflow contains a cycle — must be a DAG")

        return errors

    async def execute(
        self,
        workflow: WorkflowSpec,
        initial_input: dict[str, Any],
    ) -> WorkflowResult:
        """Execute a workflow graph with topological dispatch."""
        start_time = time.monotonic()

        errors = self.validate_dag(workflow)
        if errors:
            for err in errors:
                logger.warning("DAG validation failed [workflow=%s]: %s", workflow.id, err)
            return WorkflowResult(
                workflow_id=workflow.id,
                status="failed",
                node_results={},
                final_output={},
                total_duration_ms=0,
                total_tokens=0,
            )

        node_states: dict[str, NodeStatus] = {n.id: NodeStatus.PENDING for n in workflow.nodes}
        node_results: dict[str, NodeResult] = {}
        node_data: dict[str, dict[str, Any]] = {}  # accumulated inputs per node
        failed_nodes: set[str] = set()

        predecessors = self._build_predecessors(workflow)

        # Seed all root nodes (no incoming edges) with initial input
        for node in workflow.nodes:
            if not predecessors.get(node.id):
                node_data[node.id] = dict(initial_input)
        successors = workflow.adjacency_list()
        edge_lookup = self._build_edge_lookup(workflow)

        while True:
            ready = self._find_ready_nodes(
                workflow,
                node_states,
                predecessors,
                failed_nodes,
            )
            if not ready:
                break

            for nid in ready:
                node_states[nid] = NodeStatus.RUNNING

            results = await asyncio.gather(
                *[self._dispatch_node(nid, node_data.get(nid, {})) for nid in ready],
                return_exceptions=True,
            )

            for nid, result in zip(ready, results, strict=False):
                if isinstance(result, BaseException):
                    logger.error(
                        "Node execution failed [workflow=%s node=%s]: %s: %s",
                        workflow.id,
                        nid,
                        type(result).__name__,
                        result,
                    )
                    nr = NodeResult(
                        node_id=nid,
                        status=NodeStatus.FAILED,
                        output={},
                        metrics={},
                        duration_ms=0,
                        error=f"{type(result).__name__}: {result}",
                    )
                    node_states[nid] = NodeStatus.FAILED
                    node_results[nid] = nr
                    failed_nodes.add(nid)
                    self._mark_downstream_skipped(
                        nid,
                        successors,
                        node_states,
                        node_results,
                        failed_nodes,
                    )
                else:
                    node_states[nid] = NodeStatus.COMPLETED
                    node_results[nid] = result
                    self._record_to_flux(nid, result)
                    # Propagate output through edges
                    for succ_id in successors.get(nid, []):
                        if succ_id not in node_data:
                            node_data[succ_id] = {}
                        edge_taken = False
                        for edge in edge_lookup.get((nid, succ_id), []):
                            # Skip conditional edges that don't match the route
                            # returned by this node (e.g. LogicSwitchNode).
                            if edge.condition is not None:
                                route_matches = any(
                                    v == edge.condition for v in result.output.values()
                                )
                                if not route_matches:
                                    continue
                            edge_taken = True
                            for key in edge.keys:
                                if key in result.output:
                                    node_data[succ_id][key] = result.output[key]
                            # If no specific keys, pass all output
                            if not edge.keys:
                                node_data[succ_id].update(result.output)
                        # If every edge to this successor was conditional and
                        # none matched, the successor is on an untaken branch —
                        # mark it SKIPPED so the workflow doesn't stall.
                        if not edge_taken:
                            self._mark_downstream_skipped(
                                succ_id,
                                successors,
                                node_states,
                                node_results,
                                failed_nodes,
                            )
                            node_states[succ_id] = NodeStatus.SKIPPED
                            node_results[succ_id] = NodeResult(
                                node_id=succ_id,
                                status=NodeStatus.SKIPPED,
                                output={},
                                metrics={},
                                duration_ms=0,
                            )

        # Determine final output from exit nodes
        final_output: dict[str, Any] = {}
        for exit_id in workflow.exit_node_ids:
            if exit_id in node_results and node_results[exit_id].status == NodeStatus.COMPLETED:
                final_output.update(node_results[exit_id].output)

        all_completed = all(
            s in (NodeStatus.COMPLETED, NodeStatus.SKIPPED) for s in node_states.values()
        )
        has_failure = any(s == NodeStatus.FAILED for s in node_states.values())

        if has_failure:
            status = "failed"
        elif all_completed:
            status = "completed"
        else:
            status = "partial"

        total_ms = (time.monotonic() - start_time) * 1000
        total_tokens = sum(nr.metrics.get("tokens", 0) for nr in node_results.values())

        return WorkflowResult(
            workflow_id=workflow.id,
            status=status,
            node_results=node_results,
            final_output=final_output,
            total_duration_ms=total_ms,
            total_tokens=total_tokens,
        )

    async def _dispatch_node(
        self,
        node_id: str,
        inputs: dict[str, Any],
    ) -> NodeResult:
        """Execute a single node and return its result."""
        impl = self._node_impls.get(node_id)
        if impl is None:
            logger.warning(
                "No implementation registered for node '%s' — treating as passthrough",
                node_id,
            )
            return NodeResult(
                node_id=node_id,
                status=NodeStatus.COMPLETED,
                output=inputs,  # passthrough
                metrics={"passthrough": True},
                duration_ms=0,
            )

        start = time.monotonic()
        output = await impl.forward(inputs)
        duration_ms = (time.monotonic() - start) * 1000

        return NodeResult(
            node_id=node_id,
            status=NodeStatus.COMPLETED,
            output=output,
            metrics={},
            duration_ms=duration_ms,
        )

    def _record_to_flux(self, node_id: str, result: NodeResult) -> None:
        """Record a compact execution summary to FLUX history. Non-blocking."""
        if self._flux is None:
            return
        impl = self._node_impls.get(node_id)
        node_name = impl.spec.name if impl else node_id
        desc = impl.spec.attributes.get("description", "") if impl else ""
        output_keys = list(result.output.keys())[:5]
        parts = [f"{node_name} completed"]
        if desc:
            parts.append(desc[:120])
        parts.append(f"outputs: {' '.join(output_keys)}")
        summary = " — ".join(parts)
        try:
            self._flux.record_history(
                summary[:300],  # Hard cap for token efficiency
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "status": result.status.value,
                    "output_keys": output_keys,
                    "duration_ms": result.duration_ms,
                },
            )
        except Exception:
            logger.warning(
                "FLUX history recording failed for node '%s' (non-blocking)",
                node_id,
                exc_info=True,
            )

    def _find_ready_nodes(
        self,
        workflow: WorkflowSpec,
        states: dict[str, NodeStatus],
        predecessors: dict[str, list[str]],
        failed_nodes: set[str],
    ) -> list[str]:
        """Find nodes whose predecessors are all completed (not failed/skipped)."""
        ready = []
        for node in workflow.nodes:
            if states[node.id] != NodeStatus.PENDING:
                continue
            if node.id in failed_nodes:
                continue
            preds = predecessors.get(node.id, [])
            if all(states.get(p) == NodeStatus.COMPLETED for p in preds):
                ready.append(node.id)
        return ready

    def _mark_downstream_skipped(
        self,
        failed_id: str,
        successors: dict[str, list[str]],
        states: dict[str, NodeStatus],
        results: dict[str, NodeResult],
        failed_nodes: set[str],
    ) -> None:
        """Mark all downstream nodes of a failed node as SKIPPED."""
        queue = deque(successors.get(failed_id, []))
        while queue:
            nid = queue.popleft()
            if states.get(nid) in (NodeStatus.SKIPPED, NodeStatus.COMPLETED, NodeStatus.FAILED):
                continue
            states[nid] = NodeStatus.SKIPPED
            failed_nodes.add(nid)
            results[nid] = NodeResult(
                node_id=nid,
                status=NodeStatus.SKIPPED,
                output={},
                metrics={},
                duration_ms=0,
            )
            queue.extend(successors.get(nid, []))

    def _has_cycle(self, workflow: WorkflowSpec) -> bool:
        """Detect cycles using Kahn's algorithm (ignores dangling edges)."""
        node_ids = {n.id for n in workflow.nodes}
        adj = workflow.adjacency_list()
        in_degree: dict[str, int] = {n.id: 0 for n in workflow.nodes}
        for edge in workflow.edges:
            if edge.sender_id in node_ids and edge.receiver_id in in_degree:
                in_degree[edge.receiver_id] += 1

        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        visited = 0
        while queue:
            nid = queue.popleft()
            visited += 1
            for succ in adj.get(nid, []):
                if succ in in_degree:
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        queue.append(succ)

        return visited != len(workflow.nodes)

    @staticmethod
    def _build_predecessors(workflow: WorkflowSpec) -> dict[str, list[str]]:
        preds: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
        for edge in workflow.edges:
            if edge.receiver_id in preds:
                preds[edge.receiver_id].append(edge.sender_id)
        return preds

    @staticmethod
    def _build_edge_lookup(
        workflow: WorkflowSpec,
    ) -> dict[tuple[str, str], list[EdgeSpec]]:
        lookup: dict[tuple[str, str], list[EdgeSpec]] = {}
        for edge in workflow.edges:
            key = (edge.sender_id, edge.receiver_id)
            lookup.setdefault(key, []).append(edge)
        return lookup
