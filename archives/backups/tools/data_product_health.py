#!/usr/bin/env python3
"""Data Product Health Monitor — Check SLA compliance for all data products.

Queries the MCP registry for registered data products and checks their
health metrics against defined SLAs. Generates a markdown report for
the vault cortex directory.

Usage:
    uv run python3 tools/data_product_health.py [--output vault|stdout]
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


# ── Data Product Health Logic ────────────────────────────────────────────────
def get_data_products() -> list[dict]:
    """Query SurrealDB for data products."""
    # Try to get from data_product table
    try:
        products = get_results(surql("SELECT * FROM data_product;"))
        if products:
            return products
    except Exception:
        pass

    # Fallback: check MCP registry via mcp_server entity
    try:
        servers = get_results(surql("SELECT * FROM mcp_server;"))
        products = []
        for server in servers:
            # Transform mcp_server into data product format
            products.append(
                {
                    "id": server.get("id"),
                    "name": server.get("name", "unknown"),
                    "tier": server.get("tier", "bronze"),
                    "status": server.get("status", "unknown"),
                    "call_count": server.get("call_count", 0),
                    "error_count": server.get("error_count", 0),
                    "last_health_check": server.get("last_health_check"),
                }
            )
        return products
    except Exception:
        return []


def check_sla_compliance(product: dict) -> dict:
    """Check SLA compliance for a data product based on its tier."""
    tier = product.get("tier", "bronze")
    call_count = product.get("call_count", 0)
    error_count = product.get("error_count", 0)

    # Calculate error rate
    error_rate = error_count / call_count if call_count > 0 else 0.0

    # SLA thresholds by tier
    sla_thresholds = {
        "gold": {"max_error_rate": 0.001, "min_uptime": 0.999},  # 99.9% uptime, 0.1% errors
        "silver": {"max_error_rate": 0.01, "min_uptime": 0.99},  # 99% uptime, 1% errors
        "bronze": {"max_error_rate": 0.05, "min_uptime": 0.95},  # 95% uptime, 5% errors
    }

    thresholds = sla_thresholds.get(tier, sla_thresholds["bronze"])

    # Check compliance
    meets_error_rate = error_rate <= thresholds["max_error_rate"]

    # Assume healthy status means good uptime
    status = product.get("status", "unknown")
    meets_uptime = status in ("healthy", "active", "online")

    meets_sla = meets_error_rate and meets_uptime

    return {
        "product_id": str(product.get("id", "unknown")),
        "name": product.get("name", "Unknown"),
        "tier": tier,
        "status": status,
        "call_count": call_count,
        "error_count": error_count,
        "error_rate": round(error_rate, 4),
        "meets_sla": meets_sla,
        "sla_violations": [],
        "recommendation": _get_recommendation(tier, call_count, error_rate, meets_sla),
    }


def _get_recommendation(tier: str, call_count: int, error_rate: float, meets_sla: bool) -> str:
    """Generate recommendation based on product health."""
    if not meets_sla:
        if error_rate > 0.1:
            return "investigate_immediately"
        elif error_rate > 0.05:
            return "review_errors"
        else:
            return "monitor_closely"

    if tier == "bronze" and call_count > 100:
        return "consider_upgrade"

    if error_rate > 0.01:
        return "optimize"

    return "maintain"


def get_lineage_info(product_id: str) -> dict:
    """Get lineage information for a data product."""
    try:
        # Query for downstream consumers
        downstream = get_results(
            surql(f"SELECT * FROM data_lineage WHERE source = '{product_id}';")
        )

        # Query for upstream dependencies
        upstream = get_results(surql(f"SELECT * FROM data_lineage WHERE target = '{product_id}';"))

        return {
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
            "blast_radius": len(downstream),
        }
    except Exception:
        return {
            "upstream_count": 0,
            "downstream_count": 0,
            "blast_radius": 0,
        }


# ── Report Generation ─────────────────────────────────────────────────────────
def generate_health_report(products: list[dict]) -> str:
    """Generate markdown report for vault cortex."""
    lines = [
        "---",
        f"title: Data Product Health Report — {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "tags: [data-mesh, data-products, health, auto-generated]",
        "aspect: governance",
        "---",
        "",
        "# Data Product Health Report",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Products Monitored: {len(products)}",
        "",
        "## Summary",
        "",
    ]

    # Calculate summary stats
    total = len(products)
    healthy = sum(1 for p in products if p["meets_sla"])
    violations = total - healthy

    by_tier = {"gold": 0, "silver": 0, "bronze": 0}
    for p in products:
        tier = p.get("tier", "bronze")
        by_tier[tier] = by_tier.get(tier, 0) + 1

    lines.extend(
        [
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Products | {total} |",
            f"| Healthy (SLA Met) | {healthy} ({100 * healthy / total:.1f}%) |"
            if total > 0
            else "| Healthy (SLA Met) | 0 |",
            f"| SLA Violations | {violations} |",
            f"| Gold Tier | {by_tier.get('gold', 0)} |",
            f"| Silver Tier | {by_tier.get('silver', 0)} |",
            f"| Bronze Tier | {by_tier.get('bronze', 0)} |",
            "",
        ]
    )

    if violations > 0:
        lines.extend(
            [
                "## ⚠️ SLA Violations",
                "",
                "| Product | Tier | Error Rate | Status | Recommendation |",
                "|---------|------|------------|--------|----------------|",
            ]
        )
        for p in sorted(products, key=lambda x: x.get("error_rate", 0), reverse=True):
            if not p["meets_sla"]:
                lines.append(
                    f"| {p['name']} | {p['tier']} | {p['error_rate']:.2%} | {p['status']} | {p['recommendation']} |"
                )
        lines.append("")

    lines.extend(
        [
            "## All Products",
            "",
            "| Product | Tier | Status | Calls | Errors | Error Rate | SLA | Recommendation |",
            "|---------|------|--------|-------|--------|------------|-----|----------------|",
        ]
    )

    for p in sorted(
        products, key=lambda x: (not x["meets_sla"], x.get("error_rate", 0)), reverse=True
    ):
        sla_icon = "✅" if p["meets_sla"] else "❌"
        lines.append(
            f"| {p['name']} | {p['tier']} | {p['status']} | {p['call_count']:,} | "
            f"{p['error_count']:,} | {p['error_rate']:.2%} | {sla_icon} | {p['recommendation']} |"
        )

    lines.extend(
        [
            "",
            "## Recommendations",
            "",
        ]
    )

    # Group recommendations
    rec_counts = {}
    for p in products:
        rec = p["recommendation"]
        rec_counts[rec] = rec_counts.get(rec, 0) + 1

    rec_descriptions = {
        "investigate_immediately": "Critical: High error rate requires immediate investigation",
        "review_errors": "High priority: Review and address error patterns",
        "monitor_closely": "Watch: SLA violations detected, monitor for trends",
        "consider_upgrade": "Strategic: High-usage bronze tier - consider promoting to silver",
        "optimize": "Low priority: Minor error rate improvements possible",
        "maintain": "No action: Product is healthy",
    }

    for rec, count in sorted(rec_counts.items(), key=lambda x: x[1], reverse=True):
        desc = rec_descriptions.get(rec, rec)
        lines.append(f"- **{rec}** ({count} products): {desc}")

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
    """Save report to vault cortex directory."""
    output_path = VAULT_PATH / "cortex" / "data-product-health.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(content)

    logger.info("Saved report to: %s", output_path)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Check data product health")
    parser.add_argument(
        "--output",
        choices=["vault", "stdout"],
        default="stdout",
        help="Where to output the report (default: stdout)",
    )
    args = parser.parse_args()

    logger.info("Querying data products from registry...")

    try:
        # Get products from SurrealDB
        raw_products = get_data_products()

        if not raw_products:
            logger.warning("No data products found in registry")
            products = []
        else:
            # Check SLA compliance for each
            products = [check_sla_compliance(p) for p in raw_products]

            # Enrich with lineage info
            for p in products:
                lineage = get_lineage_info(p["product_id"])
                p["blast_radius"] = lineage["blast_radius"]

    except Exception as e:
        logger.error("Failed to query data products: %s", e)
        sys.exit(1)

    content = generate_health_report(products)

    if args.output == "vault":
        save_to_vault(content)
    else:
        print(content)

    healthy = sum(1 for p in products if p["meets_sla"])
    logger.info(
        "Health check complete: %d/%d products healthy",
        healthy,
        len(products),
    )


if __name__ == "__main__":
    main()
