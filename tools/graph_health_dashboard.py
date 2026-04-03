#!/usr/bin/env python3
"""Graph Health Dashboard — HIHO metrics and alerts.

Generates a markdown dashboard showing graph health metrics
and saves it to the vault cortex directory.

Usage:
    uv run python3 tools/graph_health_dashboard.py [--output vault|stdout]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
SURREALDB_URL = os.getenv("SURREALDB_URL", "http://localhost:8001")
SURREALDB_NS = "cohezion"
SURREALDB_DB = "vault"
SURREALDB_USER = os.getenv("SURREALDB_USER", "root")
SURREALDB_PASS = os.getenv("SURREALDB_PASS", "root")
VAULT_PATH = Path("~/vaults/cohezion-vault").expanduser()


# ── SurrealDB helpers ─────────────────────────────────────────────────────────
def surql(query: str, timeout: int = 30) -> list[dict]:
    resp = httpx.post(
        f"{SURREALDB_URL}/sql",
        content=query,
        headers={
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "Surreal-NS": SURREALDB_NS,
            "Surreal-DB": SURREALDB_DB,
        },
        auth=(SURREALDB_USER, SURREALDB_PASS),
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def get_results(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        if row.get("status") == "OK" and isinstance(row.get("result"), list):
            out.extend(row["result"])
    return out


# ── Metrics Calculation ────────────────────────────────────────────────────────
def compute_hiho_metrics() -> dict:
    """Calculate HIHO-weighted graph health metrics."""
    # Get counts
    neuron_count = get_results(surql("SELECT count() FROM neuron GROUP ALL;"))
    synapse_count = get_results(surql("SELECT count() FROM synapse GROUP ALL;"))

    n_neurons = neuron_count[0].get("count", 0) if neuron_count else 0
    n_synapses = synapse_count[0].get("count", 0) if synapse_count else 0

    if n_neurons == 0:
        return {
            "hiho_score": 0.0,
            "status": "critical",
            "neurons": 0,
            "synapses": 0,
            "orphans": 0,
            "orphan_ratio": 1.0,
            "connectivity": 0.0,
            "reciprocity": 0.0,
            "freshness": 0.0,
        }

    # Connected nodes (have at least one synapse)
    try:
        connected = get_results(
            surql(
                "SELECT count() FROM neuron WHERE ->synapse = true OR <-synapse = true GROUP ALL;"
            )
        )
        n_connected = connected[0].get("count", 0) if connected else 0
    except Exception:
        n_connected = min(n_synapses, n_neurons)  # Fallback

    # Orphan ratio
    orphans = n_neurons - n_connected
    orphan_ratio = orphans / n_neurons

    # Connectivity (nodes with 2+ backlinks)
    try:
        well_connected = get_results(
            surql("SELECT count() FROM neuron WHERE count(<-synapse) >= 2 GROUP ALL;")
        )
        n_well_connected = well_connected[0].get("count", 0) if well_connected else 0
        connectivity = n_well_connected / n_neurons
    except Exception:
        connectivity = n_connected / n_neurons if n_neurons > 0 else 0.0

    # Reciprocity (bidirectional links)
    try:
        bidirectional = get_results(
            surql("SELECT count() FROM synapse WHERE out -> synapse -> in = true GROUP ALL;")
        )
        n_bidirectional = bidirectional[0].get("count", 0) if bidirectional else 0
        reciprocity = n_bidirectional / n_synapses if n_synapses > 0 else 0.0
    except Exception:
        reciprocity = 0.0

    # Freshness (notes created <30 days)
    try:
        recent = get_results(
            surql("SELECT count() FROM neuron WHERE created > time::now() - 30d GROUP ALL;")
        )
        n_recent = recent[0].get("count", 0) if recent else 0
        freshness = n_recent / n_neurons
    except Exception:
        freshness = 0.0

    # HIHO score (target: 0.5 +/- 0.15)
    hiho = 0.3 * connectivity + 0.2 * reciprocity + 0.2 * freshness + 0.3 * (1 - orphan_ratio)

    # Status classification
    if 0.35 <= hiho <= 0.65:
        status = "healthy"
    elif 0.2 <= hiho <= 0.8:
        status = "degraded"
    else:
        status = "critical"

    return {
        "hiho_score": round(hiho, 3),
        "status": status,
        "neurons": n_neurons,
        "synapses": n_synapses,
        "orphans": orphans,
        "orphan_ratio": round(orphan_ratio, 3),
        "connectivity": round(connectivity, 3),
        "reciprocity": round(reciprocity, 3),
        "freshness": round(freshness, 3),
    }


# ── Dashboard Generation ──────────────────────────────────────────────────────
def generate_dashboard(metrics: dict) -> str:
    """Generate markdown dashboard for vault cortex."""
    lines = [
        "---",
        f"title: Graph Health Dashboard — {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "tags: [graph-health, hiho, auto-generated]",
        "aspect: connective",
        "---",
        "",
        "# Graph Health Dashboard",
        "",
        f"**HIHO Score:** `{metrics['hiho_score']:.3f}`",
        f"**Status:** {metrics['status'].upper()}",
        "",
        "## Overview",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Neurons | {metrics['neurons']:,} |",
        f"| Synapses | {metrics['synapses']:,} |",
        f"| Orphans | {metrics['orphans']:,} ({metrics['orphan_ratio'] * 100:.1f}%) |",
        f"| Synapse/Neuron Ratio | {metrics['synapses'] / metrics['neurons']:.2f}"
        if metrics["neurons"] > 0
        else "| Synapse/Neuron Ratio | N/A |",
        "",
        "## HIHO Metrics Breakdown",
        "",
        "| Metric | Value | Weight | Contribution | Target |",
        "|--------|-------|--------|--------------|--------|",
    ]

    # Connectivity
    conn_contrib = metrics["connectivity"] * 0.3
    lines.append(
        f"| Connectivity | {metrics['connectivity']:.3f} | 0.30 | {conn_contrib:.3f} | >0.80 |"
    )

    # Reciprocity
    recip_contrib = metrics["reciprocity"] * 0.2
    lines.append(
        f"| Reciprocity | {metrics['reciprocity']:.3f} | 0.20 | {recip_contrib:.3f} | >0.60 |"
    )

    # Freshness
    fresh_contrib = metrics["freshness"] * 0.2
    lines.append(f"| Freshness | {metrics['freshness']:.3f} | 0.20 | {fresh_contrib:.3f} | >0.30 |")

    # Anti-orphan
    anti_orphan = 1 - metrics["orphan_ratio"]
    anti_contrib = anti_orphan * 0.3
    lines.append(f"| Anti-Orphan | {anti_orphan:.3f} | 0.30 | {anti_contrib:.3f} | >0.90 |")

    # Total
    lines.append(f"| **HIHO Score** | **{metrics['hiho_score']:.3f}** | 1.00 | — | **0.35-0.65** |")

    lines.extend(
        [
            "",
            "## Status Interpretation",
            "",
        ]
    )

    if metrics["status"] == "healthy":
        lines.append(
            "> ✅ **HEALTHY**: Graph is at HIHO equilibrium (0.35-0.65). The system is self-sustaining with good balance between order (connectivity) and entropy (orphans)."
        )
    elif metrics["status"] == "degraded":
        lines.append(
            "> ⚠️ **DEGRADED**: Graph is outside HIHO equilibrium. Consider reviewing orphan count and strengthening connectivity."
        )
    else:
        lines.append(
            "> 🔴 **CRITICAL**: Graph health is outside safe bounds! Immediate intervention recommended: connect orphans, strengthen weak links."
        )

    lines.extend(
        [
            "",
            "## Recommendations",
            "",
        ]
    )

    if metrics["orphan_ratio"] > 0.1:
        lines.append(
            f"- **High orphan rate ({metrics['orphan_ratio'] * 100:.1f}%)**: Run vault-keeper waking mode to connect isolated neurons."
        )
    if metrics["connectivity"] < 0.5:
        lines.append(
            f"- **Low connectivity ({metrics['connectivity']:.2f})**: Many neurons have <2 backlinks. Strengthen network density."
        )
    if metrics["reciprocity"] < 0.3:
        lines.append(
            f"- **Low reciprocity ({metrics['reciprocity']:.2f})**: Few bidirectional links. Encourage mutual connections."
        )
    if metrics["freshness"] < 0.2:
        lines.append(
            f"- **Low freshness ({metrics['freshness']:.2f})**: Few recent additions. Consider adding new content."
        )

    if metrics["status"] == "healthy":
        lines.append("- Graph is healthy. Continue current maintenance schedule.")

    lines.extend(
        [
            "",
            "---",
            "",
            f"_Generated: {datetime.now(UTC).isoformat()}_",
        ]
    )

    return "\n".join(lines)


def save_to_vault(content: str) -> None:
    """Save dashboard to vault cortex directory."""
    output_path = VAULT_PATH / "cortex" / "graph-health-dashboard.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(content)

    logger.info("Saved dashboard to: %s", output_path)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate graph health dashboard")
    parser.add_argument(
        "--output",
        choices=["vault", "stdout"],
        default="stdout",
        help="Where to output the dashboard (default: stdout)",
    )
    args = parser.parse_args()

    logger.info("Computing HIHO metrics...")

    try:
        metrics = compute_hiho_metrics()
    except Exception as e:
        logger.error("Failed to compute metrics: %s", e)
        sys.exit(1)

    content = generate_dashboard(metrics)

    if args.output == "vault":
        save_to_vault(content)
    else:
        print(content)

    logger.info("Dashboard complete: HIHO=%.3f (%s)", metrics["hiho_score"], metrics["status"])


if __name__ == "__main__":
    main()
