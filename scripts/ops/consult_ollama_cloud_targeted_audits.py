#!/usr/bin/env python3
"""Targeted Multi-Perspective Platform Audit via Tier 2 Ollama Cloud Fleet.

Queries DeepSeek-V4 Pro, Qwen 397B, and GLM-5.2 with adequate token limits for thorough thinking.
"""

import asyncio
import os
import time
import httpx
from pathlib import Path

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import get_event_bus, Event, EventType
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.data_mesh.kanban_bridge import persist_item

OLLAMA_API_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

AUDIT_QUERIES = [
    {
        "model": "deepseek-v4-pro:cloud",
        "domain": "Hyperbolic Mathematics & Topological Convergence",
        "prompt": """You are a Principal Differential Geometer. Audit Cohezion's FLUME 12D/2048D Poincaré Manifold and HIHO 0.5 Reality Precipitation Model:
1. Poincaré Metric: d_P(u, v) = arcosh(1 + 2*||u-v||^2 / ((1-||u||^2)(1-||v||^2))).
2. 0.5 Coherence Rule: Peak precipitation stability occurs at exactly 50% overlap between Spatial and Brane fabrics.
3. Fréchet Riemannian Centroid convergence for multi-agent skill embeddings.

Assess mathematical rigor, numerical stability near ||u||->1.0 boundary, and provide a clear verdict (PASS / ADVISORY / FAIL) with concrete recommendations."""
    },
    {
        "model": "qwen3.5:397b-cloud",
        "domain": "AutoHarness AST Action Verification & Kaggle Competitive Viability",
        "prompt": """You are a Kaggle Grandmaster and Compiler Systems Architect. Audit Cohezion's AutoHarness deterministic code-as-action verifiers (arXiv:2603.03329v1) deployed for ARC Prize 2026:
1. 0.00ms execution latency AST bytecode verification against training invariants.
2. Dynamic input filesystem discovery (os.walk('/kaggle/input')) across diverse competition runners.
3. 3-Stage Depth/Breadth Compositional Synthesizer f_3(f_2(f_1(x))) + Todorcevic minimal-oscillation lattice walks.

Assess search complexity bottlenecks, recommended invariant primitives (e.g. topological Euler characteristic, sub-grid parity), and provide a clear verdict (PASS / ADVISORY / FAIL)."""
    },
    {
        "model": "glm-5.2:cloud",
        "domain": "Agentic Event-Driven DataMesh & Multi-Agent Collaboration",
        "prompt": """You are a Distributed Systems & Multi-Agent Collaboration Architect. Audit Cohezion's inter-session coordination architecture between Antigravity and Claude Code:
1. EventBus in-memory pub/sub + bi-temporal async write-through bridges to SurrealDB (`data_product_event`, `event_log`).
2. Multi-hop Graph Edge Traversals: `RELATE agent->EMITTED->event_log->TRIGGERED->kanban_item`.
3. Concurrency Discipline: SmartOOMGovernor (50 GiB floor) + CrossSessionFleetLock mutexes preventing iGPU/NPU memory aperture collisions on AMD Strix Halo.

Assess deadlock risks, message ordering guarantees, cross-session state durability, and provide a clear verdict (PASS / ADVISORY / FAIL)."""
    }
]

async def query_model(client: httpx.AsyncClient, query: dict) -> dict:
    model = query["model"]
    domain = query["domain"]
    prompt = query["prompt"]
    
    print(f"▶ Querying Tier 2 Ollama Cloud model `{model}` on [{domain}]...")
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{OLLAMA_API_BASE}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 4096}
            },
            timeout=180.0
        )
        dt = time.perf_counter() - t0
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("response", "").strip()
            thinking = data.get("thinking", "").strip()
            # If response is empty but thinking has content, extract summary
            full_text = content if content else (thinking[-1200:] if thinking else "Empty Response")
            print(f"   ✓ Received response from `{model}` in {dt:.2f}s ({len(full_text)} chars)")
            return {"model": model, "domain": domain, "content": full_text, "thinking": thinking, "duration_s": dt, "status": "SUCCESS"}
        else:
            print(f"   ⚠️ Cloud endpoint returned HTTP {resp.status_code}")
            return {"model": model, "domain": domain, "content": f"HTTP {resp.status_code}: {resp.text}", "thinking": "", "duration_s": dt, "status": "ERROR"}
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f"   ⚠️ Connection notice for `{model}`: {e}")
        return {"model": model, "domain": domain, "content": f"Connection notice: {e}", "thinking": "", "duration_s": dt, "status": "ERROR"}

async def run_cloud_audits():
    print("=" * 90)
    print("☁️ RUNNING TARGETED TIER 2 OLLAMA CLOUD PLATFORM AUDITS (EXTENDED THINKING)")
    print("=" * 90)

    results = []
    async with httpx.AsyncClient() as client:
        tasks = [query_model(client, q) for q in AUDIT_QUERIES]
        results = await asyncio.gather(*tasks)

    # Compile Markdown Report
    doc_path = Path("docs/research/ollama_cloud_targeted_platform_audits.md")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    
    md_content = f"""# Targeted Platform Audits: Tier 2 Ollama Cloud Fleet

**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  
**Architecture:** Cohezion Sovereign Hybrid Silicon & Cloud Mesh  
**Models Consulted:** `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`  

---

"""
    for r in results:
        md_content += f"""## 🎯 {r['domain']}
**Auditor:** `{r['model']}` (Execution Time: {r['duration_s']:.2f}s | Status: {r['status']})  

### Audit Evaluation
{r['content']}

---

"""

    doc_path.write_text(md_content)
    print(f"\n✓ Saved comprehensive multi-perspective audit report to: {doc_path}")

    # Synchronize with EventBus & SurrealDB
    bus = await get_event_bus()
    bridge = CrossSessionEventBridge(event_bus=bus, session_id="antigravity_master_orchestrator")
    await bridge.initialize()

    ev = Event(
        type=EventType.CUSTOM,
        source="AntigravityCloudAuditor",
        priority=8,
        payload={
            "audit": "Tier 2 Ollama Cloud Fleet Multi-Perspective Platform Audit",
            "models": [r["model"] for r in results],
            "report_path": str(doc_path),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    )
    await bus.publish(ev)

    persist_item({
        "id": "ollama_cloud_platform_audit",
        "title": "Tier 2 Ollama Cloud Targeted Platform Audits Complete",
        "status": "done",
        "priority": "high",
        "source": "AntigravityCloudAuditor",
        "category": "architecture_audit",
        "details": f"Consulted DeepSeek-V4 Pro, Qwen 397B, and GLM-5.2 across mathematics, AST verifiers, and DataMesh graph topology.",
    })
    print("✓ Persisted audit card to SurrealDB `event_log` and Obsidian Kanban")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(run_cloud_audits())
