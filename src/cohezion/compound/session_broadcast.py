"""Creds-free core of the Telegram session-broadcast remote.

The user's Telegram channel is a *remote* to broadcast a directive to ALL
running sessions and have each one delegate the work to the right tier. The
actual outbound Telegram SEND requires TELEGRAM_BOT_TOKEN and is handled by
``telegram_notify.notify``; this module is the pure, network-free, fully
unit-testable core that runs whether or not credentials are present:

1. REDACT — strip any credential patterns from the broadcast text so a leaked
   directive never re-broadcasts a secret to every session.
2. CLASSIFY — use the existing ``task_classifier`` to pick the delegation tier
   (NPU / iGPU / CPU) for the directive (smart delegation).
3. FORMAT — render a deterministic HTML message ready to hand to ``notify``.

No I/O, no env reads, no network. Importing this module triggers no fleet call.
"""

from __future__ import annotations

from dataclasses import dataclass


# task_classifier node ("npu"/"gpu") → broadcast delegation tier + lemonade port.
# "gpu" maps to iGPU (13307); short categorical/answer stays on NPU (13306).
_TIER_BY_NODE: dict[str, tuple[str, int]] = {
    "npu": ("npu", 13306),
    "gpu": ("igpu", 13307),
}
# Reasoning/long work escalates to the CPU tier (Gemma-4-31B on 13309).
_CPU_TIER = ("cpu", 13309)
_CPU_OUTPUT_TYPES = frozenset({"math_reasoning", "long_generation"})


@dataclass(frozen=True)
class BroadcastPlan:
    """A redacted, tier-classified, formatted broadcast ready for ``notify``."""

    directive: str  # redacted directive text
    tier: str  # "npu" | "igpu" | "cpu"
    port: int  # lemonade port for the tier
    output_type: str  # task_classifier output_type
    confidence: float  # classifier confidence 0.0-1.0
    message: str  # formatted HTML body for telegram_notify.notify

    def __str__(self) -> str:
        return f"BroadcastPlan(tier={self.tier}, port={self.port}, type={self.output_type})"


def build_broadcast(directive: str, *, session_label: str = "all-sessions") -> BroadcastPlan:
    """Build a redacted, tier-delegated, formatted broadcast plan.

    Pure and creds-free: safe to call with or without TELEGRAM_BOT_TOKEN set.
    Does NOT send — pass ``plan.message`` to ``telegram_notify.notify`` to send.

    Parameters
    ----------
    directive:
        The remote directive to broadcast to every session.
    session_label:
        A label for the target session set (header only).
    """
    # Lazy imports keep module import network/fleet-free.
    from cohezion.compound.telegram_notify import _redact
    from cohezion.inference.task_classifier import classify

    safe = _redact(directive)
    decision = classify(safe)

    if decision.output_type in _CPU_OUTPUT_TYPES:
        tier, port = _CPU_TIER
    else:
        tier, port = _TIER_BY_NODE.get(decision.node, _CPU_TIER)

    message = (
        f"<b>Broadcast → {session_label}</b>\n"
        f"tier=<code>{tier}</code> port=<code>{port}</code> "
        f"type=<code>{decision.output_type}</code> "
        f"conf=<code>{decision.confidence:.2f}</code>\n"
        f"<code>{safe[:280]}</code>"
    )

    return BroadcastPlan(
        directive=safe,
        tier=tier,
        port=port,
        output_type=decision.output_type,
        confidence=decision.confidence,
        message=message,
    )


def broadcast(directive: str, *, session_label: str = "all-sessions") -> BroadcastPlan:
    """Build a plan AND attempt the outbound Telegram send (fire-and-forget).

    The send no-ops silently unless TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID are set,
    so this is safe to call unconditionally. Returns the plan regardless, so callers
    can log/inspect exactly what was (or would be) sent. Never raises.
    """
    from cohezion.compound.telegram_notify import notify

    plan = build_broadcast(directive, session_label=session_label)
    notify(plan.message)  # no-ops without creds; fire-and-forget; never raises
    return plan


__all__ = ["BroadcastPlan", "broadcast", "build_broadcast"]
