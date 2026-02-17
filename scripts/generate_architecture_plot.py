#!/usr/bin/env python3
"""
Generate a Plotly Architecture Diagram for the Overnight Mission
"""

from pathlib import Path

import networkx as nx
import plotly.graph_objects as go


def generate_arch_plot():
    """Create interactive architecture network graph."""

    # Define Nodes
    nodes = {
        "Coordinator": {"pos": (0, 0), "color": "#e74c3c", "size": 40},
        "Watchdog": {"pos": (0, 1), "color": "#f1c40f", "size": 30},
        "HIHO Worker 1-24": {"pos": (-1, -1), "color": "#3498db", "size": 25},
        "Ollama Worker 1-6": {"pos": (1, -1), "color": "#2ecc71", "size": 25},
        "Matsumoto Analyzer": {"pos": (2, 0), "color": "#9b59b6", "size": 30},
        "SurrealDB": {"pos": (0, -2), "color": "#34495e", "size": 35},
        "Assets/Data": {"pos": (-2, 0), "color": "#7f8c8d", "size": 30},
    }

    # Define Edges
    edges = [
        ("Coordinator", "HIHO Worker 1-24"),
        ("Coordinator", "Ollama Worker 1-6"),
        ("Watchdog", "Coordinator"),
        ("Watchdog", "HIHO Worker 1-24"),
        ("Watchdog", "Ollama Worker 1-6"),
        ("Coordinator", "Matsumoto Analyzer"),
        ("Matsumoto Analyzer", "Assets/Data"),
        ("HIHO Worker 1-24", "Assets/Data"),
        ("Ollama Worker 1-6", "Assets/Data"),
        ("Assets/Data", "SurrealDB"),
        ("Coordinator", "SurrealDB"),
    ]

    # Create Graph
    G = nx.Graph()
    for node, props in nodes.items():
        G.add_node(node, **props)
    G.add_edges_from(edges)

    # Trace nodes
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_size = []

    for node in G.nodes():
        x, y = G.nodes[node]["pos"]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_color.append(G.nodes[node]["color"])
        node_size.append(G.nodes[node]["size"])

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        hoverinfo="text",
        marker={
            "showscale": False,
            "color": node_color,
            "size": node_size,
            "line_width": 2,
        },
    )

    # Trace edges
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = G.nodes[edge[0]]["pos"]
        x1, y1 = G.nodes[edge[1]]["pos"]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line={"width": 1, "color": "#888"},
        hoverinfo="none",
        mode="lines",
    )

    # Create Figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title={
                "text": "Cohezion Overnight Mission Architecture",
                "font": {"size": 20},
            },
            showlegend=False,
            hovermode="closest",
            margin={"b": 20, "l": 5, "r": 5, "t": 40},
            xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            template="plotly_white",
        ),
    )

    # Save
    output_dir = Path("/home/mike-anderson/.gemini/antigravity/brain/1b98adc2-8dce-436b-bac3-d27890e7ce04/assets")
    output_dir.mkdir(parents=True, exist_ok=True)

    fig.write_html(str(output_dir / "overnight_architecture_interactive.html"))
    fig.write_image(
        str(output_dir / "overnight_architecture_plotly.png"),
        width=1000,
        height=800,
        scale=2,
    )

    print(f"✅ Architecture plots saved to {output_dir}")


if __name__ == "__main__":
    generate_arch_plot()
