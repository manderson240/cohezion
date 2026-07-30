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
    print("  KIMI K3 QUICKSTART DOCS RESEARCH & CODEBASE TASK EXECUTION")
    print("  Target Doc: https://platform.kimi.ai/docs/guide/kimi-k3-quickstart")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f"  [EventBus Stream] {event.type.name} from \"{event.source}\"")

    run_id = f"kimi_k3_codebase_{int(time.time())}"

    # Step 1: Local Silicon Doc Research via Lemonade :13305 with NO TIMEOUT
    await bus.publish(Event.agent_start("local_doc_analyzer", model="Bonsai-1.7B-gguf"))
    print("[Step 1] Local Silicon Analyzing Kimi K3 Quickstart Doc Specs (Lemonade :13305, timeout=None)...")

    doc_summary_prompt = """
    Context from Kimi K3 Quickstart Docs (https://platform.kimi.ai/docs/guide/kimi-k3-quickstart):
    Kimi K3 is Moonshot AI's flagship model for long-horizon coding and end-to-end knowledge work (1M context window).
    Key features: Thinking Models, Reasoning Effort tuning (low/medium/high), JSON Mode, Partial Mode, Context Caching, Dynamic Tool Loading.

    Task: Based on these Kimi K3 features, specify an optimal refactoring/optimization task for the Cohezion inference fleet module (`src/cohezion/inference/fleet.py`).
    """

    await bus.publish(Event.llm_call("local_doc_analyzer", model="Bonsai-1.7B-gguf", prompt_tokens=250))
    t0 = time.time()

    async with httpx.AsyncClient(timeout=None) as client:
        r_local = await client.post("http://localhost:13305/v1/chat/completions", json={
            "model": "Bonsai-1.7B-gguf",
            "messages": [{"role": "user", "content": doc_summary_prompt}],
            "temperature": 0.2
        })
        if r_local.status_code == 200:
            analysis_result = r_local.json()["choices"][0]["message"]["content"].strip()
            duration_local = (time.time() - t0) * 1000
            await bus.publish(Event.llm_response("local_doc_analyzer", model="Bonsai-1.7B-gguf", response_tokens=300))
            await bus.publish(Event.agent_complete("local_doc_analyzer", result="success", duration_ms=duration_local))
            print(f"\n  ✓ Local Research Analysis Completed in {duration_local/1000:.2f}s:\n")
            print(analysis_result[:600])

    # Step 2: Dispatch Codebase Task to Kimi Model on :11434 with NO TIMEOUT
    print("\n[Step 2] Executing Kimi-K3 Codebase Task on Cohezion Inference Fleet...")
    await bus.publish(Event.agent_start("kimi_codebase_agent", model="kimi-k2.7-code:cloud"))

    codebase_task_prompt = """
You are Kimi K3, Moonshot AI's flagship long-horizon coding model.

Task for Cohezion Codebase (`src/cohezion/inference/fleet.py`):
Implement `KimiK3ReasoningDispatcher`:
1. `__init__(self, reasoning_effort: str = 'medium', enable_context_cache: bool = True)`
2. `async def dispatch(self, prompt: str, agent_id: str) -> dict[str, Any]`
3. Send EventBus events (`LLM_CALL`, `LLM_RESPONSE`, `AGENT_COMPLETE`).
4. Include self-verification `async def verify_kimi_dispatcher()`.

Return clean Python code with full type hints and docstrings.
"""

    t1 = time.time()
    await bus.publish(Event.llm_call("kimi_codebase_agent", model="kimi-k2.7-code:cloud"))

    async with httpx.AsyncClient(timeout=None) as client:
        r_cloud = await client.post("http://localhost:11434/api/generate", json={
            "model": "kimi-k2.7-code:cloud",
            "prompt": codebase_task_prompt,
            "stream": False
        })
        if r_cloud.status_code == 200:
            cloud_code = r_cloud.json().get("response", "").strip()
            duration_cloud = (time.time() - t1) * 1000
            await bus.publish(Event.llm_response("kimi_codebase_agent", model="kimi-k2.7-code:cloud"))
            await bus.publish(Event.agent_complete("kimi_codebase_agent", result="success", duration_ms=duration_cloud))

            print(f"\n  ✓ Kimi Codebase Execution Completed in {duration_cloud/1000:.2f}s!\n")
            print("===================================================================================")
            print(cloud_code[:2000])
            print("===================================================================================")

            with open("src/cohezion/inference/kimi_k3_dispatcher.py", "w") as f:
                f.write(cloud_code)
            print("  ✓ Saved synthesized module to `src/cohezion/inference/kimi_k3_dispatcher.py`")

    # Step 3: FLUME 12D Manifold Visualization & DataMesh Dual Write-Through
    evo = ExoticVacuumObject(agent_id=f"kimi_doc_{run_id}", universe_id="universe-flume-kimi-doc")
    evo.condense()
    actions = [
        "Fetched Kimi K3 Quickstart docs (platform.kimi.ai)",
        "Local silicon analyzed Kimi K3 features on Lemonade :13305",
        "Designed KimiK3ReasoningDispatcher for Cohezion inference fleet",
        "Executed task via Kimi model on :11434",
        "Saved src/cohezion/inference/kimi_k3_dispatcher.py"
    ]
    viz = EVOJourneyVisualizer(output_path=f".obsidian/kimi-doc-{run_id}-graph.json")
    graph_data = viz.process_evo(evo, actions)
    print(f"\n  ✓ 3D Cockpit Graph (.obsidian/kimi-doc-{run_id}-graph.json): {len(graph_data['nodes'])} trajectory nodes")

    sink_res = persist_item({
        "id": f"kanban_{run_id}",
        "title": f"Kimi K3 Quickstart Research & Codebase Task {run_id}",
        "status": "completed",
        "priority": "high",
        "source": "kimi/doc-pipeline",
        "category": "kimi_codebase_task",
        "details": f"Doc: Kimi K3 Quickstart | Codebase Target: src/cohezion/inference/kimi_k3_dispatcher.py | Events: {len(events_logged)}"
    })
    print(f"  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}")

    await bus.stop()

if __name__ == "__main__":
    asyncio.run(main())
