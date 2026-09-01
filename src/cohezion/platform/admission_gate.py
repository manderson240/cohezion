"""Byte-aware admission gate for the lemonade router — the missing PREVENT half of OOM.

The 08-31 double hard-freeze trigger: lemond auto-loads any requested model with a
COUNT-based cap (max_models) that cannot bound bytes, and its config is ephemeral. The
landed guard actuator (session_monitor) can claw memory BACK; nothing refuses the load
up front. This module is that refusal: a thin ASGI proxy that takes :13305 (clients and
invariant N1 unchanged), forwards to lemond on an internal port, and refuses any request
that would trigger a load the box cannot afford.

Decision rules (in order):
  1. No model named in the request -> forward (GETs, health, admin).
  2. Model already resident -> forward (reuse needs no new memory; blocking a resident
     model deadlocks the task queue — the 2026-07-19 lesson in check_oom_risk).
  3. HARD FLOOR: available RAM below ``floor_gb`` -> refuse ALL non-resident loads,
     TIER-BLIND. The 08-31 killer was an FLM/NPU model — 'NPU is UMA-safe' is falsified
     as an admission rule; below the floor nothing new loads.
  4. Byte budget: ``check_oom_risk`` (footprint resolved, never 0.0 for unknowns,
     + RAM_LOAD_BUFFER_GB) decides.

Fail postures, chosen deliberately:
  - Residency unreadable (health blocks during load — exactly the emergency) -> assume
    NON-resident. 'Cannot see' is never a pass.
  - /proc/meminfo unreadable -> fail OPEN with a 'blind' flag: refusing everything on a
    proc hiccup takes the whole fleet down; telemetry sees the blind state instead.

TRUST BOUNDARY (council finding: Direct-to-Backend Bypass): lemond spawns per-model
llama-server backends on their own localhost ports (:8002, :8003, ...). Those ports are
reachable AROUND this proxy by any same-host process, and requests to a resident backend
do not trigger loads — but ``lemond``'s own port, once moved internal, is equally
reachable. This gate therefore bounds WELL-BEHAVED clients (everything that talks to
:13305) and makes the bypass surface auditable via :func:`audit_bypass_paths`; it does
not and cannot sandbox hostile same-host processes.

Config persistence (council finding: Cold-Boot Cap Persistence): every parameter is read
from the environment at construction — the systemd unit is the persistence layer. The
config object is frozen; there is no runtime mutation to lose on restart.

Deployment: scripts/cohezion-admission-gate.service + docs/ops/admission-gate-cutover.md.
"""

from __future__ import annotations

import logging
import os
import pathlib
import time
from collections.abc import Callable
from dataclasses import dataclass

from cohezion.compound.oom_guard import (
    check_oom_risk,
    fetch_loaded_models,
    model_matches_loaded_entry,
)


logger = logging.getLogger(__name__)

DEFAULT_FLOOR_GB = 16.0  # the N3 operational floor; below it nothing new loads
DEFAULT_UPSTREAM = "http://127.0.0.1:13315"
DEFAULT_LISTEN_PORT = 13305
RESIDENT_CACHE_TTL_S = 1.5  # bound per-request health fetches on the hot path
# Request-body keys that name a model; presence of any makes a request load-triggering.
_MODEL_KEYS = ("model", "model_name")


def read_available_gb_strict() -> float:
    """MemAvailable in GB, RAISING on failure — never a fabricated number.

    Deliberately NOT oom_guard.get_available_ram_gb: MemorySnapshot.capture swallows
    every exception and returns available_gb=20.0, which (being above the 16 GB floor)
    would make the gate silently approve loads on ZERO real information exactly when
    /proc reads fail under livelock. The gate's blind fail-open must be VISIBLE, so its
    reader must be allowed to fail (adversarial review 2026-09-01, HIGH-1).
    """
    info: dict[str, int] = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = int(v.split()[0])  # kB
    return info["MemAvailable"] / (1024**2)


@dataclass(frozen=True)
class GateConfig:
    """Frozen gate parameters. Persistence = the environment (systemd unit), re-read at
    every construction; runtime state can neither change nor outlive a restart."""

    floor_gb: float = DEFAULT_FLOOR_GB
    enforce: bool = True
    upstream_base: str = DEFAULT_UPSTREAM
    health_timeout_s: float = 2.0

    @classmethod
    def from_env(cls) -> GateConfig:
        # Floor fallback chain keeps the gate and the resource guard (session_monitor's
        # N3_FLOOR_GB) on ONE floor unless deliberately split — two floors that drift
        # produce admit-at-16/evict-at-24 flapping in the band between them.
        floor = os.environ.get(
            "COHEZION_ADMISSION_FLOOR_GB",
            os.environ.get("COHEZION_RESOURCE_FLOOR_GB", str(DEFAULT_FLOOR_GB)),
        )
        enforce_raw = os.environ.get("COHEZION_ADMISSION_ENFORCE", "1").strip().lower()
        cfg = cls(
            floor_gb=float(floor),
            enforce=enforce_raw not in ("0", "false", "no", "off", ""),
            upstream_base=os.environ.get("COHEZION_ADMISSION_UPSTREAM", DEFAULT_UPSTREAM),
            health_timeout_s=float(os.environ.get("COHEZION_ADMISSION_HEALTH_TIMEOUT_S", "2.0")),
        )
        logger.info(
            "admission config: floor=%.1fGB enforce=%s (raw=%r) upstream=%s",
            cfg.floor_gb,
            cfg.enforce,
            enforce_raw,
            cfg.upstream_base,
        )
        return cfg


@dataclass(frozen=True)
class AdmissionDecision:
    allow: bool
    would_refuse: bool
    reason: str
    model: str | None = None


class AdmissionGate:
    """The decision core — pure, injectable, HTTP-free (the proxy layer consumes it).

    Enforces from the FIRST call: there is no warm-up state whose absence means
    pass-through (the council's Uncapped-Window/TOCTOU test). The resident list is
    cached for RESIDENT_CACHE_TTL_S to bound health fetches on the hot path — TTL
    staleness errs safe (a just-loaded model misread as non-resident falls through to
    the budget check, never the reverse).
    """

    def __init__(
        self,
        config: GateConfig | None = None,
        *,
        read_available_gb: Callable[[], float] | None = None,
        read_resident: Callable[[], list[dict[str, object]] | None] | None = None,
    ) -> None:
        self._config = config if config is not None else GateConfig.from_env()
        self._read_available = (
            read_available_gb if read_available_gb is not None else read_available_gb_strict
        )
        # The residency probe MUST target the upstream router directly: once this gate's
        # proxy holds :13305, the module-default LEMONADE_BASE points back at the proxy
        # itself (adversarial review 2026-09-01, F1 — self-probe deadlock/latency loop).
        self._read_resident = (
            read_resident
            if read_resident is not None
            else lambda: fetch_loaded_models(
                timeout_s=self._config.health_timeout_s,
                base_url=self._config.upstream_base,
            )
        )
        self._resident_cache: tuple[float, list[dict[str, object]] | None] | None = None

    @property
    def config(self) -> GateConfig:
        return self._config

    def _resident_entries(self) -> list[dict[str, object]] | None:
        now = time.monotonic()
        if (
            self._resident_cache is not None
            and now - self._resident_cache[0] < RESIDENT_CACHE_TTL_S
        ):
            return self._resident_cache[1]
        try:
            entries = self._read_resident()
        except Exception as exc:  # a broken probe must not crash the request path
            logger.warning("admission gate: residency probe failed: %s", exc)
            entries = None
        self._resident_cache = (now, entries)
        return entries

    def decide(self, model_name: str | None) -> AdmissionDecision:
        if not model_name:
            return AdmissionDecision(True, False, "no model named — not load-triggering")

        resident = self._resident_entries()
        if resident is not None and any(
            model_matches_loaded_entry(model_name, m) for m in resident
        ):
            return AdmissionDecision(True, False, "resident — reuse needs no memory", model_name)

        try:
            available = float(self._read_available())
        except Exception as exc:
            # Cannot reason about memory at all: fail OPEN, loudly flagged. Refusing
            # everything on a proc hiccup would take the fleet down by itself. This path
            # is REACHABLE because the default reader raises (read_available_gb_strict),
            # unlike MemorySnapshot.capture's fabricated 20 GB fallback.
            logger.warning("admission gate BLIND (meminfo unreadable: %s) — allowing", exc)
            return AdmissionDecision(
                True, False, f"gate blind: memory unreadable ({exc}) — allowed", model_name
            )

        if available < self._config.floor_gb:
            reason = (
                f"below hard floor: {available:.1f} GB available < "
                f"{self._config.floor_gb:.1f} GB — no new load of any tier "
                f"(refused '{model_name}'; 08-31 killer was an NPU-tier model)"
            )
            return self._refusal(reason, model_name)

        # npu_exempt=False: the 'NPU is UMA-safe' premise is falsified for large FLM MoE
        # models (weights live in host DRAM); budget-check them like everything else.
        risk = check_oom_risk(model_name, available_gb=available, npu_exempt=False)
        if not risk.safe:
            return self._refusal(f"byte budget: {risk.reason}", model_name)
        return AdmissionDecision(True, False, risk.reason, model_name)

    def _refusal(self, reason: str, model_name: str) -> AdmissionDecision:
        if not self._config.enforce:
            logger.warning("admission gate SHADOW refusal (not enforced): %s", reason)
            return AdmissionDecision(True, True, f"shadow mode: {reason}", model_name)
        logger.warning("admission gate REFUSED: %s", reason)
        return AdmissionDecision(False, True, reason, model_name)


_FETCH_LIVE: object = object()  # sentinel: caller wants a live health fetch


def audit_bypass_paths(
    loaded: list[dict[str, object]] | object | None = _FETCH_LIVE,
    *,
    base_url: str | None = None,
) -> list[str] | None:
    """Name the routes AROUND the gate: backend URLs of spawned per-model servers.

    Returns None when the health endpoint is unreadable — 'no bypass paths found' and
    'could not look' are different answers (council: Direct-to-Backend Bypass).
    Pass ``base_url`` (the gate's upstream) when calling from the proxy — the default
    LEMONADE_BASE is the proxy's own port after cutover (F1 self-probe).
    """
    if loaded is _FETCH_LIVE:
        loaded = (
            fetch_loaded_models(base_url=base_url)
            if base_url is not None
            else fetch_loaded_models()
        )
    if loaded is None or not isinstance(loaded, list):
        return None
    return [str(m.get("backend_url", "")) for m in loaded if m.get("backend_url")]


def extract_model_name(body: object) -> str | None:
    """The model a JSON request body names, if any. Non-dict bodies name nothing."""
    if not isinstance(body, dict):
        return None
    for key in _MODEL_KEYS:
        value = body.get(key)
        if isinstance(value, str) and value:
            return value
    return None
