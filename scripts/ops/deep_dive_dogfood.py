#!/usr/bin/env python3
"""
Deep-Dive Architecture & Graph Synthesis (Local + Ollama Cloud Swarm)
========================================================================
Combines:
  1. Local NPU (`deepseek-r1-0528-8b-FLM`) -> FLUME 12D Manifold Math & Physics
  2. Local iGPU (`Qwen3-Coder-30B-A3B-Instruct-GGUF`) -> Python Implementation Contracts
  3. Ollama Cloud (`qwen3.5:397b-cloud`) -> System-Wide Scaling & Graph Topology
  4. Ollama Cloud (`deepseek-v4-pro:cloud`) -> Adversarial Resilience & Circuit Breakers
  5. Ollama Cloud (`gpt-oss:120b-cloud`) -> Master Architecture Synthesis
"""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


# Endpoints & Config
SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()
LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "dogfood"
SESSION = "deep-dive-dogfood-session"


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
    event_id = f"evt_{source}_{int(time.time() * 1000)}"
    surreal_write(
        "event_log",
        event_id,
        {
            "type": event_type,
            "source": f"deepdive.{source}",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
            "session": SESSION,
        },
    )


def query_lemonade(model: str, prompt: str, timeout: float = 60.0) -> str:
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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode())
            msg = res["choices"][0]["message"]
            return (msg.get("content") or msg.get("reasoning_content") or "").strip()
    except Exception as e:
        return f"ERROR (Lemonade {model}): {e}"


def query_ollama(model: str, prompt: str, timeout: float = 60.0) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode())
            return res.get("response", "").strip()
    except Exception as e:
        return f"ERROR (Ollama {model}): {e}"


def main():
    print("=== Deep-Dive Architecture Synthesis (Local + Ollama Cloud) ===")
    publish_event("AGENT_START", "deepdive_coordinator", {"session": SESSION})

    # 1. Retrieve Knowledge Graph context
    nodes = surreal_query("SELECT id, title, domain, summary FROM kg_node;")
    edges = surreal_query("SELECT source, relation, target FROM kg_edge;")
    kg_text = f"Nodes: {json.dumps(nodes, indent=2)}\nEdges: {json.dumps(edges, indent=2)}"

    results = {}

    # Lane 1: NPU-First Local Reasoning (deepseek-r1-0528-8b-FLM on XDNA2)
    print("\n[1/4] Local NPU: Code Implementation Contracts (deepseek-r1-0528-8b-FLM)...")
    p1 = f"Given this Knowledge Graph:\n{kg_text}\nWrite clean Python contracts for the zero-cost verifier in node_autoharness."
    t0 = time.time()
    results["code_contracts"] = query_lemonade("deepseek-r1-0528-8b-FLM", p1)
    publish_event("JOURNEY_STEP", "local_npu", {"duration_s": round(time.time() - t0, 2)})
    print(f"  ✓ Complete in {round(time.time() - t0, 2)}s")

    # Lane 2: Ollama Cloud Frontier Scaling (qwen3.5:397b-cloud)
    print("\n[2/4] Cloud Frontier: Scaling & Graph Topology (qwen3.5:397b-cloud)...")
    p2 = f"Analyze the graph topology:\n{kg_text}\nHow do we scale this to 100k nodes while maintaining 12D manifold coherence?"
    t0 = time.time()
    results["graph_scaling"] = query_ollama("qwen3.5:397b-cloud", p2)
    publish_event("JOURNEY_STEP", "cloud_scaling", {"duration_s": round(time.time() - t0, 2)})
    print(f"  ✓ Complete in {round(time.time() - t0, 2)}s")

    # Lane 3: Ollama Cloud Adversarial Resilience (deepseek-v4-pro:cloud)
    print("\n[3/4] Cloud Security: Failure Modes & Circuit Breakers (deepseek-v4-pro:cloud)...")
    p3 = f"Review the inference cascade & graph relationships:\n{kg_text}\nIdentify 5 catastrophic failure modes and specify circuit breaker guardrails."
    t0 = time.time()
    results["circuit_breakers"] = query_ollama("deepseek-v4-pro:cloud", p3)
    publish_event("JOURNEY_STEP", "cloud_security", {"duration_s": round(time.time() - t0, 2)})
    print(f"  ✓ Complete in {round(time.time() - t0, 2)}s")

    # Lane 4: Ollama Cloud Master Synthesis (gpt-oss:120b-cloud)
    print("\n[4/4] Cloud Synthesizer: Master Architecture Spec (gpt-oss:120b-cloud)...")
    p4 = (
        f"Synthesize the outputs into a Master Cohezion Architecture Specification:\n\n"
        f"--- Code Contracts ---\n{results['code_contracts'][:2000]}\n\n"
        f"--- Graph Scaling ---\n{results['graph_scaling'][:2000]}\n\n"
        f"--- Circuit Breakers ---\n{results['circuit_breakers'][:2000]}\n\n"
        f"Produce a structured Markdown document with an Executive Summary, Architecture Diagram (Mermaid), and Action Plan."
    )
    t0 = time.time()
    results["master_spec"] = query_ollama("gpt-oss:120b-cloud", p4, timeout=90.0)
    publish_event("JOURNEY_STEP", "cloud_synthesizer", {"duration_s": round(time.time() - t0, 2)})
    print(f"  ✓ Complete in {round(time.time() - t0, 2)}s")

    # Write Master Spec to Vault
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    spec_path = VAULT_DIR / "DEEP_DIVE_SPECIFICATION.md"

    spec_content = f"""---
title: Cohezion Deep-Dive Architecture Specification
date: {datetime.now(UTC).isoformat()}
tags: [architecture, graph-engineering, local-inference, ollama-cloud, flume, autoharness]
session: {SESSION}
---

# Cohezion Deep-Dive Architecture Specification

## Executive Master Synthesis (gpt-oss:120b-cloud)
{results["master_spec"]}

---

## Section 1: Code Implementation Contracts (Qwen3-Coder-30B Local iGPU)
{results["code_contracts"]}

---

## Section 2: Graph Topology & Scalability (qwen3.5:397b-cloud)
{results["graph_scaling"]}

---

## Section 3: Adversarial Resilience & Circuit Breakers (deepseek-v4-pro:cloud)
{results["circuit_breakers"]}
"""
    spec_path.write_text(spec_content)
    print(f"\n✅ Master Specification written to Vault: {spec_path}")

    # Persist to SurrealDB
    surreal_write(
        "architecture_spec",
        "deep_dive_v1",
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "session": SESSION,
            "spec_file": str(spec_path),
            "results_summary": {k: len(v.split()) for k, v in results.items()},
        },
    )
    publish_event("AGENT_COMPLETE", "deepdive_coordinator", {"spec_file": str(spec_path)})
    print("✅ Registered run & events in SurrealDB")


if __name__ == "__main__":
    main()
