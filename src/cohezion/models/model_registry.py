"""Task-aware model selection registry for SwarmService.

Originally a non-destructive remediation of the V-Model audit §10 finding (`swarm_service.py`
+ `cli` were dark on a missing `cohezion.models.model_registry.ModelRegistry`). Upgraded
2026-06-05 to be **task-aware** (research: docs/research/TASK_HARNESS_ROUTING_LEVERS_2026-06-05.md):

`get_best_for_task(task, ...)` now classifies the task STRING to a `Task` type and asks the
declarative `FleetRegistry.for_task(Task)` for the preferred specialist — "the right model for
the right task". It falls back to the complexity-based `CostAwareRouter` when no task-specialist
is registered (e.g. EXTRACTION before LFM2.5-VL is added), and to `None` when both are
unavailable (so callers fall back to their own default). Fail-soft throughout; never raises.
"""

from __future__ import annotations

import logging

from cohezion.models.routing_log import record_routing_decision


logger = logging.getLogger(__name__)


def _lane_for(model_id: str | None) -> str:
    """Best-effort lane label for a chosen model (from the fleet registry). Fail-soft → ''."""
    if not model_id:
        return ""
    try:
        from cohezion.inference.registry import get_registry

        entry = get_registry().models.get(model_id)
        return str(entry.lane) if entry is not None else ""
    except Exception:
        return ""


# task-string keyword → Task, ordered specific → general (first match wins). Kept here (the
# consumer) rather than in registry.py so the declarative map stays free of heuristics.
_TASK_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("extract", "field extraction", "key-value"), "EXTRACTION"),
    (("ocr", "scanned", "document parse", "doc parse"), "OCR_DOC"),
    (("vision", "image", "visual", "vlm", "caption", "vqa"), "VISION"),
    (("rerank", "re-rank", "reranking"), "RERANK"),
    (("fim", "fill-in", "fill in the middle", "autocomplete", "code completion"), "FIM"),
    (("function call", "function-call", "tool call", "tool-use", "tool use"), "FUNCTION_CALL"),
    (("code", "program", "refactor", "implement"), "CODE_GEN"),
    (("math", "arithmetic", "calculate", "proof", "gsm", "solve for"), "MATH"),
    (("summar", "tl;dr", "condense"), "SUMMARIZATION"),
    (("architect", "design the", "system design"), "ARCHITECT"),
    (("classify", "route to", "dispatch", "triage"), "ROUTING"),
    (("structured", "json", "schema"), "STRUCTURED"),
    (("govern", "policy", "constitution"), "GOVERNANCE"),
    (("long horizon", "long-horizon", "multi-step", "long context"), "LONG_HORIZON"),
    (("sensor", "sensing", "perceiv"), "SENSING"),
    (("reason", "analy", "think", "plan", "evaluate"), "REASONING"),
]

# Per-lane average power draw (watts) on Strix Halo. On a $0-dollar local fleet, ELECTRICITY is
# the differentiator the dollar-based CC2 cost term can't see (all local cost_usd=0). Used to
# break quality/priority ties toward the lower-wattage lane. NEEDS-CALIBRATION against real
# hardware_telemetry.tokens_per_watt before being treated as load-bearing. Lane is a StrEnum so
# its members hash as their string value ("npu", ...) and index this map directly.
_LANE_WATTS: dict[str, float] = {
    "npu": 2.0,  # XDNA2, FastFlowLM <2 W
    "igpu_rocwmma": 35.0,  # RDNA3.5
    "igpu_unified": 35.0,
    "cpu": 55.0,
    # cloud lanes draw ~0 LOCAL watts; their real cost is dollars (handled by CC2).
}
_DEFAULT_WATTS = 50.0


def _classify_task(task: str):
    """Map a free task string to a Task enum member, or None if no confident match."""
    try:
        from cohezion.inference.registry import Task
    except Exception:
        return None
    s = (task or "").strip().lower()
    if not s:
        return None
    # Direct value match first ("reasoning" -> Task.REASONING).
    for member in Task:
        if s == member.value:
            return member
    for keywords, name in _TASK_KEYWORDS:
        if any(k in s for k in keywords) and hasattr(Task, name):
            return getattr(Task, name)
    return None


class ModelRegistry:
    """Selects the best model for a task: task-type specialist first, complexity routing second.

    The CostAwareRouter is built lazily so construction stays cheap (swarm_service builds a
    ModelRegistry eagerly). `get_best_for_task` returns a model-name string, or ``None`` when
    nothing is available so the caller can fall back to its own default.
    """

    def __init__(self, router: object | None = None) -> None:
        # `None` → build a real CostAwareRouter lazily on first use.
        # A non-None value (real router or test fake) is used as-is.
        self._router = router
        self._router_tried = router is not None

    def _ensure_router(self) -> object | None:
        if not self._router_tried:
            self._router_tried = True
            try:
                from cohezion.swarm.cost_aware_router import CostAwareRouter

                self._router = CostAwareRouter()
            except Exception as exc:
                logger.debug("CostAwareRouter unavailable, ModelRegistry inert: %s", exc)
                self._router = None
        return self._router

    def _best_specialist(self, task: str, prefer_fast: bool) -> str | None:
        """Task-TYPE routing: classify task → FleetRegistry.for_task → preferred specialist.

        Returns a model_id, or None when the task is unclassifiable or has no registered
        specialist (so the caller falls back to complexity routing). Fail-soft.
        """
        task_enum = _classify_task(task)
        if task_enum is None:
            return None
        try:
            from cohezion.inference.registry import Lane, get_registry

            candidates = get_registry().for_task(task_enum)  # priority-sorted (best first)
            if not candidates:
                return None

            # Electricity-aware ranking: quality/fitness FIRST (priority, lower=better — encodes
            # task-affinity), then ELECTRICITY (watts) as the tie-breaker among equal-quality
            # candidates. We do NOT let watts override a better-fit model — the NPU is only
            # preferred when it ties on priority, never when a heavier lane is genuinely better
            # at the task. (The continuous quality×energy trade — feynman_path_weight's energy
            # term — belongs in CostAwareRouter, which has real per-model quality scores.)
            def _rank(c) -> tuple[int, float]:
                return (c.priority, _LANE_WATTS.get(c.lane, _DEFAULT_WATTS))

            if prefer_fast:
                local = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}
                preferred = [c for c in candidates if c.lane in local]
                if preferred:
                    return min(preferred, key=_rank).model_id
            return min(candidates, key=_rank).model_id
        except Exception as exc:
            logger.debug("task-specialist lookup failed for %r: %s", task, exc)
            return None

    def _log_routing(self, task: str, model: str | None, *, fell_back: bool) -> None:
        """Fail-soft: record one routing decision to the corpus (item 9 tunes from it)."""
        try:
            task_enum = _classify_task(task)
            task_class = task_enum.name if task_enum is not None else "unclassified"
            record_routing_decision(
                task_class=task_class,
                chosen_model=model,
                lane=_lane_for(model),
                fell_back=fell_back,
            )
        except Exception:
            pass  # logging must never break the routing path

    def get_best_for_task(
        self, task: str, budget: float | None = None, prefer_fast: bool = True
    ) -> str | None:
        """Return the best model name for ``task`` within ``budget``, or ``None`` to fall back.

        Order: (1) task-TYPE specialist from FleetRegistry.for_task (the right model for the
        right task); (2) complexity-based CostAwareRouter; (3) None. ``prefer_fast`` biases
        toward local lanes in (1) and the router's cache-aware fast path in (2). Every
        decision (incl. fallback / no-route) is recorded to the routing corpus (item 2).
        """
        specialist = self._best_specialist(task, prefer_fast)
        if specialist is not None:
            self._log_routing(task, specialist, fell_back=False)
            return specialist

        router = self._ensure_router()
        if router is None:
            self._log_routing(task, None, fell_back=True)
            return None
        try:
            decision, _ = router.select_model(  # type: ignore[attr-defined]
                query=task,
                max_cost_usd=budget,
                cache_hit_rate=0.95 if prefer_fast else None,
            )
            model = getattr(decision, "model", None)
            self._log_routing(task, model, fell_back=True)
            return model
        except Exception as exc:
            logger.debug("ModelRegistry.get_best_for_task failed: %s", exc)
            self._log_routing(task, None, fell_back=True)
            return None
