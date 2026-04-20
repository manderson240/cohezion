import asyncio
import logging
import shutil
import sys
from pathlib import Path

from cohezion.core.local_registry import get_local_registry


# Add src to path
sys.path.append(str(Path.cwd() / "src"))


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ModelScout")

    registry = get_local_registry()

    # 1. Storage Check
    _total, _used, free = shutil.disk_usage("/")
    free_gb = free / (1024**3)
    logger.info(f"💾 Storage Status: {free_gb:.2f} GB Free")

    if free_gb < 20.0:
        logger.warning("Scope Limited: Storage < 20GB. Only enabling net-zero swaps.")
        can_expand = False
    else:
        can_expand = True

    print("\n--- 🔭 Deep Model Scout Report (Gateway 28) ---")

    # 2. Simulated SOTA Discovery (In prod this would scrape HF/Reddit)
    # We define a "fantasy league" of current top SLMs for simulation
    sota_slms = [
        {"name": "mistral:7b-v0.3", "score": 72.5, "size_gb": 4.1},
        {"name": "phi3:mini-128k", "score": 70.2, "size_gb": 2.3},
        {"name": "qwen2:7b", "score": 74.1, "size_gb": 4.5},
        {"name": "gemma:2b", "score": 58.0, "size_gb": 1.5},
    ]

    installed = registry.available_models
    recommendations = []

    for candidate in sota_slms:
        name = candidate["name"]
        score = candidate["score"]

        # Check if we have a similar model installed
        base_name = name.split(":")[0]
        match = next((m for m in installed if m.startswith(base_name)), None)

        if not match:
            # New model family
            if can_expand:
                recommendations.append(f"NEW: Install {name} (Score: {score})")
        else:
            # Check for upgrade
            # Simulating that installed legacy models have lower score
            current_score = score - 5.0  # Assume current is older
            gain = score - current_score
            gain_pct = (gain / current_score) * 100

            if gain_pct > 5.0:
                recommendations.append(f"UPGRADE: Swap {match} -> {name} (+{gain_pct:.1f}% Perf)")

    if recommendations:
        print("\n🚀 Transfer Requests Generated:")
        for rec in recommendations:
            print(f"  - {rec}")
    else:
        print("\n✅ Roster Optimal. No upgrades needed.")


if __name__ == "__main__":
    asyncio.run(main())
