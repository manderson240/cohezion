"""A SurrealDB statement error arrives as HTTP 200 and must not reach callers as rows."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.graphrag_helpers import GraphRAGError
from mcp_server.graphrag_query import GraphRAGQuery


def _query_with_statements(statements: list[dict]) -> GraphRAGQuery:
    response = MagicMock()
    response.json.return_value = [{"status": "OK", "result": None}, *statements]
    query = GraphRAGQuery()
    query.http_client = AsyncMock()
    query.http_client.post.return_value = response
    query.generate_embedding = AsyncMock(return_value=[0.1, 0.2])
    return query


ERR = [{"status": "ERR", "result": "The table 'vault_memory' does not exist"}]
OK = [{"status": "OK", "result": [{"id": "vault_memory:a", "score": 0.9}]}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        lambda q: q.semantic_search("x"),
        lambda q: q.hybrid_search("x"),
        lambda q: q.find_related("vault_memory:a"),
    ],
    ids=["semantic_search", "hybrid_search", "find_related"],
)
async def test_statement_error_raises_with_the_database_message(call):
    with pytest.raises(GraphRAGError, match="does not exist"):
        await call(_query_with_statements(ERR))


@pytest.mark.asyncio
async def test_rows_still_reach_the_caller():
    assert await _query_with_statements(OK).semantic_search("x") == OK[0]["result"]
    assert (
        await _query_with_statements(OK).find_related("vault_memory:a")
        == OK[0]["result"][0]
    )
