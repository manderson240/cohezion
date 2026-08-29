"""Byte-budgeted, device-aware residency planning for 24/7 local inference.

Lemonade caps residency by COUNT (`max_loaded_models`, per model type). On a
unified-memory box that is the wrong unit: three 0.6B models consume the same
slot budget as three 35B models (1 GB vs 66 GB). This module plans residency in
BYTES and in DEVICES, then expresses the result as actions the supervisor may
safely apply.

Design stance
-------------
* **Advisory, not autonomous.** `plan()` returns actions; it never mutates the
  server. Application is a separate, explicitly-gated step.
* **Fail closed.** An empty or unreachable census yields an empty plan with a
  warning, never a speculative eviction.
* **Protected models are inviolable.** Eviction candidates are drawn only from
  `ResidentModel.evictable`, which itself requires positive proof of idleness.
"""

from __future__ import annotations

from dataclasses import dataclass

from cohezion.inference.silicon_residency import ResidentModel, SiliconCensus


__all__ = [
    "DEFAULT_POLICY",
    "ResidencyAction",
    "ResidencyPlan",
    "ResidencyPolicy",
    "SiliconSlot",
    "plan_residency",
]


@dataclass(frozen=True)
class SiliconSlot:
    """The model a given piece of silicon should be carrying 24/7."""

    device: str
    model: str
    ctx_size: int
    role: str
    pin: bool = False
    rationale: str = ""


@dataclass(frozen=True)
class ResidencyPolicy:
    """Desired steady state for the fleet plus the safety envelope."""

    slots: tuple[SiliconSlot, ...] = ()
    # RAM that must remain free for the OS, agents and page cache. Loads that
    # would breach this floor are refused rather than attempted.
    reserve_gb: float = 24.0
    # Hard ceiling on total resident model bytes, independent of free RAM.
    max_resident_gb: float = 80.0
    # ctx_size above which we refuse to plan a load (KV cache blow-up guard).
    max_ctx_size: int = 32768
    # Devices that can hold exactly ONE model at a time. Measured on Strix Halo
    # 2026-08-29: across every census the NPU held exactly one model, never two
    # -- FastFlowLM occupies the XDNA2 accelerator exclusively.
    #
    # This matters because two Cohezion builders request DIFFERENT models on it:
    #   build_triune_omni_orchestrator -> llama3.2-1b-FLM   (tier-0 routing)
    #   build_reasoning_orchestrator   -> deepseek-r1-8b-FLM (reasoning)
    # Both live in compound/local_inference.py, so they thrash the single slot.
    # Measured cost: 12-20s per tier-0 call (model swap) versus 0.47s when the
    # model is already resident -- a ~40x penalty that destroys the entire value
    # of a "cheap fast tier" and is why the NPU shows no productive traffic.
    single_slot_devices: frozenset[str] = frozenset({"npu"})

    def slot_for(self, device: str) -> SiliconSlot | None:
        for slot in self.slots:
            if slot.device == device:
                return slot
        return None


# Grounded in measured Strix Halo hardware (2026-08-29):
#   NPU  XDNA2      llama3.2-1b-FLM  63.6 tok/s decode, 0.47s TTFT (measured live)
#   iGPU RDNA3.5    Gemma-4-E4B      structured generation / vision
#   CPU  32C AVX512 A3B MoE          30B total but ~3B active per token, which is
#                                    what makes a big model viable on CPU at all
DEFAULT_POLICY = ResidencyPolicy(
    slots=(
        SiliconSlot(
            device="npu",
            model="llama3.2-1b-FLM",
            ctx_size=4096,
            role="classify/route (tier 0)",
            pin=True,
            rationale=(
                "Every routing decision depends on this model. Unpinned it is "
                "LRU-evictable, so its availability would be accidental rather "
                "than structural."
            ),
        ),
        SiliconSlot(
            device="igpu",
            model="Gemma-4-E4B-it-GGUF",
            ctx_size=8192,
            role="structured generation / code (tier 1)",
            pin=False,
            rationale="Vision + tool-calling tier; cheap to reload if evicted.",
        ),
        SiliconSlot(
            device="cpu",
            model="Nemotron-3-Nano-30B-A3B-GGUF",
            ctx_size=16384,
            role="multi-step reasoning (tier 2)",
            pin=False,
            rationale=(
                "A3B MoE activates ~3B of 30B params per token, which is the "
                "only shape that makes a 30B model serviceable on AVX-512 CPU. "
                "Occupies otherwise-idle silicon."
            ),
        ),
    ),
)


@dataclass(frozen=True)
class ResidencyAction:
    """A single proposed change, with the reason it is being proposed."""

    verb: str  # "load" | "pin" | "unpin" | "evict"
    model: str
    device: str = ""
    ctx_size: int | None = None
    reason: str = ""

    def as_command(self) -> str:
        """The lemonade CLI equivalent, for operator review before applying."""
        if self.verb == "load":
            return f"lemonade load {self.model} --ctx-size {self.ctx_size}"
        if self.verb in ("pin", "unpin"):
            return f"lemonade {self.verb} {self.model}"
        if self.verb == "evict":
            return f"lemonade unload {self.model}"
        return f"# unknown verb {self.verb}"

    def __str__(self) -> str:
        return f"{self.verb.upper():6s} {self.model:34s} [{self.device or '?'}] {self.reason}"


@dataclass(frozen=True)
class ResidencyPlan:
    """Advisory plan: what to change, what was refused, and why."""

    actions: tuple[ResidencyAction, ...] = ()
    warnings: tuple[str, ...] = ()
    refused: tuple[str, ...] = ()
    idle_devices: tuple[str, ...] = ()
    resident_gb: float = 0.0
    headroom_gb: float = 0.0

    @property
    def is_noop(self) -> bool:
        return not self.actions

    def of(self, verb: str) -> tuple[ResidencyAction, ...]:
        return tuple(a for a in self.actions if a.verb == verb)

    @property
    def summary(self) -> str:
        by_verb = {v: len(self.of(v)) for v in ("load", "pin", "unpin", "evict")}
        counts = " ".join(f"{v}={n}" for v, n in by_verb.items() if n)
        return (
            f"plan[{counts or 'noop'}] resident={self.resident_gb:g}GB "
            f"headroom={self.headroom_gb:g}GB "
            f"warnings={len(self.warnings)} refused={len(self.refused)}"
        )


def _catalog_size(catalog: list[dict] | None, model_id: str) -> float | None:
    """Size in GB, or None when it cannot be determined.

    None and 0.0 are DIFFERENT answers and conflating them bypasses the byte
    budget: an earlier revision returned 0.0 both for "not in the catalog" and
    for "in the catalog with no `size` key". Only the first case was caught by
    `_catalog_has`, so an entry like `{"id": "Nemotron-3-Nano-30B-A3B-GGUF"}`
    scored 0.0, passed `size > headroom` trivially, and subtracted nothing from
    the remaining budget. With `--heal` that becomes a real `lemonade load` of a
    30B model at zero headroom.

    Catalog entries genuinely lack `size` -- `kokoro-v1` does on this fleet, and
    `hotswap.py:110` already filters for a numeric `size` for the same reason.
    """
    for entry in catalog or []:
        if entry.get("id") == model_id:
            size = entry.get("size")
            return float(size) if isinstance(size, (int, float)) else None
    return None


def _catalog_has(catalog: list[dict] | None, model_id: str) -> bool:
    return any(e.get("id") == model_id for e in catalog or [])


def plan_residency(
    census: SiliconCensus,
    policy: ResidencyPolicy = DEFAULT_POLICY,
    catalog: list[dict] | None = None,
    available_gb: float = 0.0,
) -> ResidencyPlan:
    """Compute the advisory delta between the live census and the policy.

    `available_gb` is host RAM currently free. Loads are refused when they would
    breach `policy.reserve_gb` or `policy.max_resident_gb`.
    """
    actions: list[ResidencyAction] = []
    warnings: list[str] = []
    refused: list[str] = []

    # NOTE: an empty census is NOT treated as "router unreachable" and refused.
    # The daemon already handles an unreachable router in its own except branch
    # (it emits router_unreachable and keeps the last good census), so the only
    # way to reach here with no residents is a REACHABLE router with an EMPTY
    # fleet -- precisely the cold-boot state `--heal` exists to fix. An earlier
    # revision refused here, which meant the supervisor could never bootstrap
    # the tier-0 NPU router it was written to keep resident.

    resident_gb = census.total_resident_gb
    by_name = {m.name: m for m in census.residents}

    # --- hazards observed in the live fleet ---------------------------------
    for hazard in census.ctx_hazards:
        if hazard.ctx_crasher:
            warnings.append(
                f"{hazard.name} runs with ctx_size=0 -- the documented Strix Halo "
                f"hard-hang vector (harness N3)"
            )
        else:
            warnings.append(
                f"{hazard.name} has no explicit ctx cap (ctx_size={hazard.ctx_size}); "
                f"KV cache is sized by the model's own advertised window"
            )
    for flapped in census.watchdog_resets:
        warnings.append(f"{flapped.name} was restarted by the server watchdog")
    for sick in census.unhealthy:
        warnings.append(f"{sick.name} backend unhealthy: {sick.backend_health!r}")

    # --- budget --------------------------------------------------------------
    # available_gb <= 0 means the caller could not MEASURE free RAM
    # (`_available_ram_gb()` returns 0.0 on OSError or a missing MemAvailable
    # line). An earlier revision then fell back to the byte ceiling alone,
    # silently dropping the entire RAM reserve -- so a 21 GB load could proceed
    # against the nominal 80 GB ceiling on a box with 4 GB free. "Could not
    # measure" must REFUSE, not skip: headroom is zero and every load is
    # refused with a reason.
    ram_budget = max(0.0, available_gb - policy.reserve_gb)
    byte_budget = max(0.0, policy.max_resident_gb - resident_gb)
    if available_gb <= 0:
        warnings.append(
            "free RAM could not be measured (available_gb<=0); refusing all loads "
            "rather than planning against an unenforced reserve"
        )
        headroom = 0.0
    else:
        headroom = min(ram_budget, byte_budget)

    # --- per-device policy reconciliation ------------------------------------
    for slot in policy.slots:
        occ = census.occupancy(slot.device)
        resident = by_name.get(slot.model)

        if resident is None:
            if not _catalog_has(catalog, slot.model) and catalog is not None:
                refused.append(f"{slot.model}: not present in the model catalog - cannot load")
                continue
            size = _catalog_size(catalog, slot.model)
            if size is None:
                refused.append(
                    f"{slot.model}: catalog entry has no `size`, so the byte budget "
                    f"cannot be checked -- refusing rather than loading blind"
                )
                continue
            if size > headroom:
                refused.append(
                    f"{slot.model}: needs {size:g}GB but only {headroom:g}GB "
                    f"headroom (reserve={policy.reserve_gb:g}GB)"
                )
                continue
            if slot.ctx_size > policy.max_ctx_size:
                refused.append(
                    f"{slot.model}: ctx_size {slot.ctx_size} exceeds "
                    f"max_ctx_size {policy.max_ctx_size}"
                )
                continue
            actions.append(
                ResidencyAction(
                    verb="load",
                    model=slot.model,
                    device=slot.device,
                    ctx_size=slot.ctx_size,
                    reason=f"{slot.device} has no {slot.role} resident",
                )
            )
            headroom -= size
            continue

        # Resident, but is it on the silicon the policy intends?
        if resident.device != slot.device:
            warnings.append(
                f"{slot.model} is resident on {resident.device}, policy expects {slot.device}"
            )

        if slot.pin and not resident.pinned:
            actions.append(
                ResidencyAction(
                    verb="pin",
                    model=slot.model,
                    device=resident.device,
                    reason=slot.rationale or "policy marks this slot as pinned",
                )
            )

        if occ.count == 0:  # defensive: resident but device bucket empty
            warnings.append(f"{slot.device} occupancy inconsistent with residents")

    # --- single-slot contention ----------------------------------------------
    # A load onto a single-slot device DISPLACES whatever is there. If some other
    # caller wants the incumbent, the two thrash and every call pays a model
    # swap. Measured on Strix Halo 2026-08-29: 12-20s per swap versus 0.47s when
    # already resident. Silent thrash looks like "the NPU tier is just slow".
    for slot in policy.slots:
        if slot.device not in policy.single_slot_devices:
            continue
        occ = census.occupancy(slot.device)
        incumbents = [m.name for m in occ.models if m.name != slot.model]
        if incumbents and slot.model not in {m.name for m in occ.models}:
            warnings.append(
                f"{slot.device} is single-slot and holds {', '.join(incumbents)}; "
                f"loading {slot.model} DISPLACES it -- if both are wanted, every "
                f"call pays a model swap (~40x the resident latency)"
            )

    # --- silicon left entirely idle ------------------------------------------
    policy_devices = {s.device for s in policy.slots}
    idle = tuple(sorted(d for d in policy_devices if census.occupancy(d).count == 0))
    for device in idle:
        warnings.append(f"{device} carries no resident model - silicon is idle")

    return ResidencyPlan(
        actions=tuple(actions),
        warnings=tuple(warnings),
        refused=tuple(refused),
        idle_devices=idle,
        resident_gb=resident_gb,
        headroom_gb=round(max(0.0, headroom), 3),
    )


def evictable_candidates(
    census: SiliconCensus,
    need_gb: float,
    protect: frozenset[str] = frozenset(),
) -> tuple[ResidentModel, ...]:
    """Least-recently-used evictable models totalling at least `need_gb`.

    Only models proving `evictable` are eligible, and `protect` (typically the
    policy's pinned slot models) is excluded even when the server has not yet
    applied the pin. Returns () when the need cannot be met safely -- callers
    must treat that as "do not evict", never as "evict what you can".
    """
    pool = [m for m in census.residents if m.evictable and m.name not in protect and m.size_gb > 0]
    pool.sort(key=lambda m: m.last_use)  # oldest first

    chosen: list[ResidentModel] = []
    freed = 0.0
    for model in pool:
        if freed >= need_gb:
            break
        chosen.append(model)
        freed += model.size_gb

    if freed < need_gb:
        return ()
    return tuple(chosen)
