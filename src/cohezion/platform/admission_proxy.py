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

import json
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from cohezion.platform.admission_gate import (
    DEFAULT_LISTEN_PORT,
    AdmissionGate,
    audit_bypass_paths,
    extract_model_name,
)


logger = logging.getLogger(__name__)

# JSON bodies above this size are forwarded without model-hunting: no lemonade
# load-triggering request carries a model key in a multi-MB JSON payload, and parsing
# one wholesale on the hot path is pure memory/latency cost (review 2026-09-01, F4).
_MAX_PARSE_BYTES = 1_000_000

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
                    "floor_gb": active_gate.config.floor_gb,
                    "enforce": active_gate.config.enforce,
                    "upstream_base": active_gate.config.upstream_base,
                },
                "counters": dict(counters),
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
        model = None
        # PATCH included defensively; lemonade loads via POST today, but that is the
        # router's convention, not a contract (adversarial review 2026-09-01, F8).
        if body and request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("multipart/form-data"):
                # Audio routes (transcription: Whisper, 1.6 GB) carry `model` as a form
                # field — JSON-only parsing would let those loads through ungated. Size
                # is no reason to skip: the body is already buffered and field
                # extraction is cheap even from a large upload.
                try:
                    form = await request.form()
                    value = form.get("model") or form.get("model_name")
                    model = value if isinstance(value, str) and value else None
                except Exception:
                    model = None
            elif len(body) <= _MAX_PARSE_BYTES:
                try:
                    model = extract_model_name(json.loads(body))
                except (ValueError, UnicodeDecodeError):
                    model = None  # non-JSON bodies name no model
            # else: multi-MB non-multipart body — don't json-parse wholesale to hunt a
            # "model" key; no lemonade load path ships one, so forward ungated.

        # decide() does sync I/O (health fetch, /proc) — run off the event loop so one
        # blocked health call cannot stall every in-flight stream.
        decision = await run_in_threadpool(active_gate.decide, model)
        if decision.would_refuse:
            counters["shadow_refusals"] += 1
        if not decision.allow:
            counters["refused"] += 1
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "type": "admission_refused",
                        "message": decision.reason,
                        "model": decision.model,
                    }
                },
            )

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
            # A dead/mid-restart upstream is a clean 502, not a traceback-500.
            return JSONResponse(
                status_code=502,
                content={"error": {"type": "upstream_unreachable", "message": str(exc)}},
            )
        counters["forwarded"] += 1
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
    app = build_app(gate)
    logger.info(
        "admission gate listening on :%d -> upstream %s (enforce=%s, floor=%.1fGB)",
        port,
        gate.config.upstream_base,
        gate.config.enforce,
        gate.config.floor_gb,
    )
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
