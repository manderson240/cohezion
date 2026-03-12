"""Workflow builder — constructs WorkflowSpec from TeamPlan and other inputs.

Bridges existing Cohezion team orchestration (AgentSpec/TaskSpec/TeamPlan)
into the graph execution model (NodeSpec/EdgeSpec/WorkflowSpec).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from cohezion.graph.types import EdgeSpec, NodeSpec, WorkflowSpec


if TYPE_CHECKING:
    from cohezion.swarm.team_orchestrator import TeamPlan


class WorkflowBuilder:
    """Construct WorkflowSpec from various input formats."""

    def from_team_plan(self, plan: TeamPlan) -> WorkflowSpec:
        """Convert a TeamPlan into a WorkflowSpec.

        Maps TaskSpec -> NodeSpec with agent_spec/task_spec preserved.
        Maps blocked_by -> EdgeSpec dependencies.
        """
        agent_by_name = {a.name: a for a in plan.agents}

        nodes: list[NodeSpec] = []
        for task in plan.tasks:
            agent = agent_by_name.get(task.assigned_to)
            nodes.append(
                NodeSpec(
                    id=task.id,
                    name=task.subject,
                    node_type="agent",
                    pull_keys=[],
                    push_keys=[],
                    attributes={"description": task.description, "tags": task.tags},
                    agent_spec=agent,
                    task_spec=task,
                )
            )

        edges: list[EdgeSpec] = []
        for task in plan.tasks:
            for dep_id in task.blocked_by:
                edges.append(
                    EdgeSpec(
                        id=f"e-{dep_id}-{task.id}",
                        sender_id=dep_id,
                        receiver_id=task.id,
                        keys=[],
                    )
                )

        nodes_with_predecessors = {e.receiver_id for e in edges}
        nodes_with_successors = {e.sender_id for e in edges}

        roots = [n.id for n in nodes if n.id not in nodes_with_predecessors]
        leaves = [n.id for n in nodes if n.id not in nodes_with_successors]

        entry_node_id = roots[0] if roots else (nodes[0].id if nodes else "")
        exit_node_ids = leaves if leaves else ([nodes[-1].id] if nodes else [])

        return WorkflowSpec(
            id=f"wf-{uuid.uuid4().hex[:8]}",
            name=plan.name,
            nodes=nodes,
            edges=edges,
            entry_node_id=entry_node_id,
            exit_node_ids=exit_node_ids,
            attributes={"intent": plan.intent},
        )
