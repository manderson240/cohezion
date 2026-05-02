#!/usr/bin/env python3
"""Dream-to-TOE Bridge — Surface dreams relevant to physics/First Nations theory.

Queries SurrealDB for dream synapses involving physics, cosmology,
First Nations concepts, and other theory-of-everything topics.

Usage:
    uv run python3 tools/dream_toe_bridge.py [--output vault|stdout]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime

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

# Keywords that indicate TOE-relevant content
TOE_KEYWORDS = [
    # Physics
    "physics",
    "quantum",
    "cosmology",
    "universe",
    "spacetime",
    "entropy",
    "energy",
    "field",
    "symmetry",
    "gauge",
    "tensor",
    "manifold",
    # First Nations / Indigenous concepts
    "dreaming",
    "songline",
    "country",
    "mob",
    "aboriginal",
    "indigenous",
    "first nations",
    "cosmology",
    "creation",
    "ancestor",
    # Meta/TOE concepts
    "theory of everything",
    "unification",
    "emergence",
    "complexity",
    "information",
    "consciousness",
    "observer",
    "reality",
    "nature",
    "mycelium",
    "network",
    "connection",
    "resonance",
    "pattern",
]


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


# ── Bridge Logic ────────────────────────────────────────────────────────────
def is_toe_relevant(title: str | None) -> bool:
    """Check if a note title contains TOE-relevant keywords."""
    if not title:
        return False
    title_lower = title.lower()
    return any(kw in title_lower for kw in TOE_KEYWORDS)


def query_toe_dreams(days: int = 14) -> list[dict]:
    """Query dreams where either source or target is TOE-relevant."""
    # Get all recent dreams
    sql = f"""
SELECT in.title as source, out.title as target,
       resonance, quality_score, created
FROM synapse
WHERE link_type = 'dream'
  AND created > time::now() - {days}d
ORDER BY created DESC
LIMIT 100;
"""
    dreams = get_results(surql(sql))

    # Filter for TOE-relevant dreams
    toe_dreams = []
    for dream in dreams:
        source = dream.get("source", "")
        target = dream.get("target", "")
        if is_toe_relevant(source) or is_toe_relevant(target):
            toe_dreams.append(dream)

    return toe_dreams


def format_markdown(dreams: list[dict]) -> str:
    """Format dreams as markdown for vault output."""
    lines = [
        "---",
        "title: Dream-to-TOE Bridge — Physics/First Nations Connections",
        f"date: {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "tags: [dreaming, toe, physics, first-nations, auto-generated]",
        "aspect: connective",
        "---",
        "",
        "# Dream-to-TOE Bridge",
        "",
        "Dream connections between physics concepts and First Nations knowledge. ",
        "These are cross-domain resonances surfaced by the dreaming engine.",
        "",
    ]

    if not dreams:
        lines.append("*No TOE-relevant dreams found in the last 14 days.*")
        lines.append("")
        lines.append("The dreaming engine continues to search...")
        return "\n".join(lines)

    lines.append(f"## {len(dreams)} Connections\n")

    # Group by relevance type
    physics_dreams = []
    indigenous_dreams = []
    other_dreams = []

    for dream in dreams:
        source = dream.get("source", "")
        target = dream.get("target", "")

        source_lower = source.lower() if source else ""
        target_lower = target.lower() if target else ""

        has_physics = any(
            kw in source_lower or kw in target_lower
            for kw in [
                "physics",
                "quantum",
                "cosmology",
                "universe",
                "spacetime",
                "entropy",
                "energy",
                "field",
                "symmetry",
            ]
        )
        has_indigenous = any(
            kw in source_lower or kw in target_lower
            for kw in [
                "dreaming",
                "songline",
                "country",
                "aboriginal",
                "indigenous",
                "first nations",
                "ancestor",
            ]
        )

        if has_physics and has_indigenous:
            # Physics + Indigenous connection
            indigenous_dreams.append(dream)
        elif has_physics:
            physics_dreams.append(dream)
        elif has_indigenous:
            indigenous_dreams.append(dream)
        else:
            other_dreams.append(dream)

    # Output Physics ↔ Indigenous first (most valuable)
    if indigenous_dreams:
        lines.append("### 🌏 Physics ↔ First Nations\n")
        for i, dream in enumerate(indigenous_dreams, 1):
            _format_dream_entry(lines, i, dream)

    if physics_dreams:
        lines.append("### 🔬 Physics Connections\n")
        for i, dream in enumerate(physics_dreams, len(indigenous_dreams) + 1):
            _format_dream_entry(lines, i, dream)

    if other_dreams:
        lines.append("### ✨ Other Resonances\n")
        for i, dream in enumerate(other_dreams, len(indigenous_dreams) + len(physics_dreams) + 1):
            _format_dream_entry(lines, i, dream)

    return "\n".join(lines)


def _format_dream_entry(lines: list, idx: int, dream: dict) -> None:
    """Format a single dream entry."""
    source = dream.get("source", "Unknown")
    target = dream.get("target", "Unknown")
    resonance = dream.get("resonance", "No resonance text")
    score = dream.get("quality_score", 0.0)

    lines.append(f"**{idx}. {source} × {target}** (quality: {score:.2f})")
    lines.append("")
    lines.append(f"> {resonance}")
    lines.append("")
    lines.append("---")
    lines.append("")


def save_to_vault(content: str) -> None:
    """Save report to vault cortex directory."""
    output_path = os.path.join(VAULT_PATH, "cortex", "dream-toe-bridge.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        f.write(content)

    logger.info("Saved bridge report to: %s", output_path)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Bridge dreams to Theory of Everything")
    parser.add_argument(
        "--output",
        choices=["vault", "stdout"],
        default="stdout",
        help="Where to output the report (default: stdout)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of days to look back (default: 14)",
    )
    args = parser.parse_args()

    logger.info("Querying TOE-relevant dreams from last %d days...", args.days)

    try:
        dreams = query_toe_dreams(args.days)
    except Exception as e:
        logger.error("Failed to query dreams: %s", e)
        sys.exit(1)

    content = format_markdown(dreams)

    if args.output == "vault":
        save_to_vault(content)
    else:
        print(content)

    logger.info("Bridge complete: %d TOE-relevant dreams found", len(dreams))


if __name__ == "__main__":
    main()
