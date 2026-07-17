"""Idle-eviction sweep — RAM-aware relief valve for the count-gated fleet.

Why: lemonade admits models by COUNT (max_models=6/type), not by RAM. External
consumers stack heavy GPU models until available RAM crosses the K1 16GB floor
(observed 3× on 2026-07-17, worst 7GB). This module codifies the manual relief
applied that day: when RAM is tight, unload heavy models that have sat idle.

Policy (user-approved 2026-07-17):
  - trigger: available RAM < 24GB
  - target:  models with effective size ≥ 8GB, idle ≥ 30 min, not pinned
  - never:   NPU occupant (the gauntlet owns that slot), embedding models
Eviction is reversible by design — the router auto-reloads on next request.

Idle measurement: health's ``last_use`` is a counter on an unknown clock base,
so idleness is measured by OUR observation: a model is idle-for-N-minutes when
its last_use value has been UNCHANGED for N minutes of wall time (state file
``~/.cohezion/idle_eviction_state.json``). First sight of a model = not yet
provably idle.

Run:  uv run python -m cohezion.inference.idle_eviction            # one sweep (cron)
      uv run python -m cohezion.inference.idle_eviction --loop 300 # daemon loop
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.request
from pathlib import Path

from cohezion.inference.load_safety import available_ram_gb, effective_size_gb


logger = logging.getLogger(__name__)

BASE = "http://localhost:13305"
STATE_PATH = Path.home() / ".cohezion" / "idle_eviction_state.json"
LOG_PATH = Path.home() / ".cohezion" / "idle_eviction.log"

RAM_TRIGGER_GB = 24.0
IDLE_MINUTES = 30.0
MIN_SIZE_GB = 8.0


def _http_json(url: str, payload: dict | None = None, timeout: float = 30.0) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.load(r)


def eligible(model: dict, idle_minutes: float, size_gb: float | None) -> bool:
    """Pure eviction-eligibility predicate (unit-tested; policy lives here)."""
    if model.get("device") == "npu":
        return False  # the gauntlet owns the NPU slot
    if model.get("type") == "embedding":
        return False  # cheap + cache-critical
    if model.get("pinned"):
        return False
    if size_gb is None or size_gb < MIN_SIZE_GB:
        return False
    return idle_minutes >= IDLE_MINUTES


def observe_idle_minutes(state: dict, name: str, last_use: int, now: float) -> float:
    """Update observation state; return provable idle minutes for ``name``.

    Idle time counts from when we FIRST saw this exact last_use value.
    A changed last_use resets the clock (the model was used).
    """
    entry = state.get(name)
    if entry is None or entry.get("last_use") != last_use:
        state[name] = {"last_use": last_use, "observed_at": now}
        return 0.0
    return (now - entry["observed_at"]) / 60.0


def sweep(dry_run: bool = False) -> list[str]:
    """One eviction pass. Returns names of evicted (or would-evict) models."""
    avail = available_ram_gb()
    try:
        state = json.loads(STATE_PATH.read_text())
    except Exception:
        state = {}
    try:
        health = _http_json(f"{BASE}/api/v1/health", timeout=10)
        loaded = health.get("all_models_loaded", [])
        catalog = {m["id"]: m for m in _http_json(f"{BASE}/api/v1/models", timeout=10).get("data", [])}
    except Exception as exc:
        logger.warning("sweep: server unreachable (%s)", exc)
        return []

    now = time.time()
    evicted: list[str] = []
    for m in loaded:
        name = m.get("model_name", "")
        idle_min = observe_idle_minutes(state, name, m.get("last_use", -1), now)
        size = effective_size_gb(catalog.get(name, {})) if name in catalog else None
        if avail < RAM_TRIGGER_GB and eligible(m, idle_min, size):
            if not dry_run:
                try:
                    _http_json(f"{BASE}/api/v1/unload", {"model_name": name}, timeout=60)
                except Exception as exc:
                    logger.warning("unload %s failed: %s", name, exc)
                    continue
                state.pop(name, None)
            evicted.append(name)
            line = (
                f"{time.strftime('%Y-%m-%dT%H:%M:%S')} evicted {name} "
                f"(size={size:.1f}GB idle={idle_min:.0f}min avail={avail:.1f}GB)\n"
            )
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a") as f:
                f.write(line)
            logger.info("%s", line.strip())
            avail = available_ram_gb()  # re-check between evictions

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state))
    return evicted


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--loop", type=int, default=0, metavar="SECONDS",
                   help="sweep every N seconds forever (0 = one sweep and exit)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.loop <= 0:
        out = sweep(dry_run=args.dry_run)
        print(json.dumps({"evicted": out, "avail_gb": round(available_ram_gb(), 1)}))
        return
    while True:
        sweep(dry_run=args.dry_run)
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
