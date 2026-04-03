#!/usr/bin/env python3
"""Hourly MCP Tool Health Monitor — Record call counts, errors, and latency.

Appends health snapshots to JSONL log for trend analysis.
Invoked hourly via cron.

Usage:
    uv run python3 scripts/jobs/mcp_health_hourly.py
"""

from __future__ import annotations

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
LOG_PATH = VAULT_PATH / "metabolism" / "mcp-health.jsonl"


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


# ── MCP Health Logic ──────────────────────────────────────────────────────────
def get_mcp_servers() -> list[dict]:
    """Query SurrealDB for MCP server/tool health data."""
    try:
        # Try mcp_server table first
        servers = get_results(surql("SELECT * FROM mcp_server;"))
        if servers:
            return servers
    except Exception:
        pass

    # Fallback: try alternative table names
    try:
        return get_results(surql("SELECT * FROM tool_health;"))
    except Exception:
        return []


def calculate_health_metrics(servers: list[dict]) -> dict:
    """Calculate aggregate health metrics from server data."""
    if not servers:
        return {
            "total_servers": 0,
            "healthy_count": 0,
            "degraded_count": 0,
            "critical_count": 0,
            "total_calls": 0,
            "total_errors": 0,
            "aggregate_error_rate": 0.0,
        }

    total_calls = sum(s.get("call_count", 0) for s in servers)
    total_errors = sum(s.get("error_count", 0) for s in servers)

    healthy = sum(1 for s in servers if s.get("status") in ("healthy", "active", "online"))
    degraded = sum(1 for s in servers if s.get("status") in ("degraded", "warning"))
    critical = sum(1 for s in servers if s.get("status") in ("critical", "down", "offline"))

    return {
        "total_servers": len(servers),
        "healthy_count": healthy,
        "degraded_count": degraded,
        "critical_count": critical,
        "total_calls": total_calls,
        "total_errors": total_errors,
        "aggregate_error_rate": total_errors / total_calls if total_calls > 0 else 0.0,
    }


def record_health_snapshot() -> None:
    """Record a health snapshot to the JSONL log."""
    # Ensure log directory exists
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    servers = get_mcp_servers()
    metrics = calculate_health_metrics(servers)

    snapshot = {
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": metrics,
        "servers": [
            {
                "id": str(s.get("id", "unknown")),
                "name": s.get("name", "unknown"),
                "status": s.get("status", "unknown"),
                "tier": s.get("tier", "unknown"),
                "call_count": s.get("call_count", 0),
                "error_count": s.get("error_count", 0),
                "avg_latency_ms": s.get("avg_latency_ms", 0),
            }
            for s in servers
        ],
    }

    # Append to JSONL file
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(snapshot) + "\n")

    logger.info(
        "MCP health snapshot recorded: %d servers, %.2f%% error rate",
        metrics["total_servers"],
        metrics["aggregate_error_rate"] * 100,
    )


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    try:
        record_health_snapshot()
    except Exception as e:
        logger.error("Failed to record MCP health snapshot: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
