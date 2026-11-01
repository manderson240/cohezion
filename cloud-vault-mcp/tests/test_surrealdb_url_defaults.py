"""SurrealDB listens on :8001; GraphRAGQuery must actually use the URL it is given."""

import httpx
import pytest

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
