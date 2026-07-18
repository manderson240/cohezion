"""Session digest — the LLM judgment layer over salvaged sessions.

``session_salvage`` recovers WHAT happened (deterministic, exact). This turns that into
WHY it mattered: a short narrative per session, suitable for the vault.

QUARTER ON A STRING (.claude/rules/quarter-on-a-string-protocol.md): runs entirely on
local silicon via the :13305 OmniRouter at $0. No cloud tier, no escalation path — a
session digest is summarization, which the local reasoning tier handles outright. If the
local call fails, the digest is skipped; it is never worth paying for.

THINKING-MODEL HANDLING (skill: gemma4-thinking-mode-output): Gemma-4 returns the answer
in ``reasoning_content`` with ``content`` empty, and fences structured output. Both
failure modes present as "the model returned nothing", so ``parse_chat_response`` handles
them explicitly and each has a discriminating test.

Design mirrors its sibling: pure functions (``build_digest_prompt``, ``parse_chat_response``)
are unit-tested; ``lemonade_chat`` is the injectable I/O edge.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from cohezion.observability.session_salvage import SessionArtifacts, is_ephemeral


OMNIROUTER = "http://localhost:13305/api/v1/chat/completions"
# Gemma-4-26B-A4B: the loaded reasoning tier. Summarization is genuine multi-step work,
# so this is the right rung — not the 0.6B router model, not a cloud call.
DEFAULT_MODEL = "Gemma-4-26B-A4B-it-GGUF"

# Thinking models need room for the reasoning phase BEFORE the answer; a frugal cap
# truncates mid-thought and yields empty content. Local tokens are free — be generous.
DEFAULT_MAX_TOKENS = 2048

_MAX_ITEMS = 40  # per evidence category
_MAX_CHARS = 200  # per individual line

ChatFn = Callable[[str], dict]


def _bounded(items: list[str], label: str) -> str:
    """Render at most _MAX_ITEMS entries, disclosing how many were dropped."""
    if not items:
        return f"({label}: none)"
    shown = [i.replace("\n", " ")[:_MAX_CHARS] for i in items[:_MAX_ITEMS]]
    body = "\n".join(f"  - {s}" for s in shown)
    if len(items) > _MAX_ITEMS:
        body += f"\n  - ...and {len(items) - _MAX_ITEMS} more {label} (total {len(items)})"
    return body


def build_digest_prompt(art: SessionArtifacts) -> str:
    """Pure: artifacts -> a bounded prompt. Never unbounded, regardless of session size."""
    real_files = [w.path for w in art.file_writes if not is_ephemeral(w.path)]
    return f"""You are summarizing one AI coding session for an engineering knowledge vault.

SESSION
  working dir : {art.cwd or "unknown"}
  ran         : {art.first_ts[:16]} -> {art.last_ts[:16]}

WHAT THE HUMAN ASKED
{_bounded(art.user_prompts, "prompts")}

FILES WRITTEN
{_bounded(real_files, "files")}

COMMANDS RUN
{_bounded(art.bash_commands, "commands")}

Write a digest with exactly these four sections, in plain prose, no preamble:

GOAL: one sentence — what this session was trying to achieve.
OUTCOME: one or two sentences — what actually changed. If the evidence does not show
  the work completing, say so plainly. Do not assume success.
DECISIONS: any non-obvious choice with lasting consequence, one per line. If there are
  none visible in the evidence, write "none visible".
OPEN: anything left unfinished or unverified. If nothing, write "none visible".

Base every claim on the evidence above. Do not invent detail that is not shown."""


def parse_chat_response(payload: Any) -> str:
    """Pure: an OpenAI-shaped response -> text. Handles thinking-mode and fences.

    Returns "" rather than raising on any malformed shape — one bad response must not
    abort a batch.
    """
    try:
        msg = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return ""
    if not isinstance(msg, dict):
        return ""
    text = msg.get("content") or msg.get("reasoning_content") or ""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if len(lines) >= 2:
            lines = lines[1:]  # drop the ```json / ``` opener
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
    return text


def lemonade_chat(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = 180.0,
) -> dict:
    """I/O edge: one local chat completion via the :13305 OmniRouter.

    No `temperature` is sent — the model card's sampling settings are applied server-side
    at load, and overriding them client-side fights the card (see memory: lemonade serves
    card sampling).
    """
    # OMNIROUTER is module-level and therefore rebindable (tests, callers, a stray import).
    # urlopen would happily honour a file:// or custom scheme, turning a "local inference
    # call" into an arbitrary file read. Pin the scheme at the call site rather than
    # trusting the constant to still be what it looks like.
    if not OMNIROUTER.startswith(("http://", "https://")):
        raise ValueError(f"refusing non-HTTP inference endpoint: {OMNIROUTER!r}")

    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
    ).encode()
    # S310 suppressed on both lines: the scheme is pinned to http(s) immediately above,
    # which is exactly the check S310 asks for. Verified by
    # TestEndpointSchemePinning::test_non_http_endpoint_is_refused.
    req = urllib.request.Request(  # noqa: S310
        OMNIROUTER, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read())


def digest_session(art: SessionArtifacts, chat_fn: ChatFn | None = None) -> str:
    """Summarize one session on local silicon. Returns "" if the model is unreachable."""
    chat = chat_fn or lemonade_chat
    try:
        return parse_chat_response(chat(build_digest_prompt(art)))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
        return ""
