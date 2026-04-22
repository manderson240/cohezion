"""
Agent-write MCP tools for the vault graph.

Agents may write: latent synapses, dream synapses, affinity vectors,
and metadata annotations. They may NOT overwrite explicit (structural) synapses
or structural neuron fields (title, path, tags, stage).
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)


class GraphWriteError(Exception):
    """Raised when a graph write would violate write boundaries."""


def _validate_not_explicit_synapse(client: Any, from_id: str, to_id: str) -> None:
    """Raise if an explicit synapse already exists between these neurons."""
    sql = (
        f"SELECT type FROM synapse "
        f"WHERE in = {from_id} AND out = {to_id} AND type = 'explicit';"
    )
    results = client.query(sql)
    hits = results[0].get("result", [])
    if hits:
        raise GraphWriteError(
            f"An explicit synapse already exists between {from_id} and {to_id}. "
            "Agents may not overwrite structural synapses."
        )


def build_latent_synapse_sql(from_id: str, to_id: str, reason: str) -> str:
    reason_esc = reason.replace("'", "\\'")
    return (
        f"RELATE {from_id}->synapse->{to_id} SET link_type = 'latent', reason = '{reason_esc}', "
        f"created = time::now();"
    )


def build_dream_synapse_sql(from_id: str, to_id: str, resonance: str) -> str:
    resonance_esc = resonance.replace("'", "\\'")
    return (
        f"RELATE {from_id}->synapse->{to_id} SET link_type = 'dream', resonance = '{resonance_esc}', "
        f"created = time::now();"
    )


def build_affinity_update_sql(neuron_id: str, vec_12d: list[float]) -> str:
    vec_str = "[" + ", ".join(str(v) for v in vec_12d) + "]"
    return f"UPDATE {neuron_id} SET dim_agent_affinity = {vec_str};"


def build_annotate_sql(
    neuron_id: str,
    last_accessed: str | None = None,
    agent_notes: str | None = None,
    access_count_delta: int = 0,
) -> str:
    sets = []
    if last_accessed:
        sets.append(f"last_accessed = '{last_accessed}'")
    if agent_notes:
        notes_esc = agent_notes.replace("'", "\\'")
        sets.append(f"agent_notes = '{notes_esc}'")
    if access_count_delta:
        sets.append(f"access_count += {access_count_delta}")
    if not sets:
        return ""
    return f"UPDATE {neuron_id} SET {', '.join(sets)};"


def register_graph_write_tools(mcp: Any, get_surrealdb_client: Any) -> None:
    """Register the four agent-write tools with the FastMCP instance."""

    @mcp.tool()
    def graph_write_latent_synapse(from_neuron_id: str, to_neuron_id: str, reason: str) -> str:
        """Create a latent (semantically inferred) synapse between two neurons.

        Args:
            from_neuron_id: Source neuron ID (e.g. 'neuron:cortex_foo_md')
            to_neuron_id: Target neuron ID
            reason: Why this connection exists (stored on the synapse)
        """
        client = get_surrealdb_client()
        _validate_not_explicit_synapse(client, from_neuron_id, to_neuron_id)
        sql = build_latent_synapse_sql(from_neuron_id, to_neuron_id, reason)
        client.query(sql)
        return f"Latent synapse created: {from_neuron_id} -> {to_neuron_id}"

    @mcp.tool()
    def graph_write_dream_synapse(from_neuron_id: str, to_neuron_id: str, resonance: str) -> str:
        """Create a dream synapse (cross-domain resonance) between two neurons.

        Args:
            from_neuron_id: Source neuron ID
            to_neuron_id: Target neuron ID
            resonance: Description of the cross-domain connection
        """
        client = get_surrealdb_client()
        _validate_not_explicit_synapse(client, from_neuron_id, to_neuron_id)
        sql = build_dream_synapse_sql(from_neuron_id, to_neuron_id, resonance)
        client.query(sql)
        return f"Dream synapse created: {from_neuron_id} -> {to_neuron_id}"

    @mcp.tool()
    def graph_write_affinity(neuron_id: str, affinity_vector: list[float]) -> str:
        """Write a 12D FLUME affinity vector to a neuron.

        Args:
            neuron_id: Target neuron ID
            affinity_vector: 12-element float list (L2-normalized)
        """
        if len(affinity_vector) != 12:
            return f"Error: affinity_vector must have exactly 12 elements, got {len(affinity_vector)}"
        client = get_surrealdb_client()
        sql = build_affinity_update_sql(neuron_id, affinity_vector)
        client.query(sql)
        return f"Affinity vector written to {neuron_id}"

    @mcp.tool()
    def graph_annotate_neuron(
        neuron_id: str,
        last_accessed: str = "",
        agent_notes: str = "",
        increment_access_count: bool = False,
    ) -> str:
        """Annotate a neuron with agent metadata (does not touch structural fields).

        Args:
            neuron_id: Target neuron ID
            last_accessed: ISO date string (e.g. '2026-03-20')
            agent_notes: Free-form notes from the agent session
            increment_access_count: Whether to increment access_count by 1
        """
        client = get_surrealdb_client()
        sql = build_annotate_sql(
            neuron_id,
            last_accessed=last_accessed or None,
            agent_notes=agent_notes or None,
            access_count_delta=1 if increment_access_count else 0,
        )
        if not sql:
            return "No fields to update."
        client.query(sql)
        return f"Annotations written to {neuron_id}"
