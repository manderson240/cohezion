#!/usr/bin/env python3
"""Dream Quality Report — Surface high-quality dream synapses.

Queries SurrealDB for dreams with quality_score > 0.5 from last 7 days
and outputs them in a readable format.

Usage:
    uv run python3 tools/dream_quality_report.py [--output vault|stdout]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime, timedelta

import httpx

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
SURREALDB_URL = os.getenv("SURREALDB_URL", "http://localhost:8001")
SURREALDB_NS = "cohezion"
SURREALDB_DB = "vault"
SURREALDB_USER = os.getenv("SURREALDB_USER", "root")
SURREALDB_PASS = os.getenv("SURREALDB_PASS", "root")
VAULT_PATH = os.path.expanduser("~/vaults/cohezion-vault")


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


# ── Report Generation ───────────────────────────────────────────────────────
def generate_report(days: int = 7, min_quality: float = 0.5) -> list[dict]:
    """Query high-quality dreams from the last N days."""
    sql = f"""
SELECT in.title as source, out.title as target,
       resonance, quality_score, created
FROM synapse
WHERE link_type = 'dream'
  AND quality_score >= {min_quality}
  AND created > time::now() - {days}d
ORDER BY quality_score DESC, created DESC
LIMIT 20;
"""
    return get_results(surql(sql))


def format_markdown(dreams: list[dict]) -> str:
    """Format dreams as markdown for vault output."""
    lines = [
        "---",
        "title: Dream Insights — High Quality Connections",
        f"date: {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "tags: [dreaming, insights, auto-generated]",
        "aspect: connective",
        "---",
        "",
        "# Dream Insights",
        "",
        f"Auto-generated report of high-quality dream synapses (score ≥ 0.5) from the last 7 days.",
        "",
    ]

    if not dreams:
        lines.append("*No high-quality dreams found this week.*")
        return "\n".join(lines)

    lines.append(f"## {len(dreams)} Dream Connections\n")

    for i, dream in enumerate(dreams, 1):
        source = dream.get("source", "Unknown")
        target = dream.get("target", "Unknown")
        resonance = dream.get("resonance", "No resonance text")
        score = dream.get("quality_score", 0.0)
        created = dream.get("created", "Unknown")

        lines.append(f"### {i}. {source} × {target}")
        lines.append(f"**Quality Score:** {score:.2f}")
        lines.append(f"**Created:** {created}")
        lines.append("")
        lines.append(f"> {resonance}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def save_to_vault(content: str) -> None:
    """Save report to vault cortex directory."""
    output_path = os.path.join(VAULT_PATH, "cortex", "dream-insights.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        f.write(content)

    logger.info("Saved report to: %s", output_path)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate dream quality report")
    parser.add_argument(
        "--output",
        choices=["vault", "stdout"],
        default="stdout",
        help="Where to output the report (default: stdout)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.5,
        help="Minimum quality score to include (default: 0.5)",
    )
    args = parser.parse_args()

    logger.info(
        "Querying dreams from last %d days (quality >= %.2f)...", args.days, args.min_quality
    )

    try:
        dreams = generate_report(args.days, args.min_quality)
    except Exception as e:
        logger.error("Failed to query dreams: %s", e)
        sys.exit(1)

    content = format_markdown(dreams)

    if args.output == "vault":
        save_to_vault(content)
    else:
        print(content)

    logger.info("Report complete: %d dreams found", len(dreams))


if __name__ == "__main__":
    main()
