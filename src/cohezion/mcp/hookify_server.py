"""
Hookify MCP Bridge Server
Cross-platform rule engine with Obsidian vault + SurrealDB graph integration
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from cohezion.hookify.validator import HookifyValidator, Rule


logger = logging.getLogger(__name__)

# Vault path from environment or default
VAULT_PATH = Path(os.getenv("VAULT_PATH", "/home/mike-anderson/vaults/cohezion-vault"))
RULES_FILE = Path(".agent/HOOKIFY_RULES.md")


class HookifyMCPBridge:
    """
    MCP Bridge for Hookify Rule Engine

    Integrates with:
    - Obsidian vault for rule definitions (Tier 1)
    - SurrealDB for runtime lever positions (Tier 2)
    - Graph synapses for violation tracking (Tier 3)
    """

    def __init__(self, vault_path: Path = VAULT_PATH):
        self.vault_path = vault_path
        self.rules_file = vault_path.parent / RULES_FILE

        # Initialize validator with rules from Git (Tier 1)
        if self.rules_file.exists():
            self.validator = HookifyValidator(rules_path=self.rules_file)
        else:
            # Fallback: use default rules
            self.validator = HookifyValidator(rules=self._get_default_rules())

        # SurrealDB client (lazy init)
        self._db = None

    def _get_default_rules(self) -> list[Rule]:
        """Default rules if no rules file exists"""
        return [
            Rule(
                id="hiho_stability_gate",
                trigger="pre_execute",
                condition="always",
                action="block_if_coherence_below_threshold",
                levers={"threshold": 0.5, "fallback_action": "decompose_request"},
                adversarial_tests=["test_hiho_convergence", "test_stability_boundary"],
            ),
            Rule(
                id="cosmological_ralph_loop",
                trigger="session_start",
                condition='goal.matches("cosmology|solver|universe")',
                action="ralph_loop.orchestrate",
                levers={
                    "coherence_threshold": 0.5,
                    "max_iterations": 20,
                    "auto_commit": True,
                    "witness_plate": "vault/hippocampus/changelog-{session_id}.md",
                },
                adversarial_tests=["test_cosmological_convergence", "test_ralph_loop_termination"],
            ),
            Rule(
                id="akashic_commit",
                trigger="post_execute",
                condition="execution_success",
                action="auto_commit_and_push",
                levers={
                    "commit_message_template": "Session {id}: {summary}\n\nCoherence: {coherence}",
                    "require_tests_pass": True,
                    "push_to_remote": True,
                },
                adversarial_tests=["test_commit_message_format", "test_git_coordination"],
            ),
        ]

    def _get_surrealdb_client(self) -> Any | None:
        """Lazy initialization of SurrealDB client"""
        if self._db is None:
            try:
                from surrealdb import Surreal

                db = Surreal("ws://localhost:8001")
                # Signin and use database
                # db.signin({"user": "root", "pass": "root"})
                # db.use("cohezion", "vault")
                self._db = db
            except Exception as e:
                logger.warning(f"Could not connect to SurrealDB: {e}")
                return None
        return self._db

    # =====================================================================
    # MCP Tool: Validation
    # =====================================================================

    async def validate_rule(self, trigger: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        MCP Tool: Validate execution context against rules

        Args:
            trigger: Event trigger (session_start, pre_execute, post_execute)
            context: Execution context with coherence, goal, etc.

        Returns:
            Validation result with proceed/block status and violations
        """
        try:
            result = self.validator.validate(trigger, context)

            # Log violations to graph (Tier 3)
            if result.violations:
                await self._log_violations_to_graph(trigger, context, result.violations)

            return {
                "proceed": result.proceed,
                "block": result.block,
                "violations": result.violations,
                "modifications": result.modifications,
                "rules_checked": len(self.validator.rules),
            }
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "proceed": True,  # Fail open
                "block": False,
                "error": str(e),
                "rules_checked": 0,
            }

    async def _log_violations_to_graph(self, trigger: str, context: dict, violations: list[dict]):
        """Write violations as latent synapses in SurrealDB graph"""
        client = self._get_surrealdb_client()
        if not client:
            return

        try:
            # Create violation neuron
            session_id = context.get("session_id", "unknown")

            # Check if session neuron exists
            session_neuron = f"neuron:hippocampus_session_{session_id}"

            for violation in violations:
                rule_id = violation.get("rule", "unknown")

                # Create latent synapse from session to rule
                message = violation.get("message", "")
                escaped_message = message.replace("'", "\\'")
                sql = (
                    f"RELATE {session_neuron}->synapse->neuron:prefrontal_{rule_id} "
                    f"SET link_type = 'latent', "
                    f"reason = '{escaped_message}', "
                    f"coherence = {context.get('coherence', 0)}, "
                    f"created = time::now();"
                )
                client.query(sql)

                logger.debug(f"Created latent synapse for violation: {rule_id}")

        except Exception as e:
            logger.warning(f"Could not log violations to graph: {e}")

    # =====================================================================
    # MCP Tool: Lever Management
    # =====================================================================

    async def get_levers(self, rule_id: str) -> dict[str, Any]:
        """
        MCP Tool: Get current lever positions for a rule

        Returns merged levers from Git defaults + SurrealDB overrides + ENV
        """
        try:
            positions = self.validator.get_lever_positions(rule_id)
            rule = self.validator.get_rule(rule_id)

            return {
                "rule_id": rule_id,
                "levers": positions,
                "source": {
                    "git_defaults": rule.levers if rule else {},
                    "db_overrides": self._load_db_overrides_for_rule(rule_id),
                    "env_overrides": self.validator._get_env_overrides(rule_id),
                },
            }
        except Exception as e:
            return {"error": str(e)}

    async def set_lever(self, rule_id: str, lever_name: str, value: Any) -> dict[str, Any]:
        """
        MCP Tool: Set lever position (persisted to SurrealDB)

        Returns:
            Success status with previous and new values
        """
        result = self.validator.set_lever_position(rule_id, lever_name, value)
        if not result.get("success"):
            return result

        # Persist to SurrealDB for cross-session persistence (best-effort)
        try:
            client = self._get_surrealdb_client()
            if client:
                sql = (
                    f"UPDATE hookify_rules:{rule_id} "
                    f"SET lever_overrides.{lever_name} = {json.dumps(value)}, "
                    f"updated = time::now();"
                )
                client.query(sql)
        except Exception as e:
            logger.warning(f"Could not persist lever to SurrealDB: {e}")

        # Also write to vault for audit trail (best-effort)
        try:
            await self._write_lever_change_to_vault(rule_id, lever_name, result)
        except Exception as e:
            logger.warning(f"Could not write lever audit: {e}")

        return result

    async def _write_lever_change_to_vault(self, rule_id: str, lever_name: str, result: dict):
        """Write lever change decision to vault (Tier 3 audit)"""
        try:
            from datetime import datetime

            timestamp = datetime.now().isoformat()
            content = f"""---
title: "Hookify Lever Change: {rule_id}.{lever_name}"
date: {timestamp}
tags: [hookify, lever-change, audit]
aspect: prefrontal
---

# Lever Change Decision

**Rule**: `{rule_id}`
**Lever**: `{lever_name}`
**Timestamp**: {timestamp}

## Change Details

| Field | Value |
|-------|-------|
| Previous | `{result.get("previous_value", "N/A")}` |
| New | `{result.get("new_value", "N/A")}` |
| Success | {result.get("success", False)} |

## Rationale

Lever adjusted for:
- Session optimization
- Coherence target alignment
- Performance tuning

## Persistence

- **Tier 1 (Git)**: Base defaults in `.agent/HOOKIFY_RULES.md`
- **Tier 2 (SurrealDB)**: Runtime override persisted
- **Tier 3 (Vault)**: This audit record
"""

            audit_path = f"prefrontal/hookify-decisions/{rule_id}_{lever_name}_{timestamp[:10]}.md"
            audit_file = self.vault_path / audit_path
            audit_file.parent.mkdir(parents=True, exist_ok=True)
            audit_file.write_text(content)

            logger.info(f"Wrote lever change audit to {audit_path}")

        except Exception as e:
            logger.warning(f"Could not write lever audit: {e}")

    def _load_db_overrides_for_rule(self, rule_id: str) -> dict[str, Any]:
        """Load runtime overrides from SurrealDB"""
        client = self._get_surrealdb_client()
        if not client:
            return {}

        try:
            sql = f"SELECT * FROM hookify_rules:{rule_id};"
            result = client.query(sql)
            if result and len(result) > 0:
                return result[0].get("lever_overrides", {})
        except Exception:
            pass

        return {}

    # =====================================================================
    # MCP Tool: Rule Discovery
    # =====================================================================

    async def list_rules(self) -> dict[str, Any]:
        """List all available rules"""
        rules_info = []
        for rule in self.validator.rules:
            rules_info.append(
                {
                    "id": rule.id,
                    "trigger": rule.trigger,
                    "condition": rule.condition[:50] + "..."
                    if len(rule.condition) > 50
                    else rule.condition,
                    "action": rule.action,
                    "lever_count": len(rule.levers),
                    "adversarial_tests": rule.adversarial_tests,
                }
            )

        return {"rules": rules_info, "total": len(rules_info), "rules_file": str(self.rules_file)}

    async def get_rule_violation_graph(self, rule_id: str) -> dict[str, Any]:
        """
        Get graph of violations for a rule (uses SurrealDB graph)

        Returns nodes and edges for visualization
        """
        client = self._get_surrealdb_client()
        if not client:
            return {"error": "SurrealDB not available"}

        try:
            # Query graph for violations linked to this rule
            sql = f"""
                SELECT * FROM synapse
                WHERE out = neuron:prefrontal_{rule_id}
                AND link_type = 'latent';
            """
            result = client.query(sql)

            synapses = result[0].get("result", []) if result else []

            nodes = []
            edges = []

            for syn in synapses:
                from_id = syn.get("in", "").replace("neuron:", "")
                to_id = syn.get("out", "").replace("neuron:", "")

                nodes.append({"id": from_id, "type": "session"})
                nodes.append({"id": to_id, "type": "rule"})
                edges.append(
                    {
                        "from": from_id,
                        "to": to_id,
                        "reason": syn.get("reason", ""),
                        "coherence": syn.get("coherence", 0),
                    }
                )

            return {
                "rule_id": rule_id,
                "violation_count": len(synapses),
                "nodes": nodes,
                "edges": edges,
            }

        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# MCP Server Factory
# =============================================================================


def create_hookify_mcp_server(vault_path: Path | None = None) -> FastMCP:
    """Create and configure the Hookify MCP server"""

    bridge = HookifyMCPBridge(vault_path or VAULT_PATH)

    mcp = FastMCP(
        "Hookify Rule Engine",
        instructions=(
            "A universal rule engine for compound engineering with cross-platform support. "
            "Define rules with configurable levers, validate execution against HIHO coherence gates, "
            "and persist violations to the vault graph for recursive learning."
        ),
    )

    # ── Validation Tools ─────────────────────────────────────────────────

    @mcp.tool()
    async def hookify_validate(trigger: str, context: str) -> str:
        """Validate execution context against rules.

        Args:
            trigger: Event trigger (session_start, pre_execute, post_execute, pre_commit)
            context: JSON string with execution context (coherence, goal, session_id, etc.)

        Returns:
            JSON string with validation result
        """
        try:
            ctx = json.loads(context)
            result = await bridge.validate_rule(trigger, ctx)
            return json.dumps(result, indent=2)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON context"})

    @mcp.tool()
    async def hookify_get_levers(rule_id: str) -> str:
        """Get current lever positions for a rule.

        Args:
            rule_id: Rule identifier (e.g., 'cosmological_ralph_loop')

        Returns:
            JSON string with lever positions and sources
        """
        result = await bridge.get_levers(rule_id)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def hookify_set_lever(rule_id: str, lever_name: str, value: str) -> str:
        """Set lever position (persisted to SurrealDB).

        Args:
            rule_id: Rule identifier
            lever_name: Name of the lever to adjust
            value: New value (parsed as int, float, bool, or string)

        Returns:
            JSON string with success status and previous/new values
        """
        # Parse value to appropriate type
        parsed_value = bridge.validator._parse_value(value)
        result = await bridge.set_lever(rule_id, lever_name, parsed_value)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def hookify_list_rules() -> str:
        """List all available rules.

        Returns:
            JSON string with rule metadata
        """
        result = await bridge.list_rules()
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def hookify_get_violation_graph(rule_id: str) -> str:
        """Get violation graph for a rule from SurrealDB.

        Args:
            rule_id: Rule identifier

        Returns:
            JSON string with nodes and edges for visualization
        """
        result = await bridge.get_rule_violation_graph(rule_id)
        return json.dumps(result, indent=2)

    # ── Graph Integration Tools ──────────────────────────────────────────

    @mcp.tool()
    async def hookify_create_dream_synapse(from_rule: str, to_rule: str, resonance: str) -> str:
        """Create a dream synapse (cross-rule learning) in the graph.

        Args:
            from_rule: Source rule ID
            to_rule: Target rule ID
            resonance: Description of the cross-rule connection

        Returns:
            Success message
        """
        client = bridge._get_surrealdb_client()
        if not client:
            return "Error: SurrealDB not available"

        try:
            from_id = f"neuron:prefrontal_{from_rule}"
            to_id = f"neuron:prefrontal_{to_rule}"

            sql = (
                f"RELATE {from_id}->synapse->{to_id} "
                f"SET link_type = 'dream', "
                f"resonance = '{resonance.replace(chr(39), chr(92) + chr(39))}', "
                f"created = time::now();"
            )
            client.query(sql)

            return f"Dream synapse created: {from_rule} -> {to_rule}"

        except Exception as e:
            return f"Error: {e}"

    @mcp.tool()
    async def hookify_write_affinity(rule_id: str, affinity_vector: str) -> str:
        """Write 12D FLUME affinity vector to a rule neuron.

        Args:
            rule_id: Rule identifier
            affinity_vector: JSON array of 12 floats (L2-normalized)

        Returns:
            Success message
        """
        client = bridge._get_surrealdb_client()
        if not client:
            return "Error: SurrealDB not available"

        try:
            vec = json.loads(affinity_vector)
            if len(vec) != 12:
                return f"Error: affinity_vector must have exactly 12 elements, got {len(vec)}"

            neuron_id = f"neuron:prefrontal_{rule_id}"
            vec_str = "[" + ", ".join(str(v) for v in vec) + "]"

            sql = f"UPDATE {neuron_id} SET dim_agent_affinity = {vec_str};"
            client.query(sql)

            return f"Affinity vector written to {rule_id}"

        except json.JSONDecodeError:
            return "Error: Invalid JSON array"
        except Exception as e:
            return f"Error: {e}"

    return mcp


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create and run server
    mcp = create_hookify_mcp_server()

    # Support stdio for MCP
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        mcp.run(transport="stdio")
    else:
        # Default: run with SSE for web-based clients
        mcp.run()
