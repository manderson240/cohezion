#!/usr/bin/env python3
"""
Graph Context — Token-efficient vault context via SurrealDB graph traversal.

Queries the vault's neuron/synapse graph and returns compact, agent-ready context.
Designed for minimal token consumption: one call replaces reading multiple files.

Usage:
    graph_context.py neighborhood <query>     # Local neighborhood of a neuron
    graph_context.py search <query>           # Find neurons by title/tag match
    graph_context.py cluster <name>           # Cluster summary with top neurons
    graph_context.py hops <query> [depth]     # N-hop traversal (default: 2)
    graph_context.py bridges <cluster_a> <cluster_b>  # Cross-domain connectors
    graph_context.py stats                    # Global vault health snapshot
    graph_context.py resolve <query>          # Find neuron ID from partial name

Output is plain text, optimized for agent context injection.
"""

import base64
import json
import sys
import urllib.request

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "vault"
SURREAL_USER = "root"
SURREAL_PASS = "root"


def query(sql: str) -> list:
    """Execute SurrealQL and return result list."""
    creds = base64.b64encode(f"{SURREAL_USER}:{SURREAL_PASS}".encode()).decode()
    req = urllib.request.Request(
        SURREAL_URL,
        data=sql.encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "Authorization": f"Basic {creds}",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    if isinstance(data, dict) and "code" in data:
        print(f"Error: {data.get('description', data)}", file=sys.stderr)
        sys.exit(1)
    return data


def resolve_neuron(partial: str) -> str | None:
    """Find a neuron ID from a partial name match."""
    sql = f"SELECT id, title, activation FROM neuron WHERE string::contains(string::lowercase(title), string::lowercase('{_esc(partial)}')) ORDER BY activation DESC LIMIT 5;"
    results = query(sql)
    hits = results[0].get("result", [])
    if not hits:
        return None
    return str(hits[0]["id"])


def _esc(s: str) -> str:
    """Escape single quotes for SurrealQL strings."""
    return s.replace("'", "\\'")


def _act_bar(activation: float) -> str:
    """Compact activation bar: 0.85 → [████░]"""
    filled = round(activation * 5)
    return "[" + "\u2588" * filled + "\u2591" * (5 - filled) + "]"


def _format_neuron_line(n: dict, prefix: str = "") -> str:
    """Format a single neuron as a compact line."""
    act = n.get("activation", 0)
    title = n.get("title", "?")
    stage = n.get("stage", "?")
    cluster = n.get("cluster_id", n.get("cluster", ""))
    syn_out = n.get("synapse_out", 0)
    syn_in = n.get("synapse_in", 0)
    return f"{prefix}{_act_bar(act)} {act:.2f} {title} ({stage}, {cluster}, out:{syn_out} in:{syn_in})"


def cmd_neighborhood(args: list[str]):
    partial = " ".join(args)
    nid = resolve_neuron(partial)
    if not nid:
        print(f"No neuron found matching '{partial}'")
        sys.exit(1)

    sql = f"SELECT * FROM fn::context_neighborhood({nid});"
    results = query(sql)
    data = results[0]["result"][0]
    n = data["neuron"]

    print(f"=== {n['title']} ===")
    print(f"Path: {n['path']}")
    print(f"Activation: {n['activation']:.3f} | Stage: {n['stage']} | Aspect: {n['aspect']}")
    print(f"Cluster: {n['cluster_id']} | Words: {n['word_count']}")
    print(f"Tags: {', '.join(n.get('tags', []))}")
    print(f"Synapses: out={n['synapse_out']} in={n['synapse_in']}")

    if data["outbound"]:
        print(f"\n--- Outbound ({len(data['outbound'])}) ---")
        for link in sorted(data["outbound"], key=lambda x: x.get("activation", 0), reverse=True):
            print(_format_neuron_line(link, "  -> "))

    if data["inbound"]:
        print(f"\n--- Inbound ({len(data['inbound'])}) ---")
        for link in sorted(data["inbound"], key=lambda x: x.get("activation", 0), reverse=True):
            print(_format_neuron_line(link, "  <- "))

    if data["cluster_top"]:
        print(f"\n--- Cluster Siblings (top 5 in '{n['cluster_id']}') ---")
        for sib in data["cluster_top"]:
            print(f"  {_act_bar(sib['activation'])} {sib['activation']:.2f} {sib['title']}")


def cmd_search(args: list[str]):
    q = " ".join(args)
    sql = f"SELECT * FROM fn::context_search('{_esc(q)}');"
    results = query(sql)
    hits = results[0]["result"]
    if not hits:
        print(f"No neurons matching '{q}'")
        return
    print(f"=== Search: '{q}' ({len(hits)} results) ===")
    for n in hits:
        print(_format_neuron_line(n))


def cmd_cluster(args: list[str]):
    name = args[0] if args else "cortex"
    sql = f"SELECT * FROM fn::context_cluster('{_esc(name)}');"
    results = query(sql)
    data = results[0]["result"][0]

    print(f"=== Cluster: {data['cluster']} ===")
    print(f"Neurons: {data['total_neurons']} | Avg Activation: {data['avg_activation']:.3f} | Coherence: {data['coherence']:.3f}")
    print(f"\n--- Top Neurons ---")
    for n in data["top_neurons"]:
        print(_format_neuron_line(n, "  "))


def cmd_hops(args: list[str]):
    partial = args[0] if args else ""
    depth = int(args[1]) if len(args) > 1 else 2
    nid = resolve_neuron(partial)
    if not nid:
        print(f"No neuron found matching '{partial}'")
        sys.exit(1)

    sql = f"SELECT * FROM fn::context_hops({nid}, {depth});"
    results = query(sql)
    hits = results[0]["result"]
    print(f"=== {depth}-hop neighborhood ({len(hits)} neurons) ===")
    for n in hits:
        print(_format_neuron_line(n, "  "))


def cmd_bridges(args: list[str]):
    if len(args) < 2:
        print("Usage: bridges <cluster_a> <cluster_b>")
        sys.exit(1)
    sql = f"SELECT * FROM fn::context_bridges('{_esc(args[0])}', '{_esc(args[1])}');"
    results = query(sql)
    hits = results[0]["result"]
    print(f"=== Bridges: {args[0]} <-> {args[1]} ({len(hits)} connectors) ===")
    for n in hits:
        print(_format_neuron_line(n, "  "))


def cmd_stats(args: list[str]):
    sql = "SELECT * FROM fn::vault_stats();"
    results = query(sql)
    data = results[0]["result"][0]

    def _unwrap_count(v):
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v[0].get("count", v)
        return v

    print(f"=== Vault Stats ===")
    print(f"Neurons: {_unwrap_count(data['total_neurons'])} | Synapses: {_unwrap_count(data['total_synapses'])}")

    print(f"\n--- Stage Distribution ---")
    for s in data["stage_distribution"]:
        print(f"  {s['stage']}: {s['n']}")

    print(f"\n--- Clusters (top 10) ---")
    for c in data["clusters"][:10]:
        print(f"  {c['cluster_id']}: {c['n']} neurons (avg act: {c['avg_act']:.3f})")


def cmd_resolve(args: list[str]):
    partial = " ".join(args)
    sql = f"SELECT id, title, activation, path FROM neuron WHERE string::contains(string::lowercase(title), string::lowercase('{_esc(partial)}')) ORDER BY activation DESC LIMIT 10;"
    results = query(sql)
    hits = results[0].get("result", [])
    if not hits:
        print(f"No neurons matching '{partial}'")
        return
    for n in hits:
        print(f"  {n['activation']:.2f} {n['id']} — {n['title']}")


COMMANDS = {
    "neighborhood": cmd_neighborhood,
    "n": cmd_neighborhood,
    "search": cmd_search,
    "s": cmd_search,
    "cluster": cmd_cluster,
    "c": cmd_cluster,
    "hops": cmd_hops,
    "h": cmd_hops,
    "bridges": cmd_bridges,
    "b": cmd_bridges,
    "stats": cmd_stats,
    "resolve": cmd_resolve,
    "r": cmd_resolve,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__.strip())
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(k for k in COMMANDS if len(k) > 1)}")
        sys.exit(1)

    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
