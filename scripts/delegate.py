"""Delegate a short prompt to the local fleet (Lemonade / Ollama) first,
with optional escalation to a cloud Claude model if the local result fails a
quality gate. Stdout is the model's text response; stderr has dispatch metadata.

This is the CLI wrapper around `cohezion.inference.fleet.extend_claude()` + `route()`
designed for *operator / interactive-session* delegation — specifically so that a
Claude Code (or any other) session can hand sub-500-token tasks off to the local
fleet instead of burning cloud context on cheap work.

Default behavior: try local (Lemonade iGPU / Ollama) lanes first; escalate to
the named cloud model only if local output fails the quality gate.

Usage examples:
    # Short delegation to local-first; output to stdout, metadata to stderr
    uv run python scripts/delegate.py "Summarize: <long text here>"

    # Pin a specific model (bypass task-affinity routing)
    uv run python scripts/delegate.py --model phi4:latest "Why is the sky blue?"

    # Local-only, no escalation — fail loudly if local can't
    uv run python scripts/delegate.py --local-only "Short structural question"

    # Read prompt from stdin (useful for piping larger prompts)
    echo "review this code" | uv run python scripts/delegate.py -

    # Emit a JSON envelope for programmatic callers
    uv run python scripts/delegate.py --json "Your prompt here"

    # Inspect the per-session delegation budget
    uv run python scripts/delegate.py --show-budget

Environment:
    DELEGATE_TIMEOUT        request timeout in seconds (default 30)
    DELEGATE_MAX_TOKENS     max output tokens (default 512)
    DELEGATE_CLAUDE_MODEL   cloud escalation target (default claude-sonnet-4-6)
    DELEGATE_CLOUD_BUDGET   per-session cloud token cap (default 10000)
    COHEZION_SESSION_ID     used as the budget-tracking key; auto-derived from PID if unset

Exit codes:
    0  success — model responded with non-empty text
    1  all candidates exhausted / empty response
    2  CLI arg parse / prompt empty error
    3  cloud budget exhausted and local fallback failed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path


# Keep stdlib-heavy so this script is importable without the full dev deps
# when the operator runs it outside `uv run`. Cohezion imports are lazy below.


# ---------------------------------------------------------------------------
# DelegationBudget — per-session cloud-escalation quota
# ---------------------------------------------------------------------------
# Why this exists: AGI_GOLF_STATUS flagged "daily submission quota is the
# architecture discipline" — a scarce resource that's always available to
# retry-debug becomes a free-escalation habit. For delegate.py, the cloud
# Claude fallback is that scarce resource. Without a per-session cap, every
# call can silently escalate and the cumulative cost is invisible.
#
# Design:
#   * State lives at ~/.cohezion-engine/sessions/<session_id>/delegate_budget.json
#     (matches the `cz` session directory convention; survives across calls
#     within the same session, resets naturally on new session).
#   * Budget is measured in output tokens (est. via len(result.text) / 4).
#   * Check is BEFORE the call: if the current cumulative cloud-tokens + a
#     conservative estimate of max_tokens would exceed, the call is forced to
#     --local-only. The operator can always raise DELEGATE_CLOUD_BUDGET or
#     pass --local-only explicitly to bypass.
#   * Record is AFTER the call: actual tokens used are credited.


def _session_id() -> str:
    """Session-budget key. Prefer $COHEZION_SESSION_ID (matches `cz` CLI);
    fall back to a per-PID pseudo-session so dev runs still track."""
    return os.environ.get("COHEZION_SESSION_ID") or f"pid-{os.getpid()}"


def _budget_state_path(session_id: str) -> Path:
    return Path.home() / ".cohezion-engine" / "sessions" / session_id / "delegate_budget.json"


def _load_budget_state(path: Path) -> dict:
    if not path.exists():
        return {
            "cloud_tokens_used": 0,
            "local_tokens_used": 0,
            "calls_total": 0,
            "calls_escalated": 0,
            "calls_forced_local": 0,
            "last_call_ts": None,
        }
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        # Corrupt state → start over; losing the budget history is better
        # than blocking delegation.
        return {
            "cloud_tokens_used": 0,
            "local_tokens_used": 0,
            "calls_total": 0,
            "calls_escalated": 0,
            "calls_forced_local": 0,
            "last_call_ts": None,
        }


def _save_budget_state(path: Path, state: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2))
    except OSError:
        # Budget is a hint, not a hard constraint — never block a delegation
        # call on a filesystem write failure.
        pass


def _estimate_tokens(text: str) -> int:
    """Coarse token estimate. 4 chars/token is the common heuristic for
    English-heavy text; overestimates for code, underestimates for CJK.
    Fine for budget gating — we're counting order-of-magnitude, not billing."""
    return max(1, len(text) // 4)


def _cloud_escalation_allowed(state: dict, max_tokens: int, cloud_budget: int) -> tuple[bool, int]:
    """Return (allowed, remaining). Conservative: treat max_tokens as the
    full cost of this call even though most calls use fewer."""
    remaining = cloud_budget - state["cloud_tokens_used"]
    return (remaining >= max_tokens, remaining)


def _record_call(state: dict, *, tokens: int, escalated: bool, forced_local: bool) -> dict:
    if escalated:
        state["cloud_tokens_used"] += tokens
        state["calls_escalated"] += 1
    else:
        state["local_tokens_used"] += tokens
    if forced_local:
        state["calls_forced_local"] += 1
    state["calls_total"] += 1
    state["last_call_ts"] = time.time()
    return state


def _format_budget_summary(session_id: str, state: dict, cloud_budget: int) -> str:
    remaining = cloud_budget - state["cloud_tokens_used"]
    return (
        f"session={session_id} calls_total={state['calls_total']} "
        f"cloud_used={state['cloud_tokens_used']} cloud_budget={cloud_budget} "
        f"remaining={remaining} escalated={state['calls_escalated']} "
        f"forced_local={state['calls_forced_local']}"
    )


# ---------------------------------------------------------------------------
# Prompt + dispatch
# ---------------------------------------------------------------------------


def _read_prompt(text_arg: str | None) -> str:
    """If arg is '-' or missing, read stdin. Otherwise return the arg as-is."""
    if text_arg == "-" or text_arg is None:
        return sys.stdin.read().strip()
    return text_arg


async def _dispatch(
    prompt: str,
    *,
    model: str | None,
    local_only: bool,
    claude_model: str,
    timeout: float,
    max_tokens: int,
) -> dict:
    """Call cohezion.inference.fleet.{route,extend_claude} and return a dict
    summary suitable for stderr metadata output or JSON envelope."""
    # Lazy import — running under `uv run` from this script, not at module load.
    from cohezion.inference.fleet import extend_claude_guarded, route

    start = time.perf_counter()
    if local_only:
        result = await route(
            prompt,
            prefer=model,
            budget_usd=0.0,
            timeout=timeout,
            max_tokens=max_tokens,
        )
    elif model:
        # Explicit model pin: no escalation, just route to the named model.
        result = await route(prompt, prefer=model, timeout=timeout, max_tokens=max_tokens)
    else:
        # Default path: local first, escalate to cloud Claude if quality gate fails AND the
        # live Claude-quota allows it (item 138 — never run out of Claude, doctrine bullet 5).
        result = await extend_claude_guarded(
            prompt,
            claude_model=claude_model,
            timeout=timeout,
        )
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "text": result.text,
        "model": result.model,
        "lane": result.lane,
        "latency_ms": result.latency_ms,
        "total_ms": elapsed_ms,
        "ttft_ms": result.ttft_ms,
        "tokens_per_sec": result.tokens_per_sec,
        "cost_usd": result.cost_usd,
        "escalated_to_cloud": result.escalated_to_cloud,
        "attempts": list(result.attempts),
        "error": result.error,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="The prompt text. Use '-' (or omit) to read from stdin.",
    )
    parser.add_argument(
        "--model",
        help="Pin to a specific model_id from the fleet registry (skips task routing).",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Never escalate to cloud; fail if no local candidate succeeds.",
    )
    parser.add_argument(
        "--claude-model",
        default=os.environ.get("DELEGATE_CLAUDE_MODEL", "claude-sonnet-4-6"),
        help="Cloud escalation target (ignored if --local-only or --model).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("DELEGATE_TIMEOUT", "30")),
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.environ.get("DELEGATE_MAX_TOKENS", "512")),
        help="Max output tokens.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON envelope on stdout instead of plain text; metadata included.",
    )
    parser.add_argument(
        "--cloud-budget",
        type=int,
        default=int(os.environ.get("DELEGATE_CLOUD_BUDGET", "10000")),
        help="Per-session cloud-escalation token cap (default 10000; env DELEGATE_CLOUD_BUDGET).",
    )
    parser.add_argument(
        "--show-budget",
        action="store_true",
        help="Print the per-session delegation budget summary and exit.",
    )
    parser.add_argument(
        "--reset-budget",
        action="store_true",
        help="Zero the per-session delegation budget state and exit.",
    )
    args = parser.parse_args(argv)

    # Budget-only operations exit before any prompt handling.
    session_id = _session_id()
    budget_path = _budget_state_path(session_id)
    if args.show_budget:
        state = _load_budget_state(budget_path)
        print(_format_budget_summary(session_id, state, args.cloud_budget))
        return 0
    if args.reset_budget:
        try:
            if budget_path.exists():
                budget_path.unlink()
            print(f"[delegate] budget reset for session={session_id}")
        except OSError as exc:
            print(f"delegate.py: could not reset budget ({exc})", file=sys.stderr)
            return 2
        return 0

    prompt = _read_prompt(args.prompt)
    if not prompt.strip():
        print("delegate.py: empty prompt", file=sys.stderr)
        return 2

    # Budget gate. If the caller requested escalation (default path — no
    # --model, no --local-only) AND the budget would be exceeded, force
    # local_only. The operator can raise --cloud-budget or use --local-only
    # to bypass, but a silent escalation is what we're preventing.
    state = _load_budget_state(budget_path)
    forced_local = False
    effective_local_only = args.local_only
    escalation_possible = not args.local_only and args.model is None
    if escalation_possible:
        allowed, _remaining = _cloud_escalation_allowed(state, args.max_tokens, args.cloud_budget)
        if not allowed:
            effective_local_only = True
            forced_local = True
            print(
                f"[delegate] cloud budget exhausted ({state['cloud_tokens_used']}/"
                f"{args.cloud_budget} tokens, need {args.max_tokens}); "
                f"forcing --local-only. Override: --cloud-budget=<higher> or --reset-budget.",
                file=sys.stderr,
            )

    try:
        meta = asyncio.run(
            _dispatch(
                prompt,
                model=args.model,
                local_only=effective_local_only,
                claude_model=args.claude_model,
                timeout=args.timeout,
                max_tokens=args.max_tokens,
            )
        )
    except ImportError as exc:
        print(f"delegate.py: cohezion import failed ({exc}) — run under `uv run`.", file=sys.stderr)
        return 2

    # Record actual usage. Estimate tokens from result text length; cheap and
    # good enough for budget gating (real billing would come from provider API).
    actual_tokens = _estimate_tokens(meta.get("text") or "")
    escalated = bool(meta.get("escalated_to_cloud"))
    state = _record_call(
        state, tokens=actual_tokens, escalated=escalated, forced_local=forced_local
    )
    _save_budget_state(budget_path, state)
    meta["forced_local"] = forced_local
    meta["budget_remaining"] = max(0, args.cloud_budget - state["cloud_tokens_used"])

    if args.json:
        json.dump(meta, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(meta["text"])
        if not meta["text"].endswith("\n"):
            sys.stdout.write("\n")
        # Minimal one-line metadata summary on stderr so the caller can see
        # WHERE the response came from without parsing stdout.
        summary = (
            f"[delegate] model={meta['model']} lane={meta['lane']} "
            f"latency_ms={meta['latency_ms']:.0f} "
            f"escalated={meta['escalated_to_cloud']} "
            f"attempts={','.join(meta['attempts'])} "
            f"budget_remaining={meta['budget_remaining']}"
        )
        if forced_local:
            summary += " forced_local=True"
        if meta["error"]:
            summary += f" error={meta['error']}"
        print(summary, file=sys.stderr)

    if meta["text"] and not meta["error"]:
        return 0
    # Special exit code 3: we forced local because budget was exhausted AND
    # the local path also failed. Distinguishes budget-driven failure from
    # generic fleet exhaustion.
    if forced_local and (not meta["text"] or meta["error"]):
        return 3
    return 1


if __name__ == "__main__":
    sys.exit(main())
