#!/usr/bin/env python3
"""
Data Mesh Guard - SLA Monitoring & Self-Healing.

Monitors data_mesh_registry.json for freshness and SLA violations.
If a GOLD or SILVER product is stale, it creates a GitHub Issue to
trigger the asynchronous workforce.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path


# Resolve project root
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.mcp.servers.github.server import get_service


# Paths
REGISTRY_PATH = PROJECT_ROOT / "src/cohezion/data_mesh/data_mesh_registry.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("data-mesh-guard")

# SLA Configuration (TTL in seconds)
SLA_CONFIG = {
    "gold": 86400,  # 24 hours
    "silver": 259200,  # 72 hours
    "bronze": None,  # Best effort
}


async def check_slas():
    """Scan registry for stale products."""
    if not REGISTRY_PATH.exists():
        logger.error(f"Registry not found at {REGISTRY_PATH}")
        return

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    github = get_service()
    OWNER = os.getenv("GITHUB_OWNER", "manderson240")
    REPO = os.getenv("GITHUB_REPO", "cohezion")

    current_time = time.time()
    violations = 0

    for product_id, product in registry.items():
        tier = product.get("quality_tier", "bronze")
        ttl = SLA_CONFIG.get(tier)

        if not ttl:
            continue

        last_updated = product.get("last_updated", 0)
        age = current_time - last_updated

        if age > ttl:
            logger.warning(f"⚠️ SLA Violation: {product_id} ({tier}) is {int(age / 3600)}h old.")

            # Create a GitHub Issue for self-healing
            issue_title = f"Data Mesh SLA Violation: Refresh {product_id}"
            issue_body = (
                f"The Data Product `{product_id}` ({tier} tier) has exceeded its freshness SLA.\n\n"
                f"- **Age**: {int(age / 3600)} hours\n"
                f"- **Max TTL**: {int(ttl / 3600)} hours\n"
                f"- **Owner Domain**: {product.get('owner_domain')}\n\n"
                f"Please dispatch an agent to verify and refresh this data product."
            )

            try:
                result = await github.create_issue(
                    OWNER,
                    REPO,
                    title=issue_title,
                    body=issue_body,
                    labels=["agent-task", "sla-violation"],
                )
                if "number" in result:
                    logger.info(f"  ✅ Triggered self-healing issue #{result['number']}")
                    violations += 1
            except Exception as e:
                logger.error(f"  ❌ Failed to trigger self-healing: {e}")

    if violations == 0:
        logger.info("✅ All Data Products are within SLA limits.")


if __name__ == "__main__":
    asyncio.run(check_slas())
