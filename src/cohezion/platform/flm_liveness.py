"""FLM/NPU work-path liveness probe — the gap lemond's own watchdog cannot see.

lemond runs a BackendWatchdog per FLM backend, but it probes ``/api/tags`` — a
METADATA endpoint. An amdxdna/NPU wedge leaves that endpoint answering 200 while
inference hangs: a metadata endpoint answering while the work endpoint hangs is the
canonical split-probe blind spot (kimi council gap, 2026-09-01; same class as the
health-endpoint-is-not-a-liveness-oracle lesson). The only honest liveness signal
for the NPU is a bounded 1-token GENERATION (measured 0.4 s on a healthy lane).

Watcher, not actuator: the probe classifies and reports; restarting a wedged FLM
backend is an ops decision (mirrors the guard's own watcher→actuator evolution).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from cohezion.compound.oom_guard import fetch_loaded_models
from cohezion.platform.admission_gate import DEFAULT_UPSTREAM


logger = logging.getLogger(__name__)

PROBE_TIMEOUT_S = 6.0  # healthy lane answers in ~0.4 s; a wedge hangs far past this
_PROBE_BODY = {
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 1,
    "temperature": 0,
}


@dataclass(frozen=True)
class FLMProbe:
    """Outcome of one work-path probe.

    status: 'alive' (generated a token), 'wedged' (backend reachable but generation
    timed out or 5xx'd — the amdxdna signature), 'unreachable' (health or backend
    connection down — lemond's own watchdog territory), 'no_flm_resident' (nothing
    to probe; not an error), 'probe_error' (4xx — the probe's own naming/shape bug,
    never an NPU alarm).
    """

    status: str
    model: str = ""
    latency_s: float = 0.0
    detail: str = ""


def _post_chat(backend_url: str, model_checkpoint: str, timeout_s: float) -> None:
    body = json.dumps({"model": model_checkpoint, **_PROBE_BODY}).encode()
    # S310: backend_url comes from lemond's own /api/v1/health (127.0.0.1 backends),
    # never from caller input — http scheme by construction.
    req = urllib.request.Request(  # noqa: S310
        f"{backend_url.rstrip('/')}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as r:  # noqa: S310
        payload = json.load(r)
    if not (payload.get("choices") or []):
        raise ValueError("no choices in completion response")


def probe_flm_generation(
    *,
    upstream_base: str | None = None,
    timeout_s: float = PROBE_TIMEOUT_S,
    post_fn: object | None = None,
) -> FLMProbe:
    """Probe the first idle resident FLM lane with a bounded 1-token generation.

    ``upstream_base`` defaults to the SAME env the admission gate honors
    (COHEZION_ADMISSION_UPSTREAM) so a redeployed upstream cannot strand this
    probe on a stale literal (rv-flm-probe M1 — the sibling-drift class).
    """
    if upstream_base is None:
        upstream_base = os.environ.get("COHEZION_ADMISSION_UPSTREAM", DEFAULT_UPSTREAM)
    # Health gets the house 2s budget, not the generation timeout — worst case per
    # probe stays bounded at ~2s + timeout_s inside the guard's 60s poll.
    loaded = fetch_loaded_models(timeout_s=min(timeout_s, 2.0), base_url=upstream_base)
    if loaded is None:
        return FLMProbe("unreachable", detail="health endpoint unreadable")
    # is_busy verified REAL in the live payload (2026-09-01: present on all entries,
    # observed True on busy lanes) — probing a busy lane would queue behind work.
    flm = [
        m
        for m in loaded
        if str(m.get("recipe", "")) == "flm" and m.get("backend_url") and not m.get("is_busy")
    ]
    if not flm:
        return FLMProbe("no_flm_resident")
    entry = flm[0]
    model = str(entry.get("model_name", ""))
    checkpoint = str(entry.get("checkpoint") or model)
    poster = post_fn if post_fn is not None else _post_chat
    t0 = time.monotonic()
    try:
        poster(str(entry["backend_url"]), checkpoint, timeout_s)  # type: ignore[operator]
    except urllib.error.HTTPError as exc:
        # 5xx: the server answered (lemond's /api/tags watchdog stays green) yet the
        # work path failed — wedge. 4xx is the PROBE's own fault (e.g. a checkpoint
        # naming mismatch 404s) and must not raise a false wedge alarm
        # (rv-flm-probe M3). HTTPError must be caught BEFORE URLError (subclass).
        latency = time.monotonic() - t0
        if exc.code >= 500:
            return _wedged(model, latency, f"HTTP {exc.code}", str(exc)[:120])
        logger.warning(
            "FLM probe misfire on %s: HTTP %s — probe/naming bug, NOT an NPU wedge",
            model,
            exc.code,
        )
        return FLMProbe("probe_error", model=model, latency_s=latency, detail=f"HTTP {exc.code}")
    except (TimeoutError, ValueError) as exc:
        # A bare timeout is the hang itself; an empty completion is compute failing.
        return _wedged(model, time.monotonic() - t0, type(exc).__name__, str(exc)[:120])
    except urllib.error.URLError as exc:
        # urllib wraps read timeouts in URLError; a timeout while the server accepted
        # the connection is the wedge, a refused connection is dead-backend territory
        # that lemond's own BackendWatchdog already covers.
        latency = time.monotonic() - t0
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            return _wedged(model, latency, "URLError:timeout", "timeout")
        return FLMProbe("unreachable", model=model, latency_s=latency, detail=str(exc)[:120])
    except OSError as exc:
        return FLMProbe(
            "unreachable", model=model, latency_s=time.monotonic() - t0, detail=str(exc)[:120]
        )
    return FLMProbe("alive", model=model, latency_s=time.monotonic() - t0)


def _wedged(model: str, latency_s: float, kind: str, detail: str) -> FLMProbe:
    logger.warning(
        "FLM work-path WEDGE suspected on %s (%s after %.1fs) — lemond's /api/tags "
        "watchdog cannot see this; check amdxdna/NPU state",
        model,
        kind,
        latency_s,
    )
    return FLMProbe("wedged", model=model, latency_s=latency_s, detail=detail)
