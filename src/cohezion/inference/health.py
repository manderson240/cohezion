"""Fleet health probes.

Used by ``make health-fleet`` and by ``fleet.route()`` before dispatching to
a lane that may be down. Probes are single-flight cached for 30 s so rapid
back-to-back calls don't hammer the endpoints.

Returns structured status for each silicon lane:

- NPU (:13306, FLM backend)
- iGPU ROCWMMA (:13307)
- iGPU Unified (:13308)
- CPU AVX-VNNI (:13309)
- Ollama (:11434)
- Anthropic API (https://api.anthropic.com)
- Omnibus gateway dashboard snapshot

Does not start or stop endpoints — those are the job of
``scripts/symphony_warmstart.sh`` and ``scripts/launch_gemma4_symphony.sh``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 30.0
_LAST_CHECK_AT: float = 0.0
_LAST_RESULT: FleetHealth | None = None


class LaneStatus(StrEnum):
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"  # reachable but slow or errored
    UNKNOWN = "unknown"


@dataclass
class LaneHealth:
    lane: str
    endpoint: str
    status: LaneStatus
    latency_ms: float | None = None
    models_available: list[str] = field(default_factory=list)
    detail: str = ""


@dataclass
class FleetHealth:
    checked_at: float
    lanes: dict[str, LaneHealth]
    omnibus_dashboard: str | None = None

    @property
    def local_lanes_up(self) -> int:
        local = {"npu", "igpu_rocwmma", "igpu_unified", "cpu"}
        return sum(
            1 for name, h in self.lanes.items() if name in local and h.status == LaneStatus.UP
        )

    @property
    def any_local_up(self) -> bool:
        return self.local_lanes_up > 0


def _probe_openai_endpoint(lane: str, endpoint: str, timeout: float = 2.0) -> LaneHealth:
    """Probe an OpenAI-compatible /v1/models endpoint."""
    start = time.perf_counter()
    try:
        resp = httpx.get(f"{endpoint}/v1/models", timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        if resp.status_code == 200:
            data = resp.json()
            model_ids = [m.get("id", "") for m in data.get("data", [])]
            return LaneHealth(
                lane=lane,
                endpoint=endpoint,
                status=LaneStatus.UP,
                latency_ms=latency_ms,
                models_available=model_ids,
            )
        return LaneHealth(
            lane=lane,
            endpoint=endpoint,
            status=LaneStatus.DEGRADED,
            latency_ms=latency_ms,
            detail=f"HTTP {resp.status_code}",
        )
    except httpx.ConnectError as exc:
        return LaneHealth(lane=lane, endpoint=endpoint, status=LaneStatus.DOWN, detail=str(exc))
    except httpx.HTTPError as exc:
        return LaneHealth(lane=lane, endpoint=endpoint, status=LaneStatus.DEGRADED, detail=str(exc))


def _probe_ollama(endpoint: str = "http://localhost:11434", timeout: float = 2.0) -> LaneHealth:
    """Probe Ollama — uses /api/tags, not /v1/models."""
    start = time.perf_counter()
    try:
        resp = httpx.get(f"{endpoint}/api/tags", timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        if resp.status_code == 200:
            data = resp.json()
            model_ids = [m.get("name", "") for m in data.get("models", [])]
            return LaneHealth(
                lane="ollama",
                endpoint=endpoint,
                status=LaneStatus.UP,
                latency_ms=latency_ms,
                models_available=model_ids,
            )
        return LaneHealth(
            lane="ollama",
            endpoint=endpoint,
            status=LaneStatus.DEGRADED,
            latency_ms=latency_ms,
            detail=f"HTTP {resp.status_code}",
        )
    except httpx.HTTPError as exc:
        return LaneHealth(lane="ollama", endpoint=endpoint, status=LaneStatus.DOWN, detail=str(exc))


def _probe_cli(
    binary: str,
    lane_name: str,
    probe_args: list[str] | None = None,
    timeout_s: float = 5.0,
) -> LaneHealth:
    """Probe a headless CLI tool by running a tiny live command.

    ``probe_args`` defaults to ``["--version"]`` which only verifies the binary
    exists on PATH. Lanes that need end-to-end verification (auth + network +
    model route) should pass a live-dispatch probe such as
    ``["-p", "ping", "--max-tokens", "1"]`` — this costs a handful of tokens
    but confirms the path that real requests will take.
    """
    import shutil
    import subprocess

    resolved = shutil.which(binary)
    if resolved is None:
        return LaneHealth(
            lane=lane_name,
            endpoint=f"cli:{binary}",
            status=LaneStatus.DOWN,
            detail=f"{binary} CLI not on PATH",
        )
    args = probe_args if probe_args is not None else ["--version"]
    try:
        start = time.perf_counter()
        result = subprocess.run(
            [resolved, *args], capture_output=True, timeout=timeout_s, text=True
        )
        latency_ms = (time.perf_counter() - start) * 1000
        if result.returncode == 0:
            detail = result.stdout.strip() or result.stderr.strip()
            return LaneHealth(
                lane=lane_name,
                endpoint=f"cli:{resolved}",
                status=LaneStatus.UP,
                latency_ms=latency_ms,
                detail=detail[:200] if detail else None,
            )
        return LaneHealth(
            lane=lane_name,
            endpoint=f"cli:{resolved}",
            status=LaneStatus.DEGRADED,
            latency_ms=latency_ms,
            detail=f"exit {result.returncode}",
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return LaneHealth(
            lane=lane_name,
            endpoint=f"cli:{resolved}",
            status=LaneStatus.DEGRADED,
            detail=str(exc),
        )


def _probe_anthropic() -> LaneHealth:
    """Claude Code CLI availability — live `-p` dispatch under a tight budget cap.

    Unlike ``--version`` this confirms auth + network + model route in one shot,
    so a green probe guarantees real requests can reach the API. Flag shape
    reflects the actual Claude Code CLI (no ``--max-tokens`` flag exists; use
    ``--max-budget-usd`` instead). ``--bare`` skips hooks / LSP / plugin sync
    to keep per-probe latency low. Expected cost per probe on Haiku: < $0.0001.
    Output ignored — we only consume the exit code. 30s cache in ``check_fleet``
    bounds cost.
    """
    return _probe_cli(
        "claude",
        "claude",
        probe_args=[
            "-p",
            "ping",
            "--bare",
            "--model",
            "haiku-4-5",
            "--max-budget-usd",
            "0.01",
        ],
    )


def _probe_gemini() -> LaneHealth:
    """Gemini CLI availability — parallel headless-CLI lane to Claude."""
    return _probe_cli("gemini", "gemini")


def _omnibus_dashboard() -> str | None:
    """Snapshot the Omnibus gateway dashboard if the import succeeds."""
    try:
        from cohezion.gateways.omnibus import Omnibus

        return Omnibus().get_gateway_dashboard()
    except Exception as exc:
        logger.debug("Omnibus dashboard unavailable: %s", exc)
        return None


def check_fleet(*, force: bool = False) -> FleetHealth:
    """Probe every lane and return consolidated status.

    Cached for ``_CACHE_TTL_SECONDS`` to avoid spamming endpoints on hot paths.
    Pass ``force=True`` to bypass the cache.
    """
    global _LAST_CHECK_AT, _LAST_RESULT

    now = time.time()
    if not force and _LAST_RESULT is not None and now - _LAST_CHECK_AT < _CACHE_TTL_SECONDS:
        return _LAST_RESULT

    lanes: dict[str, LaneHealth] = {
        "npu": _probe_openai_endpoint("npu", "http://localhost:13306"),
        "igpu_rocwmma": _probe_openai_endpoint("igpu_rocwmma", "http://localhost:13307"),
        "igpu_unified": _probe_openai_endpoint("igpu_unified", "http://localhost:13308"),
        "cpu": _probe_openai_endpoint("cpu", "http://localhost:13309"),
        "ollama": _probe_ollama(),
        "claude": _probe_anthropic(),
        "gemini": _probe_gemini(),
    }

    # Router-centric reconciliation (F1 fix, adversarial audit 2026-06-09): the
    # lemonade router on :13305 serves every local lane on demand, and the dedicated
    # per-port daemons (:13306-:13309) are often down + redundant in the router-centric
    # topology. If a local lane's dedicated daemon is not UP but the router IS, the lane
    # is still servable via the router — mark it UP so route()/extend_claude do not
    # silently escalate every local request to the paid cloud CLI.
    router = _probe_openai_endpoint("router", "http://localhost:13305")
    lanes["router"] = router
    if router.status == LaneStatus.UP:
        for lane_name in ("npu", "igpu_rocwmma", "igpu_unified", "cpu"):
            if lanes[lane_name].status != LaneStatus.UP:
                lanes[lane_name] = LaneHealth(
                    lane=lane_name,
                    endpoint="http://localhost:13305",
                    status=LaneStatus.UP,
                    latency_ms=router.latency_ms,
                    models_available=router.models_available,
                    detail="via router :13305",
                )

    result = FleetHealth(
        checked_at=now,
        lanes=lanes,
        omnibus_dashboard=_omnibus_dashboard(),
    )

    _LAST_CHECK_AT = now
    _LAST_RESULT = result
    return result


def format_fleet_summary(health: FleetHealth) -> str:
    """One-line-per-lane human-readable summary."""
    lines = [f"Fleet health @ {time.ctime(health.checked_at)}:"]
    icons = {
        LaneStatus.UP: "✓",
        LaneStatus.DOWN: "✗",
        LaneStatus.DEGRADED: "~",
        LaneStatus.UNKNOWN: "?",
    }
    for name, h in health.lanes.items():
        icon = icons[h.status]
        latency = f"{h.latency_ms:.0f}ms" if h.latency_ms is not None else "-"
        models = f"{len(h.models_available)} models" if h.models_available else h.detail
        lines.append(f"  {icon} {name:14s} {h.endpoint:30s} {latency:>7s}  {models}")
    return "\n".join(lines)


def integrate_omnibus_gateways() -> dict[str, Any]:
    """Trigger the cache-gateway unlock (sets TurboQuant env vars) and return status.

    Unlocking the ``cache`` gateway in Omnibus literally does::

        os.environ["TRITON_AMD_WMMA"] = "1"
        os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.5.1"

    which is the minimum environment for TurboQuant on gfx1151. Call this once
    at fleet launch to align env without shell-scripted exports.
    """
    try:
        from cohezion.gateways.omnibus import Omnibus

        omnibus = Omnibus()
        status = omnibus.get_master_status()
        return {
            "available": True,
            "gateways_unlocked": status["gateways_unlocked"],
            "gateways_locked": status["gateways_locked"],
            "total_health": status["total_health"],
        }
    except Exception as exc:
        logger.warning("Omnibus integration unavailable: %s", exc)
        return {"available": False, "reason": str(exc)}
