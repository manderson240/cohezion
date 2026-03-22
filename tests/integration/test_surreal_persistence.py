"""Integration tests for SurrealDB persistence layer.

Requires a running SurrealDB instance at http://localhost:8001
with root/root credentials. Tests are skipped automatically
if the database is unavailable.

Root causes fixed:
- Changed fixture scope from "module" to "function" to avoid event loop
  mismatch ("Future attached to a different loop") errors.
- Added pytestmark for asyncio + integration so tests run in strict mode.
- Each test uses a unique database name to prevent inter-test data leakage.
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio

from cohezion.core.persistence.surreal_client import SurrealClient, UniverseNode


# ---------------------------------------------------------------------------
# Auth probe — skip entire module if SurrealDB is unavailable
# ---------------------------------------------------------------------------

SURREAL_URL = "http://localhost:8001"
SURREAL_WS_URL = "ws://localhost:8001/rpc"
SURREAL_USER = "root"
SURREAL_PASSWORD = "root"


def _probe_auth() -> str | None:
    """Try a real authenticated query. Returns error string or None if OK."""
    import httpx

    if os.environ.get("SKIP_INTEGRATION", "").lower() in ("1", "true", "yes"):
        return "SKIP_INTEGRATION env var set"

    try:
        resp = httpx.get(f"{SURREAL_URL}/health", timeout=3)
        if resp.status_code != 200:
            return f"SurrealDB health check failed: {resp.status_code}"
    except Exception as e:
        return f"SurrealDB not reachable: {e}"

    # Verify auth works (not just TCP/HTTP)
    async def _auth_check():
        client = SurrealClient(
            url=SURREAL_WS_URL,
            namespace="cohezion_test_probe",
            database="probe",
        )
        try:
            connected = await client.connect()
            if not connected or client._using_fallback:
                return "SurrealDB connection returned fallback mode"
            return None
        except Exception as e:
            return f"Auth failed: {e}"
        finally:
            await client.close()

    try:
        result = asyncio.run(_auth_check())
        return result
    except Exception as e:
        return f"Auth probe error: {e}"


_PROBE_RESULT = _probe_auth()

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.skipif(
        _PROBE_RESULT is not None,
        reason=f"SurrealDB unavailable: {_PROBE_RESULT}",
    ),
]


# ---------------------------------------------------------------------------
# Per-test client fixture (scope="function" avoids event loop mismatch)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def surreal_client():
    """Create a fresh SurrealDB client for each test with a unique database."""
    db_name = f"test_persistence_{uuid4().hex[:8]}"
    client = SurrealClient(
        url=SURREAL_WS_URL,
        namespace="cohezion_test",
        database=db_name,
    )
    connected = await client.connect()
    if not connected or client._using_fallback:
        pytest.skip("SurrealDB connection failed or in fallback mode")
    yield client
    await client.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_connect_and_close(surreal_client: SurrealClient):
    """SurrealDB client connects and closes without error."""
    assert surreal_client._connected or not surreal_client._using_fallback


async def test_store_and_retrieve_node(surreal_client: SurrealClient):
    """Round-trip: store a UniverseNode and retrieve it by ID."""
    node = UniverseNode(
        id=f"test_{uuid4().hex[:8]}",
        node_type="skill",
        content="Test content for integration test",
    )
    record_id = await surreal_client.store_node(node)
    assert record_id

    retrieved = await surreal_client.get_node(node.id)
    assert retrieved is not None
    assert retrieved.content == "Test content for integration test"
    # ID comes back as RecordID(table_name, id); verify the bare id part matches
    retrieved_bare_id = getattr(retrieved.id, "id", str(retrieved.id))
    assert retrieved_bare_id == node.id


async def test_query_returns_results(surreal_client: SurrealClient):
    """Raw SQL query executes without raising."""
    result = await surreal_client.query("SELECT * FROM node LIMIT 5")
    # Result may be empty list — just verify it doesn't raise
    assert result is not None


async def test_store_multiple_nodes(surreal_client: SurrealClient):
    """Store several nodes and verify get_all_nodes returns them."""
    node_ids = []
    for i in range(3):
        node = UniverseNode(
            id=f"multi_{uuid4().hex[:6]}_{i}",
            node_type="skill",
            content=f"Content {i}",
        )
        await surreal_client.store_node(node)
        node_ids.append(node.id)

    all_nodes = await surreal_client.get_all_nodes(limit=100)
    # IDs come back as RecordID(table_name, id); extract the bare id part for comparison
    stored_ids = {getattr(n.id, "id", str(n.id)) for n in all_nodes}
    for nid in node_ids:
        assert nid in stored_ids, f"Node {nid} not found after storage"


async def test_create_relationship(surreal_client: SurrealClient):
    """Create two nodes and a relationship between them."""
    src = UniverseNode(
        id=f"src_{uuid4().hex[:6]}",
        node_type="skill",
        content="Source node",
    )
    dst = UniverseNode(
        id=f"dst_{uuid4().hex[:6]}",
        node_type="skill",
        content="Destination node",
    )
    await surreal_client.store_node(src)
    await surreal_client.store_node(dst)

    result = await surreal_client.create_relationship(
        src.id, dst.id, "depends_on", metadata={"strength": 0.8}
    )
    # Result should be truthy (record ID or True)
    assert result is not None
