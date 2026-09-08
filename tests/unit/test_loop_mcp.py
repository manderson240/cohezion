"""Unit tests for the Loop MCP server — one per tool, mocked at source (no live services)."""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.mcp.loop_mcp import (
    _http_error,
    _lit,
    _surreal_sql,
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


def _mock_httpx_returning(body: object) -> MagicMock:
    """Async-context-manager mock whose POST returns HTTP 200 with `body` as JSON."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = body
    client = MagicMock()
    client.post = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


@pytest.mark.asyncio
async def test_surreal_sql_surfaces_statement_error_inside_http_200() -> None:
    """SurrealDB reports SurrealQL failures as HTTP 200 + per-statement status ERR.

    A wrong implementation that checks only the HTTP code returns {"result": ...}
    here and certifies a write that never happened (bug 0b, 2026-08-11).
    """
    body = [{"status": "ERR", "result": "Found NONE for field `priority` ... Expected `int`"}]
    with patch("cohezion.mcp.loop_mcp._httpx_client", return_value=_mock_httpx_returning(body)):
        res = await _surreal_sql("CREATE data_product_event CONTENT {};", hint="h")
    assert "error" in res, f"statement-level ERR must surface as an error dict, got: {res}"
    assert "priority" in res["error"]  # the actual DB message reaches the caller
    assert res["hint"] == "h"


@pytest.mark.asyncio
async def test_surreal_sql_ok_statements_still_succeed() -> None:
    """Positive control: guards against 'fixed' by making everything an error."""
    body = [{"status": "OK", "result": [{"count": 3}]}]
    with patch("cohezion.mcp.loop_mcp._httpx_client", return_value=_mock_httpx_returning(body)):
        res = await _surreal_sql("SELECT count() FROM x GROUP ALL;", hint="h")
    assert "error" not in res
    assert res == {"result": body}


@pytest.mark.asyncio
async def test_surreal_sql_mixed_statements_fail_closed() -> None:
    """One ERR among OK statements must still surface as an error (fail-closed)."""
    body = [
        {"status": "OK", "result": []},
        {"status": "ERR", "result": "Expected `float` but found d'2026-08-11T16:25:56Z'"},
    ]
    with patch("cohezion.mcp.loop_mcp._httpx_client", return_value=_mock_httpx_returning(body)):
        res = await _surreal_sql("SELECT 1; CREATE bad;", hint="h")
    assert "error" in res


@pytest.mark.asyncio
async def test_event_publish_writes_schema_conformant_row() -> None:
    """The generated SurrealQL must satisfy the SCHEMAFULL data_product_event table.

    Schema requires `priority` (TYPE int, no default) and `timestamp` (TYPE float).
    The broken implementation omitted priority and wrote time::now() (a datetime) —
    both rejected by the DB while the tool still reported success (bug 0a).
    """
    captured: dict[str, str] = {}

    async def fake_sql(sql: str, *, hint: str) -> dict[str, object]:
        captured["sql"] = sql
        return {"result": [{"result": [], "status": "OK"}]}

    with patch("cohezion.mcp.loop_mcp._surreal_sql", new=fake_sql):
        result = await event_publish("custom", "unit-test", {"k": "v"})

    assert result.get("success") is True
    sql = captured["sql"]
    assert "priority: 0" in sql, f"required int `priority` missing from: {sql}"
    assert "time::now()" not in sql, "timestamp must be an epoch float, not a datetime"
    ts_match = re.search(r"timestamp: (\d+\.\d+)", sql)
    assert ts_match, f"timestamp must be a float literal, got: {sql}"
    assert abs(float(ts_match.group(1)) - time.time()) < 60.0  # sane wall-clock epoch


@pytest.mark.asyncio
async def test_event_publish_priority_passthrough() -> None:
    """An explicit priority must reach the SurrealQL as an int literal."""
    captured: dict[str, str] = {}

    async def fake_sql(sql: str, *, hint: str) -> dict[str, object]:
        captured["sql"] = sql
        return {"result": [{"result": [], "status": "OK"}]}

    with patch("cohezion.mcp.loop_mcp._surreal_sql", new=fake_sql):
        await event_publish("custom", "unit-test", {}, priority=2)

    assert "priority: 2" in captured["sql"]


def test_import_does_not_pull_kaggle_or_write_stdout() -> None:
    """`import cohezion.mcp.loop_mcp` must be stdout-silent AND kaggle-free.

    stdout is the stdio MCP JSON-RPC channel; the kaggle package conditionally
    prints a version warning to stdout at import (bug 0c), so the only safe fix
    is for it to not be in the import chain at all. The stdout==0 assertion
    alone would pass whenever the installed kaggle happens to be current —
    checking sys.modules is the discriminating half.
    """
    src = Path(__file__).resolve().parents[2] / "src"
    code = (
        f"import sys; sys.path.insert(0, {str(src)!r}); "
        "from cohezion.mcp import loop_mcp; "
        "kag = [m for m in sys.modules if m == 'kaggle' or m.startswith(('kaggle.', 'kagglehub', 'kagglesdk'))]; "
        "print('KAGGLE=' + ','.join(kag), file=sys.stderr); "
        "assert hasattr(loop_mcp, 'event_publish')"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, timeout=300, check=False
    )
    assert proc.returncode == 0, f"import failed: {proc.stderr[-400:]!r}"
    assert proc.stdout == b"", f"stdout must be empty, got {proc.stdout[:200]!r}"
    kag_line = [ln for ln in proc.stderr.decode().splitlines() if ln.startswith("KAGGLE=")]
    assert kag_line and kag_line[-1] == "KAGGLE=", f"kaggle modules imported: {kag_line}"
