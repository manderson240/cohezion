"""GraphReactor — importable module extracted from scripts/graph_reactor.py.

Contains the pure computation logic. The scripts/graph_reactor.py CLI wrapper
delegates to this module.
"""

import datetime
import math
from typing import Any

import networkx as nx


LAMBDA_DECAY = 0.05


def compute_bridging_scores(
    neuron_ids: list[str], edges: list[tuple[str, str]]
) -> dict[str, float]:
    """Betweenness centrality normalized 0-1."""
    G = nx.DiGraph()
    G.add_nodes_from(neuron_ids)
    G.add_edges_from(edges)
    raw = nx.betweenness_centrality(G, normalized=True)
    return {node: round(score, 4) for node, score in raw.items()}


def compute_completion_score(neuron: dict[str, Any]) -> float:
    """Heuristic completeness 0-1."""
    word_count = neuron.get("word_count") or 0
    tag_count = len(neuron.get("tags") or [])
    stage = neuron.get("stage", "embryo")
    stage_score = {"embryo": 0.1, "seedling": 0.3, "growing": 0.6, "mature": 1.0}.get(
        stage, 0.2
    )
    word_score = min(word_count / 400.0, 1.0)
    tag_score = min(tag_count / 4.0, 1.0)
    return round(0.5 * word_score + 0.3 * stage_score + 0.2 * tag_score, 4)


def compute_recency_score(modified_date: str | None) -> float:
    """Exponential recency decay exp(-0.05 * days). Half-life ~14 days."""
    if not modified_date:
        return 0.0
    try:
        date = datetime.date.fromisoformat(modified_date[:10])
        days = (datetime.date.today() - date).days
        return round(math.exp(-LAMBDA_DECAY * max(days, 0)), 4)
    except (ValueError, TypeError):
        return 0.0


def build_briefing(neurons: list[dict[str, Any]], n_synapses: int) -> str:
    """Build the metabolism/graph-briefing.md content string."""
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    n_neurons = len(neurons)

    top_bridging = sorted(
        [n for n in neurons if n.get("dim_bridging") is not None],
        key=lambda x: x.get("dim_bridging", 0),
        reverse=True,
    )[:5]

    stubs = sorted(
        [
            n
            for n in neurons
            if (n.get("dim_completion") or 1) < 0.4 and (n.get("dim_bridging") or 0) > 0.05
        ],
        key=lambda x: x.get("dim_bridging", 0),
        reverse=True,
    )[:3]

    recent = sorted(
        [n for n in neurons if n.get("dim_recency") is not None],
        key=lambda x: x.get("dim_recency", 0),
        reverse=True,
    )[:5]

    lines = [
        f"## Graph State — {now}",
        "",
        f"**Vault:** {n_neurons} neurons · {n_synapses} synapses",
        "",
        "**Hot neurons** (high bridging):",
    ]
    for n in top_bridging:
        lines.append(f"- {n.get('title', '?')} (bridging={n.get('dim_bridging', 0):.3f})")

    lines += ["", "**Bridges** (connect otherwise-disconnected clusters):"]
    for n in top_bridging[:3]:
        lines.append(f"- {n.get('title', '?')} → {n.get('cluster_id', '?')}")

    lines += ["", "**Completion gaps** (low completion, high bridging — worth fleshing out):"]
    for n in stubs:
        lines.append(f"- {n.get('title', '?')} (completion={n.get('dim_completion', 0):.2f})")

    lines += ["", "**Recent activity**:"]
    for n in recent:
        lines.append(f"- {n.get('title', '?')} (recency={n.get('dim_recency', 0):.3f})")

    return "\n".join(lines) + "\n"
