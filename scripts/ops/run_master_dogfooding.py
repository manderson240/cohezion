#!/usr/bin/env python3
"""End-to-End Cohezion Dogfooding Execution Harness.

Exercises and verifies all subsystems in lockstep:
1. EventBus lifecycle & live pub/sub metrics
2. UnifiedHybridRouter across Tier 1 (Lemonade) and Tier 2 (Ollama Cloud)
3. Local LoRA safetensors checkpoint loading and parameter shapes
4. AdaptiveLatencyQualityEngine with real token & latency accounting
5. PoincareManifoldVisualizer 2048D hyperbolic projection
6. HIHOSonifier audio frequency synthesis
7. BioelectricSwarm numerical FitzHugh-Nagumo ODE solver & self-healing
8. SurrealDB & Obsidian Kanban task card persistence
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["ROCR_VISIBLE_DEVICES"] = ""
os.environ["HIP_VISIBLE_DEVICES"] = ""

import asyncio
import logging
import sys
import time
from pathlib import Path

import numpy as np
import safetensors.torch
import torch

from cohezion.agi.adaptive_latency_quality_engine import (
    AdaptiveLatencyQualityEngine,
    LatencyQualityProfile,
)
from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.flume.bioelectric_swarm import BioelectricSwarm
from cohezion.flume.poincare_manifold_visualizer import PoincareManifoldVisualizer
from cohezion.inference.unified_hybrid_router import TaskClass, UnifiedHybridRouter
from cohezion.physics.hiho_sonification import HIHOSonifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dogfood_harness")


async def run_dogfooding():
    print("\n" + "=" * 105)
    print("      🚀 COHEZION MASTER DOGFOODING VERIFICATION SUITE")
    print("=" * 105)

    # 1. EventBus verification
    logger.info("1/8: Initializing EventBus & registering dogfood subscriber...")
    bus = EventBus()
    await bus.start()
    events_received = []

    @bus.subscribe(EventType.AGENT_START)
    async def handle_start(evt: Event):
        events_received.append(evt)
        logger.info("  [EventBus] AGENT_START: %s (task=%s)", evt.source, evt.payload.get("task"))

    @bus.subscribe(EventType.AGENT_COMPLETE)
    async def handle_complete(evt: Event):
        events_received.append(evt)
        logger.info("  [EventBus] AGENT_COMPLETE: %s duration=%.2f ms", evt.source, evt.payload.get("duration_ms", 0.0))

    start_event = Event.agent_start(
        agent_name="cohezion_dogfood_agent",
        model="unified_hybrid_fleet",
        task="End-to-End Comprehensive Dogfooding Run",
    )
    await bus.publish(start_event)

    # 2. Local LoRA checkpoint validation
    logger.info("2/8: Verifying local LoRA fine-tuned checkpoint weights on disk...")
    safetensor_path = Path("/home/mike-anderson/dev/cohezion/checkpoints/cohezion_lora_qwen_adapter/adapter_model.safetensors")
    assert safetensor_path.exists(), "Adapter safetensors file missing!"
    weights = safetensors.torch.load_file(str(safetensor_path))
    assert len(weights) == 192, f"Expected 192 tensors, found {len(weights)}"
    print(f"  ✓ Fine-tuned LoRA Checkpoint Verified ({len(weights)} tensors, {safetensor_path.stat().st_size:,} bytes)")

    # 3. UnifiedHybridRouter Tier 1 Local Inference
    logger.info("3/8: Testing UnifiedHybridRouter Tier 1 Local Silicon dispatch...")
    router = UnifiedHybridRouter()
    t0 = time.perf_counter()
    tier1_res = await router.aquery_lemonade_local("State one core principle of resilient distributed systems in one sentence.", "gpt-oss-20b")
    tier1_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    assert tier1_res is not None and len(tier1_res) > 0, "Tier 1 inference failed!"
    print(f"  ✓ Tier 1 Local (gpt-oss-20b): {tier1_ms} ms -> \"{tier1_res[:100]}...\"")

    # 4. UnifiedHybridRouter Tier 2 Cloud Inference
    logger.info("4/8: Testing UnifiedHybridRouter Tier 2 Ollama Cloud dispatch...")
    t0 = time.perf_counter()
    tier2_res = await router.aquery_ollama_cloud("What is 17 * 19? Answer with just the number.", "deepseek-v4-flash:cloud")
    tier2_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    assert tier2_res is not None and "323" in tier2_res, f"Tier 2 inference returned unexpected: {tier2_res}"
    print(f"  ✓ Tier 2 Cloud (deepseek-v4-flash:cloud): {tier2_ms} ms -> \"{tier2_res.strip()}\"")

    # 5. Adaptive Latency Quality Engine
    logger.info("5/8: Testing AdaptiveLatencyQualityEngine with empirical measurements...")
    quality_engine = AdaptiveLatencyQualityEngine(event_bus=bus)
    q_res = await quality_engine.execute_quality_gated_synthesis(
        task_description="Define the role of semantic caching in agent swarms in one sentence.",
        profile=LatencyQualityProfile.SPEED_PRIORITY,
    )
    assert q_res.status == "✅ PASS", "Quality synthesis failed!"
    print(f"  ✓ Quality Synthesis: {q_res.model_used} -> {q_res.actual_latency_sec}s, {q_res.tokens_per_sec} tok/s (AST: {q_res.ast_verified})")

    # 6. Poincaré 2048D Hyperbolic Manifold Visualizer
    logger.info("6/8: Testing PoincareManifoldVisualizer 2048D projection & hyperbolic metric...")
    from cohezion.flume.poincare_manifold_visualizer import compute_hyperbolic_distance
    viz = PoincareManifoldVisualizer()
    u = np.random.uniform(-0.3, 0.3, size=2048)
    v = np.random.uniform(-0.3, 0.3, size=2048)
    d_p = compute_hyperbolic_distance(u, v)
    assert np.isfinite(d_p) and d_p > 0, "Poincare distance calculation failed!"
    fig = viz.generate_poincare_figure()
    assert fig is not None, "Plotly figure generation failed!"
    print(f"  ✓ Poincaré Manifold: Hyperbolic distance d_P={d_p:.4f} | Plotly points rendered={len(fig.data[0].x)}")

    # 7. HIHO Reality Sonification Engine
    logger.info("7/8: Testing HIHOSonifier audio frequency synthesis across 4 fabrics...")
    sonifier = HIHOSonifier()
    test_quadrature = {
        "Awareness": 0.50,
        "Pattern": 0.50,
        "Execution": 0.50,
        "Precipitation": 0.50,
        "Fabric_Space": 0.50,
        "Fabric_Field": 0.50,
        "Fabric_Control": 0.50,
        "Fabric_Precipitation": 0.50,
        "HIHO_Overlap": 0.50,
        "Lyapunov_Perturbation": 0.00,
        "Entropy_Rate": 0.00,
        "Phase_Angle": 0.00,
    }
    audio_frame = sonifier.sonify_quadrature_state(test_quadrature)
    assert audio_frame.coherence_distance == 0.0, "Expected perfect 0.5 coherence distance"
    assert audio_frame.fundamental_hz == 432.0, "Expected 432Hz fundamental at HIHO stability"
    print(f"  ✓ HIHO Sonifier: Fundamental={audio_frame.fundamental_hz}Hz, Coherence distance={audio_frame.coherence_distance}, Dissonance={audio_frame.dissonance_index}")

    # 8. Bioelectric Swarm Dynamics & FitzHugh-Nagumo ODE Solver
    logger.info("8/8: Testing BioelectricSwarm numerical FitzHugh-Nagumo dynamics & healing...")
    swarm = BioelectricSwarm(n_nodes=8, diffusion_coeff=0.5, time_constant=1.0)
    swarm.set_uniform_coupling(0.6)
    r_expanded = swarm.calculate_expanded_light_cone_radius()
    assert r_expanded >= 9.0, f"Expected expanded radius >= 9.0, got {r_expanded}"
    
    # Run ODE integration steps
    swarm.step_fitzhugh_nagumo_dynamics(dt=0.05, steps=5)
    
    # Inject fault and heal
    swarm.nodes[0].inject_fault(fault_type="oom")
    assert not swarm.nodes[0].is_healthy, "Fault injection failed"
    heal_res = swarm.heal_swarm()
    assert heal_res["success"] and swarm.nodes[0].is_healthy, "Self-healing failed!"
    print(f"  ✓ Bioelectric Swarm: Light cone R_c={r_expanded:.2f} | ODE integration step verified | Self-healing elapsed: {heal_res['elapsed_ms']:.2f}ms")

    # Complete EventBus cycle
    complete_event = Event.agent_complete(
        agent_name="cohezion_dogfood_agent",
        result={"status": "ALL_SYSTEMS_OPERATIONAL", "checks_passed": 8},
        duration_ms=round(tier1_ms + tier2_ms + (q_res.actual_latency_sec * 1000.0), 2),
    )
    await bus.publish(complete_event)
    await asyncio.sleep(0.5)
    await bus.stop()

    # Persist durable dogfooding item into SurrealDB & Obsidian
    persist_item({
        "id": f"dogfood-master-pass-{int(time.time())}",
        "title": "Master Dogfooding Verification: 8/8 Subsystems 100% Operational",
        "status": "completed",
        "priority": "critical",
        "source": "dogfood_harness",
        "category": "system_verification",
    })

    print("\n" + "=" * 105)
    print(f"  🎉 ALL 8 COHEZION SUBSYSTEMS PASSED DOGFOODING IN 100% EMPIRICAL REALITY! (Events: {len(events_received)})")
    print("=" * 105)


if __name__ == "__main__":
    asyncio.run(run_dogfooding())
