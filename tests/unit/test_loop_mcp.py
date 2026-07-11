"""Unit tests for the Loop MCP server — one per tool, mocked at source (no live services)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.mcp.loop_mcp import (
    _http_error,
    _lit,
    event_publish,
    loop_health,
    loop_stats,
    proposals_append,
    proposals_query,
    queue_file,
    queue_list,
    queue_patch,
)


@pytest.mark.asyncio
async def test_queue_list() -> None:
    with patch(
        "cohezion.mcp.loop_mcp._safe_get",
        new=AsyncMock(
            return_value={"items": [{"id": "1", "status": "pending_review"}], "count": 1}
        ),
    ):
        result = await queue_list(status="pending_review")
    assert result == {"items": [{"id": "1", "status": "pending_review"}], "count": 1}


@pytest.mark.asyncio
async def test_queue_file() -> None:
    with patch(
        "cohezion.mcp.loop_mcp._safe_post",
        new=AsyncMock(return_value={"id": "abc", "status": "created"}),
    ):
        result = await queue_file({"type": "improvement", "title": "t"})
    assert result == {"id": "abc", "status": "created"}


@pytest.mark.asyncio
async def test_queue_patch() -> None:
    with patch(
        "cohezion.mcp.loop_mcp._safe_post",
        new=AsyncMock(return_value={"id": "abc", "status": "approved"}),
    ):
        result = await queue_patch("abc", status="approved")
    assert result == {"id": "abc", "status": "approved"}


@pytest.mark.asyncio
async def test_proposals_query() -> None:
    proposals = [
        {"id": "1", "verdict": "APPLY", "domain": "cache"},
        {"id": "2", "verdict": "IGNORE", "domain": "cache"},
    ]
    with patch("cohezion.mcp.loop_mcp._read_proposals", return_value=proposals):
        result = await proposals_query(verdict="APPLY")
    assert result == {"items": [{"id": "1", "verdict": "APPLY", "domain": "cache"}], "count": 1}


@pytest.mark.asyncio
async def test_proposals_append() -> None:
    with (
        patch("cohezion.mcp.loop_mcp._write_proposal") as mock_write,
        patch("cohezion.mcp.loop_mcp._read_proposals", return_value=[{"verdict": "APPLY"}]),
    ):
        result = await proposals_append({"verdict": "APPLY", "domain": "cache"})
    mock_write.assert_called_once_with({"verdict": "APPLY", "domain": "cache"})
    assert result == {"success": True, "count": 1}


@pytest.mark.asyncio
async def test_event_publish_escapes_injection() -> None:
    """event_publish must _lit-escape values so a quote cannot break out of the literal."""
    captured: dict[str, str] = {}
    attack = "evt'; DROP TABLE data_product_event; --"

    async def fake_sql(sql: str, *, hint: str) -> dict[str, object]:
        captured["sql"] = sql
        return {"result": [{"result": [], "status": "OK"}]}

    with patch("cohezion.mcp.loop_mcp._surreal_sql", new=fake_sql):
        result = await event_publish(attack, "loop", {"k": "v"})

    assert result == {"success": True, "event_type": attack, "table": "data_product_event"}
    # The attack value must appear ONLY inside a double-quoted SurrealQL literal (_lit),
    # never as bare single-quoted text that could terminate the literal and inject SQL.
    assert f"event_type: {_lit(attack)}" in captured["sql"]
    assert f"'{attack}'" not in captured["sql"]  # old vulnerable single-quote form is gone


@pytest.mark.asyncio
async def test_loop_stats() -> None:
    surreal_result = {
        "result": [
            {"result": [{"count": 3}]},
            {"result": [{"count": 5}]},
            {"result": [{"count": 0}]},
            {"result": [{"count": 1}]},
            {"result": [{"count": 2}]},
        ]
    }
    with (
        patch("cohezion.mcp.loop_mcp._surreal_sql", new=AsyncMock(return_value=surreal_result)),
        patch(
            "cohezion.mcp.loop_mcp._safe_get",
            new=AsyncMock(
                return_value={"items": [{"status": "pending_review"}, {"status": "done"}]}
            ),
        ),
    ):
        result = await loop_stats()
    assert result == {
        "compound_loop": 3,
        "agent_journey": 5,
        "yielded": 0,
        "spawned": 1,
        "automerge_log": 2,
        "work_queue_status_counts": {"pending_review": 1, "done": 1},
    }


@pytest.mark.asyncio
async def test_loop_health() -> None:
    with patch(
        "cohezion.mcp.loop_mcp._probe_service",
        new=AsyncMock(side_effect=["healthy", "unhealthy", "healthy"]),
    ):
        result = await loop_health()
    assert result == {
        "work_queue": "healthy",
        "inference": "unhealthy",
        "surrealdb": "healthy",
        "healthy": False,
    }


def test_http_error_is_actionable() -> None:
    """Errors must never be a bare status code — they carry the URL and an actionable hint."""
    err = _http_error(
        404,
        "Not Found",
        "http://localhost:8080/api/work-queue/stale-id",
        "If this 404s, the item_id is stale — call queue_list for current ids.",
    )
    assert err["error"] != "HTTP 404"  # not bare
    assert err["error"] == "HTTP 404 from http://localhost:8080/api/work-queue/stale-id"
    assert "queue_list" in err["hint"]  # names the tool to call next


def test_lit_escapes_quotes() -> None:
    """_lit wraps values in a JSON string literal, neutralizing SurrealQL injection."""
    assert _lit("a'b") == '"a\'b"'
    assert _lit('a"b') == '"a\\"b"'
