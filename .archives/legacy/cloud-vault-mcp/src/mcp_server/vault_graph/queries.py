"""Thin async wrappers around SurrealDB stored functions."""

from .client import GraphClient, get_graph_client


async def neighborhood(neuron_id: str, client: GraphClient | None = None) -> dict:
    c = client or get_graph_client()
    results = await c.query(f"SELECT * FROM fn::context_neighborhood({neuron_id});")
    return results[0] if results else {}


async def search(query: str, client: GraphClient | None = None) -> list:
    c = client or get_graph_client()
    q = query.replace("'", "\\'")
    return await c.query(f"SELECT * FROM fn::context_search('{q}');")


async def cluster(cluster_name: str, client: GraphClient | None = None) -> dict:
    c = client or get_graph_client()
    name = cluster_name.replace("'", "\\'")
    results = await c.query(f"SELECT * FROM fn::context_cluster('{name}');")
    return results[0] if results else {}


async def hops(
    neuron_id: str, depth: int = 2, client: GraphClient | None = None
) -> list:
    c = client or get_graph_client()
    return await c.query(f"SELECT * FROM fn::context_hops({neuron_id}, {depth});")


async def bridges(
    cluster_a: str, cluster_b: str, client: GraphClient | None = None
) -> list:
    c = client or get_graph_client()
    a = cluster_a.replace("'", "\\'")
    b = cluster_b.replace("'", "\\'")
    return await c.query(f"SELECT * FROM fn::context_bridges('{a}', '{b}');")


async def stats(client: GraphClient | None = None) -> dict:
    c = client or get_graph_client()
    results = await c.query("SELECT * FROM fn::vault_stats();")
    return results[0] if results else {}
