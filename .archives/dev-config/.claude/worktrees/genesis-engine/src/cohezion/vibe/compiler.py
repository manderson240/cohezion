"""Vibe Compiler — VibeWorkflowSpec to WorkflowSpec (executable graph).

Converts human-readable node/edge descriptions into concrete NodeSpec and
EdgeSpec objects that the WorkflowEngine can execute. Validates references
and sets entry/exit nodes automatically.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from cohezion.graph.types import EdgeSpec, NodeSpec, WorkflowSpec


if TYPE_CHECKING:
    from cohezion.vibe.types import VibeWorkflowSpec


class VibeCompiler:
    """Compiles a VibeWorkflowSpec into an executable WorkflowSpec.

    Mapping rules:
    - Each NodeDescription → NodeSpec with node_type="agent"
    - Each EdgeDescription → EdgeSpec
    - Entry node = NodeSpec with no incoming edges
    - Exit nodes = NodeSpecs with no outgoing edges

    Parameters
    ----------
    workflow_id_prefix : str
        Prefix for generated workflow IDs.
    """

    def __init__(self, workflow_id_prefix: str = "vibe") -> None:
        self._prefix = workflow_id_prefix

    def compile(self, vibe_spec: VibeWorkflowSpec) -> WorkflowSpec:
        """Compile VibeWorkflowSpec into a WorkflowSpec.

        Parameters
        ----------
        vibe_spec : VibeWorkflowSpec
            Output from VibeSpecifier.

        Returns
        -------
        WorkflowSpec
            Executable workflow ready for WorkflowEngine.

        Raises
        ------
        ValueError
            If node_descriptions is empty or edges reference unknown nodes.
        """
        if not vibe_spec.node_descriptions:
            raise ValueError("Cannot compile a VibeWorkflowSpec with no nodes")

        # Assign stable IDs to nodes (name → id)
        name_to_id: dict[str, str] = {
            node.name: f"{self._prefix}-node-{uuid.uuid4().hex[:8]}" for node in vibe_spec.node_descriptions
        }

        # Validate edges reference known nodes
        for edge in vibe_spec.edge_descriptions:
            if edge.from_name not in name_to_id:
                raise ValueError(
                    f"Edge references unknown source node '{edge.from_name}'. Known nodes: {list(name_to_id)}"
                )
            if edge.to_name not in name_to_id:
                raise ValueError(
                    f"Edge references unknown target node '{edge.to_name}'. Known nodes: {list(name_to_id)}"
                )

        # Build NodeSpec list
        nodes = [
            NodeSpec(
                id=name_to_id[desc.name],
                name=desc.name,
                node_type="agent",
                pull_keys=list(desc.inputs),
                push_keys=list(desc.outputs),
                attributes={
                    "agent_role": desc.agent_role,
                    "role": desc.role,
                    "vibe_compiled": True,
                },
            )
            for desc in vibe_spec.node_descriptions
        ]

        # Build EdgeSpec list
        edges = [
            EdgeSpec(
                id=f"{self._prefix}-edge-{uuid.uuid4().hex[:8]}",
                sender_id=name_to_id[e.from_name],
                receiver_id=name_to_id[e.to_name],
                keys=list(e.keys),
                condition=e.condition,
            )
            for e in vibe_spec.edge_descriptions
        ]

        # Determine entry/exit nodes
        receivers = {e.receiver_id for e in edges}
        senders = {e.sender_id for e in edges}
        entry_candidates = [n for n in nodes if n.id not in receivers]
        exit_candidates = [n for n in nodes if n.id not in senders]

        entry_node_id = entry_candidates[0].id if entry_candidates else nodes[0].id
        exit_node_ids = [n.id for n in exit_candidates] if exit_candidates else [nodes[-1].id]

        # Build workflow name from intent
        intent_text = vibe_spec.intent.raw_text or "vibe-workflow"
        name = f"vibe:{intent_text[:40]}"

        workflow_id = f"{self._prefix}-{uuid.uuid4().hex[:12]}"
        return WorkflowSpec(
            id=workflow_id,
            name=name,
            nodes=nodes,
            edges=edges,
            entry_node_id=entry_node_id,
            exit_node_ids=exit_node_ids,
            attributes={
                "vibe_compiled": True,
                "operation_type": vibe_spec.intent.operation_type.value,
                "complexity": vibe_spec.intent.complexity,
                **vibe_spec.parameters,
            },
        )
