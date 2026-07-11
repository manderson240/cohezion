"""Cohezion Loop MCP Server — expose the local compound-loop control surface over stdio.

A stdio FastMCP bridge that lets premier (cloud) reasoning models drive the local
Cohezion compound loop: manage the work queue, read/append ADA proposals, publish
events onto the datamesh backbone, and read loop statistics / service health.

Backends (all local, all resolved lazily):
    work-queue API   http://localhost:8080/api/work-queue
    inference router http://localhost:13305/api/v1/health
    SurrealDB /sql   http://127.0.0.1:8001/sql   (ns=cohezion, db=main)
    proposals log    ~/.cohezion/ada_proposals.jsonl

Environment:
    MCP_TRANSPORT   "stdio" or "http" (default: stdio)
    MCP_PORT        HTTP server port when transport=http (default: 8363)

Usage:
    uv run python -m cohezion.mcp.loop_mcp
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from fastmcp import FastMCP


logger = logging.getLogger("loop-mcp")

app = FastMCP("cohezion-loop")


# --------------------------------------------------------------------------- #
# Lazy config — nothing resolves at import time (stdio-silent).               #
# --------------------------------------------------------------------------- #
def _work_queue_url() -> str:
    """Return the local work-queue API base URL."""
    return "http://localhost:8080/api/work-queue"


def _surreal_url() -> str:
    """Return the local SurrealDB HTTP /sql endpoint."""
    return "http://127.0.0.1:8001/sql"


def _surreal_headers() -> dict[str, str]:
    """Return SurrealDB HTTP headers (ns/db/auth) — fleet defaults, matches event_consumer."""
    return {
        "surreal-ns": "cohezion",
        "surreal-db": "main",
        "Content-Type": "text/plain",
        "Authorization": "Basic cm9vdDpyb290",  # root:root — fleet default
    }


def _proposals_path() -> Path:
    """Return the path to the ADA proposals JSONL log."""
    return Path.home() / ".cohezion" / "ada_proposals.jsonl"


def _httpx_client() -> httpx.AsyncClient:
    """Create a short-lived async HTTP client with a generous timeout."""
    return httpx.AsyncClient(timeout=120.0)


def _lit(value: object) -> str:
    """Render a SurrealQL string literal, injection-safe via json.dumps.

    json.dumps escapes embedded quotes and backslashes, so untrusted values can
    never break out of the literal — the fix for the event_publish injection
    flagged in review 03 (mirrors compound_persist._lit).

    Args:
        value: Any value; coerced to str then JSON-escaped.
    """
    return json.dumps(str(value))


def _http_error(status_code: int, text: str, url: str, hint: str) -> dict[str, Any]:
    """Build an actionable error dict for a failed HTTP call.

    Never returns a bare status code — always pairs it with the target URL and a
    hint naming valid values and/or the tool to call next.

    Args:
        status_code: HTTP status code received.
        text: Response body (already truncated by the caller).
        url: The URL that was called.
        hint: Actionable next-step guidance for the caller.
    """
    return {
        "error": f"HTTP {status_code} from {url}",
        "detail": text,
        "hint": hint,
    }


# --------------------------------------------------------------------------- #
# Transport helpers                                                           #
# --------------------------------------------------------------------------- #
async def _safe_get(url: str, *, hint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """GET JSON from url, returning the parsed body or an actionable error dict.

    Args:
        url: Endpoint to GET.
        hint: Actionable next-step guidance included in any error dict.
        params: Optional query-string parameters.
    """
    async with _httpx_client() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return _http_error(exc.response.status_code, exc.response.text[:400], url, hint)
        except Exception as exc:  # pragma: no cover - real network failures
            return {"error": f"Cannot reach {url}: {exc}", "hint": hint}


async def _safe_post(url: str, payload: dict[str, Any], *, hint: str) -> dict[str, Any]:
    """POST JSON to url, returning the parsed body or an actionable error dict.

    Args:
        url: Endpoint to POST to.
        payload: JSON body to send.
        hint: Actionable next-step guidance included in any error dict.
    """
    async with _httpx_client() as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return _http_error(exc.response.status_code, exc.response.text[:400], url, hint)
        except Exception as exc:  # pragma: no cover - real network failures
            return {"error": f"Cannot reach {url}: {exc}", "hint": hint}


async def _surreal_sql(sql: str, *, hint: str) -> dict[str, Any]:
    """Execute SurrealQL against the local SurrealDB and return its result.

    On success returns {"result": [<one entry per statement>]}; on failure returns
    an actionable error dict. Values in `sql` MUST already be escaped via _lit.

    Args:
        sql: SurrealQL statement(s) to execute.
        hint: Actionable next-step guidance included in any error dict.
    """
    url = _surreal_url()
    async with _httpx_client() as client:
        try:
            resp = await client.post(url, content=sql, headers=_surreal_headers())
            resp.raise_for_status()
            return {"result": resp.json()}
        except httpx.HTTPStatusError as exc:
            return _http_error(exc.response.status_code, exc.response.text[:400], url, hint)
        except Exception as exc:  # pragma: no cover - real network failures
            return {"error": f"Cannot reach SurrealDB at {url}: {exc}", "hint": hint}


async def _probe_service(url: str) -> str:
    """Return "healthy" if a GET to url returns 2xx within 5s, else "unhealthy".

    Args:
        url: Health/liveness endpoint to probe.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        return "healthy"
    except Exception:  # pragma: no cover - probing is best-effort
        return "unhealthy"


# --------------------------------------------------------------------------- #
# Proposals JSONL helpers                                                     #
# --------------------------------------------------------------------------- #
def _read_proposals() -> list[dict[str, Any]]:
    """Read all proposal objects from the JSONL log, skipping malformed lines."""
    path = _proposals_path()
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("skipping malformed proposal line")
            continue
        if isinstance(obj, dict):
            items.append(obj)
    return items


def _write_proposal(entry: dict[str, Any]) -> None:
    """Append one proposal object to the JSONL log, creating the dir if needed.

    Args:
        entry: The proposal object to append.
    """
    path = _proposals_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


# --------------------------------------------------------------------------- #
# MCP tools                                                                   #
# --------------------------------------------------------------------------- #
@app.tool()
async def queue_list(status: str | None = None, relevance: str | None = None) -> dict[str, Any]:
    """List work-queue items, optionally filtered by status and/or relevance.

    Args:
        status: Filter by item status. Valid: pending_review, approved, rejected,
            in_progress, done.
        relevance: Filter by relevance. Valid: APPLY, IGNORE.
    """
    params: dict[str, str] = {}
    if status:
        params["status"] = status
    if relevance:
        params["relevance"] = relevance
    return await _safe_get(
        _work_queue_url(),
        params=params or None,
        hint="If this fails, run loop_health to confirm the work-queue API (:8080) is up.",
    )


@app.tool()
async def queue_file(item: dict[str, Any]) -> dict[str, Any]:
    """File a new work-queue item.

    Args:
        item: The work item to create, e.g. {"type": "improvement", "title": ...,
            "description": ..., "relevance": "APPLY", "domain": ...}.
    """
    if not isinstance(item, dict) or not item:
        return {
            "error": "item must be a non-empty object",
            "hint": "Pass fields like {'type':'improvement','title':...,'description':...}.",
        }
    return await _safe_post(
        _work_queue_url(),
        item,
        hint="If this fails, run loop_health to confirm the work-queue API (:8080) is up.",
    )


@app.tool()
async def queue_patch(
    item_id: str, status: str | None = None, notes: str | None = None
) -> dict[str, Any]:
    """Update a work-queue item's status and/or notes.

    Args:
        item_id: The id of the item to update. Use queue_list to find valid ids.
        status: New status. Valid: pending_review, approved, rejected, in_progress, done.
        notes: Free-text notes to set on the item.
    """
    if not item_id:
        return {
            "error": "item_id is required",
            "hint": "Call queue_list first to obtain a valid item_id.",
        }
    payload: dict[str, Any] = {}
    if status is not None:
        payload["status"] = status
    if notes is not None:
        payload["notes"] = notes
    if not payload:
        return {
            "error": "nothing to update",
            "hint": "Pass status (pending_review|approved|rejected|in_progress|done) or notes.",
        }
    return await _safe_post(
        f"{_work_queue_url()}/{item_id}",
        payload,
        hint="If this 404s, the item_id is stale — call queue_list for current ids.",
    )


@app.tool()
async def proposals_query(verdict: str | None = None, domain: str | None = None) -> dict[str, Any]:
    """Query ADA proposals from the local JSONL log.

    Args:
        verdict: Filter by proposal verdict (e.g. APPLY, IGNORE).
        domain: Filter by proposal domain.
    """
    items = _read_proposals()
    if verdict:
        items = [i for i in items if i.get("verdict") == verdict]
    if domain:
        items = [i for i in items if i.get("domain") == domain]
    return {"items": items, "count": len(items)}


@app.tool()
async def proposals_append(entry: dict[str, Any]) -> dict[str, Any]:
    """Append an ADA proposal to the local JSONL log.

    Args:
        entry: The proposal object to append, e.g. {"verdict": "APPLY",
            "domain": ..., "summary": ...}.
    """
    if not isinstance(entry, dict) or not entry:
        return {
            "error": "entry must be a non-empty object",
            "hint": "Pass a JSON object, e.g. {'verdict':'APPLY','domain':...,'summary':...}.",
        }
    try:
        _write_proposal(entry)
    except OSError as exc:
        return {
            "error": f"Cannot write proposals log: {exc}",
            "hint": f"Check write permission on {_proposals_path().parent}.",
        }
    return {"success": True, "count": len(_read_proposals())}


@app.tool()
async def event_publish(event_type: str, source: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Publish an event onto the datamesh backbone (SurrealDB data_product_event).

    The event is consumed by the datamesh EventConsumer. Values are escaped via
    _lit so the SurrealQL cannot be injected.

    Args:
        event_type: Event type, e.g. data_product_quality_alert, domain_health_degraded.
        source: Source identifier for the event.
        payload: Arbitrary JSON payload; stored as a JSON string.
    """
    if not event_type or not source:
        return {
            "error": "event_type and source are required",
            "hint": "Provide both, e.g. event_publish('domain_health_degraded', 'loop', {...}).",
        }
    sql = (
        "CREATE data_product_event CONTENT { "
        f"event_type: {_lit(event_type)}, "
        f"source: {_lit(source)}, "
        f"payload: {_lit(json.dumps(payload, sort_keys=True))}, "
        "timestamp: time::now() };"
    )
    res = await _surreal_sql(
        sql,
        hint="If this fails, run loop_health to confirm SurrealDB (:8001) is up.",
    )
    if "error" in res:
        return res
    return {"success": True, "event_type": event_type, "table": "data_product_event"}


@app.tool()
async def loop_stats() -> dict[str, Any]:
    """Report compound-loop table counts (SurrealDB) and work-queue status counts.

    Returns counts for compound_loop, agent_journey, yielded, spawned, and
    automerge_log, plus a per-status breakdown of the work queue.
    """
    tables = ["compound_loop", "agent_journey", "yielded", "spawned", "automerge_log"]
    sql = "".join(f"SELECT count() AS count FROM {t} GROUP ALL;" for t in tables)
    res = await _surreal_sql(
        sql,
        hint="If this fails, run loop_health to confirm SurrealDB (:8001) is up.",
    )
    if "error" in res:
        return res

    raw = res.get("result") or []
    counts: dict[str, int] = {}
    for table, stmt in zip(tables, raw):
        rows = stmt.get("result") or [] if isinstance(stmt, dict) else []
        counts[table] = int(rows[0].get("count", 0)) if rows else 0

    queue = await _safe_get(
        _work_queue_url(),
        hint="If this fails, run loop_health to confirm the work-queue API (:8080) is up.",
    )
    status_counts: dict[str, int] = {}
    if isinstance(queue, dict) and "error" not in queue:
        for item in queue.get("items", []):
            key = str(item.get("status", "unknown"))
            status_counts[key] = status_counts.get(key, 0) + 1

    return {**counts, "work_queue_status_counts": status_counts}


@app.tool()
async def loop_health() -> dict[str, Any]:
    """Probe the loop's backing services and report per-service health.

    Probes the work-queue API (:8080), the inference router (:13305), and
    SurrealDB (:8001). Returns "healthy"/"unhealthy" per service plus an overall
    `healthy` boolean.
    """
    services = {
        "work_queue": "http://localhost:8080/api/work-queue",
        "inference": "http://localhost:13305/api/v1/health",
        "surrealdb": "http://127.0.0.1:8001/version",
    }
    results = await asyncio.gather(*[_probe_service(u) for u in services.values()])
    health: dict[str, Any] = dict(zip(services, results))
    health["healthy"] = all(v == "healthy" for v in results)
    return health


def main() -> None:
    """Run the Loop MCP server over the configured transport."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    logger.info("Loop MCP server starting (transport=%s)", transport)
    if transport == "stdio":
        app.run(transport="stdio")
    else:
        port = int(os.getenv("MCP_PORT", "8363"))
        app.run(host="0.0.0.0", port=port, transport="http")


if __name__ == "__main__":
    main()
