"""run_with_reflection — the live activation seam wiring worker ``run_task`` -> orchestrator ``reflect``.

``error_loop.reflect`` (the controller), ``skill_adaptor`` (fault attribution), and ``ReDispatchLedger``
(the persisted livelock bound) were all built and tested but never wired to a live execution path —
the stack was latent. This module is that wiring, and it is deliberately *additive*: it composes a
duck-typed worker (anything exposing ``async run_task(task, env=, timeout=) -> ExecutionTrace`` —
e.g. ``UnifiedAgent``) with ``reflect``, and never edits the tested worker loop.

The one architectural commitment, forced by the headline bug (RETRO-2026-06-02c): **the re-dispatch
bound must outlive the stateless worker.** Worker-level counters (``UnifiedAgent.recovery_attempts``)
reset on every fresh dispatch, so they cannot stop an orchestrator from re-dispatching the same
unfixable fault forever. Therefore the ``ledger`` is a **required, caller-held** parameter — never
worker-resident state. A fresh worker passed the same ledger inherits the bound; that is the whole
point, and ``test_bound_survives_fresh_worker`` proves it.

Honest scope (no overclaiming):
  * "Activated" means the dispatch -> reflect -> attribute_fault/adapt_skill path runs and records a
    structured decision per dispatch. It does NOT mean skills self-modify: ``adapt_skill`` computes a
    targeted, acceptance-gated *proposal* and (optionally) records trust corroboration, but mutates no
    skill file here.
  * A ``retry`` re-runs the SAME task. This is correct for TRANSIENT faults (re-run often succeeds);
    for divergence/resource faults it is thin until the proposed guidance is fed into planning — which
    is a separate, future change to ``_plan_next_action``, intentionally not done here.
  * **Concurrency: single-flight per ledger.** The livelock scenario is inherently sequential — you
    re-dispatch only *after* seeing the prior failure — so this orchestrator is written for sequential
    re-dispatch. ``ReDispatchLedger`` is NOT safe for concurrent admission: running several
    ``run_with_reflection`` coroutines against ONE shared ledger via ``asyncio.gather`` has a
    check-then-dispatch-then-increment TOCTOU window that can exceed the cap. For concurrent batches,
    give each its own ledger (or serialize admission externally). The "no matter how many fresh
    workers are spawned" guarantee is about *sequential* re-spawns, which is the actual livelock case.
  * **Wall-clock is enforced here.** The worker's own ``timeout`` is advisory (the canonical
    ``UnifiedAgent`` bounds only by ``max_steps`` x per-tool timeouts and ignores ``timeout`` for its
    main loop), so the dispatch runs under an orchestrator-side ``asyncio.wait_for``. A hung or dying
    worker is counted by the ledger like any other fault, so it cannot evade the bound by *not
    returning a trace*.

Bound semantics (the guards):
  1. per-signature cap — ``reflect`` consults the ledger; past the cap it returns ``abandon``.
  2. pre-dispatch short-circuit — once a signature is known to be at cap, abandon WITHOUT paying
     another ``run_task``. ``prior_signature`` threads a known-exhausted signature from a previous
     call so a fresh invocation abandons with zero dispatches. NOTE: this assumes signature
     stationarity for the task — pass a ``prior_signature`` that actually corresponds to THIS task,
     or a clean run could be falsely abandoned.
  3. absolute outer bound — ``max_redispatch`` stops the loop even if the signature changes every time
     and so evades the per-signature ledger.
  4. dispatch-failure counting — a raised/timed-out dispatch is counted in the ledger so a worker that
     *dies* (OOM-kill) instead of returning a fault trace is still bounded.
  5. commit health gate — absence of a tool-call fault is necessary but NOT sufficient for success; a
     trace that did not actually complete (or carries an error) is downgraded from commit to escalate.
  6. commit reset — on a terminal ``commit`` every signature retried in this run is ``reset`` so its
     budget recovers (the ledger's "so it can recur freely later" semantics).
"""

from __future__ import annotations

import asyncio
import logging

from cohezion.agent.error_loop import ErrorClassifier, ReDispatchLedger, error_signature, reflect


logger = logging.getLogger(__name__)

__all__ = ["run_with_reflection"]

# Added to the worker's advisory timeout before the orchestrator force-aborts a hung dispatch.
_DISPATCH_GRACE_S = 30


def _trace_is_success(trace: object) -> bool:
    """A trace is a real success only if it completed AND carries no top-level error.

    Guard 5: ``reflect`` returns 'commit' when no *tool_call* error exists, but a worker that
    exhausts ``max_steps`` (completed=False) or breaks on max-recoveries (trace.error set, empty
    tool_calls) has no tool-call fault yet did not succeed. This catches that false success.
    """
    return (
        trace is not None
        and getattr(trace, "completed", False)
        and not getattr(trace, "error", None)
    )


async def run_with_reflection(
    agent: object,
    task: object,
    *,
    ledger: ReDispatchLedger,
    env: dict | None = None,
    timeout: int = 1800,
    max_redispatch: int = 3,
    classifier: ErrorClassifier | None = None,
    trust: object | None = None,
    prior_signature: str | None = None,
) -> dict:
    """Dispatch ``agent.run_task``, reflect on the returned trace, and bounded-re-dispatch.

    Parameters
    ----------
    agent:
        Duck-typed worker exposing ``async run_task(task, env=, timeout=) -> ExecutionTrace``.
    ledger:
        REQUIRED, caller-held ``ReDispatchLedger`` — the orchestrator-owned bound that must outlive
        the stateless worker. Single-flight per ledger (see module docstring on concurrency).
    max_redispatch:
        Absolute cap on re-dispatches (>= 0). Belt-and-suspenders for signatures that evade the ledger.
    prior_signature:
        A known-exhausted signature (for THIS task) from a previous call; if already at the ledger cap
        the loop abandons before dispatching at all.

    Returns
    -------
    dict with ``action`` (commit|escalate|abandon), ``reason``, ``dispatches`` (real ``run_task``
    attempts incl. raised ones), ``decisions`` (full audit trail — may exceed ``dispatches`` by the
    pre-dispatch abandons), ``signature`` (terminal fault signature, or None on commit), and
    ``trace`` (the final ExecutionTrace, or None if abandoned pre-dispatch / every dispatch raised).

    Raises
    ------
    ValueError: if ``max_redispatch`` is negative (fail fast — never report a no-run as success).
    """
    if max_redispatch < 0:
        raise ValueError(f"max_redispatch must be >= 0, got {max_redispatch}")

    clf = classifier or ErrorClassifier()
    decisions: list[dict] = []
    retried: set[str] = set()
    last_sig: str | None = prior_signature
    trace = None
    dispatches = 0

    for _ in range(max_redispatch + 1):
        # Guard 2: a known-capped signature is abandoned WITHOUT paying another dispatch.
        if last_sig is not None and ledger.attempts(last_sig) >= ledger.max_per_signature:
            decisions.append(
                {
                    "action": "abandon",
                    "signature": last_sig,
                    "reason": "signature already at re-dispatch cap — abandoned pre-dispatch",
                    "attempts": ledger.attempts(last_sig),
                }
            )
            break

        # Dispatch the untrusted worker under an orchestrator wall-clock (Guard 4): the worker's own
        # timeout is advisory and the canonical UnifiedAgent ignores it for its main loop.
        try:
            trace = await asyncio.wait_for(
                agent.run_task(task, env=env, timeout=timeout),
                timeout=timeout + _DISPATCH_GRACE_S,
            )
        except Exception as exc:
            # failure (wall-clock timeout, OOM-kill, worker death) MUST be counted by the ledger, or a
            # worker that dies instead of returning a fault trace would evade the livelock bound.
            dispatches += 1
            sig = error_signature(type(agent).__name__, f"{type(exc).__name__}: {exc}")
            last_sig = sig
            allowed = ledger.allow(sig)
            logger.warning(
                "run_with_reflection dispatch raised %s; counted as %s (allowed=%s)",
                type(exc).__name__,
                sig,
                allowed,
            )
            decisions.append(
                {
                    "action": "retry" if allowed else "abandon",
                    "signature": sig,
                    "class": "transient",
                    "reason": f"dispatch raised: {type(exc).__name__}: {exc}"[:200],
                    "attempts": ledger.attempts(sig),
                }
            )
            if allowed:
                retried.add(sig)
                continue
            break

        dispatches += 1
        decision = reflect(trace, ledger=ledger, classifier=clf, trust=trust)
        decisions.append(decision)
        last_sig = decision.get("signature") or last_sig
        if decision["action"] == "retry":
            if decision.get("signature"):
                retried.add(decision["signature"])
            continue
        break

    # Resolve the terminal verdict. Never default a no-run to success.
    final_action = decisions[-1]["action"] if decisions else "abandon"
    reason = decisions[-1].get("reason", "") if decisions else "no dispatch performed"

    # Guard 5: a commit is only real if the trace actually completed without error.
    if final_action == "commit" and not _trace_is_success(trace):
        final_action = "escalate"
        reason = "no tool-call fault but trace incomplete/errored — not a real success"
    # A terminal 'retry' means budget remained but max_redispatch stopped the loop; normalize to a
    # resolved verdict so the caller never receives an action the orchestrator did not act on.
    elif final_action == "retry":
        final_action = "abandon"
        reason = "max_redispatch reached with budget remaining — re-invoke for more attempts"

    # Guard 6: a confirmed success frees the budget of everything retried on the way there.
    if final_action == "commit":
        for sig in retried:
            ledger.reset(sig)

    return {
        "action": final_action,
        "reason": reason,
        "dispatches": dispatches,
        "decisions": decisions,
        "signature": None if final_action == "commit" else last_sig,
        "trace": trace,
    }
