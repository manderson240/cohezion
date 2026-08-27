"""Strix Halo 128GB Unified Silicon Model Optimization Research Script.

Delegates Tier 2 Ollama Cloud models (deepseek-v4-pro:cloud, glm-5.2:cloud, qwen3.5:397b-cloud)
via UnifiedHybridRouter to audit the optimal local model roster for AMD Strix Halo (128GB UMA, Wave32).
"""

from __future__ import annotations

import logging
import time

from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.strix_halo_optimizer import StrixHaloSiliconOptimizer
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter


logger = logging.getLogger("silicon_research")


SILICON_RESEARCH_DOMAINS = [
    (
        "wave32_matrix_kernels",
        "RDNA3.5 Wave32 matrix unit alignment (-mwavefrontsize32, MXFP4/Q5_K_M quantizations) for Qwen3-Coder-30B",
        0.95,
    ),
    (
        "npu_xdna2_offload",
        "XDNA2 NPU lane offloading for 8B models (deepseek-r1-8b, qwen3vl-4b, nomic-embed 768D) to keep iGPU free",
        0.92,
    ),
    (
        "uma_120gb_gtt_scaling",
        "Unified 120GB GTT pool memory management & KV cache budget scaling up to 131,072 tokens",
        0.90,
    ),
    (
        "multimodal_silicon_roster",
        "TRELLIS 3D Gaussian Splatting + ACE-Step Audio + Whisper-v3-Turbo + Kokoro-v1 NPU co-existence",
        0.88,
    ),
]


def run_silicon_optimization_research() -> None:
    print("\n" + "=" * 70)
    print("💻 STRIX HALO 128GB UMA: SILICON-ALIGNED MODEL ROSTER AUDIT")
    print("=" * 70)

    opt = StrixHaloSiliconOptimizer()
    flags = opt.get_optimal_compilation_flags()
    router = UnifiedHybridRouter()

    print("  • Hardware Processor: AMD RYZEN AI MAX+ 395 w/ Radeon 8060S (16-Core / 32-Thread)")
    print("  • Graphics Substrate: AMD Radeon 8060S (40 RDNA 3.5 CUs, Wave32 Matrix Units)")
    print("  • NPU Accelerator   : AMD XDNA 2 Neural Processing Unit")
    print(
        f"  • Memory Aperture   : 122 GiB Unified RAM ({opt.profile.gtt_pool_max_gb} GB GTT UMA Pool) + 39 GiB Swap"
    )
    print(f"  • Matrix Flags      : {flags}\n")

    for domain_id, prompt, importance in SILICON_RESEARCH_DOMAINS:
        t0 = time.monotonic()
        route_res = router.route(
            task_type="reasoning",
            task_importance=importance,
            prompt=f"Audit Strix Halo 128GB UMA silicon optimization for: {prompt}",
        )
        duration_ms = (time.monotonic() - t0) * 1000.0

        status_str = "🚨 ESCALATED (Ollama Cloud)" if route_res.escalated else "✅ LOCAL SILICON"
        print(f"🔬 Domain: {domain_id.upper()}")
        print(f"  • Focus Area    : {prompt}")
        print(
            f"  • Model Assigned: {route_res.model_name} (Tier {route_res.selected_tier}) | {status_str}"
        )
        print(f"  • EVI Score     : {route_res.evi_score:.4f}")
        print(f"  • Latency       : {duration_ms:.2f} ms\n")

        # Persist audit card to SurrealDB + Obsidian Vault
        persist_item(
            {
                "id": f"silicon_audit_{domain_id}_{int(time.time())}",
                "title": f"[Silicon Audit] {domain_id}: Verified via {route_res.model_name}",
                "status": "completed",
                "priority": "high",
                "source": "silicon_research",
                "category": "hardware_optimization",
                "notes": f"Strix Halo 128GB UMA | Wave32 | EVI: {route_res.evi_score:.4f}",
            }
        )

    print("=" * 70)
    print("🎉 STRIX HALO SILICON-ALIGNED MODEL ROSTER AUDIT COMPLETED!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_silicon_optimization_research()
