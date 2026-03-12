"""Workflow graph persistence — in-memory store with SurrealDB schema.

Provides CRUD for workflow runs, node results, and edge relations.
Uses in-memory storage by default; SurrealDB schema is generated for
production deployment via ``get_schema_statements()``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.graph.types import (
        EdgeSpec,
        NodeResult,
        WorkflowResult,
        WorkflowSpec,
    )


logger = logging.getLogger(__name__)


class WorkflowPersistence:
    """Persist and query workflow execution graphs.

    In-memory by default. Call ``get_schema_statements()`` for SurrealDB
    DDL to set up production tables.
    """

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._node_results: dict[str, dict[str, dict[str, Any]]] = {}
        self._edges: dict[str, list[dict[str, Any]]] = {}

    def persist_workflow_run(
        self,
        workflow: WorkflowSpec,
        result: WorkflowResult,
    ) -> str:
        """Store a workflow run record. Returns the workflow ID."""
        self._runs[result.workflow_id] = {
            "id": result.workflow_id,
            "name": workflow.name,
            "status": result.status,
            "total_duration_ms": result.total_duration_ms,
            "total_tokens": result.total_tokens,
            "final_output": result.final_output,
            "node_count": len(workflow.nodes),
            "edge_count": len(workflow.edges),
        }
        return result.workflow_id

    def get_workflow_run(self, workflow_id: str) -> dict[str, Any] | None:
        return self._runs.get(workflow_id)

    def list_workflow_runs(self) -> list[dict[str, Any]]:
        return list(self._runs.values())

    def persist_node_results(
        self,
        workflow_id: str,
        node_results: dict[str, NodeResult],
    ) -> None:
        """Store node execution results for a workflow run."""
        self._node_results[workflow_id] = {
            nid: {
                "node_id": nr.node_id,
                "status": nr.status.value,
                "output": nr.output,
                "metrics": nr.metrics,
                "duration_ms": nr.duration_ms,
                "error": nr.error,
            }
            for nid, nr in node_results.items()
        }

    def get_node_results(self, workflow_id: str) -> dict[str, dict[str, Any]]:
        return self._node_results.get(workflow_id, {})

    def persist_edges(
        self,
        workflow_id: str,
        edges: list[EdgeSpec],
    ) -> None:
        """Store workflow edges."""
        self._edges[workflow_id] = [
            {
                "id": e.id,
                "sender_id": e.sender_id,
                "receiver_id": e.receiver_id,
                "keys": e.keys,
                "condition": e.condition,
                "weight": e.weight,
            }
            for e in edges
        ]

    def get_edges(self, workflow_id: str) -> list[dict[str, Any]]:
        return self._edges.get(workflow_id, [])

    @staticmethod
    def get_schema_statements() -> list[str]:
        """Return SurrealDB DDL statements for workflow graph tables."""
        return [
            # Node records
            "DEFINE TABLE workflow_node SCHEMAFULL",
            "DEFINE FIELD workflow_id ON TABLE workflow_node TYPE string",
            "DEFINE FIELD name ON TABLE workflow_node TYPE string",
            "DEFINE FIELD node_type ON TABLE workflow_node TYPE string",
            "DEFINE FIELD status ON TABLE workflow_node TYPE string DEFAULT 'pending'",
            "DEFINE FIELD input_data ON TABLE workflow_node TYPE object DEFAULT {}",
            "DEFINE FIELD output_data ON TABLE workflow_node TYPE object DEFAULT {}",
            "DEFINE FIELD metrics ON TABLE workflow_node TYPE object DEFAULT {}",
            "DEFINE FIELD duration_ms ON TABLE workflow_node TYPE float DEFAULT 0.0",
            "DEFINE FIELD error ON TABLE workflow_node TYPE option<string>",
            "DEFINE FIELD created_at ON TABLE workflow_node TYPE datetime DEFAULT time::now()",
            "DEFINE INDEX idx_wf_node ON workflow_node FIELDS workflow_id",
            # Edge table (used with RELATE)
            "DEFINE TABLE workflow_edge SCHEMAFULL",
            "DEFINE FIELD in ON TABLE workflow_edge TYPE record<workflow_node>",
            "DEFINE FIELD out ON TABLE workflow_edge TYPE record<workflow_node>",
            "DEFINE FIELD keys ON TABLE workflow_edge TYPE array DEFAULT []",
            "DEFINE FIELD condition ON TABLE workflow_edge TYPE option<string>",
            "DEFINE FIELD weight ON TABLE workflow_edge TYPE float DEFAULT 1.0",
            "DEFINE FIELD message_log ON TABLE workflow_edge TYPE array DEFAULT []",
            # Run records
            "DEFINE TABLE workflow_run SCHEMAFULL",
            "DEFINE FIELD name ON TABLE workflow_run TYPE string",
            "DEFINE FIELD status ON TABLE workflow_run TYPE string DEFAULT 'pending'",
            "DEFINE FIELD total_duration_ms ON TABLE workflow_run TYPE float DEFAULT 0.0",
            "DEFINE FIELD total_tokens ON TABLE workflow_run TYPE int DEFAULT 0",
            "DEFINE FIELD created_at ON TABLE workflow_run TYPE datetime DEFAULT time::now()",
        ]
