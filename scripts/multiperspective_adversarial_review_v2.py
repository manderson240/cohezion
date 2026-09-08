import asyncio
import time

import httpx

from cohezion.core.event_bus import Event, EventBus
from cohezion.data_mesh.kanban_bridge import persist_item


async def main():
    print("===================================================================================")
    print("  MULTIPERSPECTIVE ADVERSARIAL REVIEW PIPELINE (V2)")
    print("  Local Silicon (Lemonade :13305) & Ollama Cloud Peer Models (:11434)")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f'  [EventBus Stream] {event.type.name} from "{event.source}"')

    run_id = f"adv_review_{int(time.time())}"

    # Target codebase modules for review
    code_under_review = """
Modules Under Review:
1. `src/cohezion/core/bidirectional_event_bridge.py`: 2-way request-reply RPC with correlation IDs over EventBus.
2. `src/cohezion/inference/lemonade_cli_monitor.py`: Lemonade status parser & Event.fleet_status publisher.
3. `src/cohezion/inference/load_safety.py`: defer_to_kanban_on_memory_pressure() function.
4. `src/cohezion/flume/scalar_manifold_coordinates.py`: HIHO 0.5 Coherence scalar math (C_0.5 = max(0.0, 1.0 - 2.0*|c-0.5|)).
"""

    # Perspective 1: Security Auditor (gpt-oss:120b-cloud on :11434)
    print("[Perspective 1] Security Auditor (gpt-oss:120b-cloud on :11434, timeout=None)...")
    await bus.publish(Event.agent_start("security_auditor", model="gpt-oss:120b-cloud"))

    sec_prompt = f"""
You are an Adversarial Security Auditor.

{code_under_review}

Examine these modules for:
1. Correlation ID spoofing / replay attacks in BiDirectionalEventBridge.
2. Injection vulnerabilities in kanban_bridge / SurrealDB persistence.
3. Unsanitized status output in LemonadeCLIMonitor subprocess calls.

Provide 3 concise, high-severity findings with recommended patches.
"""

    t0 = time.time()
    await bus.publish(Event.llm_call("security_auditor", model="gpt-oss:120b-cloud"))

    sec_report = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_sec = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "gpt-oss:120b-cloud", "prompt": sec_prompt, "stream": False},
        )
        if r_sec.status_code == 200:
            sec_report = r_sec.json().get("response", "").strip()
            duration_sec = (time.time() - t0) * 1000
            await bus.publish(Event.llm_response("security_auditor", model="gpt-oss:120b-cloud"))
            await bus.publish(
                Event.agent_complete("security_auditor", result="success", duration_ms=duration_sec)
            )
            print(f"  ✓ Security Audit Completed in {duration_sec / 1000:.2f}s!")

    # Perspective 2: Memory & Concurrency Architect (kimi-k2.7-code:cloud on :11434)
    print(
        "\n[Perspective 2] Memory & Concurrency Architect (kimi-k2.7-code:cloud on :11434, timeout=None)..."
    )
    await bus.publish(Event.agent_start("concurrency_architect", model="kimi-k2.7-code:cloud"))

    conc_prompt = f"""
You are a Lead Concurrency Architect.

{code_under_review}

Examine these modules for:
1. Race conditions during parallel defer_to_kanban_on_memory_pressure() calls under high load.
2. EventBus handler execution deadlocks when requests block on pending futures.
3. Memory leak / unhandled futures in BiDirectionalEventBridge._pending_requests.

Provide 3 concise findings with concurrency fixes.
"""

    t1 = time.time()
    await bus.publish(Event.llm_call("concurrency_architect", model="kimi-k2.7-code:cloud"))

    conc_report = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_conc = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "kimi-k2.7-code:cloud", "prompt": conc_prompt, "stream": False},
        )
        if r_conc.status_code == 200:
            conc_report = r_conc.json().get("response", "").strip()
            duration_conc = (time.time() - t1) * 1000
            await bus.publish(
                Event.llm_response("concurrency_architect", model="kimi-k2.7-code:cloud")
            )
            await bus.publish(
                Event.agent_complete(
                    "concurrency_architect", result="success", duration_ms=duration_conc
                )
            )
            print(f"  ✓ Concurrency Audit Completed in {duration_conc / 1000:.2f}s!")

    # Perspective 3: Physics & FLUME Manifold Specialist (Local Silicon: Bonsai-1.7B-gguf on :13305)
    print(
        "\n[Perspective 3] Physics & FLUME Manifold Specialist (Local Silicon: Bonsai-1.7B-gguf on :13305, timeout=None)..."
    )
    await bus.publish(Event.agent_start("physics_specialist", model="Bonsai-1.7B-gguf"))

    phys_prompt = f"""
You are a Theoretical Physicist & FLUME Manifold Specialist.

{code_under_review}

Examine `scalar_manifold_coordinates.py` for:
1. C_0.5 mathematical derivative continuity at c = 0.5 (kink at absolute value slope).
2. Numerical underflow in P_precip = C_0.5 * exp(-entropy).
3. 12D manifold stability bounds under high entropy gradients.

Provide 3 concise mathematical recommendations.
"""

    t2 = time.time()
    await bus.publish(Event.llm_call("physics_specialist", model="Bonsai-1.7B-gguf"))

    phys_report = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_phys = await client.post(
            "http://localhost:13305/v1/chat/completions",
            json={
                "model": "Bonsai-1.7B-gguf",
                "messages": [{"role": "user", "content": phys_prompt}],
                "temperature": 0.2,
            },
        )
        if r_phys.status_code == 200:
            phys_report = r_phys.json()["choices"][0]["message"]["content"].strip()
            duration_phys = (time.time() - t2) * 1000
            await bus.publish(Event.llm_response("physics_specialist", model="Bonsai-1.7B-gguf"))
            await bus.publish(
                Event.agent_complete(
                    "physics_specialist", result="success", duration_ms=duration_phys
                )
            )
            print(f"  ✓ Physics Audit Completed in {duration_phys / 1000:.2f}s!")

    # Save Aggregated Report Artifact
    report_file = "multiperspective_adversarial_review_v2.md"
    aggregated = f"""# Multiperspective Adversarial Review (V2)

*Aggregated from Ollama Cloud (`gpt-oss:120b-cloud`, `kimi-k2.7-code:cloud`) & Local Silicon (`Bonsai-1.7B-gguf`)*

---

## Perspective 1: Security Audit (`gpt-oss:120b-cloud`)
{sec_report}

---

## Perspective 2: Concurrency & Memory Audit (`kimi-k2.7-code:cloud`)
{conc_report}

---

## Perspective 3: Physics & FLUME Manifold Audit (`Bonsai-1.7B-gguf`)
{phys_report}
"""

    with open(report_file, "w") as f:
        f.write(aggregated)
    print(f"\n  ✓ Saved aggregated adversarial review to `{report_file}`")

    sink_res = persist_item(
        {
            "id": f"kanban_{run_id}",
            "title": f"Multiperspective Adversarial Review V2 {run_id}",
            "status": "completed",
            "priority": "high",
            "source": "inference/adversarial-review",
            "category": "security_audit",
            "details": f"Security: gpt-oss:120b | Concurrency: kimi-k2.7-code | Physics: Bonsai-1.7B | Report: {report_file} | Events: {len(events_logged)}",
        }
    )
    print(
        f"  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}"
    )

    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
