#!/usr/bin/env python3
"""Data Lineage Impact Analyzer — Show downstream impact of data changes.

Analyzes the blast radius of modifying a data product by tracing
upstream dependencies and downstream consumers.

Usage:
    uv run python3 tools/data_lineage_impact.py <product_id> [--output vault|stdout]
"""

from __future__ import annotations

import argparse
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


# ── Lineage Analysis ─────────────────────────────────────────────────────────
def get_product_info(product_id: str) -> dict | None:
    """Get basic info about a data product."""
    # Try multiple table formats
    for table in ["data_product", "mcp_server"]:
        try:
            result = get_results(surql(f"SELECT * FROM {table} WHERE id = '{product_id}';"))
            if result:
                return {
                    "id": product_id,
                    "name": result[0].get("name", "Unknown"),
                    "tier": result[0].get("tier", "unknown"),
                    "status": result[0].get("status", "unknown"),
                }
        except Exception:
            continue
    return None


def get_upstream_dependencies(product_id: str) -> list[dict]:
    """Get upstream data sources that this product depends on."""
    try:
        # Query data_lineage table where target is this product
        upstream = get_results(surql(f"SELECT * FROM data_lineage WHERE target = '{product_id}';"))
        return [
            {
                "id": u.get("source"),
                "relationship": u.get("relationship_type", "depends_on"),
                "criticality": u.get("criticality", "standard"),
            }
            for u in upstream
            if u.get("source")
        ]
    except Exception:
        return []


def get_downstream_consumers(product_id: str) -> list[dict]:
    """Get downstream products that depend on this one."""
    try:
        # Query data_lineage table where source is this product
        downstream = get_results(
            surql(f"SELECT * FROM data_lineage WHERE source = '{product_id}';")
        )
        return [
            {
                "id": d.get("target"),
                "relationship": d.get("relationship_type", "consumer"),
                "criticality": d.get("criticality", "standard"),
            }
            for d in downstream
            if d.get("target")
        ]
    except Exception:
        return []


def analyze_impact(product_id: str) -> dict:
    """Analyze the full impact of changing a data product."""
    product = get_product_info(product_id)
    if not product:
        return {"error": f"Product {product_id} not found"}

    upstream = get_upstream_dependencies(product_id)
    downstream = get_downstream_consumers(product_id)

    # Calculate blast radius
    gold_tier_downstream = sum(1 for d in downstream if get_product_tier(d["id"]) == "gold")
    silver_tier_downstream = sum(1 for d in downstream if get_product_tier(d["id"]) == "silver")

    # Determine risk level
    if gold_tier_downstream > 0:
        risk_level = "high"
    elif silver_tier_downstream > 0:
        risk_level = "medium"
    elif len(downstream) > 0:
        risk_level = "low"
    else:
        risk_level = "minimal"

    return {
        "product": product,
        "upstream_count": len(upstream),
        "downstream_count": len(downstream),
        "gold_dependents": gold_tier_downstream,
        "silver_dependents": silver_tier_downstream,
        "blast_radius": len(downstream),
        "risk_level": risk_level,
        "upstream": upstream,
        "downstream": downstream,
    }


def get_product_tier(product_id: str) -> str:
    """Helper to get tier of a product."""
    info = get_product_info(product_id)
    return info.get("tier", "unknown") if info else "unknown"


# ── Report Generation ─────────────────────────────────────────────────────────
def format_impact_report(analysis: dict) -> str:
    """Format impact analysis as markdown."""
    if "error" in analysis:
        return f"# Error\n\n{analysis['error']}"

    product = analysis["product"]

    lines = [
        "---",
        f"title: Lineage Impact Analysis — {product['name']}",
        f"date: {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "tags: [data-mesh, lineage, impact-analysis, auto-generated]",
        "aspect: governance",
        "---",
        "",
        f"# Impact Analysis: {product['name']}",
        "",
        f"**Product ID:** `{product['id']}`",
        f"**Tier:** {product['tier']}",
        f"**Status:** {product['status']}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Upstream Dependencies | {analysis['upstream_count']} |",
        f"| Downstream Consumers | {analysis['downstream_count']} |",
        f"| Gold Tier Dependents | {analysis['gold_dependents']} |",
        f"| Silver Tier Dependents | {analysis['silver_dependents']} |",
        f"| **Blast Radius** | **{analysis['blast_radius']}** |",
        f"| **Risk Level** | **{analysis['risk_level'].upper()}** |",
        "",
    ]

    # Risk level interpretation
    risk_messages = {
        "high": "🔴 **HIGH RISK**: Changes will impact gold-tier data products. Requires careful planning and stakeholder coordination.",
        "medium": "⚠️ **MEDIUM RISK**: Changes affect silver-tier products. Plan for downstream notification.",
        "low": "🟡 **LOW RISK**: Limited impact on non-critical consumers. Standard change management applies.",
        "minimal": "✅ **MINIMAL RISK**: No downstream dependencies. Safe to modify with standard testing.",
    }

    lines.extend(
        [
            risk_messages.get(analysis["risk_level"], ""),
            "",
        ]
    )

    # Upstream dependencies
    if analysis["upstream"]:
        lines.extend(
            [
                "## Upstream Dependencies",
                "",
                "Products this depends on:",
                "",
                "| Product | Relationship | Criticality |",
                "|---------|--------------|-------------|",
            ]
        )
        for u in analysis["upstream"]:
            info = get_product_info(u["id"])
            name = info["name"] if info else u["id"]
            lines.append(f"| {name} | {u['relationship']} | {u['criticality']} |")
        lines.append("")
    else:
        lines.extend(
            [
                "## Upstream Dependencies",
                "",
                "*No upstream dependencies detected.*",
                "",
            ]
        )

    # Downstream consumers
    if analysis["downstream"]:
        lines.extend(
            [
                "## Downstream Consumers",
                "",
                "Products that depend on this:",
                "",
                "| Product | Tier | Relationship | Criticality |",
                "|---------|------|--------------|-------------|",
            ]
        )
        for d in sorted(
            analysis["downstream"],
            key=lambda x: get_product_tier(x["id"]),
            reverse=True,  # Gold first
        ):
            info = get_product_info(d["id"])
            name = info["name"] if info else d["id"]
            tier = info["tier"] if info else "unknown"
            lines.append(f"| {name} | {tier} | {d['relationship']} | {d['criticality']} |")
        lines.append("")
    else:
        lines.extend(
            [
                "## Downstream Consumers",
                "",
                "*No downstream consumers detected.*",
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

    if analysis["risk_level"] == "high":
        lines.extend(
            [
                "1. **Schedule maintenance window** — Gold tier dependencies require coordinated downtime",
                "2. **Notify stakeholders** — Contact owners of dependent gold-tier products",
                "3. **Prepare rollback plan** — Have revert procedure ready before making changes",
                "4. **Run full integration tests** — Validate all downstream consumers before deployment",
            ]
        )
    elif analysis["risk_level"] == "medium":
        lines.extend(
            [
                "1. **Notify downstream teams** — Alert owners of silver-tier consumers",
                "2. **Test in staging** — Validate changes against dependent products",
                "3. **Monitor after deployment** — Watch for errors in downstream pipelines",
            ]
        )
    elif analysis["risk_level"] == "low":
        lines.extend(
            [
                "1. **Standard testing** — Run unit and integration tests",
                "2. **Monitor metrics** — Check for increased error rates post-change",
            ]
        )
    else:
        lines.append(
            "- **Proceed with standard change management** — No special precautions needed"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            f"_Generated: {datetime.now(UTC).isoformat()}_",
        ]
    )

    return "\n".join(lines)


def save_to_vault(content: str, product_name: str) -> None:
    """Save report to vault cortex directory."""
    safe_name = product_name.replace(" ", "-").lower()
    output_path = VAULT_PATH / "cortex" / f"lineage-impact-{safe_name}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(content)

    logger.info("Saved impact report to: %s", output_path)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Analyze data lineage impact")
    parser.add_argument(
        "product_id",
        help="ID of the data product to analyze (e.g., 'data_product:abc123' or just 'abc123')",
    )
    parser.add_argument(
        "--output",
        choices=["vault", "stdout"],
        default="stdout",
        help="Where to output the report (default: stdout)",
    )
    args = parser.parse_args()

    # Normalize product ID
    product_id = args.product_id
    if ":" not in product_id:
        # Try to find the full ID
        product_id = f"data_product:{product_id}"

    logger.info("Analyzing lineage impact for: %s", product_id)

    try:
        analysis = analyze_impact(product_id)
        if "error" in analysis:
            logger.error(analysis["error"])
            sys.exit(1)
    except Exception as e:
        logger.error("Failed to analyze impact: %s", e)
        sys.exit(1)

    content = format_impact_report(analysis)

    if args.output == "vault":
        save_to_vault(content, analysis["product"]["name"])
    else:
        print(content)

    logger.info(
        "Impact analysis complete: risk_level=%s, blast_radius=%d",
        analysis["risk_level"],
        analysis["blast_radius"],
    )


if __name__ == "__main__":
    main()
