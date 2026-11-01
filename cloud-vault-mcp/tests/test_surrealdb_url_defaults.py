"""SurrealDB listens on :8001; GraphRAGQuery must actually use the URL it is given."""

import httpx
import pytest

from mcp_server.graphrag_helpers import batch_create_edges, check_document_exists, safe_create_edge
from mcp_server.graphrag_import import GraphRAGImporter
from mcp_server.graphrag_pattern_detector import PatternDetector
from mcp_server.graphrag_query import GraphRAGQuery


@pytest.mark.asyncio
async def test_graphrag_query_sends_to_configured_surrealdb_url():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=[{"result": []}, {"result": [{"id": "x"}]}])

    query = GraphRAGQuery(surrealdb_url="http://surreal.test:9123/")
    query.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await query.find_related("vault_memory:abc")
    await query.http_client.aclose()

    assert seen == ["http://surreal.test:9123/sql"]


def test_default_surrealdb_url_is_port_8001():
    assert GraphRAGQuery().surrealdb_url == "http://localhost:8001"


def _recording_client(
    seen: list[str], queries: list[str] | None = None
) -> httpx.AsyncClient:
    """Answer every query with one row, so existence checks pass and RELATE actually runs."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if queries is not None:
            queries.append(request.content.decode())
        row = {"id": "vault_memory:a"}
        return httpx.Response(200, json=[{"status": "OK", "result": [row]}])

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_semantic_and_hybrid_search_use_configured_url(monkeypatch):
    seen: list[str] = []
    query = GraphRAGQuery(surrealdb_url="http://surreal.test:9123/")
    query.http_client = _recording_client(seen)

    async def fake_embedding(_text: str) -> list[float]:
        return [0.1, 0.2]

    monkeypatch.setattr(query, "generate_embedding", fake_embedding)
    await query.semantic_search("q")
    await query.hybrid_search("q")
    await query.find_related("vault_memory:a")
    await query.http_client.aclose()

    assert seen
    assert set(seen) == {"http://surreal.test:9123/sql"}


@pytest.mark.asyncio
async def test_pattern_detector_posts_to_configured_url(tmp_path):
    seen: list[str] = []
    detector = PatternDetector(vault_path=tmp_path, surrealdb_url="http://surreal.test:9123/")
    detector.query_engine.http_client = _recording_client(seen)

    await detector.detect_patterns()
    await detector.suggest_patterns("vault_memory:abc")
    await detector.get_pattern_impact_summary()
    await detector.query_engine.http_client.aclose()

    # Three entry points run four queries; the failure mode was passing the URL string as the client.
    assert len(seen) >= 3
    assert set(seen) == {"http://surreal.test:9123/sql"}


@pytest.mark.asyncio
async def test_edge_helpers_pass_the_url_through():
    seen: list[str] = []
    queries: list[str] = []
    client = _recording_client(seen, queries)
    url = "http://surreal.test:9123/sql"

    await check_document_exists("vault_memory:a", client, url=url)
    await safe_create_edge("vault_memory:a", "informed_by", "vault_memory:b", None, client, url=url)
    await batch_create_edges(
        [{"source": "vault_memory:a", "type": "led_to", "target": "vault_memory:b"}],
        client,
        url=url,
    )
    await client.aclose()

    assert sum("RELATE" in q for q in queries) == 2
    assert set(seen) == {url}


@pytest.mark.asyncio
async def test_importer_creates_edges_on_configured_url(tmp_path):
    seen: list[str] = []
    importer = GraphRAGImporter(vault_path=tmp_path, surrealdb_url="http://surreal.test:9123/")
    queries: list[str] = []
    importer.http_client = _recording_client(seen, queries)

    await importer._create_edges_for_document("vault_memory:a", "See [[b]].")
    assert any("RELATE" in q for q in queries)
    await importer.http_client.aclose()

    assert seen
    assert set(seen) == {"http://surreal.test:9123/sql"}
