import asyncio
import json
import time
import httpx

from cohezion.core.event_bus import EventBus, Event, EventType
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.flume.evo_visualizer import EVOJourneyVisualizer
from cohezion.physics.evo_model import ExoticVacuumObject

async def main():
    print("===================================================================================")
    print("  REPO HEALTH AUDIT & BLEEDING-EDGE GITHUB ALTERNATIVES RESEARCH")
    print("  Endpoints: Local Silicon (:13305) & Ollama Cloud Peer Models (:11434)")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f"  [EventBus Stream] {event.type.name} from \"{event.source}\"")

    run_id = f"repo_forge_{int(time.time())}"

    # -----------------------------------------------------------------------------------
    # Step 1: Local Silicon Codebase Health Audit on Lemonade :13305 (timeout=None)
    # -----------------------------------------------------------------------------------
    await bus.publish(Event.agent_start("local_health_auditor", model="Bonsai-1.7B-gguf"))
    print("[Step 1] Local Silicon Conducting Repository Health Audit (Lemonade :13305, timeout=None)...")

    health_prompt = """
You are a Senior Principal Codebase Architect auditing the Cohezion repository.

System Context:
- Python >=3.13 (no-GIL ready), 88-char Black formatting, strict mypy typing.
- Module Size Limit: <550 LOC for all package entrypoints (`__init__.py`).
- Inference Discipline: Quarter on a String protocol (FleetLock, max 3 large models, single endpoint :13305).
- Test Hygiene: `pytest tests/unit/test_import_smoke.py` (26/26 passed), version governance hook active.

Task: Audit the repository health across 4 pillars:
1. Entrypoint Modularization (Extracting inline logic to factory modules).
2. Physical Memory Safety (128GB Unified RAM protection & iGPU aperture lock prevention).
3. AutoHarness Synthesis (Code-as-action-verifier & determinism).
4. CI/CD Ratchet Integrity (SemVer governance & import smoke validation).

Provide concise, actionable health ratings and recommendations.
"""

    await bus.publish(Event.llm_call("local_health_auditor", model="Bonsai-1.7B-gguf", prompt_tokens=350))
    t0 = time.time()

    local_health_report = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_local = await client.post("http://localhost:13305/v1/chat/completions", json={
            "model": "Bonsai-1.7B-gguf",
            "messages": [{"role": "user", "content": health_prompt}],
            "temperature": 0.2
        })
        if r_local.status_code == 200:
            local_health_report = r_local.json()["choices"][0]["message"]["content"].strip()
            duration_local = (time.time() - t0) * 1000
            await bus.publish(Event.llm_response("local_health_auditor", model="Bonsai-1.7B-gguf", response_tokens=400))
            await bus.publish(Event.agent_complete("local_health_auditor", result="success", duration_ms=duration_local))
            print(f"\n  ✓ Local Health Audit Completed in {duration_local/1000:.2f}s:\n")
            print(local_health_report[:900])

    # -----------------------------------------------------------------------------------
    # Step 2: Bleeding-Edge GitHub Alternatives Research via Ollama Cloud (:11434)
    # -----------------------------------------------------------------------------------
    print("\n[Step 2] Ollama Cloud Peer Model (kimi-k2.7-code:cloud on :11434) Researching GitHub Alternatives...")
    await bus.publish(Event.agent_start("cloud_forge_researcher", model="kimi-k2.7-code:cloud"))

    forge_research_prompt = """
You are a Distributed Systems & Open-Source Code Forge Specialist.

Cohezion Mission:
An autonomous AI swarm orchestration platform with FLUME 12D manifold encoding, local silicon acceleration (AMD Ryzen AI Max+ 395, 128GB Unified RAM, XDNA 2 NPU), and local-first data mesh storage (SurrealDB + Obsidian Vault).

Task: Research bleeding-edge GitHub alternatives and self-hosted code collaboration platforms that better suit Cohezion's autonomous agent swarm workflow:

Evaluate these alternatives:
1. Radicle (P2P, local-first, cryptographic Git collaboration protocol without central servers).
2. Forgejo / Gitea (Lightweight Go-based forge, low RAM footprint <100MB, native CI Actions runner support).
3. Soft Serve (Charm.sh) (Terminal-native, SSH-driven Git server built for CLI/agent automation).
4. OneDev (Self-hosted Git with AST code search, smart auto-test harness, and containerized CI).

Compare them against GitHub on:
- Agent Autonomy & Headless API Control
- Local Privacy & Zero-Cloud Dependency
- Resource Overhead on 128GB Unified RAM
- Agentic Workflow Integration (Hooks & Webhooks)

Provide a definitive recommendation matrix.
"""

    t1 = time.time()
    await bus.publish(Event.llm_call("cloud_forge_researcher", model="kimi-k2.7-code:cloud"))

    cloud_forge_report = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_cloud = await client.post("http://localhost:11434/api/generate", json={
            "model": "kimi-k2.7-code:cloud",
            "prompt": forge_research_prompt,
            "stream": False
        })
        if r_cloud.status_code == 200:
            cloud_forge_report = r_cloud.json().get("response", "").strip()
            duration_cloud = (time.time() - t1) * 1000
            await bus.publish(Event.llm_response("cloud_forge_researcher", model="kimi-k2.7-code:cloud"))
            await bus.publish(Event.agent_complete("cloud_forge_researcher", result="success", duration_ms=duration_cloud))

            print(f"\n  ✓ Cloud Research Completed in {duration_cloud/1000:.2f}s!\n")
            print("===================================================================================")
            print(cloud_forge_report[:1800])
            print("===================================================================================")

    # -----------------------------------------------------------------------------------
    # Step 3: Aggregate Artifact, FLUME 3D Cockpit Graph & DataMesh Persistence
    # -----------------------------------------------------------------------------------
    aggregated_markdown = f"""# Cohezion Repository Health & Code Forge Alternatives Report

*Generated via Local Silicon (Bonsai-1.7B-gguf on :13305) & Ollama Cloud (kimi-k2.7-code:cloud on :11434)*

---

## 1. Local Silicon Repository Health Audit
{local_health_report}

---

## 2. Bleeding-Edge Code Forge Alternatives Research
{cloud_forge_report}
"""

    report_file = "repo_health_and_forge_alternatives.md"
    with open(report_file, "w") as f:
        f.write(aggregated_markdown)
    print(f"\n  ✓ Saved comprehensive report to `{report_file}`")

    evo = ExoticVacuumObject(agent_id=f"forge_{run_id}", universe_id="universe-flume-forge")
    evo.condense()
    actions = [
        "Local silicon audited codebase health across 4 pillars",
        "Ollama cloud researched 4 bleeding-edge GitHub alternatives (Radicle, Forgejo, Soft Serve, OneDev)",
        "Synthesized comparative recommendation matrix",
        "Exported repo_health_and_forge_alternatives.md artifact"
    ]
    viz = EVOJourneyVisualizer(output_path=f".obsidian/repo-health-{run_id}-graph.json")
    graph_data = viz.process_evo(evo, actions)
    print(f"  ✓ 3D Cockpit Graph (.obsidian/repo-health-{run_id}-graph.json): {len(graph_data['nodes'])} trajectory nodes")

    sink_res = persist_item({
        "id": f"kanban_{run_id}",
        "title": f"Repo Health & GitHub Alternatives Research {run_id}",
        "status": "completed",
        "priority": "high",
        "source": "research/forge-alternatives",
        "category": "architecture_research",
        "details": f"Local: Bonsai-1.7B | Cloud: kimi-k2.7-code:cloud | Report: {report_file} | Events: {len(events_logged)}"
    })
    print(f"  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}")

    await bus.stop()

if __name__ == "__main__":
    asyncio.run(main())
