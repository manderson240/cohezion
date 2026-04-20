"""MCP Server for graph health monitoring and vault maintenance."""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .graph_health import classify_health, compute_graph_hiho


logger = logging.getLogger(__name__)

SURREAL_URL = os.environ.get("SURREAL_URL", "ws://localhost:8000")
SURREAL_NS = os.environ.get("SURREAL_NS", "cohezion")
SURREAL_DB = os.environ.get("SURREAL_DB", "cohezion")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")
VAULT_PATH = Path(os.environ.get("VAULT_PATH", os.path.expanduser("~/vaults/cohezion-vault")))

EXPECTED_TABLES = [
    "neurons",
    "synapses",
    "decisions",
    "experiments",
    "patterns",
    "skills",
    "code_modules",
    "journeys",
    "agents",
]

mcp = FastMCP(
    "Cohezion Maintenance",
    stateless_http=True,
    port=8362,
    instructions=(
        "Graph health monitoring and vault maintenance for Cohezion. "
        "Check graph HIHO health, prune orphans, audit vault notes, "
        "and inspect SurrealDB schema and table stats."
    ),
)


async def _surreal_query(query: str) -> list:
    """Execute a SurrealDB query with graceful fallback."""
    try:
        from surrealdb import AsyncSurreal

        db = AsyncSurreal(SURREAL_URL)
        await db.connect()
        await db.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
        await db.use(SURREAL_NS, SURREAL_DB)
        return await db.query(query)
    except Exception as e:
        logger.warning("SurrealDB unavailable: %s", e)
        return [{"status": "ERR", "error": str(e)}]


def _is_error(result: list) -> str | None:
    """Return error string if query failed, else None."""
    if result and isinstance(result[0], dict) and result[0].get("status") == "ERR":
        return result[0].get("error", "unknown error")
    return None


# ── Tool 1: graph_health ─────────────────────────────────────────────


@mcp.tool()
async def graph_health() -> str:
    """Return graph health metrics including HIHO score."""
    total_res = await _surreal_query("SELECT count() AS c FROM neurons GROUP ALL")
    edge_res = await _surreal_query("SELECT count() AS c FROM synapses GROUP ALL")

    if err := _is_error(total_res):
        return json.dumps({"error": f"SurrealDB unavailable: {err}", "metrics": {}})

    total_nodes = _extract_count(total_res)
    total_edges = _extract_count(edge_res)

    # Connected nodes: those appearing as source or target in synapses
    conn_res = await _surreal_query(
        "SELECT count() AS c FROM (SELECT source FROM synapses UNION SELECT target FROM synapses) GROUP ALL"
    )
    connected = min(_extract_count(conn_res), total_nodes)
    orphan_count = max(total_nodes - connected, 0)
    orphan_ratio = orphan_count / total_nodes if total_nodes > 0 else 0.0
    avg_density = total_edges / total_nodes if total_nodes > 0 else 0.0

    # Freshness: nodes updated in last 30 days
    fresh_res = await _surreal_query(
        "SELECT count() AS c FROM neurons WHERE updated_at > time::now() - 30d GROUP ALL"
    )
    fresh_count = _extract_count(fresh_res)
    freshness = fresh_count / total_nodes if total_nodes > 0 else 0.0

    # Reciprocity: fraction of edges that have a reverse edge
    recip_res = await _surreal_query(
        "SELECT count() AS c FROM synapses WHERE ->synapses<->(target)->synapses->(source) GROUP ALL"
    )
    recip_count = _extract_count(recip_res)
    reciprocity = recip_count / total_edges if total_edges > 0 else 0.0
    connectivity = connected / total_nodes if total_nodes > 0 else 0.0

    metrics = {
        "total_nodes": total_nodes,
        "connected_nodes": connected,
        "orphan_count": orphan_count,
        "orphan_ratio": round(orphan_ratio, 4),
        "avg_synapse_density": round(avg_density, 4),
        "freshness": round(freshness, 4),
        "connectivity": round(connectivity, 4),
        "reciprocity": round(reciprocity, 4),
    }
    hiho = compute_graph_hiho(metrics)
    metrics["graph_hiho"] = round(hiho, 4)
    metrics["health_status"] = classify_health(hiho)
    return json.dumps(metrics, indent=2)


# ── Tool 2: graph_prune_orphans ───────────────────────────────────────


@mcp.tool()
async def graph_prune_orphans(dry_run: bool = True) -> str:
    """Find and optionally archive disconnected neurons.

    Args:
        dry_run: If True, list orphans without modifying. If False, archive them.
    """
    orphan_res = await _surreal_query(
        "SELECT id FROM neurons WHERE id NOT IN "
        "(SELECT source FROM synapses) AND id NOT IN (SELECT target FROM synapses)"
    )
    if err := _is_error(orphan_res):
        return json.dumps({"error": err, "orphans": []})

    orphans = _extract_records(orphan_res)
    orphan_ids = [str(r.get("id", "")) for r in orphans]

    if dry_run or not orphan_ids:
        return json.dumps({"dry_run": True, "count": len(orphan_ids), "orphan_ids": orphan_ids})

    # Archive: copy to archived_neurons, then delete from neurons
    for oid in orphan_ids:
        await _surreal_query(
            f"INSERT INTO archived_neurons (SELECT *, time::now() AS archived_at FROM {oid})"
        )
        await _surreal_query(f"DELETE {oid}")

    return json.dumps(
        {"dry_run": False, "archived_count": len(orphan_ids), "orphan_ids": orphan_ids}
    )


# ── Tool 3: graph_compact ─────────────────────────────────────────────


@mcp.tool()
async def graph_compact(similarity_threshold: float = 0.95) -> str:
    """Identify near-duplicate neurons by FLUME affinity vector similarity.

    Args:
        similarity_threshold: Cosine similarity threshold (0.0-1.0). Default 0.95.
    """
    vec_res = await _surreal_query(
        "SELECT id, affinity_vector FROM neurons WHERE affinity_vector IS NOT NULL"
    )
    if err := _is_error(vec_res):
        return json.dumps({"error": err, "candidates": []})

    records = _extract_records(vec_res)
    if len(records) < 2:
        return json.dumps({"candidates": [], "message": "Not enough neurons with affinity vectors"})

    # Compute pairwise cosine similarity
    candidates = []
    for i, a in enumerate(records):
        for b in records[i + 1 :]:
            sim = _cosine_similarity(a.get("affinity_vector", []), b.get("affinity_vector", []))
            if sim >= similarity_threshold:
                candidates.append(
                    {
                        "neuron_a": str(a["id"]),
                        "neuron_b": str(b["id"]),
                        "similarity": round(sim, 6),
                    }
                )

    return json.dumps(
        {"candidates": candidates, "count": len(candidates), "threshold": similarity_threshold}
    )


# ── Tool 4: verify_graph_schema ───────────────────────────────────────


@mcp.tool()
async def verify_graph_schema() -> str:
    """Check that all expected tables and indexes exist in SurrealDB."""
    info_res = await _surreal_query("INFO FOR DB")
    if err := _is_error(info_res):
        return json.dumps({"error": err, "tables": {}})

    db_info = _extract_first(info_res)
    existing_tables = set(db_info.get("tables", {}).keys()) if isinstance(db_info, dict) else set()

    missing = [t for t in EXPECTED_TABLES if t not in existing_tables]
    extra = [t for t in existing_tables if t not in EXPECTED_TABLES]

    # Check indexes per table
    index_report = {}
    for table in EXPECTED_TABLES:
        if table in existing_tables:
            idx_res = await _surreal_query(f"INFO FOR TABLE {table}")
            tbl_info = _extract_first(idx_res)
            indexes = list(tbl_info.get("indexes", {}).keys()) if isinstance(tbl_info, dict) else []
            index_report[table] = {"exists": True, "indexes": indexes}
        else:
            index_report[table] = {"exists": False, "indexes": []}

    return json.dumps(
        {
            "missing_tables": missing,
            "extra_tables": extra,
            "tables": index_report,
            "schema_valid": len(missing) == 0,
        },
        indent=2,
    )


# ── Tool 5: vault_audit ──────────────────────────────────────────────


@mcp.tool()
async def vault_audit() -> str:
    """Audit Obsidian vault health: frontmatter, broken links, staleness, tags."""
    if not VAULT_PATH.is_dir():
        return json.dumps({"error": f"Vault not found at {VAULT_PATH}"})

    missing_frontmatter = []
    broken_links = []
    stale_notes = []
    no_tags = []
    now = datetime.now(tz=timezone.utc)
    all_notes = {p.stem for p in VAULT_PATH.rglob("*.md")}

    for md_file in VAULT_PATH.rglob("*.md"):
        rel = str(md_file.relative_to(VAULT_PATH))
        if rel.startswith("."):
            continue

        content = md_file.read_text(errors="replace")

        # Frontmatter check
        if not content.startswith("---"):
            missing_frontmatter.append(rel)

        # Tag check (YAML tags: or inline #tag)
        has_tags = "tags:" in content or "#" in content.split("---")[-1]
        if not has_tags:
            no_tags.append(rel)

        # Staleness (90+ days since modification)
        mtime = datetime.fromtimestamp(md_file.stat().st_mtime, tz=timezone.utc)
        if (now - mtime).days > 90:
            stale_notes.append(rel)

        # Broken wikilinks
        for match in re.finditer(r"\[\[([^\]|]+)", content):
            link_target = match.group(1).strip()
            if link_target not in all_notes:
                broken_links.append({"note": rel, "broken_link": link_target})

    return json.dumps(
        {
            "total_notes": len(all_notes),
            "missing_frontmatter": {
                "count": len(missing_frontmatter),
                "notes": missing_frontmatter[:20],
            },
            "broken_links": {"count": len(broken_links), "links": broken_links[:20]},
            "stale_notes": {"count": len(stale_notes), "notes": stale_notes[:20]},
            "no_tags": {"count": len(no_tags), "notes": no_tags[:20]},
        },
        indent=2,
    )


# ── Tool 6: surreal_table_stats ───────────────────────────────────────


@mcp.tool()
async def surreal_table_stats() -> str:
    """Return row counts for each SurrealDB table and connection health."""
    info_res = await _surreal_query("INFO FOR DB")
    if err := _is_error(info_res):
        return json.dumps({"connected": False, "error": err, "tables": {}})

    db_info = _extract_first(info_res)
    tables = list(db_info.get("tables", {}).keys()) if isinstance(db_info, dict) else []

    stats = {}
    for table in tables:
        count_res = await _surreal_query(f"SELECT count() AS c FROM {table} GROUP ALL")
        stats[table] = _extract_count(count_res)

    return json.dumps({"connected": True, "endpoint": SURREAL_URL, "tables": stats}, indent=2)


# ── Helpers ───────────────────────────────────────────────────────────


def _extract_count(result: list) -> int:
    """Extract count from a SurrealDB GROUP ALL query result."""
    if not result:
        return 0
    first = result[0] if isinstance(result, list) else result
    if isinstance(first, dict):
        if "result" in first and isinstance(first["result"], list) and first["result"]:
            return first["result"][0].get("c", 0)
        return first.get("c", 0)
    return 0


def _extract_records(result: list) -> list:
    """Extract record list from a SurrealDB SELECT result."""
    if not result:
        return []
    first = result[0] if isinstance(result, list) else result
    if isinstance(first, dict) and "result" in first:
        return first["result"] if isinstance(first["result"], list) else []
    if isinstance(first, list):
        return first
    return result if isinstance(result, list) else []


def _extract_first(result: list) -> dict:
    """Extract first result dict from a SurrealDB info query."""
    if not result:
        return {}
    first = result[0] if isinstance(result, list) else result
    if isinstance(first, dict) and "result" in first:
        r = first["result"]
        return r if isinstance(r, dict) else (r[0] if isinstance(r, list) and r else {})
    return first if isinstance(first, dict) else {}


def _cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def main():
    """Entry point for cohezion-maintenance-mcp."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
