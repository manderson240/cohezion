"""LLM-judge preference function for per-task model tournament (item 99, Thread N).

Provides ``granite_prefer`` — a drop-in replacement for the deterministic proxy
``_default_preference`` in :func:`~cohezion.inference.model_tournament.model_tournament`.

Arena-as-judge pattern (Marktechpost LLM-Eval tutorial, distilled 2026-06-06):
  - Judge sees BLIND descriptions of model capabilities — NOT model IDs or names.
  - "Blind" eliminates brand-familiarity sycophancy (the judge cannot know that
    "Model A" is a well-known brand and prefer it on that basis alone).
  - Granite-4.1-8B-GGUF on ``:13305`` at ``temperature=0`` for replay safety.
  - Falls back to the deterministic proxy on any network error, timeout, or
    ambiguous response — the tournament never breaks because the judge is offline.

Usage::

    from cohezion.inference.lm_judge import granite_prefer
    from cohezion.inference.model_tournament import model_tournament

    result = model_tournament(task, candidates, prefer=granite_prefer)

The judge is stateless: each call is an independent HTTP round-trip.

OOM discipline (K1): Granite-4.1-8B-GGUF is already hot on ``:13305``
(Vulkan/iGPU; no model load required).  Never spin up dedicated per-port servers.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from cohezion.inference.model_tournament import _default_preference


if TYPE_CHECKING:
    from cohezion.inference.registry import ModelEntry, Task

logger = logging.getLogger(__name__)

# Judge configuration
_JUDGE_URL = "http://localhost:13305/v1/chat/completions"
_JUDGE_MODEL = "Granite-4.1-8B-GGUF"
_JUDGE_TIMEOUT_S = 10  # per-call HTTP timeout; pairwise pairs are short prompts
_JUDGE_MAX_TOKENS = 8   # we only need "A" or "B" back
_JUDGE_TEMPERATURE = 0  # deterministic / replay-safe


def _describe_model(entry: ModelEntry, task: Task) -> str:
    """Build a compact, ID-free capability description for blind evaluation.

    All potentially identifying strings (model_id, endpoint, runtime) are
    redacted.  The judge sees only objective properties.
    """
    has_affinity = task in entry.task_affinity
    verified = "verified-working" if entry.verified_working else "not-yet-verified"
    ctx_k = entry.context_window // 1000
    cost = entry.cost_per_1k_input_usd + entry.cost_per_1k_output_usd
    cost_str = "free (local)" if cost == 0.0 else f"${cost:.4f}/1k tokens"

    latency_parts: list[str] = []
    if entry.observed_ttft_ms_p50 is not None:
        latency_parts.append(f"TTFT p50={entry.observed_ttft_ms_p50:.0f}ms")
    if entry.observed_tokens_per_sec is not None:
        latency_parts.append(f"{entry.observed_tokens_per_sec:.0f} TPS")
    latency_str = ", ".join(latency_parts) or "latency unknown"

    return (
        f"- Task coverage for '{task.value}': {'YES' if has_affinity else 'NO'}\n"
        f"- Status: {verified}\n"
        f"- Context window: {ctx_k}k tokens\n"
        f"- Cost: {cost_str}\n"
        f"- Latency: {latency_str}\n"
        f"- Priority tier: {entry.priority}"
    )


def _build_judge_prompt(
    a: ModelEntry,
    b: ModelEntry,
    task: Task,
) -> str:
    """Return the blind pairwise comparison prompt.

    The judge is asked to pick A or B for the given task based on capabilities
    alone.  Model identities are never included.
    """
    desc_a = _describe_model(a, task)
    desc_b = _describe_model(b, task)
    return (
        f"You are evaluating two AI models for the task: '{task.value}'.\n"
        f"Their capabilities (IDs redacted) are:\n\n"
        f"Model A:\n{desc_a}\n\n"
        f"Model B:\n{desc_b}\n\n"
        f"Which model is BETTER suited for '{task.value}'? "
        f"Reply with ONLY the single letter A or B. No explanation."
    )


def _call_judge(prompt: str) -> str | None:
    """POST to Granite on :13305 and return the raw reply text, or None on failure."""
    payload = json.dumps(
        {
            "model": _JUDGE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": _JUDGE_MAX_TOKENS,
            "temperature": _JUDGE_TEMPERATURE,
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310
        _JUDGE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_JUDGE_TIMEOUT_S) as resp:  # noqa: S310
            body = json.loads(resp.read())
            return body["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
        logger.debug("LM-judge call failed (%s); falling back to proxy", exc)
        return None


def _parse_verdict(text: str | None, a: ModelEntry, b: ModelEntry) -> ModelEntry | None:
    """Extract A/B verdict from judge text.

    Accepts the first ASCII letter A or B (case-insensitive) anywhere in the
    first token of the response.  Returns None if the response is ambiguous.
    """
    if not text:
        return None
    first = text.strip().split()[0].upper() if text.strip() else ""
    if first.startswith("A"):
        return a
    if first.startswith("B"):
        return b
    return None  # ambiguous — caller falls back to proxy


def granite_prefer(a: ModelEntry, b: ModelEntry, task: Task) -> ModelEntry:
    """LLM-judge preference function using Granite-4.1-8B-GGUF on :13305.

    Drop-in replacement for ``_default_preference`` in
    :func:`~cohezion.inference.model_tournament.model_tournament`.

    Behaviour:
    - Blind evaluation: judge sees capability metadata, NOT model IDs.
    - temperature=0 for replay safety.
    - Fail-soft: returns ``_default_preference(a, b, task)`` on any error,
      timeout, or ambiguous verdict.  The tournament never raises.

    Args:
        a: First candidate model.
        b: Second candidate model.
        task: The task the models are competing on.

    Returns:
        The preferred :class:`~cohezion.inference.registry.ModelEntry`.
    """
    prompt = _build_judge_prompt(a, b, task)
    raw = _call_judge(prompt)
    preferred = _parse_verdict(raw, a, b)
    if preferred is None:
        logger.debug(
            "granite_prefer: ambiguous verdict '%s'; falling back to deterministic proxy",
            raw,
        )
        return _default_preference(a, b, task)
    return preferred


def is_judge_available() -> bool:
    """Return True when the :13305 judge endpoint is reachable.

    OOM-safe probe: sends zero inference tokens.  Used by tests that want to
    conditionally skip the live-judge path.
    """
    try:
        with urllib.request.urlopen(
            "http://localhost:13305/v1/models",
            timeout=2,
        ) as resp:
            return resp.status == 200
    except Exception:
        return False
