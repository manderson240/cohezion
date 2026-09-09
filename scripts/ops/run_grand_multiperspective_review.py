#!/usr/bin/env python3
"""Run Grand Multi-Perspective Adversarial Review & Bleeding-Edge Research Synthesis.

Invokes 4 distinct frontier personas via Tier 2 Ollama Cloud Fleet:
1. `deepseek-v4-pro:cloud`: Cynical Competitive Grandmaster & ARC-AGI Red Teamer.
2. `qwen3.5:397b-cloud`: Principal Systems Architect & GPU Kernel Engine Reviewer.
3. `glm-5.2:cloud`: Frontier Category-Theoretic & Topological Cohomology Researcher.
4. `deepseek-v4-pro:cloud`: AGI Autonomous Self-Improvement & Continuous Learning Auditor.

Saves comprehensive report to `docs/research/grand_multiperspective_adversarial_review.md`.
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

REVIEWS = [
    {
        "model": "deepseek-v4-pro:cloud",
        "persona": "Cynical Kaggle Grandmaster & ARC Red Teamer",
        "prompt": """You are a Cynical Kaggle Grandmaster and ARC-AGI Red Teamer.
Critique our latest solver stack:
- Object Graph DSL (connected component segmentation, bounding boxes, gravity, largest/smallest filters).
- 4-depth compositional beam search (width 30) + GFlowNet flow matching.
- Anytime GPU iterative synthesis loop with Qwen2.5-Coder and DeepSeek-R1.

Attack our blind spots:
1. What tasks will this STILL fail on (e.g. geometric symmetry, spatial analogies, topology, self-similar fractals)?
2. How do we close the gap to the 70%+ Kaggle leaderboard leaders?
3. Detail 3 high-leverage primitives we must implement immediately.
Keep it direct, adversarial, and under 250 words."""
    },
    {
        "model": "qwen3.5:397b-cloud",
        "persona": "Principal Systems & Strix Halo Hardware Architect",
        "prompt": """You are a Principal Hardware & Systems Architect for AMD Strix Halo (128GB unified RAM, XDNA2 NPU, Radeon iGPU).
Review our overnight autonomous learning loop and Kaggle execution model:
1. Substrate allocation: Dual T4 vs Local Strix Halo UMA memory bus contention.
2. AST verifier latency & zero-cost policy compilation (AutoHarness).
3. Memory leak risks in long-running overnight asyncio loops with SurrealDB / EventBus.
Provide a rigorous technical evaluation and failure prevention checklist under 250 words."""
    },
    {
        "model": "glm-5.2:cloud",
        "persona": "Frontier Category Theory & Topological Cohomology Researcher",
        "prompt": """You are a Theoretical Physicist and Cohomology Researcher.
Synthesize the next bleeding-edge mathematical breakthroughs Cohezion should deploy:
1. Cellular Sheaf Cohomology on ARC object graphs for obstruction detection ($H^0(X, \mathcal{F}) \to H^1(X, \mathcal{F})$).
2. Curvature-adaptive Ricci Flow on Riemannian latent manifolds for continuous shape deformation.
3. Hodge-Helmholtz decomposition of agent communication flows.
Detail how these elevate sovereign AGI reasoning beyond discrete search heuristics under 250 words."""
    },
    {
        "model": "deepseek-v4-pro:cloud",
        "persona": "AGI Recursive Self-Improvement & Experiential Learning Theorist",
        "prompt": """You are an AGI Recursive Self-Improvement Architect.
Evaluate Cohezion's experiential memory flywheel (12D/2048D Poincaré manifold clustering + SurrealDB learning table + skill distillation):
1. How to prevent experiential catastrophic forgetting during long overnight runs.
2. How to turn failed ARC task attempts into negative contrastive training pairs for test-time LoRA fine-tuning.
3. Design a closed-loop recursive skill refinement policy.
Keep it rigorous and actionable under 250 words."""
    }
]

async def query_reviewer(client: httpx.AsyncClient, item: dict) -> dict:
    model = item["model"]
    persona = item["persona"]
    prompt = item["prompt"]
    print(f"▶ Invoking Reviewer `{model}` ({persona})...")
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{OLLAMA_API_BASE}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2, "num_predict": 2500}},
            timeout=180.0
        )
        dt = time.perf_counter() - t0
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("response", "").strip() or data.get("thinking", "")[-1200:]
            print(f"   ✓ Review delivered by `{model}` ({persona}) in {dt:.2f}s")
            return {"model": model, "persona": persona, "content": content, "duration_s": dt, "status": "SUCCESS"}
        else:
            return {"model": model, "persona": persona, "content": f"HTTP {resp.status_code}: {resp.text}", "duration_s": dt, "status": "ERROR"}
    except Exception as e:
        return {"model": model, "persona": persona, "content": f"Notice: {e}", "duration_s": dt, "status": "ERROR"}

async def main():
    print("=" * 90)
    print("⚔️ RUNNING GRAND MULTI-PERSPECTIVE ADVERSARIAL REVIEW & BLEEDING-EDGE RESEARCH")
    print("=" * 90)

    async with httpx.AsyncClient() as client:
        tasks = [query_reviewer(client, item) for item in REVIEWS]
        results = await asyncio.gather(*tasks)

    doc_path = Path("docs/research/grand_multiperspective_adversarial_review.md")
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    md = f"""# Grand Multi-Perspective Adversarial Review & Frontier Research Synthesis

**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  
**Reviewer Fleet:** `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`  

---

"""
    for r in results:
        md += f"""# 🛡️ Perspective: {r['persona']}
**Model:** `{r['model']}` (Latency: {r['duration_s']:.2f}s | Status: {r['status']})  

### Adversarial Findings & Bleeding-Edge Directives
{r['content']}

---

"""
    doc_path.write_text(md)
    print(f"\n✓ Saved Grand Multi-Perspective Review to: {doc_path}")

    bus = await get_event_bus()
    bridge = CrossSessionEventBridge(event_bus=bus, session_id="multiperspective_reviewer")
    await bridge.initialize()

    ev = Event(
        type=EventType.CUSTOM,
        source="GrandMultiPerspectiveReviewer",
        priority=10,
        payload={
            "review": "Grand Multi-Perspective Adversarial Review & Frontier Research",
            "report_path": str(doc_path),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    )
    await bus.publish(ev)

    persist_item({
        "id": "grand_multiperspective_adversarial_review",
        "title": "Grand Multi-Perspective Review & Frontier Research Published",
        "status": "done",
        "priority": "critical",
        "source": "MultiPerspectiveReviewer",
        "category": "frontier_research",
        "details": "4-perspective adversarial audit delivered: Red Team gaps, Strix Halo UMA memory bus safety, Cellular Sheaf Cohomology, and Closed-Loop Contrastive Learning.",
    })
    print("✓ Persisted review card to SurrealDB and Obsidian Kanban")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(main())
