"""Vibe Specifier — VibeIntent to VibeWorkflowSpec.

Maps an extracted intent to a concrete workflow description using:
- Operation-type templates (RESEARCH → [researcher, reviewer])
- Complexity scaling (more nodes for higher complexity)
- Optional CapabilityRegistry for capability-aware node selection
- Optional FLUX context for vault template matching
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cohezion.vibe.types import (
    EdgeDescription,
    NodeDescription,
    OperationType,
    VibeIntent,
    VibeWorkflowSpec,
)


if TYPE_CHECKING:
    from cohezion.flux.aggregator import FluxAggregator


logger = logging.getLogger(__name__)


# Template: (agent_role, role_description, output_keys)
_NodeTemplate = tuple[str, str, list[str]]

# Maps OperationType to ordered node templates per complexity tier
# Tiers: [complexity=1, complexity=2, complexity=3+]
_OPERATION_TEMPLATES: dict[OperationType, list[list[_NodeTemplate]]] = {
    OperationType.RESEARCH: [
        # complexity 1
        [("researcher", "Gather relevant background information", ["research_summary"])],
        # complexity 2
        [
            ("researcher", "Gather relevant background information", ["research_summary"]),
            ("reviewer", "Synthesise and critique findings", ["final_report"]),
        ],
        # complexity 3+
        [
            ("researcher", "Gather relevant background information", ["research_summary"]),
            ("analyst", "Analyse patterns and identify key insights", ["insights"]),
            ("reviewer", "Synthesise findings into actionable report", ["final_report"]),
        ],
    ],
    OperationType.IMPLEMENT: [
        # complexity 1
        [("coder", "Write implementation code", ["code"])],
        # complexity 2
        [
            ("planner", "Create implementation plan and design", ["plan"]),
            ("coder", "Write implementation code", ["code"]),
        ],
        # complexity 3+
        [
            ("planner", "Create implementation plan and design", ["plan"]),
            ("coder", "Write implementation code", ["code"]),
            ("tester", "Write tests and verify correctness", ["test_results"]),
        ],
    ],
    OperationType.ANALYZE: [
        # complexity 1
        [("analyst", "Analyse data and produce summary", ["analysis"])],
        # complexity 2
        [
            ("analyst", "Analyse data and produce summary", ["analysis"]),
            ("reporter", "Format and present results", ["report"]),
        ],
        # complexity 3+
        [
            ("collector", "Gather and preprocess input data", ["raw_data"]),
            ("analyst", "Analyse patterns and relationships", ["analysis"]),
            ("reporter", "Format findings into structured report", ["report"]),
        ],
    ],
    OperationType.TRANSFORM: [
        # complexity 1
        [("transformer", "Transform input data to target format", ["output"])],
        # complexity 2
        [
            ("parser", "Parse and validate input data", ["parsed"]),
            ("transformer", "Transform to target format", ["output"]),
        ],
        # complexity 3+
        [
            ("parser", "Parse and validate input data", ["parsed"]),
            ("transformer", "Transform to target format", ["intermediate"]),
            ("validator", "Validate transformed output", ["output"]),
        ],
    ],
    OperationType.VALIDATE: [
        # complexity 1
        [("validator", "Validate inputs against requirements", ["validation_result"])],
        # complexity 2
        [
            ("inspector", "Inspect artifacts against criteria", ["findings"]),
            ("validator", "Produce validation summary", ["validation_result"]),
        ],
        # complexity 3+
        [
            ("inspector", "Inspect artifacts against criteria", ["findings"]),
            ("tester", "Run automated checks", ["test_results"]),
            ("validator", "Consolidate validation report", ["validation_result"]),
        ],
    ],
    OperationType.ORCHESTRATE: [
        # complexity 1
        [("orchestrator", "Coordinate workflow execution", ["result"])],
        # complexity 2
        [
            ("planner", "Plan and decompose the workflow", ["plan"]),
            ("orchestrator", "Execute and coordinate agents", ["result"]),
        ],
        # complexity 3+
        [
            ("planner", "Plan and decompose the workflow", ["plan"]),
            ("orchestrator", "Execute and coordinate agents", ["intermediate"]),
            ("monitor", "Track progress and handle failures", ["result"]),
        ],
    ],
    OperationType.UNKNOWN: [
        # Always generic single node
        [("agent", "Execute requested task", ["result"])],
        [("agent", "Execute requested task", ["result"])],
        [("agent", "Execute requested task", ["result"])],
    ],
}


def _pick_template(op: OperationType, complexity: int) -> list[_NodeTemplate]:
    """Select template tier based on operation type and complexity."""
    templates = _OPERATION_TEMPLATES.get(op, _OPERATION_TEMPLATES[OperationType.UNKNOWN])
    if complexity <= 1:
        tier = 0
    elif complexity <= 2:
        tier = 1
    else:
        tier = 2
    return templates[min(tier, len(templates) - 1)]


def _build_nodes_from_template(
    template: list[_NodeTemplate],
    intent: VibeIntent,
) -> list[NodeDescription]:
    """Convert template tuples to NodeDescription objects."""
    nodes: list[NodeDescription] = []
    prev_outputs: list[str] = []
    for i, (agent_role, role_desc, outputs) in enumerate(template):
        node = NodeDescription(
            name=f"{agent_role}-{i + 1}" if len(template) > 1 else agent_role,
            role=role_desc,
            agent_role=agent_role,
            inputs=list(prev_outputs),
            outputs=list(outputs),
        )
        nodes.append(node)
        prev_outputs = list(outputs)
    return nodes


def _build_edges(nodes: list[NodeDescription]) -> list[EdgeDescription]:
    """Build a linear chain of edges from node descriptions."""
    edges: list[EdgeDescription] = []
    for i in range(len(nodes) - 1):
        src = nodes[i]
        dst = nodes[i + 1]
        edges.append(
            EdgeDescription(
                from_name=src.name,
                to_name=dst.name,
                keys=list(src.outputs),
            )
        )
    return edges


class VibeSpecifier:
    """Maps a VibeIntent to a VibeWorkflowSpec.

    Uses operation-type templates for node layout, scaled by complexity.
    Optionally consults a CapabilityRegistry to select specific capabilities
    and a FluxAggregator to surface similar past workflows.

    Parameters
    ----------
    capability_registry : Any | None
        Optional registry for capability-aware node naming.
    flux_aggregator : FluxAggregator | None
        Optional FLUX aggregator for vault template matching.
    """

    def __init__(
        self,
        capability_registry: Any | None = None,
        flux_aggregator: FluxAggregator | None = None,
    ) -> None:
        self._registry = capability_registry
        self._flux = flux_aggregator

    async def specify(self, intent: VibeIntent) -> VibeWorkflowSpec:
        """Map a VibeIntent to a VibeWorkflowSpec.

        Parameters
        ----------
        intent : VibeIntent
            Parsed intent from VibeParser.

        Returns
        -------
        VibeWorkflowSpec
            Proposed nodes, edges, and parameters.
        """
        template = _pick_template(intent.operation_type, intent.complexity)
        nodes = _build_nodes_from_template(template, intent)
        edges = _build_edges(nodes)

        # Optionally enrich node names from registry
        if self._registry is not None:
            nodes = await self._enrich_from_registry(nodes, intent)

        # Optionally find similar past workflows via FLUX
        similar: list[str] = []
        template_used: str | None = None
        if self._flux is not None:
            similar, template_used = await self._find_similar_workflows(intent)

        return VibeWorkflowSpec(
            intent=intent,
            node_descriptions=nodes,
            edge_descriptions=edges,
            parameters={"complexity": intent.complexity, "operation": intent.operation_type.value},
            similar_past_workflows=similar,
            template_used=template_used,
        )

    async def _enrich_from_registry(
        self,
        nodes: list[NodeDescription],
        intent: VibeIntent,
    ) -> list[NodeDescription]:
        """Replace generic agent roles with specific capabilities from registry."""
        try:
            # Query registry for capabilities matching the intent keywords
            query = " ".join(intent.keywords[:5]) if intent.keywords else intent.raw_text
            capabilities = self._registry.find(query, top_k=len(nodes))
            cap_list = list(capabilities or [])
            for i, node in enumerate(nodes):
                if i < len(cap_list):
                    cap = cap_list[i]
                    # Preserve the role/agent_role from template, just log capability found
                    logger.debug("Matched capability %s to node %s", cap.name, node.name)
        except Exception:
            logger.debug("CapabilityRegistry query failed (non-blocking)")
        return nodes

    async def _find_similar_workflows(self, intent: VibeIntent) -> tuple[list[str], str | None]:
        """Query FLUX for similar past workflows and applicable templates."""
        try:
            ctx = await self._flux.get_context(intent.raw_text, top_k=5)  # type: ignore[union-attr]
            similar: list[str] = []
            template_used: str | None = None
            for block in ctx.blocks:
                meta = block.metadata or {}
                wf_id = meta.get("workflow_id")
                if wf_id:
                    similar.append(str(wf_id))
                if template_used is None:
                    template_used = meta.get("template_name")
            return similar, template_used
        except Exception:
            logger.debug("FLUX workflow search failed (non-blocking)")
            return [], None
