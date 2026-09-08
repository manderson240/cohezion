import asyncio
import time

import httpx

from cohezion.core.event_bus import Event, EventBus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.flume.evo_visualizer import EVOJourneyVisualizer
from cohezion.physics.evo_model import ExoticVacuumObject


async def main():
    print("===================================================================================")
    print("  WD-MYBOOK NETWORK HDD DIAGNOSTIC PIPELINE")
    print("  Endpoints: Local Silicon (:13305) & Ollama Cloud Peer Models (:11434)")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f'  [EventBus Stream] {event.type.name} from "{event.source}"')

    run_id = f"wd_diag_{int(time.time())}"

    # Step 1: Local Silicon Diagnostic Checklist
    await bus.publish(Event.agent_start("local_network_diagnostician", model="Bonsai-1.7B-gguf"))
    print(
        "[Step 1] Local Silicon Generating WD-MyBook NAS Network & Protocol Checklist (Lemonade :13305, timeout=None)..."
    )

    local_prompt = """
You are a Linux Systems Administration & Network Attached Storage (NAS) Specialist.

Problem Statement:
The user cannot access their local networked WD-MyBook HDD on a Linux system.

Analyze potential root causes:
1. Network Discovery & Addressing: mDNS / Avahi (.local resolution), static vs DHCP IP address changes, router client isolation.
2. Protocol & Version Compatibility: WD MyBook World / Live / Duo legacy SMB1 (NT1) vs SMB2/SMB3 requirements in modern Linux kernels (cifs-utils, `vers=1.0` vs `vers=2.1/3.0`, NTLM vs NTLMv2).
3. Linux Mount & Driver Configuration: Missing `cifs-utils`, `nfs-common`, `/etc/fstab` configuration, permission/UID mapping (`uid=1000,gid=1000`), or firewall (ufw / iptables) blocking ports 137, 138, 139, 445.

Provide a step-by-step diagnostic workflow.
"""

    await bus.publish(
        Event.llm_call("local_network_diagnostician", model="Bonsai-1.7B-gguf", prompt_tokens=300)
    )
    t0 = time.time()

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
            local_diag_text = r_local.json()["choices"][0]["message"]["content"].strip()
            duration_local = (time.time() - t0) * 1000
            await bus.publish(
                Event.llm_response(
                    "local_network_diagnostician", model="Bonsai-1.7B-gguf", response_tokens=400
                )
            )
            await bus.publish(
                Event.agent_complete(
                    "local_network_diagnostician", result="success", duration_ms=duration_local
                )
            )
            print(f"\n  ✓ Local Silicon Analysis Completed in {duration_local / 1000:.2f}s:\n")
            print(local_diag_text[:1000])

    # Step 2: Ollama Cloud Peer Model Deep Troubleshooting & Shell Script Generation
    print(
        "\n[Step 2] Ollama Cloud Peer Model (kimi-k2.7-code:cloud on :11434) Synthesizing Repair & Mount Script..."
    )
    await bus.publish(Event.agent_start("cloud_sysadmin_expert", model="kimi-k2.7-code:cloud"))

    cloud_prompt = f"""
You are an expert Linux Network & Storage Administrator.

Context from Local Research:
{local_diag_text[:1500]}

Task: Synthesize a safe, comprehensive Linux Shell Diagnostic & Repair Script `scripts/check_wd_mybook.sh` to troubleshoot and fix connectivity to the networked WD-MyBook HDD.

The script must:
1. Probe local subnet IP addresses for SMB ports (139, 445) and mDNS hostname `wdmybook.local` or `mybook.local`.
2. Test SMB protocol negotiations (`smbclient -L` with NTLM/SMB1 vs SMB2).
3. Check required packages (`cifs-utils`, `smbclient`, `avahi-daemon`).
4. Output recommended `/etc/fstab` mount entry for modern Linux kernels.

Return clean, executable Bash code.
"""

    t1 = time.time()
    await bus.publish(Event.llm_call("cloud_sysadmin_expert", model="kimi-k2.7-code:cloud"))

    async with httpx.AsyncClient(timeout=None) as client:
        r_cloud = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "kimi-k2.7-code:cloud", "prompt": cloud_prompt, "stream": False},
        )
        if r_cloud.status_code == 200:
            cloud_code = r_cloud.json().get("response", "").strip()
            duration_cloud = (time.time() - t1) * 1000
            await bus.publish(
                Event.llm_response("cloud_sysadmin_expert", model="kimi-k2.7-code:cloud")
            )
            await bus.publish(
                Event.agent_complete(
                    "cloud_sysadmin_expert", result="success", duration_ms=duration_cloud
                )
            )

            print(f"\n  ✓ Cloud Model Execution Completed in {duration_cloud / 1000:.2f}s!\n")
            print(
                "==================================================================================="
            )
            print(cloud_code[:1800])
            print(
                "==================================================================================="
            )

            with open("wd_mybook_diagnostic_guide.md", "w") as f:
                f.write(
                    f"# WD-MyBook Networked HDD Troubleshooting Guide\n\n## Local Silicon Analysis\n{local_diag_text}\n\n## Cloud Peer Synthesis & Diagnostic Workflow\n{cloud_code}\n"
                )
            print("  ✓ Saved report to `wd_mybook_diagnostic_guide.md`")

    # Step 3: FLUME 12D Manifold Visualization & DataMesh Dual Write-Through
    evo = ExoticVacuumObject(agent_id=f"wd_{run_id}", universe_id="universe-flume-wd")
    evo.condense()
    actions = [
        "Local silicon analyzed WD-MyBook network NAS failure modes",
        "Dispatched synthesis task to kimi-k2.7-code:cloud on :11434",
        "Generated wd_mybook_diagnostic_guide.md",
        "Persisted findings to SurrealDB and Vault",
    ]
    viz = EVOJourneyVisualizer(output_path=f".obsidian/wd-diag-{run_id}-graph.json")
    graph_data = viz.process_evo(evo, actions)
    print(
        f"\n  ✓ 3D Cockpit Graph (.obsidian/wd-diag-{run_id}-graph.json): {len(graph_data['nodes'])} trajectory nodes"
    )

    sink_res = persist_item(
        {
            "id": f"kanban_{run_id}",
            "title": f"WD-MyBook Networked HDD Diagnostics {run_id}",
            "status": "completed",
            "priority": "high",
            "source": "nas/wd-mybook-diag",
            "category": "network_storage",
            "details": "Local: Bonsai-1.7B (:13305) | Cloud: kimi-k2.7-code:cloud (:11434) | Report: wd_mybook_diagnostic_guide.md",
        }
    )
    print(
        f"  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}"
    )

    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
