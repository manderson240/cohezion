"""Item 118: Bot full-fabric tier routing — report-only plan (compound variant).

``bot_tier_plan(message, *, engines)`` proposes which engine the Hermes bot
should use for a turn, applying the Triune routing ladder to the bot's own traffic:

    short / classify  → NPU   (fast categorical, 42 TPS, llama3.2-1b-FLM)
    interactive chat  → iGPU  (~200ms, RDNA 3.5, Qwen3.6-A3B)
    long / reasoning  → CPU   (~800ms, 32-thread, Gemma-4-31B)

Composes item-114 :func:`~cohezion.compound.fabric_utilization.place_task` for
engine selection respecting capacity, and the Hermes ``smart_model_routing``
length signal to determine the task_kind.

Report-only — the actual Hermes config change (``cheap_model``→NPU model,
add a CPU escalation aux) is gateway-STOPPED and must be applied separately.

Pure (injected ``engines``; no live gateway probe under pytest).

User directive 2026-06-06: "the bot should also leverage the full neural net."
"""

from __future__ import annotations

from dataclasses import dataclass

from cohezion.compound.fabric_utilization import Engine, place_task


# ---------------------------------------------------------------------------
# Length thresholds (message classification)
# ---------------------------------------------------------------------------

# Messages at-or-below this length are classified as "short" → NPU / classify tier.
# Calibrated so "hi" / "" → short, "explain FLUME vae plz" (21 chars) → normal with default.
_DEFAULT_SHORT_MAX_CHARS: int = 20

# Messages above this length are classified as "long/deep-reasoning" → CPU tier.
# Calibrated so normal conversational messages (~50-200 chars) → iGPU, long analysis → CPU.
_DEFAULT_LONG_MIN_CHARS: int = 200


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BotTierPlan:
    """Report-only tier plan for one Hermes bot turn (item 118).

    Attributes
    ----------
    proposed_engine:
        The engine the bot should use: ``"npu"``, ``"igpu"``, or ``"cpu"``.
        ``None`` when all engines are at capacity (caller queues / retries).
    message:
        The original bot message (forwarded for observability).
    task_kind:
        Derived task classification: ``"classify"``, ``"interactive"``, or
        ``"deep-reasoning"``.  Maps directly to item-114 task affinity.
    """

    proposed_engine: str | None
    message: str
    task_kind: str


# ---------------------------------------------------------------------------
# bot_tier_plan
# ---------------------------------------------------------------------------


def bot_tier_plan(
    message: str,
    *,
    engines: list[Engine],
    short_max_chars: int = _DEFAULT_SHORT_MAX_CHARS,
    long_min_chars: int = _DEFAULT_LONG_MIN_CHARS,
) -> BotTierPlan:
    """Propose which engine the Hermes bot should use for *message* (item 118). READ-ONLY.

    Applies the Triune routing ladder to the bot's own traffic:

    1. ``len(message) <= short_max_chars``  → ``"classify"`` task → NPU
    2. ``len(message) >= long_min_chars``   → ``"deep-reasoning"`` task → CPU
    3. Otherwise                            → ``"interactive"`` task → iGPU

    Then delegates to :func:`~cohezion.compound.fabric_utilization.place_task`
    to respect engine capacity (spillover when preferred engine is at capacity).
    Returns ``proposed_engine=None`` when all engines are at capacity.

    Args:
        message:
            The incoming Hermes bot message (may be empty).
        engines:
            Injected fleet snapshot.  No live gateway probe is made.
        short_max_chars:
            Inclusive upper bound on message length for the NPU / classify tier.
            Defaults to :data:`_DEFAULT_SHORT_MAX_CHARS` (20).
        long_min_chars:
            Inclusive lower bound for the CPU / deep-reasoning tier.
            Defaults to :data:`_DEFAULT_LONG_MIN_CHARS` (200).

    Returns:
        :class:`BotTierPlan` with the proposed engine, original message, and
        derived task_kind.

    Pure (no writes, no network calls).  Report-only.
    """
    msg_len = len(message)

    # Classify the turn.
    if msg_len <= short_max_chars:
        task_kind = "classify"
        _place_kind = "classify"
    elif msg_len >= long_min_chars:
        task_kind = "deep-reasoning"
        _place_kind = "deep_reasoning"  # fabric_utilization key uses underscore
    else:
        task_kind = "interactive"
        _place_kind = "interactive"

    # Delegate placement to item-114 place_task (respects capacity + spillover).
    proposed = place_task(_place_kind, engines=engines)

    return BotTierPlan(
        proposed_engine=proposed,
        message=message,
        task_kind=task_kind,
    )
