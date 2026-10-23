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

import contextlib
import logging
import os
import pathlib
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from cohezion.compound.oom_guard import (
    MODEL_FOOTPRINT_GB,
    _kv_reservation_gb,
    fetch_loaded_models,
    normalize_model_name,
)


logger = logging.getLogger(__name__)

DEFAULT_UPSTREAM = "http://127.0.0.1:13315"
DEFAULT_LISTEN_PORT = 13305
RESIDENT_CACHE_TTL_S = 1.5  # bound per-request health fetches on the hot path
# An admitted load holds its footprint until the model shows up as resident (its memory is
# then in the cgroup reading) or this expires. Without it, concurrent requests each see the
# same headroom and all pass.
RESERVATION_TTL_S = 180.0
# A positive residency answer stays usable this long: /api/v1/health blocks while any model
# loads, and losing "resident" then re-prices chats to already-loaded models as fresh loads.
RESIDENT_LAST_GOOD_S = 60.0
# The catalog is refreshed in the background (it stalls under load, so never on the hot
# path). A name missing from a catalog younger than this is unknown to lemonade itself.
CATALOG_FRESH_S = 300.0
CATALOG_REFRESH_S = 120.0
CATALOG_RETRY_S = 15.0
_WALK_MAX_NODES = 5000
LEMOND_CGROUP = pathlib.Path("/sys/fs/cgroup/system.slice/lemond.service")
CGROUP_HIGH_FRACTION = 0.9
# Routes that name a model but never load one: freeing memory must never be refused, and
# lemonade budgets its own downloads (pull refuses below size + 8 GB available).
_NON_LOAD_ROUTES = frozenset(
    f"{prefix}{verb}"
    for prefix in ("api/v1/", "v1/", "api/v0/")
    for verb in ("unload", "delete", "pull")
)


def read_lemond_cgroup_gb() -> tuple[float, float] | None:
    """(working_set_gb, memory_high_gb) for lemond's cgroup, or None.

    Working set = anon + min(shmem + file_mapped, file): an upper bound on memory the
    kernel cannot drop to stay under memory.high. That set is anon + shmem + mapped regular
    file pages. ``file_mapped`` counts mapped shmem too, and ``file`` counts all shmem, so
    mapped regular pages are at most min(file_mapped, file - shmem). memory.stat has no field
    for mapped shmem, so this bound is the tightest one it allows.
    It is exact when no unmapped cache sits in ``file`` beside the mapped pages, and safe when it is
    not. ``amdxdna`` pins NPU buffers with drm_gem_shmem_pin whether or not anything maps
    them, so anon + max(shmem, file_mapped) would under-count pinned NPU shmem beside
    mmap'd GGUF weights and admit a load that throttles every model.
    Measured 2026-10-22 with an FLM model resident: anon 6.25, shmem 7.21, file_mapped 9.13,
    file 13.79 GB. The old anon + shmem + file_mapped read 22.6 GB against a whole-cgroup
    charge of 20.12 GB and refused a 6.8 GB load that fit; this reads 20.04 GB.
    Unmapped file cache is excluded whichever LRU list it sits on: after a model is unloaded
    its weights stay on the ACTIVE file list (16.9 GB measured 2026-10-21), so
    ``memory.current - inactive_file`` would refuse every load. The result is clamped to
    ``memory.current`` (read separately, so an unload between the two reads cannot leave
    the figure above the charge).
    None when the cgroup is unreadable or has no memory.high (fail open).
    """
    try:
        high_raw = (LEMOND_CGROUP / "memory.high").read_text().strip()
        if high_raw == "max":
            return None
        stat: dict[str, int] = {}
        for line in (LEMOND_CGROUP / "memory.stat").read_text().splitlines():
            key, _, value = line.partition(" ")
            if key in ("anon", "shmem", "file_mapped", "file"):
                stat[key] = int(value)
        working_set = stat["anon"] + min(stat["shmem"] + stat["file_mapped"], stat["file"])
    except (OSError, ValueError, KeyError):
        return None
    # No readable charge to clamp against: the stat-based figure stands.
    with contextlib.suppress(OSError, ValueError):
        working_set = min(working_set, int((LEMOND_CGROUP / "memory.current").read_text()))
    return working_set / (1024.0**3), int(high_raw) / (1024.0**3)


def is_load_path(path: str) -> bool:
    """False only for the exact routes that name a model but cannot load one."""
    return path.strip("/").lower() not in _NON_LOAD_ROUTES


def models_named(body: object) -> list[str]:
    """Every model a parsed request names, in order, without duplicates.

    Collects string values under any key containing "model" or named "checkpoint", at any
    depth, through lists (JSON-RPC batches) and dicts (MCP ``params.arguments``). Keys, not
    values, select: a chat message that merely mentions a model name is not a load.
    """
    found: list[str] = []
    queue: deque[object] = deque([body])
    seen = 0
    while queue and seen < _WALK_MAX_NODES:
        node = queue.popleft()
        seen += 1
        if isinstance(node, dict):
            for key, value in node.items():
                k = str(key).lower()
                if isinstance(value, str):
                    if value and ("model" in k or k == "checkpoint") and value not in found:
                        found.append(value)
                elif isinstance(value, (dict, list)):
                    queue.append(value)
        elif isinstance(node, list):
            queue.extend(node)
    return found


def extract_model_name(body: object) -> str | None:
    """The first model a request names (see :func:`models_named`)."""
    names = models_named(body)
    return names[0] if names else None


def _resident_match(model_name: str, entry: dict[str, object]) -> bool:
    """Exact match on the entry's name or its checkpoint stem; never a substring."""
    want = normalize_model_name(model_name).lower()
    name = normalize_model_name(str(entry.get("model_name", ""))).lower()
    stem = str(entry.get("checkpoint", "")).lower().split(":")[0].rsplit("/", 1)[-1]
    return bool(want) and want in (name, stem)


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
    """The decision core — injectable and HTTP-free on the hot path (the proxy consumes it).

    Network reads (health, catalog) happen OUTSIDE the decision lock; the lock covers only
    the arithmetic and the reservation, so one slow lemond answer cannot queue every request.
    """

    def __init__(
        self,
        config: GateConfig | None = None,
        *,
        read_resident: Callable[[], list[dict[str, object]] | None] | None = None,
        read_cgroup: Callable[[], tuple[float, float] | None] | None = None,
        read_size_gb: Callable[[str], float | None] | None = None,
        read_catalog: Callable[[], dict[str, dict[str, object]] | None] | None = None,
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
        self._read_catalog = read_catalog or self._fetch_catalog
        self._catalog: dict[str, dict[str, object]] = {}
        self._catalog_at: float | None = None
        self._read_size_gb = read_size_gb or self._cached_footprint_gb
        self._reserved: dict[str, tuple[float, float]] = {}  # model -> (gb, expires_at)
        self._lock = threading.Lock()  # proxy calls decide() from a threadpool
        self._resident_cache: tuple[float, list[dict[str, object]] | None] | None = None
        self._last_good: tuple[float, list[dict[str, object]]] | None = None
        self._cgroup_warned_at = 0.0
        self.cgroup_readable = True
        if read_size_gb is None:
            self.refresh_catalog()

    @property
    def config(self) -> GateConfig:
        return self._config

    # -- catalog (background) -------------------------------------------------------------

    def _fetch_catalog(self) -> dict[str, dict[str, object]] | None:
        """{normalized id: catalog entry} from lemonade, or None if it does not answer."""
        try:
            r = httpx.get(
                f"{self._config.upstream_base}/api/v1/models",
                params={"show_all": "true"},
                timeout=httpx.Timeout(5.0),
            )
            r.raise_for_status()
            entries = r.json().get("data", [])
            return {
                normalize_model_name(str(e.get("id", ""))): e
                for e in entries
                if isinstance(e, dict)
            }
        except (httpx.HTTPError, ValueError, AttributeError, TypeError) as exc:
            logger.warning("admission gate: catalog unreadable: %s", exc)
            return None

    def refresh_catalog(self) -> bool:
        """Replace the cached catalog from lemonade. False when it did not answer."""
        fresh = self._read_catalog()
        if not fresh:
            return False
        self._catalog = fresh
        self._catalog_at = time.monotonic()
        return True

    def start_refresher(self) -> None:
        """Daemon thread keeping the catalog fresh, so decide() never fetches it."""

        def loop() -> None:
            while True:
                ok = self.refresh_catalog()
                time.sleep(CATALOG_REFRESH_S if ok else CATALOG_RETRY_S)

        threading.Thread(target=loop, name="admission-catalog", daemon=True).start()

    def catalog_age_s(self) -> float | None:
        return None if self._catalog_at is None else time.monotonic() - self._catalog_at

    def _catalog_is_fresh(self) -> bool:
        age = self.catalog_age_s()
        return age is not None and age < CATALOG_FRESH_S

    def _cached_footprint_gb(self, model_name: str) -> float | None:
        """Weights + KV reservation for *model_name*, or None when its size is unknown.

        Weights are the larger of lemonade's catalog size and oom_guard's curated
        MODEL_FOOTPRINT_GB: the catalog has under-reported (a 35B at 1.68 GB, harness RS7),
        and a wrong small size is more dangerous than a missing one.
        """
        key = normalize_model_name(model_name)
        entry = self._catalog.get(key)
        size = entry.get("size") if entry else None
        catalog_gb = float(size) if isinstance(size, (int, float)) and size > 0 else 0.0
        curated_gb = MODEL_FOOTPRINT_GB.get(key, 0.0)
        weights = max(catalog_gb, curated_gb)
        if weights <= 0.0:
            return None
        if curated_gb and catalog_gb and abs(curated_gb - catalog_gb) > 0.5 * curated_gb:
            logger.info(
                "admission gate: size for %s: catalog %.1f vs curated %.1f GB, using %.1f",
                model_name,
                catalog_gb,
                curated_gb,
                weights,
            )
        return weights + _kv_reservation_gb(model_name, weights, entry)

    # -- residency ------------------------------------------------------------------------

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
        if entries is not None:
            self._last_good = (now, entries)
        return entries

    def _is_resident(self, model_name: str, resident: list[dict[str, object]] | None) -> bool:
        if resident is not None:
            return any(_resident_match(model_name, m) for m in resident)
        # health is blocked (a load is in progress): trust a recent positive answer only
        if self._last_good and time.monotonic() - self._last_good[0] < RESIDENT_LAST_GOOD_S:
            return any(_resident_match(model_name, m) for m in self._last_good[1])
        return False

    def _npu_slot_credit_gb(
        self, model_name: str, path: str, resident: list[dict[str, object]] | None
    ) -> float:
        """Size of the ONE resident FLM llm that loading an FLM llm will evict, else 0.

        Only chat/completions-style paths load an llm; audio, image and embedding FLM
        models use other slots and evict nothing.
        """
        p = path.lower()
        if not model_name.lower().endswith("-flm") or any(
            t in p for t in ("embedding", "audio", "image", "transcri", "speech")
        ):
            return 0.0
        sizes = [
            self._read_size_gb(str(e.get("model_name", ""))) or 0.0
            for e in resident or []
            if e.get("recipe") == "flm" and e.get("type") == "llm"
        ]
        return max(sizes, default=0.0)

    # -- decision -------------------------------------------------------------------------

    def decide(self, model_name: str | None, path: str = "") -> AdmissionDecision:
        if not model_name or not is_load_path(path):
            return AdmissionDecision(True, False, "not load-triggering", model_name)

        # Slow reads first, outside the lock.
        resident = self._resident_entries()
        if self._is_resident(model_name, resident):
            return AdmissionDecision(True, False, "resident — reuse needs no memory", model_name)
        cgroup = self._read_cgroup()
        if cgroup is None:
            self.cgroup_readable = False
            now = time.monotonic()
            if now - self._cgroup_warned_at > 60:
                self._cgroup_warned_at = now
                logger.warning("admission gate: lemond cgroup unreadable — not gating loads")
            return AdmissionDecision(
                True, False, "cgroup unreadable — Lemonade decides", model_name
            )
        self.cgroup_readable = True
        size = self._read_size_gb(model_name)
        if size is None:
            if self._catalog_is_fresh():
                return AdmissionDecision(
                    True, False, "not in lemonade's catalog — lemonade will answer", model_name
                )
            return self._refusal(
                f"model size unknown for '{model_name}': lemonade's catalog has not been read "
                "yet (it stalls while a load is in progress) — retry shortly",
                model_name,
            )
        credit = self._npu_slot_credit_gb(model_name, path, resident)
        working_set, high = cgroup
        budget = CGROUP_HIGH_FRACTION * high
        key = normalize_model_name(model_name).lower()

        with self._lock:
            now = time.monotonic()
            for k, (_gb, expires) in list(self._reserved.items()):
                landed = resident is not None and any(_resident_match(k, m) for m in resident)
                if landed or now > expires:
                    del self._reserved[k]
            if key in self._reserved:  # same model already admitted and still loading
                return AdmissionDecision(True, False, "already admitted — loading", model_name)
            reserved = sum(gb for gb, _ in self._reserved.values())
            total = working_set + reserved - credit + size
            detail = (
                f"{working_set:.1f}GB working set + {reserved:.1f}GB reserved - {credit:.1f}GB "
                f"NPU swap + {size:.1f}GB '{model_name}' = {total:.1f}GB"
            )
            if total > budget:
                return self._refusal(
                    f"lemond cgroup headroom: {detail} > {budget:.1f}GB "
                    f"({CGROUP_HIGH_FRACTION:.0%} of memory.high {high:.0f}GB) — past "
                    "memory.high the kernel throttles every model in lemond",
                    model_name,
                )
            self._reserved[key] = (size, now + RESERVATION_TTL_S)
        logger.info("admission gate ADMIT: %s <= %.1fGB", detail, budget)
        return AdmissionDecision(True, False, f"fits: {detail} <= {budget:.1f}GB", model_name)

    def release(self, model_name: str) -> None:
        """Drop an admitted load's reservation (the upstream request failed)."""
        with self._lock:
            self._reserved.pop(normalize_model_name(model_name).lower(), None)

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
