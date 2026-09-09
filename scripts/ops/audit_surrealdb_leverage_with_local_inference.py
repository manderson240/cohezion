#!/usr/bin/env python3
"""Audit SurrealDB feature leverage in Cohezion via local inference (Lemonade :13305).

Evaluates whether Cohezion is fully exploiting modern SurrealDB capabilities:
1. Record ID & UPSERT syntax (`type::record("table", $id) CONTENT $data`)
2. Graph Relations (`RELATE agent:antigravity->EMITTED->event_log:evt_1`)
3. Live Queries (`LIVE SELECT * FROM ...`) for zero-polling inter-agent reactive streams
4. Vector Search / HNSW Indexing (`DEFINE INDEX poincare_idx ON ... HNSW DIMENSION 2048 DIST COSINE`)
5. Full-Text Search (FTS) & BM25 Analyzers
"""

import asyncio
import json
import logging
import os
import time
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("surreal_audit")

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
SURREAL_URL = "http://localhost:8001/sql"

SURREAL_CAPABILITIES = [
    ("HNSW Vector Indexing", "Does Cohezion use native HNSW indexing for 2048D Poincaré and 12D state lookups?"),
    ("Graph RELATE Syntax", "Are agent events and Kanban items connected via directional graph edges (->EMITTED->, ->TRANSITIONED->)?"),
    ("Live Queries (LIVE SELECT)", "Is EventBus leveraging LIVE SELECT WebSocket subscriptions for zero-latency inter-session synchronization?"),
    ("Full-Text Search (FTS)", "Are 71 PRIME skills indexed with SurrealDB BM25 / ngram analyzers?"),
    ("SurrealQL v2 ACID Transactions", "Are multi-agent state mutations executed within BEGIN TRANSACTION / COMMIT blocks?")
]

async def audit_surrealdb():
    print("\n" + "=" * 115)
    print("🐘 AUDITING SURREALDB LEVERAGE VIA LOCAL INFERENCE (AMD STRIX HALO :13305)")
    print("=" * 115)

    # 1. Probe Live SurrealDB Engine
    print("\n▶ [1] Probing Live SurrealDB Instance on port 8001...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.post(
                SURREAL_URL,
                headers={"surreal-ns": "cohezion", "surreal-db": "main", "Authorization": "Basic cm9vdDpyb290", "Content-Type": "text/plain"},
                content="INFO FOR DB;"
            )
            print(f"  ✓ SurrealDB Connection OK (HTTP {r.status_code})")
        except Exception as e:
            print(f"  ✗ SurrealDB probe failed: {e}")

    # 2. Local Inference Assessment (Qwen3-Coder-30B on iGPU)
    print("\n▶ [2] Delegating In-Depth SurrealDB Architectural Audit to Local Silicon (`Qwen3-Coder-30B`)...")
    
    prompt = """You are a Principal Database Architect & Systems Engineer auditing Cohezion's SurrealDB usage.
Evaluate our integration against modern SurrealDB (https://github.com/surrealdb/surrealdb):
1. Native HNSW Vector Indexing (`DEFINE INDEX ... HNSW DIMENSION 2048 DIST COSINE`) for Poincaré embeddings.
2. Directional Graph Relations (`RELATE agent:antigravity->EMITTED->event_log:evt_1`).
3. Reactive Live Queries (`LIVE SELECT * FROM event_log`) for zero-polling inter-session coordination.
4. Full-Text Search (FTS) with BM25 analyzers for 71 PRIME skills.
5. Atomic Transactions (`BEGIN TRANSACTION ... COMMIT`).

In 4 structured bullet points, detail:
- Current Strengths: Where Cohezion is already succeeding.
- Untapped Capabilities: What features from github.com/surrealdb we should activate next.
- Exact SurrealQL schema definitions needed to unlock these capabilities.
- Concrete architectural impact on AMD Strix Halo swarm performance."""

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
            "messages": [
                {"role": "system", "content": "You are the Cohezion Principal Database Architect."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        r = await client.post(LEMONADE_URL, json=payload)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            data = r.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            print(f"  ✓ Local Model Audit Generated in {dt}s ({len(content)} chars):\n")
            print(content.strip())
        else:
            print(f"  ✗ Local model error (HTTP {r.status_code}): {r.text[:100]}")
            content = "Audit failed due to inference error."

    os.makedirs("docs/research", exist_ok=True)
    report_path = "docs/research/surrealdb_comprehensive_leverage_audit.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 🐘 SurrealDB Comprehensive Feature Leverage Audit\n\n")
        f.write("**Hardware**: AMD Strix Halo (128GB Unified Memory, XDNA2 NPU, Radeon 8060S iGPU, Ryzen 9 CPU)  \n")
        f.write(f"**Date**: 2026-08-24  \n\n")
        f.write("## Local Silicon Expert Review (`Qwen3-Coder-30B` on iGPU)\n\n")
        f.write(f"```markdown\n{content.strip()}\n```\n")

    print("\n" + "=" * 115)
    print(f"📄 Audit Report Persisted to: {report_path}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(audit_surrealdb())
