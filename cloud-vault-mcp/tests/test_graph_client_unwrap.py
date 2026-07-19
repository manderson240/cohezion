"""Discriminating tests for GraphClient response unwrapping.

THE BUG (2026-07-19): `graph_stats` and `graph_bridges` both threw
`'str' object has no attribute 'get'`, so the vault's two connection-finding tools were
dead. Root cause was one missing type check:

    if data and isinstance(data, list) and "result" in data[0]:

When `data[0]` is a str, `"result" in data[0]` is a SUBSTRING test rather than a key
lookup. A string response therefore fell through, was returned as-is, and the caller's
`.get()` exploded. Same family as every other defect found that night: checking
truthiness or membership where TYPE was the thing that mattered.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_server.vault_graph.client import GraphClient  # noqa: E402


class _FakeDB:
    """Stands in for the SurrealDB async client, returning a canned payload."""

    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def signin(self, _):
        return None

    async def use(self, _ns, _db):
        return None

    async def query(self, _sql):
        return self.payload


def _client_returning(payload, monkeypatch) -> GraphClient:
    c = GraphClient()
    monkeypatch.setattr(c, "_make_connection", lambda: _FakeDB(payload))
    return c


@pytest.mark.asyncio
class TestUnwrap:
    async def test_wrapped_result_is_unwrapped(self, monkeypatch):
        c = _client_returning([{"result": [{"id": "neuron:1"}]}], monkeypatch)
        assert await c.query("SELECT 1") == [{"id": "neuron:1"}]

    async def test_bare_list_of_dicts_passes_through(self, monkeypatch):
        """Newer SDKs return rows directly, with no {"result": ...} envelope."""
        rows = [{"id": "neuron:1"}, {"id": "neuron:2"}]
        assert await _client_returning(rows, monkeypatch).query("SELECT 1") == rows

    async def test_string_response_does_not_crash_the_caller(self, monkeypatch):
        """THE REGRESSION TEST. A list-of-strings response must come back intact rather
        than being mistaken for an envelope. An impl using `"result" in data[0]` without
        the isinstance guard raises TypeError here (string indices must be integers)."""
        payload = ["some error string containing the word result"]
        assert await _client_returning(payload, monkeypatch).query("SELECT 1") == payload

    async def test_string_without_the_word_result(self, monkeypatch):
        payload = ["plain failure message"]
        assert await _client_returning(payload, monkeypatch).query("SELECT 1") == payload

    async def test_empty_response_is_empty_list(self, monkeypatch):
        assert await _client_returning([], monkeypatch).query("SELECT 1") == []
        assert await _client_returning(None, monkeypatch).query("SELECT 1") == []


@pytest.mark.asyncio
class TestStatsToolShape:
    """tool_graph_stats must survive a non-dict from the queries layer."""

    async def test_string_payload_reports_shape_instead_of_raising(self, monkeypatch):
        from mcp_server.vault_graph import queries, tools

        async def fake_stats(*_a, **_k):
            return "unexpected string payload"

        monkeypatch.setattr(queries, "stats", fake_stats)
        out = await tools.tool_graph_stats()
        assert isinstance(out, str)
        assert "str" in out  # names the actual type it received
        assert "unexpected string payload" in out  # and shows the payload, for diagnosis

    async def test_empty_dict_still_reports_cleanly(self, monkeypatch):
        from mcp_server.vault_graph import queries, tools

        async def fake_stats(*_a, **_k):
            return {}

        monkeypatch.setattr(queries, "stats", fake_stats)
        assert "Could not fetch" in await tools.tool_graph_stats()
