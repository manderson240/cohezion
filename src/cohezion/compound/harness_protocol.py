r"""Harness Context Protocol (HCP) & Model-Harness Co-Design
=========================================================
Synthesizes arXiv:2608.09819:
"Macaron-V1: Towards Open Continual Learning with Self-Improvement and Mixture-of-LoRA"

Key Formalisms:
1. Model-Harness Co-Design:
   - Frozen foundation models (NPU FastFlowLM, CPU llama.cpp, Cloud MoE).
   - Domain capability is expanded via specialized execution harnesses and external contracts.

2. Harness Context Protocol (HCP v1.0):
   - Formal versioned contract governing how models interact with execution environments:
     * Protocol Versioning (semantic versioning of capabilities).
     * Action Substrates (REPL, AST verification, tool invocation schema).
     * Deterministic Verifiers (AutoHarness zero-cost verification gates).
     * Structured Receipt Format (standardized feedback for Recuris & Hippocam).
"""

from __future__ import annotations

import ast
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


logger = logging.getLogger(__name__)


class ActionSubstrateType(StrEnum):
    """Execution substrates supported under HCP."""

    STATEFUL_REPL = "stateful_repl"
    DETERMINISTIC_AST = "deterministic_ast"
    EXTERNAL_CLI = "external_cli"
    KAGGLE_KERNEL = "kaggle_kernel"


@dataclass(frozen=True)
class ActionReceipt:
    """Standardized environment execution receipt returned under HCP."""

    action_id: str
    substrate: ActionSubstrateType
    success: bool
    return_code: int
    output_payload: str
    diagnostic: str = ""
    latency_ms: float = 0.0
    verified_by: str = "HCP_VERIFIER"


@dataclass
class ToolContract:
    """Formal interface contract for an agent tool or invariant verifier."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    verifier_fn: Callable[[Any], tuple[bool, str]] | None = None
    timeout_s: float = 30.0


class HarnessContextProtocol:
    """Harness Context Protocol (HCP) v1.0 Engine.

    Coordinates stateful action execution and validation across local NPU and cloud models.
    """

    PROTOCOL_VERSION = "1.0.0"

    def __init__(self, agent_id: str = "cohezion_sovereign_agent") -> None:
        self.agent_id = agent_id
        self.registered_tools: dict[str, ToolContract] = {}

    def register_tool(self, contract: ToolContract) -> None:
        self.registered_tools[contract.name] = contract
        logger.debug("HCP [%s]: Registered tool contract '%s'", self.agent_id, contract.name)

    def generate_hcp_manifest(self) -> dict[str, Any]:
        """Generates the HCP context manifest injected into the model's system prompt."""
        return {
            "hcp_version": self.PROTOCOL_VERSION,
            "agent_id": self.agent_id,
            "available_tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "schema": t.parameters_schema,
                }
                for t in self.registered_tools.values()
            ],
            "action_rules": [
                "1. All state-changing actions MUST return an ActionReceipt.",
                "2. Goals in Working Memory are only marked VERIFIED upon success=True in receipt.",
                "3. Inconclusive failures MUST be routed to trace-based failure localization.",
            ],
        }

    def execute_ast_action(self, code_str: str) -> ActionReceipt:
        """Executes a code action under the deterministic AST substrate."""
        try:
            tree = ast.parse(code_str)
            # Verify no forbidden constructs
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in ("eval", "exec", "__import__")
                ):
                    return ActionReceipt(
                        action_id="ast_check",
                        substrate=ActionSubstrateType.DETERMINISTIC_AST,
                        success=False,
                        return_code=1,
                        output_payload="",
                        diagnostic=f"Forbidden function call: {node.func.id}",
                    )
            return ActionReceipt(
                action_id="ast_check",
                substrate=ActionSubstrateType.DETERMINISTIC_AST,
                success=True,
                return_code=0,
                output_payload="AST cleanly parsed and verified.",
            )
        except SyntaxError as e:
            return ActionReceipt(
                action_id="ast_check",
                substrate=ActionSubstrateType.DETERMINISTIC_AST,
                success=False,
                return_code=1,
                output_payload="",
                diagnostic=f"SyntaxError: {e}",
            )
