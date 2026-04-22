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

Environment:
    DELEGATE_TIMEOUT   request timeout in seconds (default 30)
    DELEGATE_MAX_TOKENS max output tokens (default 512)
    DELEGATE_CLAUDE_MODEL cloud escalation target (default claude-sonnet-4-6)

Exit codes:
    0  success — model responded with non-empty text
    1  all candidates exhausted / empty response
    2  CLI arg parse / prompt empty error
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time


# Keep stdlib-heavy so this script is importable without the full dev deps
# when the operator runs it outside `uv run`. Cohezion imports are lazy below.


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
    from cohezion.inference.fleet import extend_claude, route

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
        # Default path: local first, escalate to cloud Claude if quality gate fails.
        result = await extend_claude(
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
    args = parser.parse_args(argv)

    prompt = _read_prompt(args.prompt)
    if not prompt.strip():
        print("delegate.py: empty prompt", file=sys.stderr)
        return 2

    try:
        meta = asyncio.run(
            _dispatch(
                prompt,
                model=args.model,
                local_only=args.local_only,
                claude_model=args.claude_model,
                timeout=args.timeout,
                max_tokens=args.max_tokens,
            )
        )
    except (ImportError, ModuleNotFoundError) as exc:
        print(f"delegate.py: cohezion import failed ({exc}) — run under `uv run`.", file=sys.stderr)
        return 2

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
            f"attempts={','.join(meta['attempts'])}"
        )
        if meta["error"]:
            summary += f" error={meta['error']}"
        print(summary, file=sys.stderr)

    return 0 if meta["text"] and not meta["error"] else 1


if __name__ == "__main__":
    sys.exit(main())
