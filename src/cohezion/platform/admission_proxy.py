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

import asyncio
import contextlib
import json
import logging
import os
import pathlib
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from cohezion.platform.admission_gate import (
    CGROUP_HIGH_FRACTION,
    DEFAULT_LISTEN_PORT,
    AdmissionDecision,
    AdmissionGate,
    audit_bypass_paths,
    has_backend_override,
    is_load_path,
    models_named,
)


logger = logging.getLogger(__name__)

RETRY_AFTER_S = 15  # refused clients back off instead of retrying in a tight loop
# Under a held GPU lease a refused GPU-placed request WAITS (displaced fleet work must wait
# or fall back, not fail), polling the lease, then gets a 503 only when the hold expires.
LEASE_HOLD_S_DEFAULT = 120.0
LEASE_POLL_S = 1.0
_CPU_FALLBACK_ROUTES = frozenset({"v1/load", "api/v1/load"})
_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def cpu_fallback_body(
    gate: AdmissionGate, path: str, parsed: object, name: str, overrides: object = None
) -> bytes | None:
    """The load body rewritten to run on the CPU, or None when fallback does not apply.

    Only an explicit load (lemonade honours ``*_backend`` on load routes only) of a llamacpp
    (GGUF) model whose request (body, query string, form: ``overrides``) sets no backend
    override of its own. ``save_options`` is forced off: the CPU placement is for this lease
    only and must not persist as a per-model cpu pin in lemonade's recipe options.
    """
    if path.strip("/").lower() not in _CPU_FALLBACK_ROUTES or not isinstance(parsed, dict):
        return None
    if gate.recipe_of(name) != "llamacpp" or has_backend_override([parsed, overrides]):
        return None
    return json.dumps({**parsed, "llamacpp_backend": "cpu", "save_options": False}).encode()


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
    lease_hold_s: float | None = None,
    lease_poll_s: float = LEASE_POLL_S,
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
    hold_s = (
        lease_hold_s
        if lease_hold_s is not None
        else float(os.environ.get("COHEZION_GPU_LEASE_HOLD_S", str(LEASE_HOLD_S_DEFAULT)))
    )
    counters = {"forwarded": 0, "refused": 0, "shadow_refusals": 0}
    lease_counters = {"held_requests": 0, "refused": 0, "cpu_fallbacks": 0, "abandoned": 0}

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
                    "upstream_base": active_gate.config.upstream_base,
                },
                "counters": dict(counters),
                "cgroup_readable": active_gate.cgroup_readable,
                "catalog_age_s": active_gate.catalog_age_s(),
                "bypass_paths": bypass,
                "gpu_lease": await run_in_threadpool(active_gate.lease_status),
                "gpu_lease_counters": dict(lease_counters),
                "reserved": await run_in_threadpool(active_gate.reserved_models),
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
        # Every key the request carries outside a JSON body: a *_backend/*_args override in
        # the query string or a multipart field counts the same as one in the body.
        side_fields: dict[str, list[str]] = {}
        for k, v in request.query_params.multi_items():
            side_fields.setdefault(k, []).append(v)
        parsed: object = None
        if body and request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "").lower()
            if content_type.startswith("multipart/form-data"):
                try:
                    form = await request.form()
                    for k, v in form.multi_items():
                        if isinstance(v, str):
                            side_fields.setdefault(k, []).append(v)
                    names += [
                        v
                        for k, v in form.multi_items()
                        if "model" in k.lower() and isinstance(v, str) and v
                    ]
                except Exception as exc:
                    logger.warning("admission gate: unparseable multipart body: %s", exc)
            else:
                with contextlib.suppress(ValueError, UnicodeDecodeError):  # not JSON: no model
                    parsed = await run_in_threadpool(json.loads, body)
                    names += models_named(parsed)
        names = list(dict.fromkeys(names))

        async def run_gate(
            lease_exempt: str | None = None, gate_body: object = None
        ) -> tuple[AdmissionDecision | None, list[str]]:
            """(refusal or None, names admitted as new loads). decide() reads health and
            /proc, so it runs off the event loop."""
            admitted: list[str] = []
            checks: list[str | None] = list(names)
            # An unnamed write to a load-capable path is checked once: a held lease
            # refuses it (with no lease decide() forwards it as before).
            if (
                not checks
                and request.method not in _READ_METHODS
                and is_load_path(path)
                and active_gate.gpu_lease_held()
            ):
                checks = [None]
            for name in checks:
                decision = await run_in_threadpool(
                    lambda n=name: active_gate.decide(
                        n,
                        path,
                        method=request.method,
                        body=[parsed if gate_body is None else gate_body, side_fields],
                        lease_exempt=lease_exempt,
                    )
                )
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
                    for n in admitted:
                        active_gate.release(n)
                    return decision, []
                if new_load and name:
                    admitted.append(name)
            return None, admitted

        loop = asyncio.get_running_loop()
        deadline = loop.time() + hold_s
        refusal, admitted = await run_gate()
        held_once = False
        while refusal is not None and refusal.kind == "gpu_lease":
            fallback = cpu_fallback_body(
                active_gate, path, parsed, refusal.model or "", side_fields
            )
            if fallback is not None:
                # Fall back immediately: holding a load for a multi-hour lease only ends in
                # a 503. The rewritten load still faces the full-footprint cgroup check and
                # the lease's memory bound; only the rewritten model is lease-exempt.
                fb_refusal, fb_admitted = await run_gate(
                    lease_exempt=refusal.model, gate_body=json.loads(fallback)
                )
                if fb_refusal is None:
                    refusal, admitted, body = None, fb_admitted, fallback
                    lease_counters["cpu_fallbacks"] += 1
                    logger.info("admission CPU fallback under GPU lease: /%s", path)
                    break
                if fb_refusal.kind != "gpu_lease":  # e.g. cgroup headroom: answer now
                    refusal = fb_refusal
                    break
            if loop.time() >= deadline:
                break
            if not held_once:
                held_once = True
                lease_counters["held_requests"] += 1
            while active_gate.gpu_lease_held() and loop.time() < deadline:
                if await request.is_disconnected():
                    # The client gave up: forwarding later would load a model for nobody.
                    lease_counters["abandoned"] += 1
                    return Response(status_code=499)
                await asyncio.sleep(lease_poll_s)
            if await request.is_disconnected():
                lease_counters["abandoned"] += 1
                return Response(status_code=499)
            refusal, admitted = await run_gate()

        if refusal is not None:
            counters["refused"] += 1
            headers_out = {"Retry-After": str(RETRY_AFTER_S)}
            if refusal.kind == "gpu_lease":
                lease_counters["refused"] += 1
                headers_out["X-Cohezion-Refusal"] = "gpu_lease"
            return JSONResponse(
                status_code=503,
                headers=headers_out,
                content={
                    "error": {
                        "type": "admission_refused",
                        "message": refusal.reason,
                        "model": refusal.model,
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
            for name in admitted:  # nothing loaded: free the reservation now, not in 180 s
                active_gate.release(name)
            # A dead/mid-restart upstream is a clean 502, not a traceback-500.
            return JSONResponse(
                status_code=502,
                content={"error": {"type": "upstream_unreachable", "message": str(exc)}},
            )
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
