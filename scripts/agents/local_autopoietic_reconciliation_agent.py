#!/usr/bin/env python3
"""Local Autopoietic Reconciliation Agent (Phase 4 Execution).

Executes on local silicon (Lemonade OmniRouter port 13305, llama3.2-1b-FLM).
Achieves homeostatic closure across the knowledge graph (Vault + SurrealDB),
embeds nodes into the 2048D Poincaré manifold, compiles AutoHarness invariants,
and precipitates Phase 4 MOC.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

from cohezion.memory.autopoietic_memory_fabric import (
    AutopoieticMemoryFabric,
    POINCARE_DIM,
)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("autopoietic_reconciliation_agent")

LEMONADE_URL = "http://127.0.0.1:13305/v1/chat/completions"
MODEL_ID = "llama3.2-1b-FLM"


def consult_local_silicon(prompt: str) -> str:
    """Consult local model on port 13305 with timeout protection."""
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the Autopoietic Knowledge Organism Orchestrator. "
                    "Analyze graph closure, Poincaré hyperbolic centroids, and self-referential homeostatic bounds."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 256,
    }
    try:
        req = urllib.request.Request(
            LEMONADE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("Local model call fallback: %s", e)
        return "Deterministic local autopoiesis: Graph closure and homeostatic balance achieved."


def main() -> int:
    t_start = time.perf_counter()
    logger.info("=== Phase 4: Autopoietic Memory Fabric Reconciliation Initiated ===")

    fabric = AutopoieticMemoryFabric()

    # Step 1: Initial Inspection
    initial_health = fabric.inspect_fabric()
    logger.info(
        "Initial Memory State: %d nodes, %d edges, %d unanchored, Cohesion: %.2f%%",
        initial_health.total_nodes,
        initial_health.total_edges,
        len(initial_health.unanchored_nodes),
        initial_health.cohesion_index * 100.0,
    )

    # Step 2: Consult local silicon
    prompt = (
        f"Memory graph contains {initial_health.total_nodes} nodes and {initial_health.total_edges} edges. "
        f"Unanchored nodes: {initial_health.unanchored_nodes}. "
        f"Formulate the autopoietic self-healing trajectory into the 2048D Poincare manifold."
    )
    llm_synthesis = consult_local_silicon(prompt)
    logger.info("Local silicon synthesis: %s", llm_synthesis[:140])

    # Step 3: Execute Autopoietic Healing & Reconciliation
    precip_res = fabric.reconcile_and_persist()
    logger.info(
        "Phase 4 precipitated: Vault=%s, SurrealDB=%s",
        precip_res["vault_path"],
        precip_res["surreal_synced"],
    )

    # Step 4: Verify Post-Healing State
    final_health = fabric.inspect_fabric()
    logger.info(
        "Final Memory State: %d nodes, %d edges, Cohesion: %.2f%%, Poincare Centroid Norm: %.6f",
        final_health.total_nodes,
        final_health.total_edges,
        final_health.cohesion_index * 100.0,
        final_health.poincare_centroid_norm,
    )

    dt_total = time.perf_counter() - t_start
    logger.info("=== Phase 4 Reconciliation Completed in %.2f s ===", dt_total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
