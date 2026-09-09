#!/usr/bin/env python3
"""Verification & Demo of Graph Engineering Relational Mesh & SurrealQL Pipeline."""

import json
import logging
import numpy as np

from cohezion.graph.graph_engine import KnowledgeGraphMesh, EdgeType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [DEMO_GRAPH] %(message)s")
logger = logging.getLogger("demo_graph")

def demo_graph_mesh():
    mesh = KnowledgeGraphMesh()

    # 1. Add Graph Nodes (Agent, Goals, Artefacts, Verification Certificates)
    n_agent = mesh.add_node("agent:antigravity", "agent", {"tier": "Master Orchestrator", "host": "AMD Strix Halo"})
    n_goal1 = mesh.add_node("goal:first_principles", "goal", {"status": "satisfied", "priority": "high"})
    n_goal2 = mesh.add_node("goal:sovereign_inference", "goal", {"status": "satisfied", "priority": "critical"})
    n_mod1 = mesh.add_node("module:nano_chaos", "code_module", {"loc": 67, "verified": True})
    n_mod2 = mesh.add_node("module:nano_uma_compactor", "code_module", {"loc": 75, "verified": True})
    n_cert = mesh.add_node("proof:zkfv_sha256", "verification_proof", {"r0_score": 1.0, "status": "valid"})

    # 2. Add Directed Relational Edges
    mesh.add_edge("agent:antigravity", EdgeType.EXECUTES, "goal:first_principles")
    mesh.add_edge("agent:antigravity", EdgeType.EXECUTES, "goal:sovereign_inference")
    mesh.add_edge("goal:first_principles", EdgeType.DEPENDS_ON, "goal:sovereign_inference")
    mesh.add_edge("goal:first_principles", EdgeType.MUTATES, "module:nano_chaos")
    mesh.add_edge("goal:sovereign_inference", EdgeType.MUTATES, "module:nano_uma_compactor")
    mesh.add_edge("module:nano_chaos", EdgeType.SATISFIES, "proof:zkfv_sha256")
    mesh.add_edge("module:nano_uma_compactor", EdgeType.SATISFIES, "proof:zkfv_sha256")

    print("\n" + "=" * 95)
    print("🕸️ GRAPH ENGINEERING MESH: TOPOLOGY & RELATIONAL TRAVERSAL")
    print("=" * 95)

    # 3. Neighborhood Query
    neighbors = mesh.get_neighbors("agent:antigravity", direction="out")
    print(f"• 'agent:antigravity' Outgoing Neighbors: {neighbors}")
    assert "goal:first_principles" in neighbors

    # 4. K-Hop Subgraph Extraction
    sub_nodes, sub_edges = mesh.k_hop_subgraph("agent:antigravity", k=2)
    print(f"• 2-Hop Subgraph around 'agent:antigravity': {len(sub_nodes)} Nodes, {len(sub_edges)} Edges")
    assert len(sub_nodes) >= 4

    # 5. Topological Ordering
    order = mesh.topological_sort()
    print(f"• Topological Dependency Order: {order}")

    # 6. SurrealDB v2 Relational Statement Synthesis
    statements = mesh.generate_surrealql_batch()
    print(f"\n• Generated {len(statements)} SurrealDB v2 Relational Statements:")
    for stmt in statements[:6]:
        print(f"   {stmt}")

    print("\n" + "=" * 95)
    print("🎉 GRAPH ENGINEERING REFACTOR DEMO COMPLETED & VERIFIED!")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    demo_graph_mesh()
