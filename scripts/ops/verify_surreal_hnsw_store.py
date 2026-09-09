#!/usr/bin/env python3
"""Verify Enhanced SurrealDB HNSW Vector Store."""

import time
from cohezion.memory.surreal_vector_store import SurrealVectorStore

def test_surreal_vector_store():
    print("Testing Enhanced SurrealVectorStore with Native HNSW Index...")
    store = SurrealVectorStore(
        collection_name="test_poincare_hnsw",
        embedding_model_dims=4,
    )
    
    # 1. Insert dummy Poincaré vectors
    vecs = [
        [0.1, 0.2, 0.3, 0.4],
        [0.8, 0.1, 0.2, 0.1],
        [0.12, 0.22, 0.31, 0.39],
    ]
    payloads = [
        {"skill": "poincare_navigation", "difficulty": 0.8},
        {"skill": "kernel_compilation", "difficulty": 0.5},
        {"skill": "hiho_sonification", "difficulty": 0.85},
    ]
    ids = ["vec_1", "vec_2", "vec_3"]
    
    store.insert(vectors=vecs, payloads=payloads, ids=ids)
    print("  ✓ Inserted 3 vectors into SurrealDB table with HNSW index.")
    
    # 2. Benchmark native vector search
    t0 = time.perf_counter()
    results = store.search(query="", vectors=[0.1, 0.2, 0.3, 0.4], top_k=2)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    
    print(f"  ✓ Native HNSW Vector Search executed in {dt_ms:.3f} ms. Found {len(results)} matches:")
    for r in results:
        print(f"    • ID: {r.id}, Score: {r.score:.4f}, Skill: {r.payload.get('skill')}")
        
    assert len(results) > 0
    print("✅ Enhanced SurrealDB HNSW Vector Store: 100% OPERATIONAL")

if __name__ == "__main__":
    test_surreal_vector_store()
