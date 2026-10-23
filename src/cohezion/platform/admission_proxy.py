"""ASGI proxy wrapping :class:`AdmissionGate` — the deployable half of the lemond gate.

Sits on :13305 (the port every client already uses — invariant N1 preserved) and forwards
to lemond on an internal port. POST bodies naming a model are gated BEFORE forwarding;
everything else passes through untouched, streaming in both directions.

Refusals return 503 with a JSON body naming the reason — a well-behaved client (the
triune orchestrator, executors) treats that like any other capacity error and falls back
to a smaller model via its existing cascade. GET /admission/status exposes the live
config, decision counters, and the bypass-path audit for telemetry.

Run: ``python -m cohezion.platform.admission_proxy`` (see
scripts/cohezion-admission-gate.service and docs/ops/admission-gate-cutover.md).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import pathlib
import re
from collections.abc import Callable
from contextlib import asynccontextmanager
from functools import partial

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from cohezion.platform.admission_gate import (
    CGROUP_HIGH_FRACTION,
    DEFAULT_LISTEN_PORT,
    GTT_BASELINE_GB,
    GTT_HOST_SHARE,
    GTT_TOTAL_FRACTION,
    AdmissionDecision,
    AdmissionGate,
    WalkTruncatedError,
    audit_bypass_paths,
    models_named,
    request_options,
)


logger = logging.getLogger(__name__)

RETRY_AFTER_S = 15  # refused clients back off instead of retrying in a tight loop
# Writing a model's saved options changes its placement before the catalog shows it.
_OPTIONS_ROUTE = re.compile(r"(?:api/)?v[01]/models/(.+)/options", re.IGNORECASE)
# Writes that can change ANY model's recipe, size or default backend: (re-)registration,
# pull (register-then-install), backend installs, and lemond's config and model-sync writes
# (routes from lemonade.md and the lemond binary; pin, telemetry and aliases change neither).
_CONFIG_WRITE = re.compile(
    r"(?:api/)?v[01]/(?:models/register|pull|install|uninstall)"
    r"|internal/(?:set|config(?:/.*)?|models/sync)",
    re.IGNORECASE,
)


def unnamed_tool_calls(parsed: object) -> bool | None:
    """For MCP ``tools/call`` requests that name no model (lemonade then picks and may load
    one itself): None when there are none, else whether any of them allows a download."""
    calls = [
        c
        for c in (parsed if isinstance(parsed, list) else [parsed])
        if isinstance(c, dict) and c.get("method") == "tools/call" and not models_named(c)
    ]
    if not calls:
        return None
    allow = False
    for call in calls:
        params = call.get("params")
        args = params.get("arguments") if isinstance(params, dict) else None
        allow = allow or (isinstance(args, dict) and bool(args.get("allow_download")))
    return allow


def _refused(decision: AdmissionDecision) -> JSONResponse:
    """The refusal response: 503 + Retry-After, or the decision's non-retryable status."""
    return JSONResponse(
        status_code=decision.status,
        headers={"Retry-After": str(RETRY_AFTER_S)} if decision.status == 503 else None,
        content={
            "error": {
                "type": "admission_refused",
                "message": decision.reason,
                "model": decision.model,
            }
        },
    )


def client_identity(
    client_port: int, server_port: int, proc: pathlib.Path = pathlib.Path("/proc")
) -> str:
    """'<systemd unit> pid=<pid>' for the local process on the far end of a connection.

    Attribution is for logs only: any failure reports 'unknown', never fails a request.

    Maps the client's TCP source port to its socket inode via /proc/net/tcp{,6}, then the
    inode to the process holding it. The gate runs as the same user as the cohezion services,
    so their fds are readable; anything else reports 'unknown'.
    """
    try:
        return _client_identity(client_port, server_port, proc)
    except Exception:
        return "unknown"


def _client_identity(client_port: int, server_port: int, proc: pathlib.Path) -> str:
    inodes: set[str] = set()
    for table in ("net/tcp", "net/tcp6"):
        try:
            lines = (proc / table).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            f = line.split()
            if (
                len(f) > 9
                and int(f[1].rsplit(":", 1)[1], 16) == client_port
                and int(f[2].rsplit(":", 1)[1], 16) == server_port
            ):
                inodes.add(f"socket:[{f[9]}]")
    if not inodes:
        return "unknown"
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            for fd in (pid_dir / "fd").iterdir():
                if os.readlink(fd) in inodes:
                    unit = (pid_dir / "cgroup").read_text().strip().rsplit("/", 1)[-1]
                    return f"{unit} pid={pid_dir.name}"
        except OSError:
            continue
    return "unknown"


# Hop-by-hop headers must not be forwarded verbatim (RFC 9110 §7.6.1).
_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
        # Ask upstream for identity encoding: the non-streaming fallback serves
        # httpx-DECODED bytes, which under a relayed content-encoding header would be
        # corrupt. On a loopback proxy, forgoing gzip costs nothing and removes the
        # decoded-bytes/encoded-header mismatch class entirely.
        "accept-encoding",
        "content-encoding",
    }
)


def build_app(
    gate: AdmissionGate | None = None,
    *,
    client: httpx.AsyncClient | None = None,
    background_catalog: bool = False,
) -> FastAPI:
    """Assemble the proxy app. ``client`` is injectable so tests supply a MockTransport."""
    # A distinct, annotated local so the route closures capture a name pyright can
    # narrow (a reassigned parameter loses narrowing inside nested functions).
    active_gate: AdmissionGate = gate if gate is not None else AdmissionGate()
    upstream = active_gate.config.upstream_base.rstrip("/")
    # read=None is deliberate: streamed completions run for minutes; connect/write/pool
    # stay bounded so a dead upstream fails fast instead of hanging the client.
    _timeout = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)
    http = client if client is not None else httpx.AsyncClient(base_url=upstream, timeout=_timeout)

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        if background_catalog:
            active_gate.start_refresher()
        yield
        await http.aclose()  # release pooled upstream connections on graceful shutdown

    app = FastAPI(
        title="cohezion-admission-gate", docs_url=None, redoc_url=None, lifespan=_lifespan
    )
    counters = {"forwarded": 0, "refused": 0, "shadow_refusals": 0}

    @app.get("/admission/status")
    async def status() -> JSONResponse:
        # The audit is sync HTTP: run it off-loop, and aim it at the UPSTREAM — with the
        # default base it would call the proxy's own port from inside the event loop and
        # deadlock on itself (adversarial review 2026-09-01, F1).
        bypass = await run_in_threadpool(
            audit_bypass_paths, base_url=active_gate.config.upstream_base
        )
        return JSONResponse(
            {
                "config": {
                    "cgroup_high_fraction": CGROUP_HIGH_FRACTION,
                    "enforce": active_gate.config.enforce,
                    "gguf_backend": active_gate.config.gguf_backend,
                    "backend_overrides": dict(active_gate.config.backend_overrides),
                    "mem_available_floor_gb": active_gate.config.mem_available_floor_gb,
                    "gtt_total_fraction": GTT_TOTAL_FRACTION,
                    "gtt_host_share": GTT_HOST_SHARE,
                    "gtt_baseline_gb": GTT_BASELINE_GB,
                    "upstream_base": active_gate.config.upstream_base,
                },
                "counters": dict(counters),
                "cgroup_readable": active_gate.cgroup_readable,
                "catalog_age_s": active_gate.catalog_age_s(),
                "bypass_paths": bypass,
            }
        )

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    )
    async def proxy(path: str, request: Request) -> Response:
        if path.startswith("admission/"):
            # Gate-control surface is never proxied: a POST here must not leak upstream.
            return JSONResponse(status_code=404, content={"error": {"type": "not_found"}})

        body = await request.body()
        # Every model the request names: query string, multipart fields, and any JSON body
        # whatever its size (a vision or audio chat is easily > 1 MB and still loads).
        names = [v for k, v in request.query_params.multi_items() if "model" in k.lower() and v]
        # Load options the request sets for itself (lemonade's /v1/load lets a body
        # llamacpp_backend / ctx_size override the saved recipe options).
        options: dict[str, object] = {}
        parsed: object = None
        if body and request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "").lower()
            if content_type.startswith("multipart/form-data"):
                try:
                    form = await request.form()
                    fields = [(k, v) for k, v in form.multi_items() if isinstance(v, str)]
                    names += [v for k, v in fields if "model" in k.lower() and v]
                    parsed = dict(fields)
                    options = request_options(parsed)
                except Exception as exc:
                    logger.warning("admission gate: unparseable multipart body: %s", exc)
            else:
                try:
                    with contextlib.suppress(ValueError, UnicodeDecodeError):  # not JSON
                        parsed = await run_in_threadpool(json.loads, body)
                        names += await run_in_threadpool(models_named, parsed)
                        options = request_options(parsed)
                except WalkTruncatedError as exc:  # A9: a model named past the walk limit
                    unread = active_gate.refuse(f"request body not fully readable: {exc}")
                    if not unread.allow:
                        counters["refused"] += 1
                        return _refused(unread)
                    counters["shadow_refusals"] += 1

        # Config writes change placement before the catalog shows them: uncertain until a
        # catalog read that starts after lemonade has answered the write (stamped twice).
        invalidations: list[str | None] = []
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            stripped = path.strip("/")
            options_write = _OPTIONS_ROUTE.fullmatch(stripped)
            if options_write:
                invalidations.append(options_write.group(1))
            if _CONFIG_WRITE.fullmatch(stripped):
                invalidations.append(None)
        if isinstance(parsed, dict) and parsed.get("save_options") not in (None, False, "", 0):
            invalidations += names
        for target in invalidations:
            active_gate.invalidate(target)

        decisions: list[tuple[str | None, Callable[[], AdmissionDecision]]] = [
            (name, partial(active_gate.decide, name, path, options))
            for name in dict.fromkeys(names)
        ]
        allow_download = unnamed_tool_calls(parsed)
        if allow_download is not None:
            decisions.append(
                (None, partial(active_gate.decide_unnamed, path, allow_download=allow_download))
            )

        # decide() reads health and /proc -- keep it off the event loop.
        admitted: list[str] = []
        refusal: AdmissionDecision | None = None
        for asked, decide in decisions:
            decision = await run_in_threadpool(decide)
            name = decision.model or asked
            if decision.would_refuse:
                counters["shadow_refusals"] += 1
            new_load = decision.reason.startswith("fits")
            if (not decision.allow or new_load) and request.client is not None:
                server_port = (request.scope.get("server") or (None, 0))[1] or 0
                who = await run_in_threadpool(client_identity, request.client.port, server_port)
                logger.info(
                    "admission %s client=%s model=%s path=/%s: %s",
                    "ADMIT" if decision.allow else "REFUSE",
                    who,
                    name,
                    path,
                    decision.reason,
                )
            if not decision.allow:
                refusal = decision
                break
            if new_load and name:
                admitted.append(name)
        if refusal is not None:
            for name in admitted:
                active_gate.release(name)
            counters["refused"] += 1
            return _refused(refusal)

        headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_HEADERS}
        # Pin identity explicitly: with the header merely absent, httpx injects its own
        # 'gzip, deflate', resurrecting the decoded-bytes/encoded-header mismatch.
        headers["accept-encoding"] = "identity"
        upstream_req = http.build_request(
            request.method,
            f"/{path}",
            params=request.query_params,
            headers=headers,
            content=body if body else None,
        )
        try:
            upstream_resp = await http.send(upstream_req, stream=True)
        except httpx.HTTPError as exc:
            for target in invalidations:
                active_gate.invalidate(target)
            for name in admitted:  # nothing loaded: free the reservation now, not in 180 s
                active_gate.release(name)
            # A dead/mid-restart upstream is a clean 502, not a traceback-500.
            return JSONResponse(
                status_code=502,
                content={"error": {"type": "upstream_unreachable", "message": str(exc)}},
            )
        for target in invalidations:  # A8: outlive any refresh that overlapped the write
            active_gate.invalidate(target)
        counters["forwarded"] += 1
        if upstream_resp.status_code >= 400:
            for name in admitted:
                active_gate.release(name)
        resp_headers = {
            k: v for k, v in upstream_resp.headers.items() if k.lower() not in _HOP_HEADERS
        }
        if upstream_resp.is_stream_consumed or upstream_resp.is_closed:
            # Content already materialised (MockTransport in tests, cached bodies) —
            # streaming an already-read response raises StreamConsumed.
            return Response(
                content=upstream_resp.content,
                status_code=upstream_resp.status_code,
                headers=resp_headers,
                media_type=upstream_resp.headers.get("content-type"),
            )
        return StreamingResponse(
            upstream_resp.aiter_raw(),
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            # Close the upstream response when streaming ends OR the client
            # disconnects mid-stream — otherwise every abandoned generation leaks a
            # pooled connection until the pool exhausts under lemond's slow streams.
            background=BackgroundTask(upstream_resp.aclose),
            media_type=upstream_resp.headers.get("content-type"),
        )

    return app


def main() -> int:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("COHEZION_ADMISSION_PORT", str(DEFAULT_LISTEN_PORT)))
    gate = AdmissionGate()
    app = build_app(gate, background_catalog=True)
    logger.info(
        "admission gate listening on :%d -> upstream %s (enforce=%s)",
        port,
        gate.config.upstream_base,
        gate.config.enforce,
    )
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
