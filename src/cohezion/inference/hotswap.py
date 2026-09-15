"""Demand-driven model hotswap for the Lemonade fleet — the missing composition.

Every piece of this already existed; none of them closed the loop:

* ``inference/oom_guard.pre_load_gate`` answers "is this load safe?" but only ever
  REFUSES — it never frees anything.
* ``platform/oom_evictor.OOMEvictor`` really unloads, but only on a memory-pressure
  CRITICAL rising edge — it is pressure-driven, not demand-driven.
* ``inference/ram_scheduler.RamScheduler.ensure_loaded`` is explicitly advisory
  ("does not make HTTP calls") and its LRU starts EMPTY, so a fresh instance believes
  0 GB is in use while ten models are resident.
* ``compound/autonomous_loop/local_executor._recover_model`` makes the correct
  unload+load calls, but is private and only reloads the SAME model.

This module closes it: **gate → evict LRU → re-gate → load**, driven by demand.

Two design choices worth keeping:

1. **Residency and LRU come from the SERVER, not local bookkeeping.**
   ``/api/v1/health`` reports ``model_name``, ``last_use`` and ``is_busy`` per model, so
   the eviction victim is chosen from ground truth. Local LRU tables drift the moment
   anything else loads a model (measured: the fleet churned three times in one session).

2. **Free RAM is read from /proc/meminfo, not assumed.** A fixed "88 GB available"
   ceiling is fiction on a box that was at 14.3 GB with swap exhausted.

3. **The resident fleet is COUNT-capped (default 3), not just RAM-gated.** The fit gate
   bounds each load's SIZE; the 2026-09-14 OOM spiral showed the gap — 7 models resident
   at once, every load individually "fitting", collectively fatal. The LRU loop never
   fired because nothing asked it to; the cap gives it a second trigger.

N3 safety, non-negotiable:
  * every load carries a BOUNDED ``ctx_size`` (unbounded KV cache is the documented
    2026-06-09 hard-freeze vector),
  * a load is REFUSED rather than attempted when it still does not fit after eviction,
  * a BUSY model is never evicted,
  * callers may ``protect`` models that must not be evicted,
  * the resident set is COUNT-capped (``DEFAULT_MAX_RESIDENT``): at/over the cap the
    gate frees a slot first, and refuses when it cannot.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

LEMONADE_BASE = "http://localhost:13305"
RAM_FLOOR_GB = 16.0  # harness N3 item 5: never consume the last 16 GB
MAX_CTX = 16384  # N3 cap; callers may request less, never more

# Hard cap on the resident fleet. 2026-09-14 the box died with 7 models resident at once
# ('Total loaded: 7' at 20:43, GTT pinned 61-62G, swap 50-56%): the fit gate bounds each
# load's SIZE, but nothing bounded the COUNT — LRU eviction only fired when a load did
# not fit, so a fleet of individually-harmless models could creep to any count, and the
# fatal straw was one more auto-load. The cap is the count-side twin of RAM_FLOOR_GB.
DEFAULT_MAX_RESIDENT = 3
ENV_MAX_RESIDENT = "COHEZION_MAX_RESIDENT_MODELS"


@dataclass
class SwapResult:
    ok: bool
    model_id: str
    reason: str
    evicted: list[str] = field(default_factory=list)
    already_resident: bool = False


def _post(path: str, payload: dict, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(  # noqa: S310 - fixed localhost base
        f"{LEMONADE_BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return r.status, r.read().decode(errors="ignore")[:200]
    except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
        return e.code, e.read().decode(errors="ignore")[:200]
    except Exception as exc:
        return 0, str(exc)[:200]


def free_gb_or_none() -> float | None:
    """Actual MemAvailable in GB, or None when UNREADABLE.

    The distinction matters because the two consumers need OPPOSITE polarities:
    admission must fail CLOSED (treat unknown as no headroom, refuse the load),
    but reclaim must ABSTAIN (treat unknown as "do not evict") — reading the
    0.0 sentinel as a real measurement made ``tick()`` tear down the entire
    non-protected fleet whenever /proc/meminfo was unreadable.
    """
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1048576
    except Exception:
        pass
    return None


def free_gb() -> float:
    """Actual MemAvailable in GB. Returns 0.0 when unreadable (fail-closed).

    Admission-path view of ``free_gb_or_none()`` — unknown means "assume no
    headroom". Reclaim paths must use ``free_gb_or_none()`` and abstain.
    """
    v = free_gb_or_none()
    return 0.0 if v is None else v


def resident_models_or_none() -> list[dict] | None:
    """Loaded models newest-used first, or None when /health is UNREACHABLE.

    Callers that verify a postcondition (``unload``) must distinguish "the
    model is gone" from "the server could not be asked" — collapsing both to
    ``[]`` made phantom unloads report success under a degraded /health.
    """
    try:
        with urllib.request.urlopen(  # noqa: S310
            f"{LEMONADE_BASE}/api/v1/health", timeout=10
        ) as r:
            health = json.loads(r.read())
    except Exception as exc:
        logger.debug("hotswap: health unavailable: %s", exc)
        return None
    out = [m for m in (health.get("all_models_loaded") or []) if m.get("loaded")]
    out.sort(key=lambda m: m.get("last_use") or 0, reverse=True)
    return out


def resident_models() -> list[dict]:
    """Loaded models from the server, newest-used first. Empty on any failure."""
    return resident_models_or_none() or []


def _catalog_sizes() -> dict[str, float]:
    try:
        with urllib.request.urlopen(  # noqa: S310
            f"{LEMONADE_BASE}/api/v1/models", timeout=10
        ) as r:
            data = json.loads(r.read()).get("data", [])
    except Exception:
        return {}
    return {m["id"]: float(m["size"]) for m in data if isinstance(m.get("size"), (int, float))}


_PARAM_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*B(?![a-z])", re.IGNORECASE)

# Floor bytes-per-parameter. The most aggressive quantisation anyone actually ships is ~1
# bit/weight, i.e. 0.125 GB per billion params. Half that is used as the floor so a genuinely
# exotic quant (e.g. Bonsai-27B-gguf-Q1_0 at 4.41GB = 0.163 GB/B) is never wrongly rejected.
_MIN_GB_PER_B = 0.0625


def params_b_from_name(model_id: str) -> float | None:
    """Parameter count in billions, parsed from a model id. None when absent.

    Two traps this handles:
      * ``Gemma-4-26B`` — the leading 4 is a VERSION, not a size. Only ``<n>B`` counts.
      * ``35B-A3B`` — 35B total, 3B ACTIVE. Residency is driven by TOTAL (all experts must
        be reachable), so the MAXIMUM match is taken; reading A3B would under-gate by 10x.
    """
    matches = _PARAM_RE.findall(model_id or "")
    if not matches:
        return None
    try:
        return max(float(m) for m in matches)
    except ValueError:
        return None


def implausible_size_gb(model_id: str, size_gb: float) -> bool:
    """True when a reported size is too small to be real for that parameter count.

    A WRONG size is more dangerous than a missing one: ``ensure_resident`` already refuses an
    unknown size, but a wrong one looks like knowledge and passes the gate. Measured
    2026-08-04: the live catalog reports ``Qwen3.6-35B-A3B-GGUF`` at 1.68 GB — a 35B cannot
    be (its MTP sibling reports 22.10 GB). Trusting it would compute needed=2.68GB, admit,
    and then attempt a ~20 GB load — the blind cold load N3 item 5 forbids.

    Fails OPEN when the parameter count is unknown: there is no floor to compare against, and
    the existing unknown-size path already covers genuinely missing metadata.
    """
    params = params_b_from_name(model_id)
    if params is None:
        return False
    return size_gb < params * _MIN_GB_PER_B


def _kv_overhead_gb(weights_gb: float) -> float:
    """Mirrors ram_scheduler._kv_overhead: KV cache at a bounded ctx_size."""
    return 3.0 if weights_gb > 10.0 else 1.0


def unload(model_id: str, timeout: float = 30.0) -> bool:
    """Unload one model and VERIFY the RAM actually came back.

    ``force: true`` is sent unconditionally, but the claim that it is REQUIRED is STALE.

    Re-measured 2026-07-29 on lemonade 11.5.0: a plain unload with NO force works for IDLE
    models — ``Gemma-4-E4B-it-GGUF`` (5.56 GB) took RAM 80 -> 86 GB and left the resident set;
    the CLI ``lemonade unload`` freed 20 GB on Gemma-4-31B. The original claim (skill
    lemonade-heavy-model-safe-enablement, 2026-07-23) presumably held on an older build.
    NOT re-tested on a BUSY model, where force may still matter — so it stays, being harmless.

    THE DURABLE HALF IS UNCHANGED, and is why this function exists: a 200 does not prove the
    RAM came back. Success is defined by the POSTCONDITION — the model is no longer in the
    resident set — not by the status code. Returning True on a phantom unload would make the
    caller believe it had freed memory and proceed into a load that OOMs.
    """
    status, body = _post("/api/v1/unload", {"model_name": model_id, "force": True}, timeout)
    if status not in (200, 204, 404):
        logger.warning("hotswap: unload %s -> HTTP %s %s", model_id, status, body)
        return False
    server = resident_models_or_none()
    if server is None:
        logger.warning(
            "hotswap: unload %s returned HTTP %s but /health is unreachable — "
            "cannot VERIFY the postcondition, refusing to claim success",
            model_id,
            status,
        )
        return False
    still_resident = model_id in {m.get("model_name", "") for m in server}
    if still_resident:
        logger.warning(
            "hotswap: PHANTOM UNLOAD — %s returned HTTP %s but is still resident; "
            "RAM was not freed",
            model_id,
            status,
        )
        return False
    logger.info("hotswap: unloaded %s (verified not resident)", model_id)
    return True


def _resolve_max_resident(max_resident: int | None) -> int:
    """Effective cap: explicit param > ``ENV_MAX_RESIDENT`` > ``DEFAULT_MAX_RESIDENT``.

    The env override exists so ops can tighten/loosen the cap on a degraded box without a
    code change (the 2026-09-14 spiral needed exactly that at 20:43). A malformed or
    non-positive env value is ignored rather than trusted: an env var is an unvetted
    input, and a cap of 0 would refuse every load — that must be a deliberate param, not
    a typo in a profile export.
    """
    if max_resident is not None:
        return int(max_resident)
    raw = os.environ.get(ENV_MAX_RESIDENT)
    if raw:
        try:
            v = int(raw)
        except ValueError:
            logger.warning("hotswap: ignoring non-integer %s=%r", ENV_MAX_RESIDENT, raw)
        else:
            if v > 0:
                return v
            logger.warning("hotswap: ignoring non-positive %s=%r", ENV_MAX_RESIDENT, raw)
    return DEFAULT_MAX_RESIDENT


def ensure_resident(
    model_id: str,
    *,
    ctx_size: int = MAX_CTX,
    min_free_gb: float = RAM_FLOOR_GB,
    protect: tuple[str, ...] = (),
    load_timeout: float = 300.0,
    ledger: object | None = None,
    max_resident: int | None = None,
) -> SwapResult:
    """Make ``model_id`` resident, evicting least-recently-used models if needed.

    Returns a :class:`SwapResult`; never raises. A refusal is a SUCCESSFUL outcome of the
    safety gate — callers should fall back to another lane rather than retry.

    ``max_resident`` hard-caps the resident fleet (default
    ``DEFAULT_MAX_RESIDENT`` = 3, overridable via ``ENV_MAX_RESIDENT``; an explicit
    param wins over the env). When the server already holds >= the cap and the target is
    not among them, LRU non-busy non-protected models are evicted until the target's slot
    is open AND the weights+KV fit check passes; if that cannot be satisfied, the gate
    refuses — refusing is success for the gate, and callers fall back to another lane.
    The cap check runs BEFORE the fit gate so eviction decisions account for it.

    ``ledger`` (a :class:`~cohezion.inference.residency_ledger.ResidencyLedger`) is the
    degraded-mode fallback. ``resident_models()`` reads ``/api/v1/health``, which stops
    answering under exactly the memory pressure this gate exists to relieve; it then
    returns ``[]``, which yields an empty VICTIM list and a permanently-refusing gate.
    With a ledger supplied, eviction stays possible. The server still wins whenever it
    answers — passing a ledger never overrides ground truth.
    """
    max_resident = _resolve_max_resident(max_resident)
    ctx_size = max(1024, min(int(ctx_size), MAX_CTX))

    loaded = resident_models()
    if ledger is not None:
        from cohezion.inference.residency_ledger import resident_view

        loaded = resident_view(loaded, ledger)  # type: ignore[arg-type]
    names = {m.get("model_name", "") for m in loaded}
    if model_id in names:
        return SwapResult(True, model_id, "already resident", already_resident=True)

    sizes = _catalog_sizes()
    weights = sizes.get(model_id)
    if weights is None:
        # Refusing a blind cold load is deliberate: an unknown footprint cannot be gated,
        # and an mmap load that "succeeds" still page-storms the box (N3 item 5).
        return SwapResult(False, model_id, "unknown weight size — refusing blind cold load")
    if implausible_size_gb(model_id, weights):
        # Bad metadata is worse than missing metadata: it passes the gate. Route it to the
        # same refusal rather than sizing a load from a number that cannot be true.
        params = params_b_from_name(model_id)
        return SwapResult(
            False,
            model_id,
            f"implausible catalog size {weights:.2f}GB for a {params:g}B model — "
            f"refusing blind cold load (bad metadata defeats the weights-fit gate)",
        )
    needed = weights + _kv_overhead_gb(weights)

    evicted: list[str] = []
    # Victims: least-recently-used first, never busy, never protected, never the target.
    victims = [
        m
        for m in reversed(loaded)
        if not m.get("is_busy")
        and m.get("model_name") not in protect
        and m.get("model_name") != model_id
    ]

    # COUNT cap BEFORE the fit gate: eviction decisions must account for the slot the
    # target needs, not just its bytes. The 2026-09-14 spiral had 7 models resident with
    # every load individually fitting — a RAM-only trigger evicts nothing on the way to
    # model #8. `over` is how many models must GO before the target may come in
    # (len(loaded) - (max_resident - 1)); the fit deficit, if any, is folded into the
    # SAME loop below, so one eviction pass serves both the cap and the RAM gate.
    #
    # Only victims (non-busy, non-protected) can be evicted: when the non-evictable set
    # alone already holds the fleet at/over the cap, `over` stays positive, the loop
    # cannot satisfy it, and the post-loop check refuses with the cap reason.
    over = max(0, len(loaded) - (max_resident - 1))

    # Refuse BEFORE evicting when even a full teardown of the evictables cannot get the
    # count under the cap. Eviction is destructive and slow; discovering the cap refusal
    # afterwards costs every unloadable model its slot for nothing. (The byte-side twin of
    # this shortcut is the fit check below — same philosophy, count instead of bytes.)
    if over > 0 and len(victims) < over:
        return SwapResult(
            False,
            model_id,
            f"resident model cap reached ({max_resident}): {len(loaded)} resident but only "
            f"{len(victims)} evictable (busy/protected models are never evicted) — "
            f"refusing load of {model_id}",
        )

    # Refuse BEFORE evicting when even a full teardown provably cannot fit the target.
    # Eviction is destructive and slow; discovering the refusal afterwards costs the whole
    # fleet for nothing. Observed live 2026-08-03: a 128B model evicted 4 models and was
    # then refused by 0.1 GB.
    #
    # This is an OPTIMISATION, so it only fires when it can be CERTAIN. A victim whose size
    # is unknown might still free real memory, so treating it as 0 would refuse loads that
    # the eviction loop would have satisfied (caught by HS4). When any victim size is
    # unknown, skip the shortcut and let the loop decide empirically.
    #
    # The cap is folded into this accounting: the first `over` victims will be consumed by
    # the cap regardless of the byte math, and further victims only as the byte math
    # demands — so `reachable` is the budget plus exactly the bytes the combined loop
    # would actually free, never the whole victim pool.
    victim_sizes = [sizes.get(m.get("model_name", "")) for m in victims]
    if all(s is not None for s in victim_sizes):
        # Inside this branch every entry is known; the None-filtered comprehension
        # re-materialises them as floats for the arithmetic below (narrowing the type).
        known = [s for s in victim_sizes if s is not None]
        budget = free_gb() - min_free_gb
        cap_bytes = sum(known[:over])
        remaining = needed - budget
        byte_bytes = 0.0
        for s in known[over:]:
            if remaining <= 0:
                break
            byte_bytes += s
            remaining -= s
        reachable = budget + cap_bytes + byte_bytes
        if reachable < needed:
            return SwapResult(
                False,
                model_id,
                # Preserves HS3's contract ("insufficient RAM" in the reason) while adding
                # the new detail. Widening a message is non-destructive; rewriting a
                # pre-existing test's assertion to match new wording would not be.
                f"insufficient RAM — refused before evicting: need {needed:.1f}GB, "
                f"max reachable {reachable:.1f}GB even after evicting {len(victims)}",
            )

    while (over > 0 or (free_gb() - min_free_gb) < needed) and victims:
        victim = victims.pop(0)
        vid = victim.get("model_name", "")
        if unload(vid):
            evicted.append(vid)
            if ledger is not None:
                # Write-through on the VERIFIED postcondition, not on the status code —
                # `unload` already refuses to report success for a phantom unload.
                ledger.record_unload(vid)  # type: ignore[attr-defined]
            if over > 0:
                over -= 1
        else:
            logger.debug("hotswap: could not evict %s; trying next", vid)

    budget = free_gb() - min_free_gb
    if budget < needed:
        return SwapResult(
            False,
            model_id,
            f"insufficient RAM after evicting {len(evicted)}: "
            f"need {needed:.1f}GB, budget {budget:.1f}GB "
            f"(free {free_gb():.1f}GB - {min_free_gb:.0f}GB floor)",
            evicted=evicted,
        )
    if over > 0:
        # The cap could not be met: every remaining resident model is busy or protected
        # (or its unload failed), and the count still exceeds what the target may join.
        # Refusal — not an out-of-cap load — is the success path here; callers fall back.
        return SwapResult(
            False,
            model_id,
            f"resident model cap reached ({max_resident}): {len(loaded)} resident, "
            f"{len(loaded) - len(evicted)} remain after evicting {len(evicted)}, "
            f"all busy/protected or unload-failed — refusing load of {model_id}",
            evicted=evicted,
        )

    status, body = _post(
        "/api/v1/load",
        {"model_name": model_id, "ctx_size": ctx_size, "save_options": False},
        load_timeout,
    )
    if status != 200:
        return SwapResult(False, model_id, f"load failed: HTTP {status} {body}", evicted=evicted)

    # Verify rather than trust the status code — a 200 that did not produce residency
    # would otherwise look identical to success.
    #
    # The verification reads the SAME endpoint that degrades under memory pressure, and an
    # empty result is AMBIGUOUS: it means both "health answered, fleet is empty" and "health
    # did not answer". Collapsing the two would report every successful load as failed while
    # /health is down.
    #
    # Strictness is therefore the DEFAULT and is only relaxed when the caller passes a
    # ledger — that is the explicit signal that it expects to operate through a degraded
    # /health. Without one, an unobservable load stays a failure (HS7).
    server_now = resident_models()
    if model_id in {m.get("model_name", "") for m in server_now}:
        if ledger is not None:
            ledger.record_load(model_id, weights)  # type: ignore[attr-defined]
        return SwapResult(True, model_id, f"loaded (ctx_size={ctx_size})", evicted=evicted)

    if ledger is None or server_now:
        # Either strict mode, or health DID answer and genuinely lacks the model.
        return SwapResult(
            False, model_id, "load returned 200 but model is not resident", evicted=evicted
        )

    ledger.record_load(model_id, weights)  # type: ignore[attr-defined]
    return SwapResult(
        True,
        model_id,
        f"loaded (ctx_size={ctx_size}) — residency UNVERIFIED: /health reported nothing",
        evicted=evicted,
    )
