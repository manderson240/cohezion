import asyncio
import time

import httpx

from cohezion.core.event_bus import Event, EventBus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.lemonade_cli_monitor import LemonadeCLIMonitor


async def main():
    print("===================================================================================")
    print("  DELEGATED MODEL STATUS & KANBAN SYNCHRONIZATION PIPELINE")
    print("  Local Silicon (Lemonade :13305) & Ollama Cloud Peer Models (:11434)")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f'  [EventBus Stream] {event.type.name} from "{event.source}"')

    run_id = f"kanban_sync_{int(time.time())}"

    # Step 0: Broadcast Fleet Status
    monitor = LemonadeCLIMonitor(event_bus=bus)
    fleet_event = await monitor.publish_fleet_status("delegated_sync_agent")
    print(
        f"  ✓ Fleet Status Event Published: {len(fleet_event.payload.get('loaded_models', []))} loaded models on :13305"
    )

    # Step 1: Local Silicon Codebase & Memory Audit (Lemonade :13305, timeout=None)
    await bus.publish(Event.agent_start("local_silicon_auditor", model="Bonsai-1.7B-gguf"))
    print("\n[Step 1] Local Silicon Auditing Core System State (Lemonade :13305, timeout=None)...")

    local_prompt = """
You are a Lead Systems Auditor.

Audit the current system state:
1. Fleet Monitoring: LemonadeCLIMonitor published Event.fleet_status on EventBus.
2. 2-Way RPC: BiDirectionalEventBridge running with correlation IDs.
3. Memory Guardrails: load_safety.defer_to_kanban_on_memory_pressure active.
4. Music Library: 22 FLAC albums organized into /mnt/wd_mybook/media/music.

Summarize system readiness in 2 paragraphs.
"""

    await bus.publish(
        Event.llm_call("local_silicon_auditor", model="Bonsai-1.7B-gguf", prompt_tokens=250)
    )
    t0 = time.time()

    local_audit = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_local = await client.post(
            "http://localhost:13305/v1/chat/completions",
            json={
                "model": "Bonsai-1.7B-gguf",
                "messages": [{"role": "user", "content": local_prompt}],
                "temperature": 0.2,
            },
        )
        if r_local.status_code == 200:
            local_audit = r_local.json()["choices"][0]["message"]["content"].strip()
            duration_local = (time.time() - t0) * 1000
            await bus.publish(
                Event.llm_response(
                    "local_silicon_auditor", model="Bonsai-1.7B-gguf", response_tokens=300
                )
            )
            await bus.publish(
                Event.agent_complete(
                    "local_silicon_auditor", result="success", duration_ms=duration_local
                )
            )
            print(f"  ✓ Local Silicon Audit Completed in {duration_local / 1000:.2f}s:\n")
            print(local_audit[:800])

    # Step 2: Ollama Cloud Strategic Guidance (kimi-k2.7-code:cloud on :11434, timeout=None)
    print(
        "\n[Step 2] Ollama Cloud Peer Model (kimi-k2.7-code:cloud on :11434, timeout=None) Synthesizing Strategic Roadmap..."
    )
    await bus.publish(Event.agent_start("cloud_roadmap_synthesizer", model="kimi-k2.7-code:cloud"))

    cloud_prompt = f"""
You are Kimi K2.7 Code, a Strategic AI Systems Architect.

Local Audit Summary:
{local_audit[:1000]}

Task: Synthesize the next strategic milestone for the Cohezion Swarm Ecosystem.
1. Local Agent Execution via GAIA SDK (`amd/gaia`).
2. Continuous Experiment Daemon Integration with SurrealDB (`:8001`).
3. Automated Quality Gating & AutoHarness Synthesis.

Provide 3 actionable priorities.
"""

    t1 = time.time()
    await bus.publish(Event.llm_call("cloud_roadmap_synthesizer", model="kimi-k2.7-code:cloud"))

    cloud_roadmap = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_cloud = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "kimi-k2.7-code:cloud", "prompt": cloud_prompt, "stream": False},
        )
        if r_cloud.status_code == 200:
            cloud_roadmap = r_cloud.json().get("response", "").strip()
            duration_cloud = (time.time() - t1) * 1000
            await bus.publish(
                Event.llm_response("cloud_roadmap_synthesizer", model="kimi-k2.7-code:cloud")
            )
            await bus.publish(
                Event.agent_complete(
                    "cloud_roadmap_synthesizer", result="success", duration_ms=duration_cloud
                )
            )
            print(f"\n  ✓ Cloud Roadmap Synthesis Completed in {duration_cloud / 1000:.2f}s!\n")
            print(
                "==================================================================================="
            )
            print(cloud_roadmap[:1500])
            print(
                "==================================================================================="
            )

    # Persist to DataMesh (SurrealDB + Vault)
    sink_res = persist_item(
        {
            "id": f"kanban_{run_id}",
            "title": f"Delegated Model Status & Strategic Sync {run_id}",
            "status": "completed",
            "priority": "high",
            "source": "inference/delegated-sync",
            "category": "strategic_roadmap",
            "details": f"Local: Bonsai-1.7B | Cloud: kimi-k2.7-code | Events: {len(events_logged)} | Status: Green",
        }
    )
    print(
        f"\n  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}"
    )

    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
