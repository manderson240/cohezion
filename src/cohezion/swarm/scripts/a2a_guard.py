#!/usr/bin/env python3
"""
A2A Guard - Agent-to-Agent Protocol Synchronizer.

Generates the .well-known/agent.json configuration for dynamic agent discovery
based on the central specialist_agents_config.json.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("a2a-guard")

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "src/cohezion/swarm/specialist_agents_config.json"
WELL_KNOWN_DIR = PROJECT_ROOT / ".well-known"
AGENT_JSON_PATH = WELL_KNOWN_DIR / "agent.json"

def sync_a2a():
    """Generate .well-known/agent.json from specialist config."""
    if not CONFIG_PATH.exists():
        logger.error(f"Specialist config not found at {CONFIG_PATH}")
        return False

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    # Transform to A2A format
    a2a_agents = []
    for agent in config.get("agents", []):
        a2a_agents.append({
            "id": f"cohezion-{agent['role']}",
            "name": agent["name"],
            "capabilities": agent.get("expertise", []),
            "model": agent.get("model", "unknown"),
            "endpoint": f"http://localhost:8080/swarm/agent/{agent['role']}/execute",
            "protocol": "A2A/1.0",
            "metadata": {
                "weight": agent.get("weight", 1.0),
                "theory": "Expert Domain Lattice"
            }
        })

    well_known_config = {
        "version": "1.0.0",
        "origin": "Cohezion Swarm",
        "agents": a2a_agents
    }

    if not WELL_KNOWN_DIR.exists():
        WELL_KNOWN_DIR.mkdir(parents=True)

    with open(AGENT_JSON_PATH, "w") as f:
        json.dump(well_known_config, f, indent=2)

    logger.info(f"✅ A2A Agent Card generated at {AGENT_JSON_PATH}")
    return True

if __name__ == "__main__":
    sync_a2a()
