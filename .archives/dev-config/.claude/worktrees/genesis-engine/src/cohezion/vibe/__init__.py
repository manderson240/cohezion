"""Vibe Graphing — Natural Language to Executable Workflow.

Translates unstructured NL intent into a DAG-native WorkflowSpec ready
for the graph execution engine. Three-stage pipeline:

1. ``VibeParser`` — extracts keywords and operation type from raw text
2. ``VibeSpecifier`` — maps intent to node/edge descriptions using templates
3. ``VibeCompiler`` — compiles descriptions to a concrete WorkflowSpec

The ``VibeOrchestrator`` chains all three stages and optionally executes
the compiled graph via WorkflowEngine.
"""

from cohezion.vibe.compiler import VibeCompiler
from cohezion.vibe.orchestrator import VibeOrchestrator
from cohezion.vibe.parser import VibeParser
from cohezion.vibe.specifier import VibeSpecifier
from cohezion.vibe.types import (
    EdgeDescription,
    NodeDescription,
    OperationType,
    VibeIntent,
    VibeWorkflowSpec,
)


__all__ = [
    "EdgeDescription",
    "NodeDescription",
    "OperationType",
    "VibeCompiler",
    "VibeIntent",
    "VibeOrchestrator",
    "VibeParser",
    "VibeSpecifier",
    "VibeWorkflowSpec",
]
