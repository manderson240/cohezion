import asyncio
import time

import httpx

from cohezion.core.event_bus import Event, EventBus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.flume.evo_visualizer import EVOJourneyVisualizer
from cohezion.physics.evo_model import ExoticVacuumObject


async def main():
    print("===================================================================================")
    print("  FLUME MANIFOLD SCALAR COORDINATES & 0.5 COHERENCE PIPELINE")
    print("  Endpoints: Local Silicon (Lemonade :13305) & Ollama Cloud Peer Models (:11434)")
    print("  Physics Protocol: HIHO 12-Parameter Quadrature & 0.5 Coherence Rule")
    print("===================================================================================\n")

    bus = EventBus()
    await bus.start()
    events_logged = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_logged.append(event)
        print(f'  [EventBus Stream] {event.type.name} from "{event.source}"')

    run_id = f"flume_scalar_{int(time.time())}"

    # Step 1: Local Silicon Formulation of Scalar Coordinates (:13305, timeout=None)
    await bus.publish(Event.agent_start("local_scalar_physicist", model="Bonsai-1.7B-gguf"))
    print(
        "[Step 1] Local Silicon Formulating Manifold Scalar Coordinates (Lemonade :13305, timeout=None)..."
    )

    scalar_prompt = """
You are a Theoretical Physicist and FLUME Latent Manifold Specialist.

System Context:
- HIHO Stability Protocol: Max stability in reality precipitation occurs at exactly 0.5 coherence overlap (The 0.5 Coherence Rule).
- 12D State Vector: 3 Spatial + 1 Time + 8 Brane dimensions.

Task: Formulate the exact Scalar Coordinates to complement the 12D vector manifold:
1. Coherence Overlap Scalar (C_0.5 = 1 - 2*|c - 0.5|).
2. Entropy Density Scalar (S_ent = -sum(p * log(p))).
3. Phase Velocity Scalar (v_phase = d(theta)/dt).
4. Reality Precipitation Scalar (P_precip = C_0.5 * exp(-Delta_S)).

Provide concise mathematical definitions and physical bounds [0.0, 1.0].
"""

    await bus.publish(
        Event.llm_call("local_scalar_physicist", model="Bonsai-1.7B-gguf", prompt_tokens=300)
    )
    t0 = time.time()

    local_scalar_math = ""
    async with httpx.AsyncClient(timeout=None) as client:
        r_local = await client.post(
            "http://localhost:13305/v1/chat/completions",
            json={
                "model": "Bonsai-1.7B-gguf",
                "messages": [{"role": "user", "content": scalar_prompt}],
                "temperature": 0.2,
            },
        )
        if r_local.status_code == 200:
            local_scalar_math = r_local.json()["choices"][0]["message"]["content"].strip()
            duration_local = (time.time() - t0) * 1000
            await bus.publish(
                Event.llm_response(
                    "local_scalar_physicist", model="Bonsai-1.7B-gguf", response_tokens=350
                )
            )
            await bus.publish(
                Event.agent_complete(
                    "local_scalar_physicist", result="success", duration_ms=duration_local
                )
            )
            print(
                f"\n  ✓ Local Scalar Physics Formulation Completed in {duration_local / 1000:.2f}s:\n"
            )
            print(local_scalar_math[:800])

    # Step 2: Ollama Cloud Synthesis of Python Module (`src/cohezion/flume/scalar_manifold_coordinates.py`)
    print(
        "\n[Step 2] Ollama Cloud Peer Model (kimi-k2.7-code:cloud on :11434) Synthesizing Scalar Manifold Module..."
    )
    await bus.publish(Event.agent_start("cloud_manifold_engineer", model="kimi-k2.7-code:cloud"))

    cloud_code_prompt = f"""
You are Kimi K2.7 Code, an elite software engineer.

Math Specification from Local Physics Analysis:
{local_scalar_math[:1200]}

Task: Implement `src/cohezion/flume/scalar_manifold_coordinates.py`:
1. `class ScalarManifoldCoordinates`:
   - `coherence_overlap: float` (target = 0.5)
   - `entropy_density: float`
   - `phase_velocity: float`
   - `precipitation_scalar: float`
2. `def compute_scalar_metrics(coherence: float, entropy: float, velocity: float) -> ScalarManifoldCoordinates`:
   Compute C_0.5 = max(0.0, 1.0 - 2.0 * abs(coherence - 0.5)) and P_precip.
3. `async def verify_scalar_manifold()`:
   Self-verification test function ensuring 0.5 coherence maximizes stability.

Return clean Python code with type hints and docstrings.
"""

    t1 = time.time()
    await bus.publish(Event.llm_call("cloud_manifold_engineer", model="kimi-k2.7-code:cloud"))

    async with httpx.AsyncClient(timeout=None) as client:
        r_cloud = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "kimi-k2.7-code:cloud", "prompt": cloud_code_prompt, "stream": False},
        )
        if r_cloud.status_code == 200:
            cloud_code = r_cloud.json().get("response", "").strip()
            duration_cloud = (time.time() - t1) * 1000
            await bus.publish(
                Event.llm_response("cloud_manifold_engineer", model="kimi-k2.7-code:cloud")
            )
            await bus.publish(
                Event.agent_complete(
                    "cloud_manifold_engineer", result="success", duration_ms=duration_cloud
                )
            )

            print(f"\n  ✓ Cloud Code Synthesis Completed in {duration_cloud / 1000:.2f}s!\n")
            print(
                "==================================================================================="
            )
            print(cloud_code[:1800])
            print(
                "==================================================================================="
            )

            with open("src/cohezion/flume/scalar_manifold_coordinates.py", "w") as f:
                f.write(cloud_code)
            print(
                "  ✓ Saved synthesized module to `src/cohezion/flume/scalar_manifold_coordinates.py`"
            )

    # Step 3: Artifact, FLUME 3D Cockpit Graph & DataMesh Persistence
    report_file = "flume_scalar_coordinates_report.md"
    full_markdown = f"""# FLUME Manifold Scalar Coordinates & 0.5 Coherence Report

*Generated via Local Silicon (Lemonade :13305) & Ollama Cloud (kimi-k2.7-code:cloud on :11434)*

---

## 1. Local Physics Scalar Coordinate Formulation
{local_scalar_math}

---

## 2. Synthesized Code Module
Saved to `src/cohezion/flume/scalar_manifold_coordinates.py`.
"""

    with open(report_file, "w") as f:
        f.write(full_markdown)
    print(f"\n  ✓ Saved report to `{report_file}`")

    evo = ExoticVacuumObject(agent_id=f"scalar_{run_id}", universe_id="universe-flume-scalar")
    evo.condense()
    actions = [
        "Local silicon formulated scalar coordinates and 0.5 Coherence Rule math",
        "Ollama cloud synthesized src/cohezion/flume/scalar_manifold_coordinates.py",
        "Exported flume_scalar_coordinates_report.md and 3D Cockpit Graph",
        "Persisted record to SurrealDB (:8001) and Vault",
    ]
    viz = EVOJourneyVisualizer(output_path=f".obsidian/flume-scalar-{run_id}-graph.json")
    graph_data = viz.process_evo(evo, actions)
    print(
        f"  ✓ 3D Cockpit Graph (.obsidian/flume-scalar-{run_id}-graph.json): {len(graph_data['nodes'])} trajectory nodes"
    )

    sink_res = persist_item(
        {
            "id": f"kanban_{run_id}",
            "title": f"FLUME Manifold Scalar Coordinates & 0.5 Coherence {run_id}",
            "status": "completed",
            "priority": "high",
            "source": "flume/scalar-coordinates",
            "category": "flume_physics",
            "details": f"Local: Bonsai-1.7B | Cloud: kimi-k2.7-code:cloud | Module: src/cohezion/flume/scalar_manifold_coordinates.py | Events: {len(events_logged)}",
        }
    )
    print(
        f"  ✓ DataMesh Persistence: SurrealDB={sink_res.get('surreal')}, Vault={sink_res.get('vault')}"
    )

    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
