"""Vibe Orchestrator — full NL-to-execution pipeline.

Chains VibeParser → VibeSpecifier → VibeCompiler → WorkflowEngine into a
single ``vibe(nl_text)`` entry point.  When ``execute=False`` the compiled
WorkflowSpec is returned so callers can inspect or modify it before running.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cohezion.graph.engine import WorkflowEngine
from cohezion.graph.types import NodeSpec, WorkflowResult, WorkflowSpec
from cohezion.vibe.compiler import VibeCompiler
from cohezion.vibe.parser import VibeParser
from cohezion.vibe.specifier import VibeSpecifier
from cohezion.vibe.types import OperationType


if TYPE_CHECKING:
    from cohezion.flux.aggregator import FluxAggregator


logger = logging.getLogger(__name__)

# Minimal fallback workflow for empty/unknown intent
_FALLBACK_NODE = NodeSpec(
    id="vibe-fallback-node",
    name="agent",
    node_type="agent",
    pull_keys=[],
    push_keys=["result"],
    attributes={"agent_role": "agent", "vibe_compiled": True},
)


def _build_fallback_spec(intent_text: str) -> WorkflowSpec:
    """Return a minimal single-node WorkflowSpec for empty/unknown intent."""
    return WorkflowSpec(
        id="vibe-fallback",
        name=f"vibe:{intent_text[:40] or 'unknown'}",
        nodes=[_FALLBACK_NODE],
        edges=[],
        entry_node_id=_FALLBACK_NODE.id,
        exit_node_ids=[_FALLBACK_NODE.id],
        attributes={"vibe_compiled": True, "fallback": True},
    )


class VibeOrchestrator:
    """End-to-end NL → WorkflowSpec / WorkflowResult pipeline.

    Parameters
    ----------
    parser : VibeParser | None
        VibeParser instance (defaults to plain parser).
    specifier : VibeSpecifier | None
        VibeSpecifier instance (defaults to plain specifier).
    compiler : VibeCompiler | None
        VibeCompiler instance (defaults to plain compiler).
    engine : WorkflowEngine | None
        WorkflowEngine instance (defaults to plain engine).
    """

    def __init__(
        self,
        parser: VibeParser | None = None,
        specifier: VibeSpecifier | None = None,
        compiler: VibeCompiler | None = None,
        engine: WorkflowEngine | None = None,
    ) -> None:
        self._parser = parser or VibeParser()
        self._specifier = specifier or VibeSpecifier()
        self._compiler = compiler or VibeCompiler()
        self._engine = engine or WorkflowEngine()

    @classmethod
    def create_default(
        cls,
        flux_aggregator: FluxAggregator | None = None,
        capability_registry: Any | None = None,
    ) -> VibeOrchestrator:
        """Factory that wires FLUX and CapabilityRegistry when available.

        Parameters
        ----------
        flux_aggregator : FluxAggregator | None
            Optional FLUX aggregator for enriched parsing.
        capability_registry : Any | None
            Optional capability registry for node selection.

        Returns
        -------
        VibeOrchestrator
            Fully configured orchestrator.
        """
        parser = VibeParser(flux_aggregator=flux_aggregator)
        specifier = VibeSpecifier(
            capability_registry=capability_registry,
            flux_aggregator=flux_aggregator,
        )
        compiler = VibeCompiler()
        engine = WorkflowEngine()
        return cls(parser=parser, specifier=specifier, compiler=compiler, engine=engine)

    async def vibe(
        self,
        nl_text: str,
        execute: bool = True,
        initial_input: dict[str, Any] | None = None,
    ) -> WorkflowSpec | WorkflowResult:
        """Parse, specify, compile, and optionally execute a natural language workflow.

        Parameters
        ----------
        nl_text : str
            Natural language description of the desired workflow.
        execute : bool
            If True, execute the compiled workflow and return WorkflowResult.
            If False, return the compiled WorkflowSpec for inspection.
        initial_input : dict[str, Any] | None
            Optional initial data dict passed to the first node.

        Returns
        -------
        WorkflowSpec | WorkflowResult
            WorkflowSpec if ``execute=False``, WorkflowResult if ``execute=True``.
        """
        # Step 1: Parse NL text → VibeIntent
        intent = await self._parser.parse(nl_text)

        # Step 2: Handle empty/unknown intent with fallback
        if not nl_text or not nl_text.strip() or intent.operation_type == OperationType.UNKNOWN:
            logger.debug("Vibe: using fallback spec for intent '%s'", nl_text[:50])
            spec = _build_fallback_spec(nl_text)
        else:
            # Step 3: Specify intent → VibeWorkflowSpec
            vibe_spec = await self._specifier.specify(intent)
            # Step 4: Compile → WorkflowSpec
            spec = self._compiler.compile(vibe_spec)

        if not execute:
            return spec

        # Step 5: Execute workflow
        return await self._engine.execute(spec, initial_input=initial_input or {})
