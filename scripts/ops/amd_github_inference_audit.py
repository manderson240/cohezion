"""AMD GitHub Official Repositories Local Inference Audit Script.

Delegates Tier 2 Ollama Cloud models (deepseek-v4-pro:cloud, glm-5.2:cloud) via UnifiedHybridRouter
to audit local inference implications across AMD's official GitHub repos (https://github.com/amd).
"""

from __future__ import annotations

import logging
import time

from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.strix_halo_optimizer import StrixHaloSiliconOptimizer
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter


logger = logging.getLogger("amd_repo_audit")


AMD_REPOS_TO_AUDIT = [
    (
        "amd_skills_catalog",
        "https://github.com/amd/skills — AMD AI Agent Skills Catalog (local-ai-use, local-ai-app-integration, magpie-kernel-evaluator)",
        0.94,
    ),
    (
        "amd_ryzen_ai_sw",
        "https://github.com/amd/RyzenAI-SW — AMD Ryzen AI Software ONNX NPUExecutionProvider for XDNA2 sub-ms 8B/embedding inference",
        0.96,
    ),
    (
        "amd_vllm_rocm",
        "https://github.com/amd/vllm-amd — High-throughput vLLM serving on AMD RDNA3.5 / ROCm 6.3 Wave32 matrix units",
        0.92,
    ),
    (
        "amd_hipblaslt_rocblas",
        "https://github.com/amd/hipBLASLt — Hardware-accelerated Wave32 GEMM, MoE, and MLA decode kernels for Strix Halo iGPU",
        0.90,
    ),
]


def run_amd_github_inference_audit() -> None:
    print("\n" + "=" * 70)
    print("🔴 AMD OFFICIAL GITHUB REPOSITORIES LOCAL INFERENCE AUDIT")
    print("=" * 70)

    opt = StrixHaloSiliconOptimizer()
    flags = opt.get_optimal_compilation_flags()
    router = UnifiedHybridRouter()

    print("  • Target Hardware   : AMD RYZEN AI MAX+ 395 w/ Radeon 8060S (16-Core / 32-Thread)")
    print("  • Graphics Substrate: AMD Radeon 8060S (40 RDNA 3.5 CUs, Wave32 Matrix Units)")
    print("  • NPU Engine        : AMD XDNA 2 Neural Processing Unit")
    print(
        f"  • Memory Aperture   : 122 GiB Unified RAM ({opt.profile.gtt_pool_max_gb} GB GTT UMA Pool) + 39 GiB Swap"
    )
    print(f"  • Wave32 Flags      : {flags}\n")

    for repo_id, description, importance in AMD_REPOS_TO_AUDIT:
        t0 = time.monotonic()
        route_res = router.route(
            task_type="reasoning",
            task_importance=importance,
            prompt=f"Audit AMD official repo local inference implications for: {description}",
        )
        duration_ms = (time.monotonic() - t0) * 1000.0

        status_str = "🚨 DELEGATED (Ollama Cloud)" if route_res.escalated else "✅ LOCAL SILICON"
        print(f"🔍 AMD Repo Target: {repo_id.upper()}")
        print(f"  • Description   : {description}")
        print(
            f"  • Model Assigned: {route_res.model_name} (Tier {route_res.selected_tier}) | {status_str}"
        )
        print(f"  • EVI Score     : {route_res.evi_score:.4f}")
        print(f"  • Audit Latency : {duration_ms:.2f} ms\n")

        # Persist audit card to SurrealDB + Obsidian Vault
        persist_item(
            {
                "id": f"amd_repo_audit_{repo_id}_{int(time.time())}",
                "title": f"[AMD Repo Audit] {repo_id}: Audited via {route_res.model_name}",
                "status": "completed",
                "priority": "high",
                "source": "amd_github_inference_audit",
                "category": "hardware_optimization",
                "notes": f"AMD Repo: {description} | Strix Halo 128GB UMA | EVI: {route_res.evi_score:.4f}",
            }
        )

    print("=" * 70)
    print("🎉 AMD GITHUB OFFICIAL REPOSITORIES INFERENCE AUDIT COMPLETE!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_amd_github_inference_audit()
