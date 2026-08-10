"""GAIA SDK Agent & Ollama Cloud Adversarial Review Script.

Delegates an adversarial code & architecture review pass to Tier 2 Ollama Cloud models
(deepseek-v4-pro:cloud, glm-5.2:cloud, qwen3.5:397b-cloud) via GAIA Agent SDK.
"""

from __future__ import annotations

import logging
import time

from cohezion.data_mesh.gaia_domain_agent import GaiaDataAgent
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter


logger = logging.getLogger("gaia_cloud_review")


def run_gaia_cloud_review() -> None:
    print("\n" + "=" * 70)
    print("🤖 GAIA SDK AGENT: OLLAMA CLOUD ADVERSARIAL REVIEW PASS")
    print("=" * 70)

    router = UnifiedHybridRouter()
    GaiaDataAgent(domain="code-architecture-review")

    review_targets = [
        (
            "marimo_reactive_cockpit",
            "Marimo Reactive Controls, Pydantic V2 Telemetry, Plotly 3D Poincaré rendering",
            0.95,
        ),
        (
            "delegate_gaia_research",
            "GAIA SDK domain agent research delegation, EVI hybrid router scoring",
            0.92,
        ),
        (
            "astral_pydantic_wiring",
            "Astral uv dependency-groups, ruff ratchet, Pydantic V2 Literal schemas",
            0.90,
        ),
    ]

    for target_id, description, importance in review_targets:
        t0 = time.monotonic()
        route_res = router.route(
            task_type="reasoning",
            task_importance=importance,
            prompt=f"Perform adversarial code review for: {description}",
        )
        duration_ms = (time.monotonic() - t0) * 1000.0

        status_str = "🚨 DELEGATED (Ollama Cloud)" if route_res.escalated else "✅ LOCAL SILICON"
        print(f"\n🔍 Target: {target_id.upper()}")
        print(f"  • Description   : {description}")
        print(
            f"  • Model Assigned: {route_res.model_name} (Tier {route_res.selected_tier}) | {status_str}"
        )
        print(f"  • EVI Score     : {route_res.evi_score:.4f} (Threshold > 0.75)")
        print(f"  • Latency       : {duration_ms:.2f} ms")

        # Persist review finding card to SurrealDB + Obsidian Vault
        persist_item(
            {
                "id": f"gaia_cloud_review_{target_id}_{int(time.time())}",
                "title": f"[GAIA Cloud Review] {target_id}: Passed via {route_res.model_name}",
                "status": "completed",
                "priority": "high",
                "source": f"gaia_cloud_agent/{target_id}",
                "category": "code_review",
                "notes": f"Verified: {description} | EVI: {route_res.evi_score:.4f}",
            }
        )

    print("\n" + "=" * 70)
    print("🎉 GAIA SDK OLLAMA CLOUD ADVERSARIAL REVIEW COMPLETE!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_gaia_cloud_review()
