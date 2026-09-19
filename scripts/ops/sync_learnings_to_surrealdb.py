#!/usr/bin/env python3
"""Synchronize all key learnings and local WAL entries into SurrealDB (port 8001)."""

import base64
import json
import urllib.request
from pathlib import Path


_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_NS = "cohezion"
_SURREAL_DB = "main"
_AUTH = base64.b64encode(b"root:root").decode()


def surreal_query(sql: str) -> list[dict]:
    req = urllib.request.Request(
        _SURREAL_URL,
        data=sql.encode("utf-8"),
        headers={
            "surreal-ns": _SURREAL_NS,
            "surreal-db": _SURREAL_DB,
            "Content-Type": "text/plain",
            "Authorization": f"Basic {_AUTH}",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    print("=== SYNCHRONIZING LEARNINGS TO SURREALDB (PORT 8001) ===")

    # 1. Backfill WAL entries
    wal_path = Path.home() / ".cohezion" / "wal" / "learning_cycles.jsonl"
    wal_count = 0
    if wal_path.exists():
        for line in wal_path.read_text().splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            cycle_id = item.get("id") or f"wal_{wal_count}"
            content = {k: v for k, v in item.items() if k != "id"}
            surql = f"UPSERT learning:{cycle_id} CONTENT {json.dumps(content)};"
            try:
                surreal_query(surql)
                wal_count += 1
            except Exception as e:
                print(f"Error upserting WAL item {cycle_id}: {e}")

    print(f"✓ Backfilled {wal_count} learning cycle items from WAL into SurrealDB.")

    # 2. Upsert Key Learnings 440, 441, 442, 443
    key_learnings = [
        {
            "id": "l440",
            "learning_id": 440,
            "title": "OOM Hardening, Ternary-Bonsai & IonQ Quantum Suite",
            "date": "2026-09-17",
            "category": "infrastructure_quantum",
            "summary": "Audited local silicon memory limits on Strix Halo. Hardened against memory leaks and wired Ternary-Bonsai and IonQ quantum simulator suite.",
            "verified": True,
            "tags": ["oom-hardening", "ternary-bonsai", "ionq", "strix-halo"],
            "state_vector_12d": [0.5, 0.5, 0.5, 1.0, 0.95, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        },
        {
            "id": "l441",
            "learning_id": 441,
            "title": "Sovereign Kaggle Multi-Track Mastery, Live Ladder Displacement Autopsy & 51-Tool MCP Integration",
            "date": "2026-09-18",
            "category": "kaggle_mastery",
            "summary": "Diagnosed Kaggriculture live slot displacement (restored v4c5 and v4macro to regain 706+ rating). Integrated 51-tool kaggle-mcp-server.",
            "verified": True,
            "tags": ["kaggriculture", "kaggle-mcp", "live-slots", "autoharness"],
            "state_vector_12d": [0.5, 0.5, 0.5, 1.0, 0.95, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        },
        {
            "id": "l442",
            "learning_id": 442,
            "title": "Kaggle Multi-Track Acceleration, Quad-L4x4 Parallelism & Hidden Test Governance",
            "date": "2026-09-18",
            "category": "kaggle_hardware_scaling",
            "summary": "Activated NvidiaL4x4 on ARC-AGI-2 with 4-way worker scaling. Diagnosed RSNA Knee hidden test timeout caused by 10 members + 8-window TTA.",
            "verified": True,
            "tags": ["arc-agi-2", "nvidial4x4", "rsna-knee", "hidden-test-governance"],
            "state_vector_12d": [0.5, 0.5, 0.5, 1.0, 0.95, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        },
        {
            "id": "l443",
            "learning_id": 443,
            "title": "Sovereign Fleet Swap Reclamation, Code Submission Auth Resolution & Dual Kernel Dispatch",
            "date": "2026-09-19",
            "category": "kaggle_infrastructure_sovereignty",
            "summary": "Purged 98 orphaned bg-pty processes reclaiming 39 GiB swap to 0%. Resolved ARC2 kernelSessions.get 403 error via versionNumber=10. Dispatched Biohub adaptive threshold v2 and RSNA Knee non-overlapping TTA v7.",
            "verified": True,
            "tags": ["strix-halo", "swap-purge", "arc-agi-2", "biohub", "rsna-knee", "autoharness"],
            "state_vector_12d": [0.5, 0.5, 0.5, 1.0, 0.95, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        },
    ]

    for kl in key_learnings:
        kl_id = kl["id"]
        content = {k: v for k, v in kl.items() if k != "id"}
        surql = f"UPSERT learning:{kl_id} CONTENT {json.dumps(content)};"
        res = surreal_query(surql)
        status = res[0].get("status") if res else "UNKNOWN"
        print(f"✓ Upserted learning:{kl_id} -> {status}")

    # Query total record count
    total_res = surreal_query("SELECT count() FROM learning GROUP ALL;")
    print(f"Total learning records in SurrealDB: {total_res}")


if __name__ == "__main__":
    main()
