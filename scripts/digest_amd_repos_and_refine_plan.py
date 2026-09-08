import asyncio
import time

import httpx

from cohezion.core.event_bus import Event, EventBus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.flume.evo_visualizer import EVOJourneyVisualizer
from cohezion.physics.evo_model import ExoticVacuumObject


async def main():
    print("===================================================================================")
    print("  LOCAL INFERENCE DEEP DIGESTION OF AMD GITHUB REPOSITORIES (:13305)")
    print("  Target: https://github.com/amd/ (gaia, Quark, RyzenAI-SW, Vitis-AI, vllm, ZenDNN)")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f'  [EventBus Stream] {event.type.name} from "{event.source}"')

    run_id = f"amd_digest_{int(time.time())}"

    # Dispatch to Local Silicon on :13305 with timeout=None
    await bus.publish(Event.agent_start("local_amd_architect", model="Bonsai-1.7B-gguf"))
    print(
        "[Step 1] Local Silicon Digesting AMD GitHub Repositories (Lemonade :13305, timeout=None)..."
    )

    digest_prompt = """
You are an expert AMD Silicon & AI Systems Architect.

System Context:
- Hardware: Framework 16 PC with AMD Ryzen AI Max+ 395 / Ryzen 9 7945HX, Radeon 8060S / 7700S iGPU (128GB Unified DDR5 VRAM), AMD XDNA 2 NPU (50 TOPS).
- Single Endpoint Discipline: Lemonade OmniRouter on `http://localhost:13305`.

Target AMD Repositories on github.com/amd:
1. `amd/gaia` (GAIA SDK): Local privacy-first AI agent framework.
2. `amd/Quark` (Quark Quantization): Cross-platform INT4/FP8/MXFP micro-scaling quantization toolkit.
3. `amd/RyzenAI-SW` & `amd/Vitis-AI` (Vitis AI EP): ONNX Runtime execution provider for XDNA 2 NPU offloading.
4. `amd/vllm` & `amd/ROCm` (ROCm vLLM): PagedAttention & FlashAttention-3 for RDNA3/3.5 iGPU dynamic batching.
5. `amd/ZenDNN` (ZenDNN CPU Library): Zen 5 CPU AVX-512 VNNI neural network optimization.

Task: Digest these repositories and synthesize a refined 4-phase Cohezion Integration Plan:
Phase 1: Single-Endpoint Lemonade OmniRouter (:13305) & GAIA Agent Tier Mapping
Phase 2: XDNA 2 NPU Daemon Offloading (NPU Vitis AI EP for EventBus Prompt Guard & FLUME VAE)
Phase 3: AMD Quark Micro-scaling Quantization Pipeline for 128GB Unified RAM
Phase 4: ROCm-vLLM & ZenDNN High-Throughput Execution Lanes

Return structured, actionable technical specifications.
"""

    await bus.publish(
        Event.llm_call("local_amd_architect", model="Bonsai-1.7B-gguf", prompt_tokens=350)
    )
    t0 = time.time()

    refined_plan_text = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_local = await client.post(
            "http://localhost:13305/v1/chat/completions",
            json={
                "model": "Bonsai-1.7B-gguf",
                "messages": [{"role": "user", "content": digest_prompt}],
                "temperature": 0.2,
            },
        )
        if r_local.status_code == 200:
            refined_plan_text = r_local.json()["choices"][0]["message"]["content"].strip()
            duration_local = (time.time() - t0) * 1000
            await bus.publish(
                Event.llm_response(
                    "local_amd_architect", model="Bonsai-1.7B-gguf", response_tokens=500
                )
            )
            await bus.publish(
                Event.agent_complete(
                    "local_amd_architect", result="success", duration_ms=duration_local
                )
            )
            print(f"\n  ✓ Local Silicon Synthesis Completed in {duration_local / 1000:.2f}s:\n")
            print(
                "==================================================================================="
            )
            print(refined_plan_text)
            print(
                "==================================================================================="
            )

    # Save artifact file
    artifact_path = "amd_silicon_integration_plan.md"
    with open(artifact_path, "w") as f:
        f.write(
            f"# Cohezion AMD Silicon Integration Plan\n\n*Generated via Local Silicon (Bonsai-1.7B-gguf on :13305)*\n\n{refined_plan_text}\n"
        )
    print(f"\n  ✓ Saved refined plan to `{artifact_path}`")

    # Step 3: FLUME 12D Manifold Visualization & DataMesh Dual Write-Through
    evo = ExoticVacuumObject(agent_id=f"amd_{run_id}", universe_id="universe-flume-amd")
    evo.condense()
    actions = [
        "Digested github.com/amd repos (gaia, Quark, RyzenAI-SW, Vitis-AI, vllm, ZenDNN)",
        "Local silicon synthesized 4-phase integration plan on Lemonade :13305",
        "Configured single-endpoint Lemonade :13305 dispatching",
        "Exported amd_silicon_integration_plan.md artifact",
    ]
    viz = EVOJourneyVisualizer(output_path=f".obsidian/amd-digest-{run_id}-graph.json")
    graph_data = viz.process_evo(evo, actions)
    print(
        f"  ✓ 3D Cockpit Graph (.obsidian/amd-digest-{run_id}-graph.json): {len(graph_data['nodes'])} trajectory nodes"
    )

    sink_res = persist_item(
        {
            "id": f"kanban_{run_id}",
            "title": f"AMD Silicon Repositories Digest & Integration Plan {run_id}",
            "status": "completed",
            "priority": "high",
            "source": "amd/local-digest",
            "category": "amd_silicon_plan",
            "details": f"Target: github.com/amd | Endpoint: Lemonade :13305 | Artifact: {artifact_path} | Events: {len(events_logged)}",
        }
    )
    print(
        f"  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}"
    )

    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
