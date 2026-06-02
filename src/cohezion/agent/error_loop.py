"""Orchestration error-loop layer — the missing controller that activates step-level adaptation.

The 11-agent design workflow (RETRO-2026-06-02c) confirmed cohezion has all the *pieces* for an
autonomous error loop (recursive ExecutionTrace, skill_adaptor fault attribution, trust_hierarchy,
DivergenceDetector, sandbox backends) but no controller wiring them — and skill_adaptor was dead
code. It also found the headline gap: **livelock is not actually bounded**. Every existing limit
(``recovery_attempts``, ``max_steps``) lives on the *worker*; a fresh worker resets those counters,
so an orchestrator can re-dispatch the same unfixable step forever and burn the fleet.

This module is the orchestrator-side controller. It runs on a *returned* ExecutionTrace (it does
not touch the live ``run_task`` loop, keeping the change additive and the boundary thin), and:

  * ``error_signature`` — a value-masked fingerprint of a fault (digits/paths/hex masked) so the
    *same* failure mode is one key across runs — the dedup key for both recall and the bound.
  * ``ErrorClassifier`` — classify a fault into transient / divergence / resource / permanent,
    so retry budget is per-class (a permanent fault gets 0 self-correction; a transient gets more).
  * ``ReDispatchLedger`` — the livelock fix: an orchestrator-owned, **persisted** (to_dict/from_dict)
    count keyed by ``error_signature`` that survives the stateless worker boundary. Past its cap the
    orchestrator *abandons* the signature instead of re-dispatching — the bound the worker can't hold.
  * ``reflect`` — the controller step: attribute the fault (activating ``skill_adaptor``), classify,
    check the persisted bound, and on a correctable+within-budget fault apply a gated targeted
    adaptation. Returns a structured ``{action: commit|retry|escalate|abandon}`` decision.

Composes with ``trust_hierarchy`` (adaptation outcomes corroborate/contradict) and is the seam a
future ``run_task`` edit will call. No new infra; pure composition of existing modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from cohezion.agent.skill_adaptor import adapt_skill, attribute_fault, mask_volatile


__all__ = ["ErrorClass", "ErrorClassifier", "ReDispatchLedger", "error_signature", "reflect"]


class ErrorClass(StrEnum):
    TRANSIENT = "transient"  # retryable as-is (timeout, rate-limit, connection)
    DIVERGENCE = "divergence"  # numeric blow-up (NaN/Inf/overflow) — retry with guard
    RESOURCE = "resource"  # OOM/disk — back off, then retry
    PERMANENT = "permanent"  # bad input/syntax/not-found — no self-correct, escalate
    UNKNOWN = "unknown"


# Per-class self-correction budgets (how many times the worker may retry this fault class).
_CLASS_BUDGET: dict[ErrorClass, int] = {
    ErrorClass.TRANSIENT: 5,
    ErrorClass.DIVERGENCE: 3,
    ErrorClass.RESOURCE: 2,
    ErrorClass.UNKNOWN: 1,
    ErrorClass.PERMANENT: 0,
}


def error_signature(skill: str, reason: str) -> str:
    """Value-masked fault fingerprint: same failure mode -> same key across runs.

    Uses the shared ``mask_volatile`` (from skill_adaptor) so the ledger's bound key and the trust
    store's guard key dedupe a fault to the SAME mode: 'disk full at /tmp/a/1' and
    'disk full at /var/b/9' collapse to one signature AND one guard.
    """
    masked = mask_volatile(reason.lower())
    masked = " ".join(masked.split())[:120]
    return f"{skill}:{masked}"


class ErrorClassifier:
    """Map a fault's (skill, reason) to an ErrorClass by keyword signatures.

    Errs toward escalation on ambiguity — over-self-correcting a permanent fault is the
    dangerous direction (the workflow's thin-agent risk note).
    """

    _RULES: tuple[tuple[ErrorClass, tuple[str, ...]], ...] = (
        (
            ErrorClass.DIVERGENCE,
            ("nan", "inf", "diverg", "overflow", "not finite", "blow", "non-conserv"),
        ),
        (
            ErrorClass.RESOURCE,
            ("oom", "out of memory", "no space", "disk full", "resource exhaust", "cuda out"),
        ),
        (
            ErrorClass.TRANSIENT,
            (
                "timeout",
                "timed out",
                "connection",
                "rate limit",
                "429",
                "temporarily",
                "unavailable",
                "reset by peer",
            ),
        ),
        (
            ErrorClass.PERMANENT,
            (
                "not found",
                "404",
                "invalid",
                "syntaxerror",
                "unsupported",
                "permission",
                "no such",
                "no attribute",
                "keyerror",
            ),
        ),
    )

    def classify(self, skill: str, reason: str) -> ErrorClass:
        r = (reason or "").lower()
        for cls, kws in self._RULES:
            if any(k in r for k in kws):
                return cls
        return ErrorClass.UNKNOWN


@dataclass
class ReDispatchLedger:
    """Orchestrator-owned, persisted re-dispatch bound keyed by error_signature.

    The livelock fix: worker-level counters reset on each fresh dispatch, but this ledger lives on
    the orchestrator and (via to_dict/from_dict) survives across the stateless worker boundary, so
    the *same* fault signature cannot be re-dispatched past ``max_per_signature`` no matter how many
    fresh workers are spawned.
    """

    max_per_signature: int = 3
    _counts: dict[str, int] = field(default_factory=dict)

    def attempts(self, signature: str) -> int:
        return self._counts.get(signature, 0)

    def allow(self, signature: str) -> bool:
        """Record a dispatch for this signature; return False once the cap is reached."""
        n = self._counts.get(signature, 0)
        if n >= self.max_per_signature:
            return False
        self._counts[signature] = n + 1
        return True

    def reset(self, signature: str) -> None:
        """Clear a signature's count (call on a confirmed success so it can recur freely later)."""
        self._counts.pop(signature, None)

    def to_dict(self) -> dict:
        return {"max_per_signature": self.max_per_signature, "counts": dict(self._counts)}

    @classmethod
    def from_dict(cls, state: dict) -> ReDispatchLedger:
        led = cls(max_per_signature=state.get("max_per_signature", 3))
        led._counts = dict(state.get("counts", {}))
        return led


def reflect(
    trace: object,
    *,
    ledger: ReDispatchLedger,
    classifier: ErrorClassifier | None = None,
    trust: object | None = None,
) -> dict:
    """Orchestrator reflection step: decide commit / retry / escalate / abandon for a trace.

    Activates ``skill_adaptor`` (attribute_fault + adapt_skill) and enforces the persisted
    livelock bound. The returned ``action``:
      * ``commit``  — clean trajectory, no fault.
      * ``escalate``— permanent fault (worker can't self-correct) -> orchestrator re-plans.
      * ``abandon`` — this signature hit the persisted re-dispatch cap (livelock guard fired).
      * ``retry``   — correctable & within budget; a gated targeted adaptation was applied.
    """
    fault = attribute_fault(trace)
    if fault is None:
        return {"action": "commit", "reason": "clean trajectory", "attribution": None}

    cls = (classifier or ErrorClassifier()).classify(fault.skill, fault.reason)
    sig = error_signature(fault.skill, fault.reason)
    base = {"class": cls.value, "signature": sig, "attribution": fault.to_dict()}

    if _CLASS_BUDGET[cls] == 0:
        return {
            **base,
            "action": "escalate",
            "reason": "permanent fault — orchestrator must re-plan",
        }

    # Livelock guard: orchestrator-owned, persisted across the stateless worker boundary.
    if not ledger.allow(sig):
        return {
            **base,
            "action": "abandon",
            "reason": f"re-dispatch cap {ledger.max_per_signature} reached for this fault signature",
            "attempts": ledger.attempts(sig),
        }

    adaptation = adapt_skill(trace, trust=trust)  # activates the (previously-dead) skill_adaptor
    return {
        **base,
        "action": "retry",
        "attempts": ledger.attempts(sig),
        "budget": _CLASS_BUDGET[cls],
        "adaptation": adaptation,
    }
