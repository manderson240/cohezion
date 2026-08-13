"""Live End-to-End Dogfooding: Agentic Mesh, Symmetry Breaking Audit, & Local Silicon.

Executes a full live dogfooding loop incorporating:
1. Strix Halo Silicon Preflight (gfx1151 / Wave32 alignment & 120GB GTT pool).
2. Agentic Mesh Coordinator (Cross-session token budget scaling during ebbs/flows).
3. Symmetry Breaking Auditor (CP chirality, SBI bifurcation, HIHO 0.5 coherence).
4. Unified Hybrid Router (EVI gating & FLUME VAE 256D prompt encoding).
5. AutoHarness Policy Verifiers & ZKFV Polynomial Proof Compilation.
6. Poincaré 2048D Hyperbolic Trajectory Tracking.
7. Dual-Sink Kanban Persistence (SurrealDB + Obsidian Vault).
8. Real-Time Control Plane Cockpit Dashboard Rendering.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import numpy as np
from visual_cockpit import generate_html_cockpit, render_terminal_cockpit

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.agi.zkfv_compiler import ZKFVCompiler
from cohezion.core.event_bus import EventBus
from cohezion.data_mesh.mesh_coordinator import AgenticMeshCoordinator
from cohezion.inference.strix_halo_optimizer import StrixHaloSiliconOptimizer
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter
from cohezion.physics.poincare_manifold import PoincareManifoldTracker
from cohezion.physics.symmetry_breaking import SymmetryBreakingAuditor
from cohezion.proactive.evi_healer import EVIHealer


logger = logging.getLogger("dogfood_symmetry_mesh")


async def run_dogfooding_session() -> None:
    print("\n" + "=" * 70)
    print("🐕 LIVE DOGFOODING: AGENTIC MESH, SYMMETRY AUDIT & LOCAL SILICON")
    print("=" * 70)

    # Initialize components
    bus = EventBus()
    await bus.start()

    coordinator = AgenticMeshCoordinator(bus=bus)
    coordinator.start()

    auditor = SymmetryBreakingAuditor(bus=bus)
    router = UnifiedHybridRouter()
    policy = AutoHarnessPolicy()
    zkfv = ZKFVCompiler()
    tracker = PoincareManifoldTracker()
    healer = EVIHealer()
    optimizer = StrixHaloSiliconOptimizer()

    # 1. Strix Halo Silicon Verification
    print("\n[1/8] Verifying Strix Halo Hardware & Memory Aperture...")
    wave32_ok = optimizer.verify_wave32_alignment()
    print(f"  • Wave32 Matrix Alignment: {'✅ ALIGNED' if wave32_ok else '⚠️ UNALIGNED'}")
    print(f"  • UMA GTT Memory Pool    : {optimizer.profile.gtt_pool_max_gb} GB")

    # 2. Cross-Session Agentic Mesh Registration
    print("\n[2/8] Registering Multi-Session Agentic Mesh Nodes...")
    budget_s1 = await coordinator.register_session("session_architect", source="dogfood_runner")
    print(f"  • Session Architect Registered  : Allocated {budget_s1:,} Token Budget (Ebb State)")

    budget_s2 = await coordinator.register_session("session_engineer", source="dogfood_runner")
    print(f"  • Session Engineer Registered   : Allocated {budget_s2:,} Token Budget (Flow State)")

    # 3. Symmetry Breaking Audit (CP Chirality, SBI, HIHO 0.5 Coherence)
    print("\n[3/8] Executing Symmetry Breaking Audit on Agent State Vectors...")
    vec_architect = np.random.normal(0, 0.05, 2048)
    vec_architect[:256] += 2.5  # Break symmetry in sector 0

    audit_arch = auditor.audit_state_vector("session_architect", vec_architect)
    print(
        f"  • Architect Node  : Chirality={audit_arch.chirality_score:+.4f} | SBI={audit_arch.symmetry_breaking_index:.4f} | HIHO={'✅ STABLE' if audit_arch.hiho_stable else '⚠️ UNSTABLE'} | Bifurcation={'✅ DETECTED' if audit_arch.bifurcation_detected else '❌ NONE'}"
    )

    vec_engineer = np.ones(2048, dtype=np.float64) * 0.02
    audit_eng = auditor.audit_state_vector("session_engineer", vec_engineer)
    print(
        f"  • Engineer Node   : Chirality={audit_eng.chirality_score:+.4f} | SBI={audit_eng.symmetry_breaking_index:.4f} | HIHO={'✅ STABLE' if audit_eng.hiho_stable else '⚠️ UNSTABLE'} | Bifurcation={'✅ DETECTED' if audit_eng.bifurcation_detected else '❌ NONE'}"
    )

    # 4. Prompt Routing via EVI Router & Local Inference
    print("\n[4/8] Routing Prompts via EVI Hybrid Router & Local Inference...")
    prompts = [
        (
            "reasoning",
            "Synthesize continuous geodesic flow equations for Poincaré 2048D manifolds",
            0.92,
        ),
        (
            "coding",
            "Implement C++ HIP Wave32 kernel matrix acceleration for AMD Radeon 8060S",
            0.88,
        ),
        ("research", "Summarize LENR lattice confinement fusion developments in 2026", 0.60),
    ]
    for task_type, p_text, imp in prompts:
        route_res = router.route(task_type=task_type, task_importance=imp, prompt=p_text)
        tier_str = "🚨 ESCALATED" if route_res.escalated else "✅ LOCAL"
        print(
            f'  [{tier_str}] "{p_text[:45]}..." -> Tier {route_res.selected_tier} ({route_res.model_name}) | EVI: {route_res.evi_score:.4f}'
        )

    # 5. AutoHarness Verification & ZKFV Proof Compilation
    print("\n[5/8] Running AutoHarness (<1 ms) & Compiling ZKFV Polynomial Proofs...")
    test_code = "def mesh_pipeline(x: int) -> int:\n    return x * 42\n"
    ast_res = policy.verify_code(test_code)
    zk_proof = zkfv.compile_proof(test_code)
    print(
        f"  • AutoHarness Verification : {'✅ PASSED' if ast_res.valid else '❌ FAILED'} ({ast_res.latency_ms:.3f} ms)"
    )
    print(f"  • ZKFV Proof Signature     : {zk_proof.polynomial_signature}")

    # 6. Poincaré 2048D Hyperbolic Trajectory Tracking
    print("\n[6/8] Tracking Hyperbolic Trajectories in 2048D Poincaré Space...")
    state_arch = tracker.project_and_track("session_architect", vec_architect, time.time())
    drift = tracker.get_trajectory_drift()
    print(
        f"  • Poincaré State Norm : {state_arch.norm:.4f} | Conformal Lambda: {state_arch.conformal_factor:.4f}"
    )
    print(f"  • Geodesic Drift      : {drift:.6f}")

    # 7. EVI Self-Healing Evaluation & Dual-Sink Persistence
    print("\n[7/8] Evaluating EVI Self-Healing & Dual-Sink Kanban Persistence...")
    heal_action = healer.evaluate_trajectory_anomaly(drift=drift, component="mesh_dogfood_node")
    print(
        f"  • Self-Healing EVI Score: {heal_action.evi_score:.4f} -> {'✅ APPROVED & PERSISTED' if heal_action.approved else '❌ REJECTED'}"
    )

    # 8. Render Control Plane Cockpit
    print("\n[8/8] Rendering Real-Time Visual Control Plane Cockpit...")
    render_terminal_cockpit()

    html_path = Path("cockpit_dashboard.html")
    generate_html_cockpit(output_path=html_path)

    # Release engineer session (Ebb transition back to 1 active session)
    await coordinator.release_session("session_engineer", source="dogfood_runner")
    recalculated = coordinator.calculate_dynamic_token_budget("session_architect")
    print(
        f"  • Session Engineer Released -> Session Architect Token Budget Scaled Back Up to {recalculated:,} Tokens!"
    )

    await bus.stop()

    print("\n" + "=" * 70)
    print("🎉 END-TO-END DOGFOODING SESSION COMPLETED SUCCESSFULLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(run_dogfooding_session())
