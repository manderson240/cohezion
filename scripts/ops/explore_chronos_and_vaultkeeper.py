r"""GAIA SDK Agent Exploration script for Chronos and Vaultkeeper agents.
=======================================================================
Delegates local GAIA SDK agent exploration across Chronos cron deconfliction
and Vaultkeeper obsidian vault storage infrastructure.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cohezion.agents.specialists.vault_keeper import VaultKeeper
from cohezion.compound.chronos import get_chronos


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GaiaChronosVaultExplorer")


def explore_agents() -> dict[str, Any]:
    logger.info("🔍 GAIA SDK Agent Exploration: Chronos & VaultKeeper")

    # 1. Inspect Chronos Agent
    chronos = get_chronos()
    all_jobs = chronos.discover_all()
    deferrable_jobs = chronos.resource_advisory()

    chronos_info = {
        "agent": "Chronos",
        "description": "Unified resource-aware cron agent over systemd, Hermes, and Cohezion schedulers",
        "total_jobs_discovered": len(all_jobs),
        "deferrable_jobs_under_pressure": len(deferrable_jobs),
        "sample_deferrable_jobs": [j.name for j in deferrable_jobs[:5]],
    }

    # 2. Inspect VaultKeeper Agent
    vk_card = VaultKeeper.CARD
    vk_info = {
        "agent": vk_card.name,
        "display_name": vk_card.display_name,
        "role": vk_card.role,
        "capabilities": vk_card.capabilities,
        "principles": vk_card.principles,
        "canonical_modules": vk_card.canonical_modules,
    }

    report = {
        "chronos_exploration": chronos_info,
        "vaultkeeper_exploration": vk_info,
    }

    logger.info("✅ GAIA SDK Exploration Complete!")
    return report


if __name__ == "__main__":
    report = explore_agents()
    print(json.dumps(report, indent=2))
