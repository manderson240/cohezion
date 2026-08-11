#!/usr/bin/env python3
"""
Dogfooding Cohezion: Graph-Driven Local Inference & Event Bus Pipeline
========================================================================
Dogfoods:
  1. SurrealDB Knowledge Graph retrieval (kg_node + kg_edge + event_log)
  2. Local Inference via Lemonade OmniRouter (:13305) / GAIA Adapter
  3. Event Bus event publishing (AGENT_START, JOURNEY_STEP, AGENT_COMPLETE)
  4. Obsidian Vault + SurrealDB write-through persistence
"""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Paths & Auth
SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()
LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "dogfood"
SESSION = "dogfood-graph-session"


def surreal_query(surql: str) -> list:
    req = urllib.request.Request(
        SURREAL_URL,
        data=surql.encode(),
        headers={
            "Authorization": f"Basic {SURREAL_AUTH}",
            "Surreal-NS": "cohezion",
            "Surreal-DB": "main",
            "Accept": "application/json",
            "Content-Type": "text/plain",
        },
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())[0].get("result", [])


def surreal_write(table: str, record_id: str, data: dict) -> bool:
    clean_id = record_id.replace("-", "_")
    surql = f"UPSERT {table}:{clean_id} CONTENT {json.dumps(data)};"
    req = urllib.request.Request(
        SURREAL_URL,
        data=surql.encode(),
        headers={
            "Authorization": f"Basic {SURREAL_AUTH}",
            "Surreal-NS": "cohezion",
            "Surreal-DB": "main",
            "Accept": "application/json",
            "Content-Type": "text/plain",
        },
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        res = json.loads(r.read().decode())
        return bool(isinstance(res, list) and res and res[0].get("status") == "OK")


def publish_event(event_type: str, source: str, payload: dict) -> None:
    event_id = f"evt_{source}_{int(time.time()*1000)}"
    surreal_write(
        "event_log",
        event_id,
        {
            "type": event_type,
            "source": f"dogfood.{source}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "session": SESSION,
        },
    )


def query_local_llm(model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        LEMONADE_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        res = json.loads(r.read().decode())
        msg = res["choices"][0]["message"]
        return (msg.get("content") or msg.get("reasoning_content") or "").strip()


def main():
    print("=== Cohezion Dogfooding Execution ===")

    # 1. Publish AGENT_START to Event Bus
    publish_event(
        "AGENT_START",
        "graph_reasoner",
        {"mode": "dogfood", "timestamp": datetime.now(timezone.utc).isoformat()},
    )
    print("✓ Published AGENT_START to SurrealDB Event Bus")

    # 2. GraphRAG Retrieval: Read Knowledge Graph from SurrealDB
    nodes = surreal_query("SELECT id, title, domain, summary FROM kg_node;")
    edges = surreal_query("SELECT source, relation, target FROM kg_edge;")

    graph_context = f"Nodes ({len(nodes)}):\n" + "\n".join(
        [f"- {n['title']} ({n['domain']}): {n.get('summary','')}" for n in nodes]
    )
    graph_context += f"\n\nEdges ({len(edges)}):\n" + "\n".join(
        [f"- {e['source']} --[{e['relation']}]--> {e['target']}" for e in edges]
    )

    print(f"✓ Retrieved Knowledge Graph ({len(nodes)} nodes, {len(edges)} edges)")

    # 3. Publish JOURNEY_STEP
    publish_event(
        "JOURNEY_STEP",
        "graph_reasoner",
        {"step": "graph_retrieval_complete", "nodes": len(nodes), "edges": len(edges)},
    )

    # 4. Local Inference Pass using Bonsai-8B-gguf (iGPU lane)
    prompt = (
        "You are Cohezion's Autonomous Architecture Reasoner. "
        "Analyze the following Knowledge Graph context and synthesize a 3-point action plan "
        "to optimize Cohezion's self-healing, local inference cascade, and graph engineering:\n\n"
        f"{graph_context}\n\n"
        "Format output clearly as a Markdown report with concrete recommendations."
    )

    print("🔬 Querying Local Inference Model (Bonsai-8B-gguf on iGPU)...")
    t0 = time.time()
    synthesis = query_local_llm("Bonsai-8B-gguf", prompt)
    duration_s = round(time.time() - t0, 2)
    print(f"✓ Local Inference complete in {duration_s}s ({len(synthesis.split())} words)")

    # 5. Persist Output to Obsidian Vault & SurrealDB
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_id = f"dogfood_report_{int(time.time())}"
    vault_path = VAULT_DIR / f"{report_id}.md"

    vault_content = f"""---
title: Cohezion Dogfooding Graph Reasoning Synthesis
date: {datetime.now(timezone.utc).isoformat()}
tags: [dogfood, graph-engineering, local-inference, event-bus, surrealdb]
session: {SESSION}
---

# Cohezion Dogfooding Execution Report

**Execution Time**: {duration_s} seconds  
**Model**: `Bonsai-8B-gguf` (iGPU Vulkan)  
**Graph Input**: {len(nodes)} nodes, {len(edges)} edges  

## Graph-Driven Synthesis
{synthesis}

---
*Report generated via dogfooding pipeline: SurrealDB GraphRAG -> Local Lemonade Inference -> Event Bus Registration.*
"""
    vault_path.write_text(vault_content)
    print(f"✓ Vault report written: {vault_path}")

    # 6. Record to SurrealDB
    db_record = {
        "id": report_id,
        "session": SESSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nodes_count": len(nodes),
        "edges_count": len(edges),
        "synthesis": synthesis,
        "duration_s": duration_s,
    }
    surreal_write("dogfood_run", report_id, db_record)
    print("✓ SurrealDB record persisted (dogfood_run table)")

    # 7. Publish AGENT_COMPLETE
    publish_event(
        "AGENT_COMPLETE",
        "graph_reasoner",
        {"report_id": report_id, "duration_s": duration_s, "words": len(synthesis.split())},
    )
    print("✓ Published AGENT_COMPLETE to Event Bus")

    print("\n✅ Dogfooding execution complete with 100% success!")


if __name__ == "__main__":
    main()
