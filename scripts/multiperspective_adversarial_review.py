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
    print("  MULTIPERSPECTIVE ADVERSARIAL REVIEW VIA OLLAMA CLOUD PEER MODELS (:11434)")
    print("  Review Targets: KimiK3ReasoningDispatcher, AsyncSlidingWindowRateLimiter, AMD Plan")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f"  [EventBus Stream] {event.type.name} from \"{event.source}\"")

    run_id = f"adv_review_{int(time.time())}"

    # Read review target code
    with open("src/cohezion/inference/kimi_k3_dispatcher.py", "r") as f:
        dispatcher_code = f.read()[:2500]

    with open("amd_silicon_integration_plan.md", "r") as f:
        amd_plan = f.read()[:2000]

    review_perspectives = [
        {
            "role": "Security & Vulnerability Auditor",
            "model": "gpt-oss:120b-cloud",
            "fallback_model": "kimi-k2.7-code:cloud",
            "prompt": f"""You are a ruthless Security & Vulnerability Auditor. Perform a cynical adversarial security audit on:
1. `KimiK3ReasoningDispatcher` code:
{dispatcher_code}

2. AMD Silicon Integration Plan:
{amd_plan}

Identify edge cases, injection vectors, memory leak risks, authentication bypasses, or telemetry spoofing risks.
Provide 3 critical findings and proposed hardening fixes."""
        },
        {
            "role": "Systems Concurrency & Resilience Architect",
            "model": "kimi-k2.7-code:cloud",
            "fallback_model": "kimi-k2.7-code:cloud",
            "prompt": f"""You are a Systems Concurrency & Resilience Specialist. Perform a rigorous code and architecture review on:
1. `KimiK3ReasoningDispatcher` code:
{dispatcher_code}

2. Zero-allocation sliding-window rate limiter & AMD Plan:
{amd_plan}

Identify race conditions, lock contention under 10k concurrent requests/sec, event loop blocking risks, and async cancellation safety.
Provide 3 critical findings and architectural recommendations."""
        },
        {
            "role": "Hardware & Performance Tuning Engineer",
            "model": "glm-5.2:cloud",
            "fallback_model": "kimi-k2.7-code:cloud",
            "prompt": f"""You are a Hardware & Performance Tuning Engineer specializing in AMD RDNA3.5 iGPU and XDNA 2 NPU architecture.
Review the AMD Silicon Integration Plan:
{amd_plan}

Analyze memory bandwidth bottlenecks on 128GB Unified DDR5, NPU execution provider offloading latency, and Quark micro-scaling quantization efficiency.
Provide 3 performance tuning recommendations."""
        }
    ]

    review_results = []

    async with httpx.AsyncClient(timeout=None) as client:
        for p in review_perspectives:
            role_name = p["role"]
            target_model = p["model"]
            print(f"\n[Reviewer: {role_name}] Dispatching to {target_model} on :11434 (timeout=None)...")
            await bus.publish(Event.agent_start(role_name, model=target_model))
            await bus.publish(Event.llm_call(role_name, model=target_model))

            t0 = time.time()
            try:
                r = await client.post("http://localhost:11434/api/generate", json={
                    "model": target_model,
                    "prompt": p["prompt"],
                    "stream": False
                })
                if r.status_code != 200:
                    print(f"  · Model {target_model} returned status {r.status_code}. Using fallback {p['fallback_model']}...")
                    target_model = p["fallback_model"]
                    r = await client.post("http://localhost:11434/api/generate", json={
                        "model": target_model,
                        "prompt": p["prompt"],
                        "stream": False
                    })

                if r.status_code == 200:
                    resp_text = r.json().get("response", "").strip()
                    duration_ms = (time.time() - t0) * 1000
                    await bus.publish(Event.llm_response(role_name, model=target_model))
                    await bus.publish(Event.agent_complete(role_name, result="success", duration_ms=duration_ms))
                    print(f"  ✓ {role_name} Completed in {duration_ms/1000:.2f}s:")
                    print("-----------------------------------------------------------------------------------")
                    print(resp_text[:1200])
                    print("-----------------------------------------------------------------------------------")
                    review_results.append((role_name, target_model, resp_text))
            except Exception as exc:
                print(f"  · Review error for {role_name}: {exc}")

    # Aggregate report into Markdown Artifact
    report_content = f"# Multiperspective Adversarial Review Report\n\n*Generated via Ollama Cloud Peer Models on :11434*\n\n"
    for role, model, text in review_results:
        report_content += f"## Perspective: {role} (`{model}`)\n\n{text}\n\n---\n\n"

    report_path = "multiperspective_adversarial_review.md"
    with open(report_path, "w") as f:
        f.write(report_content)
    print(f"\n  ✓ Saved aggregated review report to `{report_path}`")

    # Step 3: FLUME 12D Manifold Visualization & DataMesh Dual Write-Through
    evo = ExoticVacuumObject(agent_id=f"adv_rev_{run_id}", universe_id="universe-flume-adv-review")
    evo.condense()
    actions = [
        "Dispatched Security & Vulnerability Auditor to Ollama cloud",
        "Dispatched Systems Concurrency Specialist to Ollama cloud",
        "Dispatched Hardware & Performance Tuning Engineer to Ollama cloud",
        "Aggregated multiperspective findings into multiperspective_adversarial_review.md"
    ]
    viz = EVOJourneyVisualizer(output_path=f".obsidian/adversarial-review-{run_id}-graph.json")
    graph_data = viz.process_evo(evo, actions)
    print(f"  ✓ 3D Cockpit Graph (.obsidian/adversarial-review-{run_id}-graph.json): {len(graph_data['nodes'])} trajectory nodes")

    sink_res = persist_item({
        "id": f"kanban_{run_id}",
        "title": f"Multiperspective Adversarial Review {run_id}",
        "status": "completed",
        "priority": "high",
        "source": "ollama-cloud/adversarial-review",
        "category": "adversarial_review",
        "details": f"Perspectives Evaluated: {len(review_results)} | Artifact: {report_path} | Events Tracked: {len(events_logged)}"
    })
    print(f"  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}")

    await bus.stop()

if __name__ == "__main__":
    asyncio.run(main())
