"""Item 118: Bot full-fabric tier routing — report-only plan (2026-06-08).

``bot_tier_plan(message)`` proposes which compute engine a bot turn should use,
spreading interactive traffic across the full Strix Halo fabric:

  - short / classify   → NPU   (llama3.2-1b-FLM, 42 TPS, $0)
  - interactive chat   → iGPU  (Gemma-4-E4B / Qwen3.6, ~200ms, $0)
  - long / deep        → CPU   (Gemma-4-31B, ~800ms, $0)

Composes:
  - Item 114 ``place_task`` / ``_TASK_AFFINITY``: NPU=classify, iGPU=interactive,
    CPU=deep-reasoning.
  - Hermes ``smart_model_routing`` length signal: short (<100 chars) → cheap_model,
    long (>500 chars) → full-context escalation.

Report-only — returns a :class:`BotTierPlan` but does NOT invoke inference,
touch lemonade, or modify Hermes config (the config write-back is a
gateway-stopped behavior-change, deferred per hermes-skill).

Pure (no I/O, no live fleet probe under pytest).
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Length thresholds (calibrated to Hermes smart_model_routing, 2026-06-06)
# ---------------------------------------------------------------------------

# Up to _SHORT_THRESHOLD chars → fast classify (NPU).
# Calibrated to Strix Halo bot traffic: greetings, acks, short factual queries.
_SHORT_THRESHOLD: int = 30
# Above _LONG_THRESHOLD chars → deep-reasoning escalation (CPU).
# Multi-paragraph requests (> ~80 words) benefit from the 31B CPU model.
_LONG_THRESHOLD: int = 400

# Task-kind → engine mapping (mirrors item-114 _TASK_AFFINITY)
_TIER_ENGINE: dict[str, str] = {
    "classify": "npu",
    "interactive": "igpu",
    "deep-reasoning": "cpu",
}


# ---------------------------------------------------------------------------
# BotTierPlan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BotTierPlan:
    """Report-only engine proposal for one bot turn (item 118).

    Attributes
    ----------
    engine:
        Proposed compute engine: ``"npu"``, ``"igpu"``, or ``"cpu"``.
    task_kind:
        The task classification driving the engine choice, using item-114's
        vocabulary: ``"classify"``, ``"interactive"``, or ``"deep-reasoning"``.
    """

    engine: str
    task_kind: str


# ---------------------------------------------------------------------------
# bot_tier_plan
# ---------------------------------------------------------------------------


def bot_tier_plan(message: str) -> BotTierPlan:
    """Propose the engine tier for one bot turn (item 118). Report-only.

    Classifies ``message`` by length into a task kind (item-114 vocabulary),
    then maps that to an engine via the Triune affinity table.

    Classification thresholds (mirrors Hermes ``smart_model_routing``):
      - ``len(message) < 100`` (including empty) → ``"classify"`` → NPU
      - ``len(message) > 500``                   → ``"deep-reasoning"`` → CPU
      - otherwise                                 → ``"interactive"`` → iGPU

    Args:
        message:
            The raw bot message text.  May be empty (treated as classify-tier).

    Returns:
        A :class:`BotTierPlan` with ``engine`` and ``task_kind``.  Never
        raises.

    Pure — no live inference, no lemonade probe, no Hermes config writes.
    """
    n = len(message)

    if n <= _SHORT_THRESHOLD:
        task_kind = "classify"
    elif n > _LONG_THRESHOLD:
        task_kind = "deep-reasoning"
    else:
        task_kind = "interactive"

    engine = _TIER_ENGINE[task_kind]
    return BotTierPlan(engine=engine, task_kind=task_kind)
