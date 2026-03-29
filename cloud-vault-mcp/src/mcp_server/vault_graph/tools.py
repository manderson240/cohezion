"""Read + write MCP tools wrapping SurrealDB stored functions."""

from . import queries


# ── Read tools ────────────────────────────────────────────────────────────────

async def tool_graph_neighborhood(neuron_id: str) -> str:
    """Return the local neighborhood of a neuron: metadata, links, cluster siblings.

    Args:
        neuron_id: Full neuron ID (e.g. 'neuron:cortex_foo_md')
    """
    data = await queries.neighborhood(neuron_id)
    if not data:
        return f"No neuron found: {neuron_id}"
    n = data.get("neuron", {})
    lines = [
        f"=== {n.get('title', '?')} ===",
        f"Activation: {n.get('activation', 0):.3f} | Stage: {n.get('stage', '?')} | Cluster: {n.get('cluster_id', '?')}",
    ]
    for link in data.get("outbound", [])[:5]:
        lines.append(f"  -> {link.get('activation', 0):.2f} {link.get('title', '?')}")
    for link in data.get("inbound", [])[:5]:
        lines.append(f"  <- {link.get('activation', 0):.2f} {link.get('title', '?')}")
    return "\n".join(lines)


async def tool_graph_search(query: str) -> str:
    """Search neurons by title/tag substring match.

    Args:
        query: Search term (e.g. 'quantum', 'attention mechanism')
    """
    hits = await queries.search(query)
    if not hits:
        return f"No neurons matching '{query}'"
    lines = [f"=== Search: '{query}' ({len(hits)} results) ==="]
    for n in hits[:15]:
        lines.append(
            f"  {n.get('activation', 0):.2f} {n.get('title', '?')} ({n.get('cluster_id', '?')})"
        )
    return "\n".join(lines)


async def tool_graph_cluster(cluster_name: str) -> str:
    """Return cluster summary: top neurons, stats, coherence.

    Args:
        cluster_name: Cluster ID (e.g. 'cortex', 'sensory', 'prefrontal')
    """
    data = await queries.cluster(cluster_name)
    if not data:
        return f"Cluster not found: {cluster_name}"
    lines = [
        f"=== Cluster: {data.get('cluster', cluster_name)} ===",
        f"Neurons: {data.get('total_neurons', 0)} | Avg Activation: {data.get('avg_activation', 0):.3f}",
    ]
    for n in data.get("top_neurons", [])[:10]:
        lines.append(f"  {n.get('activation', 0):.2f} {n.get('title', '?')}")
    return "\n".join(lines)


async def tool_graph_hops(neuron_id: str, depth: int = 2) -> str:
    """Return all neurons reachable within N hops.

    Args:
        neuron_id: Starting neuron ID
        depth: Number of hops (1 or 2, default 2)
    """
    hits = await queries.hops(neuron_id, depth)
    if not hits:
        return f"No neurons within {depth} hops of {neuron_id}"
    lines = [f"=== {depth}-hop neighborhood ({len(hits)} neurons) ==="]
    for n in hits[:20]:
        lines.append(
            f"  {n.get('activation', 0):.2f} {n.get('title', '?')} ({n.get('cluster_id', '?')})"
        )
    return "\n".join(lines)


async def tool_graph_bridges(cluster_a: str, cluster_b: str) -> str:
    """Find neurons bridging two clusters.

    Args:
        cluster_a: First cluster ID
        cluster_b: Second cluster ID
    """
    hits = await queries.bridges(cluster_a, cluster_b)
    if not hits:
        return f"No bridges between {cluster_a} and {cluster_b}"
    lines = [f"=== Bridges: {cluster_a} <-> {cluster_b} ({len(hits)}) ==="]
    for n in hits[:10]:
        lines.append(f"  {n.get('activation', 0):.2f} {n.get('title', '?')}")
    return "\n".join(lines)


async def tool_graph_stats() -> str:
    """Return global vault statistics snapshot."""
    data = await queries.stats()
    if not data:
        return "Could not fetch vault stats"

    def _unwrap_count(field):
        """fn::vault_stats() returns counts as [{count: N}] subquery arrays."""
        v = data.get(field, "?")
        if isinstance(v, list) and v and isinstance(v[0], dict) and "count" in v[0]:
            return v[0]["count"]
        return v

    lines = [
        "=== Vault Stats ===",
        f"Neurons: {_unwrap_count('total_neurons')} | Synapses: {_unwrap_count('total_synapses')}",
    ]
    for s in data.get("stage_distribution", []):
        lines.append(f"  {s.get('stage', '?')}: {s.get('n', 0)}")
    return "\n".join(lines)


def register_read_tools(mcp) -> None:
    """Register all 6 read tools with the FastMCP instance."""

    @mcp.tool()
    async def graph_neighborhood(neuron_id: str) -> str:
        """Return the local neighborhood of a neuron (metadata, links, cluster siblings)."""
        return await tool_graph_neighborhood(neuron_id)

    @mcp.tool()
    async def graph_search(query: str) -> str:
        """Search neurons by title/tag substring match."""
        return await tool_graph_search(query)

    @mcp.tool()
    async def graph_cluster(cluster_name: str) -> str:
        """Return cluster summary: top neurons, count, average activation."""
        return await tool_graph_cluster(cluster_name)

    @mcp.tool()
    async def graph_hops(neuron_id: str, depth: int = 2) -> str:
        """Return all neurons reachable within N hops of a neuron."""
        return await tool_graph_hops(neuron_id, depth)

    @mcp.tool()
    async def graph_bridges(cluster_a: str, cluster_b: str) -> str:
        """Find neurons that bridge two clusters (cross-domain connectors)."""
        return await tool_graph_bridges(cluster_a, cluster_b)

    @mcp.tool()
    async def graph_stats() -> str:
        """Return global vault statistics: neuron/synapse counts, stage distribution."""
        return await tool_graph_stats()


# ── Write tools ───────────────────────────────────────────────────────────────

def register_write_tools(mcp, get_surrealdb_client=None) -> None:
    """Register 4 agent-write tools. Uses vault_graph async client."""
    from .client import get_graph_client

    def _client():
        return get_graph_client()

    @mcp.tool()
    async def graph_write_latent_synapse(
        from_neuron_id: str, to_neuron_id: str, reason: str
    ) -> str:
        """Create a latent (semantically inferred) synapse between two neurons.

        Args:
            from_neuron_id: Source neuron ID (e.g. 'neuron:cortex_foo_md')
            to_neuron_id: Target neuron ID
            reason: Why this connection exists (stored on the synapse)
        """
        client = _client()
        existing = await client.query(
            f"SELECT type FROM synapse "
            f"WHERE in = {from_neuron_id} AND out = {to_neuron_id} AND type = 'explicit';"
        )
        if existing:
            return f"Error: explicit synapse already exists between {from_neuron_id} and {to_neuron_id}"
        reason_esc = reason.replace("'", "\\'")
        await client.execute(
            f"RELATE {from_neuron_id}->synapse->{to_neuron_id} SET link_type = 'latent', "
            f"reason = '{reason_esc}', created = time::now();"
        )
        return f"Latent synapse created: {from_neuron_id} -> {to_neuron_id}"

    @mcp.tool()
    async def graph_write_dream_synapse(
        from_neuron_id: str, to_neuron_id: str, resonance: str
    ) -> str:
        """Create a dream synapse (cross-domain resonance) between two neurons.

        Args:
            from_neuron_id: Source neuron ID
            to_neuron_id: Target neuron ID
            resonance: Description of the cross-domain connection
        """
        client = _client()
        existing = await client.query(
            f"SELECT type FROM synapse "
            f"WHERE in = {from_neuron_id} AND out = {to_neuron_id} AND type = 'explicit';"
        )
        if existing:
            return f"Error: explicit synapse already exists between {from_neuron_id} and {to_neuron_id}"
        r_esc = resonance.replace("'", "\\'")
        await client.execute(
            f"RELATE {from_neuron_id}->synapse->{to_neuron_id} SET link_type = 'dream', "
            f"resonance = '{r_esc}', created = time::now();"
        )
        return f"Dream synapse created: {from_neuron_id} -> {to_neuron_id}"

    @mcp.tool()
    async def graph_write_affinity(neuron_id: str, affinity_vector: list[float]) -> str:
        """Write a 12D FLUME affinity vector to a neuron.

        Args:
            neuron_id: Target neuron ID
            affinity_vector: 12-element float list (L2-normalized)
        """
        if len(affinity_vector) != 12:
            return f"Error: affinity_vector must have 12 elements, got {len(affinity_vector)}"
        client = _client()
        vec_str = "[" + ", ".join(str(v) for v in affinity_vector) + "]"
        await client.execute(f"UPDATE {neuron_id} SET dim_agent_affinity = {vec_str};")
        return f"Affinity vector written to {neuron_id}"

    @mcp.tool()
    async def graph_annotate_neuron(
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
        sets = []
        if last_accessed:
            sets.append(f"last_accessed = '{last_accessed}'")
        if agent_notes:
            notes_esc = agent_notes.replace("'", "\\'")
            sets.append(f"agent_notes = '{notes_esc}'")
        if increment_access_count:
            sets.append("access_count += 1")
        if not sets:
            return "No fields to update."
        client = _client()
        await client.execute(f"UPDATE {neuron_id} SET {', '.join(sets)};")
        return f"Annotations written to {neuron_id}"
