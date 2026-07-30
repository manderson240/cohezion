#!/usr/bin/env python3
"""Initialize SurrealDB Schema for Full Capabilities:
1. HNSW Vector Index on 256-dim z_vector
2. Graph RELATE edges (learnings -> skills, agents -> tasks)
3. Live Query Event Stream table (agent_event)
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("surreal_init")

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "main"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()

SURQL_SCHEMA = """
-- 1. Vector Search Memory Table & HNSW Index
DEFINE TABLE memory SCHEMALESS;
DEFINE FIELD z_vector ON TABLE memory TYPE option<array<float>>;
DEFINE INDEX z_vector_hnsw ON TABLE memory FIELDS z_vector HNSW DIMENSION 256 DIST COSINE;

-- 2. Graph Relation Tables
DEFINE TABLE applies_to SCHEMALESS;
DEFINE TABLE executes SCHEMALESS;

-- 3. Live Event Stream Table for Real-time Subscriptions
DEFINE TABLE agent_event SCHEMALESS;

-- 4. Initial Graph Relations
UPSERT learning:L397 SET title = "Authenticated CIFS & 2-Tier Cascade Router", created_at = time::now();
UPSERT skill:local_inference_routing SET title = "Local Inference Routing Skill", created_at = time::now();
UPSERT skill:cifs_authenticated_storage_recovery SET title = "CIFS Storage Recovery Skill", created_at = time::now();

RELATE learning:L397->applies_to->skill:local_inference_routing SET confidence = 0.98, created_at = time::now();
RELATE learning:L397->applies_to->skill:cifs_authenticated_storage_recovery SET confidence = 0.95, created_at = time::now();
"""


def execute_surql(statement: str) -> bool:
    try:
        req = urllib.request.Request(
            SURREAL_URL,
            data=statement.encode(),
            headers={
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
                "Content-Type": "text/plain",
                "Authorization": f"Basic {SURREAL_AUTH}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            logger.info(f"SurrealDB Schema Init Result: {data}")
            return True
    except Exception as exc:
        logger.error(f"SurrealDB Schema Init Failed: {exc}")
        return False


def main():
    logger.info("Initializing SurrealDB Full Capabilities (Vectors + Graph RELATE + Live Query)...")
    success = execute_surql(SURQL_SCHEMA)
    if success:
        logger.info("✅ SurrealDB Full Capabilities Initialized Successfully!")
    else:
        logger.error("❌ SurrealDB Schema Initialization Encountered Errors.")


if __name__ == "__main__":
    main()
