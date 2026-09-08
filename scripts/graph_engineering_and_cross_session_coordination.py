import asyncio
import time

import httpx

from cohezion.core.event_bus import Event, EventBus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.flume.evo_visualizer import EVOJourneyVisualizer
from cohezion.inference.lemonade_cli_monitor import LemonadeCLIMonitor
from cohezion.physics.evo_model import ExoticVacuumObject


async def main():
    print("===================================================================================")
    print("  GRAPH ENGINEERING & CROSS-SESSION COORDINATION PIPELINE")
    print("  Local Silicon (Lemonade :13305) | Ollama Cloud Peer Models (:11434)")
    print("  Data Stores: SurrealDB (:8001) | Obsidian Vault (~/vaults/cohezion-vault/)")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f'  [EventBus Stream] {event.type.name} from "{event.source}"')

    run_id = f"graph_coord_{int(time.time())}"

    # Step 0: Check Lemonade CLI status and publish FLEET_STATUS
    monitor = LemonadeCLIMonitor(event_bus=bus)
    fleet_event = await monitor.publish_fleet_status("graph_coordinator")
    print(
        f"  ✓ Fleet Status Event Published: {len(fleet_event.payload.get('loaded_models', []))} loaded models on :13305"
    )

    # Step 1: Codebase Investigation via Local Silicon (:13305)
    await bus.publish(Event.agent_start("local_codebase_investigator", model="Bonsai-1.7B-gguf"))
    print(
        "\n[Step 1] Local Silicon Investigating Codebase State across Swarm, Compound, FLUME & DataMesh..."
    )

    codebase_prompt = """
You are a Lead Graph Systems Architect.

Investigate Cohezion's current architecture across these modules:
- `src/cohezion/swarm/`: Multi-agent team orchestration & V-Model engineering.
- `src/cohezion/compound/`: Executor, SessionManager, SkillRefiner.
- `src/cohezion/flume/`: 12D manifold latent state encoding & EVO trajectory visualization.
- `src/cohezion/data_mesh/`: Kanban bridge & SurrealDB persistence.
- `src/cohezion/inference/`: FleetLock single-flight loader & LemonadeCLIMonitor.

Provide a 3-paragraph structural synthesis of codebase state and graph linkages.
"""

    await bus.publish(
        Event.llm_call("local_codebase_investigator", model="Bonsai-1.7B-gguf", prompt_tokens=300)
    )
    t0 = time.time()

    codebase_synthesis = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_local = await client.post(
            "http://localhost:13305/v1/chat/completions",
            json={
                "model": "Bonsai-1.7B-gguf",
                "messages": [{"role": "user", "content": codebase_prompt}],
                "temperature": 0.2,
            },
        )
        if r_local.status_code == 200:
            codebase_synthesis = r_local.json()["choices"][0]["message"]["content"].strip()
            duration_local = (time.time() - t0) * 1000
            await bus.publish(
                Event.llm_response(
                    "local_codebase_investigator", model="Bonsai-1.7B-gguf", response_tokens=400
                )
            )
            await bus.publish(
                Event.agent_complete(
                    "local_codebase_investigator", result="success", duration_ms=duration_local
                )
            )
            print(f"  ✓ Codebase Investigation Completed in {duration_local / 1000:.2f}s:\n")
            print(codebase_synthesis[:800])

    # Step 2: Cross-Session & Vault Graph Engineering via Ollama Cloud (:11434)
    print(
        "\n[Step 2] Ollama Cloud Peer Model (kimi-k2.7-code:cloud on :11434) Conducting Graph Engineering & Vault Synthesis..."
    )
    await bus.publish(Event.agent_start("cloud_graph_engineer", model="kimi-k2.7-code:cloud"))

    graph_prompt = f"""
You are a Senior Graph Engineer specializing in FLUME 12D Manifold Encoding and Cross-Session Coordination.

Codebase Synthesis:
{codebase_synthesis[:1200]}

Task: Synthesize a unified Graph Engineering & Cross-Session Coordination Blueprint:
1. Define the 12D Latent Vector Mapping (3 Spatial + 1 Time + 8 Brane dimensions) for active agent session states.
2. Outline Cross-Session Event Bus Synchronization across active daemons, background workers, and persistent stores (SurrealDB `:8001` + Obsidian Vault `~/vaults/cohezion-vault/`).
3. Specify the Graph Query Protocol for retrieving past session decisions and preventing duplicate work loops.

Return clean, structured technical specifications.
"""

    t1 = time.time()
    await bus.publish(Event.llm_call("cloud_graph_engineer", model="kimi-k2.7-code:cloud"))

    cloud_graph_report = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_cloud = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "kimi-k2.7-code:cloud", "prompt": graph_prompt, "stream": False},
        )
        if r_cloud.status_code == 200:
            cloud_graph_report = r_cloud.json().get("response", "").strip()
            duration_cloud = (time.time() - t1) * 1000
            await bus.publish(
                Event.llm_response("cloud_graph_engineer", model="kimi-k2.7-code:cloud")
            )
            await bus.publish(
                Event.agent_complete(
                    "cloud_graph_engineer", result="success", duration_ms=duration_cloud
                )
            )

            print(f"\n  ✓ Cloud Graph Synthesis Completed in {duration_cloud / 1000:.2f}s!\n")
            print(
                "==================================================================================="
            )
            print(cloud_graph_report[:1800])
            print(
                "==================================================================================="
            )

    # Step 3: Write Comprehensive Artifact & Export 12D FLUME Graph
    report_file = "graph_engineering_coordination_report.md"
    full_markdown = f"""# Graph Engineering & Cross-Session Coordination Blueprint

*Generated via Local Silicon (Lemonade :13305) & Ollama Cloud (kimi-k2.7-code:cloud on :11434)*

---

## 1. Codebase State & Architectural Linkages
{codebase_synthesis}

---

## 2. 12D Latent Manifold & Cross-Session Synchronization Protocol
{cloud_graph_report}
"""

    with open(report_file, "w") as f:
        f.write(full_markdown)
    print(f"\n  ✓ Saved report to `{report_file}`")

    # Export FLUME 12D trajectory graph
    evo = ExoticVacuumObject(agent_id=f"graph_{run_id}", universe_id="universe-flume-graph-coord")
    evo.condense()
    actions = [
        "LemonadeCLIMonitor published FLEET_STATUS to EventBus",
        "Local silicon investigated codebase state across Swarm, Compound & DataMesh",
        "Ollama cloud synthesized 12D Latent Vector Mapping and Cross-Session Sync Protocol",
        "Exported graph_engineering_coordination_report.md and 3D Cockpit Graph",
    ]
    viz = EVOJourneyVisualizer(output_path=f".obsidian/cross-session-{run_id}-graph.json")
    graph_data = viz.process_evo(evo, actions)
    print(
        f"  ✓ 3D Cockpit Graph (.obsidian/cross-session-{run_id}-graph.json): {len(graph_data['nodes'])} trajectory nodes"
    )

    sink_res = persist_item(
        {
            "id": f"kanban_{run_id}",
            "title": f"Graph Engineering & Cross-Session Coordination {run_id}",
            "status": "completed",
            "priority": "high",
            "source": "flume/graph-coordination",
            "category": "graph_engineering",
            "details": f"Fleet Status: Published | Local: Bonsai-1.7B | Cloud: kimi-k2.7-code:cloud | Report: {report_file} | Events: {len(events_logged)}",
        }
    )
    print(
        f"  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}"
    )

    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
