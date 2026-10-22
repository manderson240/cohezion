"""Thin admission gate for the lemonade router: one check Lemonade cannot do itself.

Lemonade and GAIA already manage the fleet: idle eviction, per-type slot caps, a RAM-gated
``pull``, ``auto_evict``, and GAIA's own free-memory check. What neither sees is the
``lemond.service`` cgroup. Every model lemond starts (llama-server, flm) is charged to it,
and past its ``memory.high`` the kernel throttles EVERY model in it, NPU included
(GEMS LESSONS 22, 2026-10-15: one 26B CPU probe stalled the fleet while system RAM looked
fine). This gate refuses a load that would cross that line, and nothing else.

Decision rules (in order):
  1. Request names no model, or is not load-triggering (unload/delete/pull) -> forward.
  2. Model already resident -> forward (reuse maps nothing new).
  3. lemond working set + the model's catalog size > 90% of memory.high -> refuse.
  4. Otherwise forward; Lemonade decides the rest.

Fail open when the cgroup is unreadable (a static sysfs read that does not stall). Fail
CLOSED when the model's size is unknown: lemonade's /api/v1/models stalls while a model is
loading, which is exactly when other loads arrive. On 2026-10-21 a fail-open size lookup let
a 16.9 GB CPU model through and throttle events rose 3,237 -> 4,558. Catalog sizes are static,
so they are cached and a stalled catalog only matters for a model never seen before.

TRUST BOUNDARY: lemond's per-model backends listen on their own localhost ports, reachable
around this proxy. The gate bounds well-behaved clients (everything on :13305) and makes
the bypass surface auditable via :func:`audit_bypass_paths`.

Config is read from the environment at construction (the systemd unit persists it).
Removed 2026-10-21 (user decision: use Lemonade and GAIA as they are): the name-based
aperture guard, which refused models by name and even refused unloads; the RAM floor,
swap-percent and PSI checks, which duplicated the kernel and Lemonade; GTT caps; and the
curated byte budget, replaced by Lemonade's catalog size.
"""

from __future__ import annotations

import logging
import os
import pathlib
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from cohezion.compound.oom_guard import (
    fetch_loaded_models,
    model_matches_loaded_entry,
    normalize_model_name,
)


logger = logging.getLogger(__name__)

DEFAULT_UPSTREAM = "http://127.0.0.1:13315"
DEFAULT_LISTEN_PORT = 13305
RESIDENT_CACHE_TTL_S = 1.5  # bound per-request health fetches on the hot path
LEMOND_CGROUP = pathlib.Path("/sys/fs/cgroup/system.slice/lemond.service")
CGROUP_HIGH_FRACTION = 0.9
# Request-body keys that name a model.
_MODEL_KEYS = ("model", "model_name")
# Paths that name a model but never load one: freeing memory must never be refused, and
# Lemonade budgets its own downloads (pull refuses below size + 8 GB available).
_NON_LOAD_PATH_SUFFIXES = ("unload", "delete", "pull")


def read_lemond_cgroup_gb() -> tuple[float, float] | None:
    """(working_set_gb, memory_high_gb) for lemond's cgroup, or None.

    Working set = anon + shmem + file_mapped: memory the kernel cannot drop to stay under
    memory.high. Unmapped file cache is excluded whichever LRU list it sits on: after a
    model is unloaded its weights stay on the ACTIVE file list (16.9 GB measured
    2026-10-21), so ``memory.current - inactive_file`` read 28.7 GB and would have refused
    every load while only 21.2 GB was in use. Measured on the same day: lemond's processes
    map 0 MB of shmem, so shmem and file_mapped do not overlap. None when the cgroup is
    unreadable or has no memory.high (fail open).
    """
    try:
        high_raw = (LEMOND_CGROUP / "memory.high").read_text().strip()
        if high_raw == "max":
            return None
        stat: dict[str, int] = {}
        for line in (LEMOND_CGROUP / "memory.stat").read_text().splitlines():
            key, _, value = line.partition(" ")
            if key in ("anon", "shmem", "file_mapped"):
                stat[key] = int(value)
        working_set = stat["anon"] + stat["shmem"] + stat["file_mapped"]
    except (OSError, ValueError, KeyError):
        return None
    return working_set / (1024.0**3), int(high_raw) / (1024.0**3)


def is_load_path(path: str) -> bool:
    """False for routes that name a model but cannot load one."""
    return not path.rstrip("/").lower().endswith(_NON_LOAD_PATH_SUFFIXES)


@dataclass(frozen=True)
class GateConfig:
    """Frozen gate parameters, re-read from the environment at every construction."""

    enforce: bool = True
    upstream_base: str = DEFAULT_UPSTREAM
    health_timeout_s: float = 2.0

    @classmethod
    def from_env(cls) -> GateConfig:
        enforce_raw = os.environ.get("COHEZION_ADMISSION_ENFORCE", "1").strip().lower()
        cfg = cls(
            enforce=enforce_raw not in ("0", "false", "no", "off", ""),
            upstream_base=os.environ.get("COHEZION_ADMISSION_UPSTREAM", DEFAULT_UPSTREAM),
            health_timeout_s=float(os.environ.get("COHEZION_ADMISSION_HEALTH_TIMEOUT_S", "2.0")),
        )
        logger.info(
            "admission config: enforce=%s (raw=%r) upstream=%s cgroup_fraction=%.2f",
            cfg.enforce,
            enforce_raw,
            cfg.upstream_base,
            CGROUP_HIGH_FRACTION,
        )
        return cfg


@dataclass(frozen=True)
class AdmissionDecision:
    allow: bool
    would_refuse: bool
    reason: str
    model: str | None = None


class AdmissionGate:
    """The decision core — injectable and HTTP-free (the proxy layer consumes it)."""

    def __init__(
        self,
        config: GateConfig | None = None,
        *,
        read_resident: Callable[[], list[dict[str, object]] | None] | None = None,
        read_cgroup: Callable[[], tuple[float, float] | None] | None = None,
        read_size_gb: Callable[[str], float | None] | None = None,
        read_catalog: Callable[[], dict[str, float] | None] | None = None,
    ) -> None:
        self._config = config if config is not None else GateConfig.from_env()
        # Probes target the UPSTREAM router: the module default :13305 is this proxy.
        self._read_resident = read_resident or (
            lambda: fetch_loaded_models(
                timeout_s=self._config.health_timeout_s,
                base_url=self._config.upstream_base,
            )
        )
        self._read_cgroup = read_cgroup or read_lemond_cgroup_gb
        self._read_catalog = read_catalog or self._fetch_catalog_sizes
        self._read_size_gb = read_size_gb or self._cached_size_gb
        self._sizes: dict[str, float] = {}
        self._resident_cache: tuple[float, list[dict[str, object]] | None] | None = None

    @property
    def config(self) -> GateConfig:
        return self._config

    def _fetch_catalog_sizes(self) -> dict[str, float] | None:
        """{normalized id: size_gb} from lemonade's catalog, or None if it does not answer."""
        try:
            r = httpx.get(
                f"{self._config.upstream_base}/api/v1/models",
                params={"show_all": "true"},
                timeout=10.0,
            )
            r.raise_for_status()
            entries = r.json().get("data", [])
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            logger.warning("admission gate: catalog unreadable: %s", exc)
            return None
        return {
            normalize_model_name(str(e.get("id", ""))): float(e["size"])
            for e in entries
            if isinstance(e.get("size"), (int, float)) and e["size"] > 0
        }

    def _cached_size_gb(self, model_name: str) -> float | None:
        """Catalog size, cached: sizes are static, the catalog stalls under load."""
        key = normalize_model_name(model_name)
        if key not in self._sizes:
            fresh = self._read_catalog()
            if fresh:
                self._sizes.update(fresh)
        return self._sizes.get(key)

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

    def decide(self, model_name: str | None, path: str = "") -> AdmissionDecision:
        if not model_name or not is_load_path(path):
            return AdmissionDecision(True, False, "not load-triggering", model_name)

        resident = self._resident_entries()
        if resident is not None and any(
            model_matches_loaded_entry(model_name, m) for m in resident
        ):
            return AdmissionDecision(True, False, "resident — reuse needs no memory", model_name)

        cgroup = self._read_cgroup()
        if cgroup is None:
            return AdmissionDecision(
                True, False, "cgroup unreadable — Lemonade decides", model_name
            )
        size = self._read_size_gb(model_name)
        if size is None:
            return self._refusal(
                f"model size unknown for '{model_name}': not in lemonade's catalog, or the "
                "catalog did not answer (it stalls while a load is in progress) — retry shortly",
                model_name,
            )
        working_set, high = cgroup
        budget = CGROUP_HIGH_FRACTION * high
        if working_set + size > budget:
            return self._refusal(
                f"lemond cgroup headroom: {working_set:.1f}GB working set + {size:.1f}GB "
                f"'{model_name}' > {budget:.1f}GB ({CGROUP_HIGH_FRACTION:.0%} of memory.high "
                f"{high:.0f}GB) — past memory.high the kernel throttles every model in lemond",
                model_name,
            )
        return AdmissionDecision(
            True, False, f"fits: {working_set + size:.1f}GB <= {budget:.1f}GB", model_name
        )

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
    'could not look' are different answers.
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
