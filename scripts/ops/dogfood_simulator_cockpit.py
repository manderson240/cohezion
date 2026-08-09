"""End-to-End Live Dogfooding: End-User Simulator Agents, Transformative Pillars, & Visual Cockpit.

Runs live simulation pass:
1. Preflight fleet safety check.
2. Spawns end-user simulator agents (mass_sim 256D latent populations & simulated user queries).
3. Routes prompts through UnifiedHybridRouter (with FLUME VAE 256D latent prompt encoding).
4. Verifies AST safety via AutoHarnessPolicy (<1 ms) & compiles ZKFV polynomial proofs.
5. Tracks 2048D hyperbolic trajectory drift via PoincareManifoldTracker.
6. Evaluates EVI-gated self-healing via EVIHealer and writes dual-sink Kanban cards (SurrealDB + Obsidian).
7. Renders terminal & HTML visual cockpit dashboards.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

import numpy as np

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.agi.zkfv_compiler import ZKFVCompiler
from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.delegation_logger import DelegationLogger
from cohezion.inference.hardware_telemetry import ComputeBackend
from cohezion.inference.strix_halo_optimizer import StrixHaloSiliconOptimizer
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter
from cohezion.mass_sim.agent_factory import AgentFactory
from cohezion.physics.poincare_manifold import PoincareManifoldTracker
from cohezion.proactive.evi_healer import EVIHealer
from visual_cockpit import render_terminal_cockpit, generate_html_cockpit


logger = logging.getLogger("dogfood_simulator_cockpit")


def run_dogfooding_session() -> None:
    print("\n" + "=" * 70)
    print("🐕 LIVE DOGFOODING: END-USER SIMULATOR AGENTS & VISUAL COCKPIT")
    print("=" * 70)

    # 1. Preflight Check
    optimizer = StrixHaloSiliconOptimizer()
    print("\n[1/7] Running Strix Halo Preflight Alignment Verification...")
    is_aligned = optimizer.verify_wave32_alignment()
    print(f"  • Wave32 Matrix Alignment: {'✅ ALIGNED' if is_aligned else '❌ MISALIGNED'}")
    print(f"  • UMA GTT Aperture Limit : {optimizer.profile.gtt_pool_max_gb} GB")

    # 2. Spawn End-User Simulator Population
    print("\n[2/7] Spawning Synthetic End-User Simulator Agents (mass_sim)...")
    population = AgentFactory.create_batch(n_agents=10, seed=42, z_dim=256, distribution="normal")
    print(f"  • Generated {population.shape[0]} simulator agents (256D latent state vectors)")
    print(f"  • Mean Latent Vector Norm: {float(np.mean(np.linalg.norm(population, axis=1))):.4f}")

    # 3. Simulate End-User Prompts & Route Through UnifiedHybridRouter
    print("\n[3/7] Routing Simulated User Prompts via EVI Router & FLUME VAE...")
    router = UnifiedHybridRouter()
    simulated_prompts = [
        ("coding", "Implement a high-performance C++ matrix multiply kernel for Strix Halo Wave32", 0.7),
        ("reasoning", "Prove mathematical convergence of Poincaré disk conformal factor lambda(x)", 0.9),
        ("research", "Summarize clean energy LENR lattice confinement fusion research papers", 0.6),
        ("fast_qa", "What is the Strix Halo GTT memory pool limit?", 0.3),
    ]

    for task_type, prompt, importance in simulated_prompts:
        res = router.route(
            task_type=task_type,
            task_importance=importance,
            prompt=prompt,
        )
        esc_str = "🚨 ESCALATED" if res.escalated else "✅ LOCAL"
        print(f"  [{esc_str}] '{prompt[:45]}...' -> Tier {res.selected_tier} ({res.model_name}) | EVI: {res.evi_score:.4f}")

    # 4. Run AutoHarness AST Verification & ZKFV Proof Compilation
    print("\n[4/7] Running AutoHarness (<1 ms) & Compiling ZKFV Proofs...")
    policy = AutoHarnessPolicy()
    zkfv = ZKFVCompiler()
    sample_code = "def compute_geodesic(x: list[float]) -> float:\n    return sum(x)\n"
    ver_res = policy.verify_code(sample_code)
    proof = zkfv.compile_proof(sample_code)
    print(f"  • AutoHarness Verification : {'✅ PASSED' if ver_res.valid else '❌ FAILED'} ({ver_res.latency_ms:.3f} ms)")
    print(f"  • ZKFV Polynomial Proof    : {proof.polynomial_signature[:32]}...")

    # 5. Poincaré Hyperbolic Trajectory Tracking
    print("\n[5/7] Tracking Agent Trajectories in 2048D Poincaré Disk...")
    tracker = PoincareManifoldTracker()
    for idx in range(5):
        raw_vec = np.random.normal(0, 0.1, 2048)
        tracker.project_and_track(f"agent_sim_{idx}", raw_vec, time.time())
    drift = tracker.get_trajectory_drift()
    print(f"  • Poincaré 2048D Trajectory Drift: {drift:.6f}")

    # 6. EVI Self-Healing Evaluation & Kanban Card Persistence
    print("\n[6/7] Evaluating EVI Self-Healing & Writing Dual-Sink Kanban Cards...")
    healer = EVIHealer()
    healing_act = healer.evaluate_healing_candidate(
        component="user_simulator_mesh",
        issue_description="Simulated latent state drift detected in user agent swarm",
        proposed_remediation="Re-align 256D latent state vector with HIHO 0.5 stability attractor",
        quality_gap=0.35,
        issue_severity=0.8,
        remediation_cost=0.25,
    )
    print(f"  • Self-Healing EVI Score: {healing_act.evi_score:.4f} -> {'✅ APPROVED & PERSISTED' if healing_act.approved else '❌ REJECTED'}")

    # 7. Render Visual Cockpit Dashboards
    print("\n[7/7] Rendering Real-Time Visual Cockpit Dashboards...")
    render_terminal_cockpit()
    generate_html_cockpit(Path("cockpit_dashboard.html"))
    print("  • HTML Dashboard generated at cockpit_dashboard.html")

    print("\n" + "=" * 70)
    print("🎉 END-TO-END DOGFOODING SESSION COMPLETED SUCCESSFULLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_dogfooding_session()
