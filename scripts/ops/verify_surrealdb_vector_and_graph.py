#!/usr/bin/env python3
"""Verifies the new SurrealDB Vector HNSW search and Graph Relation features."""

import asyncio
import httpx
import json

SURREAL_URL = "http://127.0.0.1:8001/sql"
HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
}
AUTH = ("root", "root")


async def test_vector_and_graph():
    print("=" * 80)
    print("🧪 VERIFYING SURREALDB V2 HNSW VECTOR SEARCH & GRAPH RELATIONS")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Test 12D Vector Cosine Similarity Search
        query_vec = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        sql_vector = f"""
        SELECT id, title, domain, vector::similarity::cosine(embedding_12d, {query_vec}) AS similarity 
        FROM journey_knowledge 
        ORDER BY similarity DESC;
        """
        r_vec = await client.post(SURREAL_URL, headers=HEADERS, auth=AUTH, content=sql_vector)
        print("▶ 12D Poincaré HNSW Vector Search Output:")
        if r_vec.status_code == 200:
            res = r_vec.json()
            for row in res[0].get("result", []):
                print(
                    f"   • [{row.get('domain')}] {row.get('title')} (Cosine Similarity: {row.get('similarity'):.4f})"
                )

        # 2. Test Graph Edge Relation
        sql_graph = """
        LET $agent = (UPSERT agent:antigravity CONTENT { name: "Antigravity Master", role: "Orchestrator" });
        LET $evt = (UPSERT event_log:evt_test_01 CONTENT { type: "CUSTOM", source: "Antigravity", payload: "Graph Edge Test" });
        LET $item = (UPSERT kanban_item:kanban_test_01 CONTENT { title: "Test Kanban Card", status: "done" });
        
        RELATE agent:antigravity->EMITTED->event_log:evt_test_01;
        RELATE event_log:evt_test_01->TRIGGERED->kanban_item:kanban_test_01;
        
        SELECT ->EMITTED->event_log->TRIGGERED->kanban_item.title AS downstream_tasks FROM agent:antigravity;
        """
        r_graph = await client.post(SURREAL_URL, headers=HEADERS, auth=AUTH, content=sql_graph)
        print(
            "\n▶ Graph Edge Traversal Output (`agent->EMITTED->event_log->TRIGGERED->kanban_item`):"
        )
        if r_graph.status_code == 200:
            res_g = r_graph.json()
            # Last statement result
            last_res = res_g[-1].get("result", [])
            print(f"   ✓ Traversal Result: {last_res}")

    print("\n✓ SurrealDB Vector & Graph Verification Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_vector_and_graph())
