#!/usr/bin/env python3
"""Unified Health Dashboard — Combined view of dreaming, graph, and data mesh health.

Aggregates all system health metrics into a single dashboard for the vault cortex.

Usage:
    uv run python3 tools/unified_health_dashboard.py [--output vault|stdout]
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


# ── Health Metric Collectors ──────────────────────────────────────────────────
def get_dreaming_metrics() -> dict:
    """Get dreaming system health metrics."""
    try:
        # Count dream synapses
        dreams = get_results(
            surql("SELECT count() FROM synapse WHERE link_type = 'dream' GROUP ALL;")
        )
        n_dreams = dreams[0].get("count", 0) if dreams else 0

        # Count high-quality dreams (quality_score >= 0.5)
        quality_dreams = get_results(
            surql(
                "SELECT count() FROM synapse WHERE link_type = 'dream' AND quality_score >= 0.5 GROUP ALL;"
            )
        )
        n_quality = quality_dreams[0].get("count", 0) if quality_dreams else 0

        # Recent dreams (last 7 days)
        recent = get_results(
            surql(
                "SELECT count() FROM synapse WHERE link_type = 'dream' AND created > time::now() - 7d GROUP ALL;"
            )
        )
        n_recent = recent[0].get("count", 0) if recent else 0

        quality_ratio = n_quality / n_dreams if n_dreams > 0 else 0.0

        # Health status
        if quality_ratio >= 0.3:
            status = "healthy"
        elif quality_ratio >= 0.15:
            status = "degraded"
        else:
            status = "critical"

        return {
            "total_dreams": n_dreams,
            "quality_dreams": n_quality,
            "recent_dreams": n_recent,
            "quality_ratio": round(quality_ratio, 3),
            "status": status,
        }
    except Exception as e:
        logger.warning("Failed to get dreaming metrics: %s", e)
        return {
            "total_dreams": 0,
            "quality_dreams": 0,
            "recent_dreams": 0,
            "quality_ratio": 0.0,
            "status": "unknown",
        }


def get_graph_metrics() -> dict:
    """Get graph health metrics using HIHO calculation."""
    try:
        # Get counts
        neuron_count = get_results(surql("SELECT count() FROM neuron GROUP ALL;"))
        synapse_count = get_results(surql("SELECT count() FROM synapse GROUP ALL;"))

        n_neurons = neuron_count[0].get("count", 0) if neuron_count else 0
        n_synapses = synapse_count[0].get("count", 0) if synapse_count else 0

        if n_neurons == 0:
            return {
                "neurons": 0,
                "synapses": 0,
                "orphans": 0,
                "orphan_ratio": 1.0,
                "connectivity": 0.0,
                "reciprocity": 0.0,
                "freshness": 0.0,
                "hiho_score": 0.0,
                "status": "critical",
            }

        # Connected nodes
        connected = get_results(
            surql(
                "SELECT count() FROM neuron WHERE ->synapse = true OR <-synapse = true GROUP ALL;"
            )
        )
        n_connected = connected[0].get("count", 0) if connected else 0

        # Orphan ratio
        orphans = n_neurons - n_connected
        orphan_ratio = orphans / n_neurons

        # Connectivity (nodes with 2+ backlinks)
        well_connected = get_results(
            surql("SELECT count() FROM neuron WHERE count(<-synapse) >= 2 GROUP ALL;")
        )
        n_well_connected = well_connected[0].get("count", 0) if well_connected else 0
        connectivity = n_well_connected / n_neurons

        # Reciprocity
        bidirectional = get_results(
            surql("SELECT count() FROM synapse WHERE out -> synapse -> in = true GROUP ALL;")
        )
        n_bidirectional = bidirectional[0].get("count", 0) if bidirectional else 0
        reciprocity = n_bidirectional / n_synapses if n_synapses > 0 else 0.0

        # Freshness
        recent = get_results(
            surql("SELECT count() FROM neuron WHERE created > time::now() - 30d GROUP ALL;")
        )
        n_recent = recent[0].get("count", 0) if recent else 0
        freshness = n_recent / n_neurons

        # HIHO score
        hiho = 0.3 * connectivity + 0.2 * reciprocity + 0.2 * freshness + 0.3 * (1 - orphan_ratio)

        # Status
        if 0.35 <= hiho <= 0.65:
            status = "healthy"
        elif 0.2 <= hiho <= 0.8:
            status = "degraded"
        else:
            status = "critical"

        return {
            "neurons": n_neurons,
            "synapses": n_synapses,
            "orphans": orphans,
            "orphan_ratio": round(orphan_ratio, 3),
            "connectivity": round(connectivity, 3),
            "reciprocity": round(reciprocity, 3),
            "freshness": round(freshness, 3),
            "hiho_score": round(hiho, 3),
            "status": status,
        }
    except Exception as e:
        logger.warning("Failed to get graph metrics: %s", e)
        return {
            "neurons": 0,
            "synapses": 0,
            "orphans": 0,
            "orphan_ratio": 1.0,
            "connectivity": 0.0,
            "reciprocity": 0.0,
            "freshness": 0.0,
            "hiho_score": 0.0,
            "status": "unknown",
        }


def get_data_mesh_metrics() -> dict:
    """Get data mesh health metrics."""
    try:
        # Try mcp_server table
        servers = get_results(surql("SELECT * FROM mcp_server;"))

        if not servers:
            return {
                "total_products": 0,
                "healthy_products": 0,
                "sla_violations": 0,
                "gold_tier": 0,
                "silver_tier": 0,
                "bronze_tier": 0,
                "status": "unknown",
            }

        total = len(servers)
        healthy = sum(1 for s in servers if s.get("status") in ("healthy", "active", "online"))

        # Count by tier
        tiers = {"gold": 0, "silver": 0, "bronze": 0}
        for s in servers:
            tier = s.get("tier", "bronze")
            tiers[tier] = tiers.get(tier, 0) + 1

        # SLA violations (rough estimate based on error rate)
        violations = sum(
            1 for s in servers if s.get("error_count", 0) / max(s.get("call_count", 1), 1) > 0.05
        )

        # Health status
        if violations == 0:
            status = "healthy"
        elif violations < total * 0.2:
            status = "degraded"
        else:
            status = "critical"

        return {
            "total_products": total,
            "healthy_products": healthy,
            "sla_violations": violations,
            "gold_tier": tiers["gold"],
            "silver_tier": tiers["silver"],
            "bronze_tier": tiers["bronze"],
            "status": status,
        }
    except Exception as e:
        logger.warning("Failed to get data mesh metrics: %s", e)
        return {
            "total_products": 0,
            "healthy_products": 0,
            "sla_violations": 0,
            "gold_tier": 0,
            "silver_tier": 0,
            "bronze_tier": 0,
            "status": "unknown",
        }


# ── Dashboard Generation ──────────────────────────────────────────────────────
def generate_dashboard(dreaming: dict, graph: dict, data_mesh: dict) -> str:
    """Generate unified markdown dashboard."""
    lines = [
        "---",
        f"title: Unified System Health Dashboard — {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "tags: [health-dashboard, unified, auto-generated]",
        "aspect: governance",
        "---",
        "",
        "# Unified System Health Dashboard",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "## System Overview",
        "",
        "| Subsystem | Status | Key Metric | Health |",
        "|-----------|--------|------------|--------|",
    ]

    # Status emojis
    def status_emoji(status: str) -> str:
        return {"healthy": "✅", "degraded": "⚠️", "critical": "🔴"}.get(status, "❓")

    lines.extend(
        [
            f"| Dreaming | {status_emoji(dreaming['status'])} {dreaming['status'].upper()} | {dreaming['total_dreams']} dreams | {dreaming['quality_ratio']:.0%} quality |",
            f"| Graph | {status_emoji(graph['status'])} {graph['status'].upper()} | HIHO={graph['hiho_score']:.3f} | {graph['neurons']} neurons |",
            f"| Data Mesh | {status_emoji(data_mesh['status'])} {data_mesh['status'].upper()} | {data_mesh['total_products']} products | {data_mesh['healthy_products']} healthy |",
            "",
        ]
    )

    # Overall health
    statuses = [dreaming["status"], graph["status"], data_mesh["status"]]
    if "critical" in statuses:
        overall = ("🔴 CRITICAL", "Immediate attention required")
    elif "degraded" in statuses:
        overall = ("⚠️ DEGRADED", "Review and address issues")
    else:
        overall = ("✅ HEALTHY", "All systems operational")

    lines.extend(
        [
            f"> **Overall Status:** {overall[0]} — {overall[1]}",
            "",
            "---",
            "",
        ]
    )

    # Dreaming section
    lines.extend(
        [
            "## 🌙 Dreaming System",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Dream Synapses | {dreaming['total_dreams']:,} |",
            f"| High-Quality Dreams | {dreaming['quality_dreams']:,} |",
            f"| Recent Dreams (7d) | {dreaming['recent_dreams']:,} |",
            f"| Quality Ratio | {dreaming['quality_ratio']:.1%} |",
            "",
        ]
    )

    # Graph section
    lines.extend(
        [
            "## 🕸️ Knowledge Graph",
            "",
            f"| Metric | Value | Target |",
            f"|--------|-------|--------|",
            f"| Neurons | {graph['neurons']:,} | — |",
            f"| Synapses | {graph['synapses']:,} | — |",
            f"| Orphans | {graph['orphans']:,} ({graph['orphan_ratio']:.1%}) | <10% |",
            f"| Connectivity | {graph['connectivity']:.3f} | >0.80 |",
            f"| Reciprocity | {graph['reciprocity']:.3f} | >0.60 |",
            f"| Freshness | {graph['freshness']:.3f} | >0.30 |",
            f"| **HIHO Score** | **{graph['hiho_score']:.3f}** | **0.35-0.65** |",
            "",
        ]
    )

    # Data Mesh section
    lines.extend(
        [
            "## 🏗️ Data Mesh",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Products | {data_mesh['total_products']:,} |",
            f"| Healthy | {data_mesh['healthy_products']:,} |",
            f"| SLA Violations | {data_mesh['sla_violations']:,} |",
            f"| Gold Tier | {data_mesh['gold_tier']:,} |",
            f"| Silver Tier | {data_mesh['silver_tier']:,} |",
            f"| Bronze Tier | {data_mesh['bronze_tier']:,} |",
            "",
        ]
    )

    # Recommendations
    lines.extend(
        [
            "## Recommendations",
            "",
        ]
    )

    has_recommendations = False

    if dreaming["status"] != "healthy":
        has_recommendations = True
        lines.append(
            "- **Dreaming:** Low dream quality. Review TOE bridge for high-value connections."
        )

    if graph["orphan_ratio"] > 0.1:
        has_recommendations = True
        lines.append(
            f"- **Graph:** High orphan ratio ({graph['orphan_ratio']:.1%}). Run vault-keeper waking mode."
        )

    if graph["hiho_score"] < 0.35 or graph["hiho_score"] > 0.65:
        has_recommendations = True
        lines.append(
            f"- **Graph:** Outside HIHO equilibrium ({graph['hiho_score']:.3f}). Review connectivity."
        )

    if data_mesh["sla_violations"] > 0:
        has_recommendations = True
        lines.append(
            f"- **Data Mesh:** {data_mesh['sla_violations']} SLA violations. Review data product health."
        )

    if not has_recommendations:
        lines.append("- All systems are healthy. Continue current maintenance schedule.")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Related Dashboards",
            "",
            "- [Graph Health Dashboard](graph-health-dashboard.md)",
            "- [Data Product Health](data-product-health.md)",
            "- [Dream Insights](dream-insights.md)",
            "",
            f"_Generated: {datetime.now(UTC).isoformat()}_",
        ]
    )

    return "\n".join(lines)


def save_to_vault(content: str) -> None:
    """Save dashboard to vault cortex directory."""
    output_path = VAULT_PATH / "cortex" / "unified-health-dashboard.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(content)

    logger.info("Saved dashboard to: %s", output_path)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate unified health dashboard")
    parser.add_argument(
        "--output",
        choices=["vault", "stdout"],
        default="stdout",
        help="Where to output the dashboard (default: stdout)",
    )
    args = parser.parse_args()

    logger.info("Collecting health metrics from all subsystems...")

    try:
        dreaming = get_dreaming_metrics()
        graph = get_graph_metrics()
        data_mesh = get_data_mesh_metrics()
    except Exception as e:
        logger.error("Failed to collect health metrics: %s", e)
        sys.exit(1)

    content = generate_dashboard(dreaming, graph, data_mesh)

    if args.output == "vault":
        save_to_vault(content)
    else:
        print(content)

    logger.info(
        "Dashboard complete: dreaming=%s, graph=%s (HIHO=%.3f), mesh=%s",
        dreaming["status"],
        graph["status"],
        graph["hiho_score"],
        data_mesh["status"],
    )


if __name__ == "__main__":
    main()
